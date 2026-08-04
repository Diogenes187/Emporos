"""Relational personal injury classification and signed natural healing."""
from dataclasses import dataclass
import secrets

import psycopg


PHYSICAL = (
    "characteristic.strength",
    "characteristic.dexterity",
    "characteristic.endurance",
)


@dataclass(frozen=True)
class NaturalHealingResult:
    command_public_id: str
    actor_public_id: str
    campaign_day_number: int
    lifestyle: str
    injury_status_before: str
    endurance_modifier: int
    healing_die_result: int | None
    signed_points: int
    allocations: tuple[tuple[str, int, int, int], ...]
    unapplied_point_magnitude: int
    injury_status_after: str
    replayed: bool


@dataclass(frozen=True)
class NaturalHealingDeterminationResult:
    command_public_id: str
    actor_public_id: str
    campaign_day_number: int
    lifestyle: str
    injury_status: str
    endurance_modifier: int
    healing_die_result: int | None
    signed_points: int
    applied_healing_command_public_id: str | None
    replayed: bool


class _FixedDie:
    def __init__(self,value):self.value=value
    def randint(self,minimum,maximum):return self.value


def _injury_status(states):
    damaged = sum(current < maximum for current, maximum in states.values())
    if damaged == 3:
        return "seriously_wounded"
    if damaged:
        return "wounded"
    return "uninjured"


def _load(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.campaign_day_number,
                  receipt.lifestyle,receipt.injury_status_before,
                  receipt.endurance_modifier,receipt.healing_die_result,
                  receipt.signed_points,
                  receipt.unapplied_point_magnitude,
                  receipt.injury_status_after
           FROM cmd_personal_natural_healing_receipt receipt
           JOIN actor_actor actor USING (actor_id)
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    allocations = tuple(connection.execute(
        """SELECT rule.rule_code,allocation.point_change,
                  allocation.value_before,allocation.value_after
           FROM cmd_personal_natural_healing_allocation allocation
           JOIN rule_rule rule
             ON rule.rule_id=allocation.characteristic_rule_id
           WHERE allocation.command_id=%s
           ORDER BY allocation.allocation_order""",
        (command_id,)).fetchall())
    return NaturalHealingResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], allocations, row[7], row[8], replayed)


def resolve_personal_natural_healing_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, lifestyle: str,
    allocations: tuple[tuple[str, int], ...], random_source=None,
) -> NaturalHealingResult:
    """Resolve one actor's signed natural healing for the current campaign day."""
    if lifestyle not in {"full_rest", "active"}:
        raise ValueError("Lifestyle must be full_rest or active")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_personal_natural_healing", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor.actor_id,actor.campaign_id,clock.day_number,
                      actor.concurrency_version
               FROM actor_actor actor
               JOIN camp_clock clock ON clock.campaign_id=actor.campaign_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor,clock""",
            (actor_public_id, initiator_reference)).fetchone()
        if actor is None:
            raise ValueError("Actor is not controlled by the initiator")
        if connection.execute(
            """SELECT 1 FROM cmd_personal_natural_healing_receipt
               WHERE actor_id=%s AND campaign_day_number=%s""",
            (actor[0], actor[2])).fetchone():
            raise ValueError(
                "Natural healing is already resolved for this campaign day")
        rows = connection.execute(
            """SELECT rule.rule_code,state.current_value,state.maximum_value,
                      rule.rule_id
               FROM actor_characteristic state
               JOIN rule_rule rule
                 ON rule.rule_id=state.characteristic_rule_id
               WHERE state.actor_id=%s AND rule.rule_code=ANY(%s)
               FOR UPDATE OF state""",
            (actor[0], list(PHYSICAL))).fetchall()
        states = {
            code: (current, maximum, rule_id)
            for code, current, maximum, rule_id in rows
        }
        if set(states) != set(PHYSICAL):
            raise ValueError("Actor lacks complete physical characteristics")
        before = _injury_status({
            code: values[:2] for code, values in states.items()})
        if before == "uninjured":
            raise ValueError("Uninjured actor cannot resolve natural healing")
        endurance = states["characteristic.endurance"]
        endurance_modifier = connection.execute(
            """SELECT modifier FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (endurance[2], endurance[0])).fetchone()[0]
        die = None
        if before == "seriously_wounded":
            if lifestyle != "full_rest":
                raise ValueError("Seriously wounded natural healing requires rest")
            signed_points = endurance_modifier
        elif lifestyle == "full_rest":
            die = rng.randint(1, 6)
            signed_points = die + endurance_modifier
        else:
            signed_points = 1 + endurance_modifier
        allocation_map = dict(allocations)
        if len(allocation_map) != len(allocations):
            raise ValueError("A characteristic may be allocated only once")
        if not set(allocation_map) <= set(PHYSICAL):
            raise ValueError("Natural healing uses only physical characteristics")
        if any(amount <= 0 for amount in allocation_map.values()):
            raise ValueError("Allocation magnitudes must be positive")
        capacity = {
            code: (
                maximum - current if signed_points > 0 else current
            )
            for code, (current, maximum, _) in states.items()
        }
        applicable = min(abs(signed_points), sum(capacity.values()))
        if sum(allocation_map.values()) != applicable:
            raise ValueError(
                "Allocations must equal the applicable signed point magnitude")
        if any(allocation_map.get(code, 0) > capacity[code] for code in PHYSICAL):
            raise ValueError("Allocation exceeds a characteristic boundary")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_natural_healing',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        if die is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',1,6,%s)""", (command_id, die))
        provisional = {
            code: [current, maximum, rule_id]
            for code, (current, maximum, rule_id) in states.items()
        }
        results = []
        sign = 1 if signed_points > 0 else -1
        for order, (code, magnitude) in enumerate(allocations, 1):
            current, maximum, rule_id = provisional[code]
            change = sign * magnitude
            after_value = current + change
            provisional[code][0] = after_value
            results.append((code, change, current, after_value, rule_id))
        after = _injury_status({
            code: values[:2] for code, values in provisional.items()})
        connection.execute(
            """INSERT INTO cmd_personal_natural_healing_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, actor[0], actor[1], actor[2], lifestyle, before,
             endurance[0], endurance_modifier, die, signed_points,
             applicable, abs(signed_points)-applicable, after,
             actor[3], actor[3]+1))
        for order, (code, change, current, after_value, rule_id) in enumerate(
            results, 1
        ):
            connection.execute(
                """UPDATE actor_characteristic SET current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (after_value, actor[0], rule_id))
            connection.execute(
                """INSERT INTO cmd_personal_natural_healing_allocation
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (command_id, order, rule_id, change, current, after_value))
        connection.execute(
            """UPDATE enc_personal_combatant combatant
               SET seriously_wounded=%s,
                   minor_actions_remaining=CASE
                     WHEN %s THEN 0
                     ELSE minor_actions_remaining
                   END
               FROM enc_personal_combat combat
               WHERE combat.encounter_id=combatant.encounter_id
                 AND combat.combat_status='active'
                 AND combatant.actor_id=%s""",
            (after == "seriously_wounded",
             after == "seriously_wounded", actor[0]))
        connection.execute(
            """UPDATE actor_actor
               SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""", (actor[0],))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load(connection, command_id, public_id, False)


def _load_natural_healing_determination(connection,command_id,public_id,replayed):
    row=connection.execute(
        """SELECT actor.public_id,result.campaign_day_number,result.lifestyle,
                  result.injury_status,result.endurance_modifier,
                  result.healing_die_result,result.signed_points,healing.public_id
           FROM cmd_personal_natural_healing_determination result
           JOIN actor_actor actor USING(actor_id)
           LEFT JOIN cmd_personal_natural_healing_determination_application applied
             ON applied.determination_command_id=result.command_id
           LEFT JOIN cmd_command healing ON healing.command_id=applied.healing_command_id
           WHERE result.command_id=%s""",(command_id,)).fetchone()
    return NaturalHealingDeterminationResult(
        str(public_id),str(row[0]),row[1],row[2],row[3],row[4],row[5],row[6],
        str(row[7]) if row[7] else None,replayed)


def determine_personal_natural_healing_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, lifestyle: str,
    random_source=None,
):
    if lifestyle not in {"full_rest","active"}:raise ValueError("Lifestyle must be full_rest or active")
    rng=random_source or secrets.SystemRandom()
    with connection.transaction():
        existing=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
        if existing:
            if existing[2:]!=("determine_personal_natural_healing","completed"):raise RuntimeError("Idempotency key belongs to another command")
            return _load_natural_healing_determination(connection,existing[0],existing[1],True)
        actor=connection.execute("""SELECT actor.actor_id,actor.campaign_id,clock.day_number,actor.concurrency_version FROM actor_actor actor JOIN camp_clock clock ON clock.campaign_id=actor.campaign_id WHERE actor.public_id=%s AND actor.controller_reference=%s FOR UPDATE OF actor,clock""",(actor_public_id,initiator_reference)).fetchone()
        if actor is None:raise ValueError("Actor is not controlled by the initiator")
        if connection.execute("SELECT 1 FROM cmd_personal_natural_healing_receipt WHERE actor_id=%s AND campaign_day_number=%s",(actor[0],actor[2])).fetchone():raise ValueError("Natural healing is already resolved for this campaign day")
        rows=connection.execute("""SELECT rule.rule_code,state.current_value,state.maximum_value,rule.rule_id FROM actor_characteristic state JOIN rule_rule rule ON rule.rule_id=state.characteristic_rule_id WHERE state.actor_id=%s AND rule.rule_code=ANY(%s) FOR UPDATE OF state""",(actor[0],list(PHYSICAL))).fetchall()
        states={code:(current,maximum,rule_id) for code,current,maximum,rule_id in rows}
        if set(states)!=set(PHYSICAL):raise ValueError("Actor lacks complete physical characteristics")
        status=_injury_status({code:value[:2] for code,value in states.items()})
        if status=="uninjured":raise ValueError("Uninjured actor cannot resolve natural healing")
        if status=="seriously_wounded" and lifestyle!="full_rest":raise ValueError("Seriously wounded natural healing requires rest")
        endurance=states["characteristic.endurance"]
        modifier=connection.execute("""SELECT modifier FROM rule_characteristic_modifier_band WHERE (characteristic_rule_id IS NULL OR characteristic_rule_id=%s) AND score_range @> %s::integer ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",(endurance[2],endurance[0])).fetchone()[0]
        die=rng.randint(1,6) if status=="wounded" and lifestyle=="full_rest" else None
        points=modifier if status=="seriously_wounded" else (die+modifier if die is not None else 1+modifier)
        command_id,public_id=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES ('determine_personal_natural_healing',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
        connection.execute("INSERT INTO cmd_personal_natural_healing_determination VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(command_id,actor[1],actor[0],actor[2],actor[3],lifestyle,status,modifier,die,points))
        if die is not None:connection.execute("INSERT INTO cmd_random_draw(command_id,draw_group,draw_order,die_sides,result) VALUES (%s,'task',1,6,%s)",(command_id,die))
        connection.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES (%s,1,'personal_natural_healing_determined')",(command_id,))
        connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
        return _load_natural_healing_determination(connection,command_id,public_id,False)


def apply_determined_personal_natural_healing_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, determination_command_public_id: str,
    allocations: tuple[tuple[str,int],...],
):
    with connection.transaction():
        row=connection.execute("""SELECT result.command_id,actor.public_id,result.lifestyle,result.healing_die_result,result.actor_version,actor.concurrency_version,result.campaign_day_number,clock.day_number FROM cmd_personal_natural_healing_determination result JOIN cmd_command command ON command.command_id=result.command_id JOIN actor_actor actor USING(actor_id) JOIN camp_clock clock ON clock.campaign_id=result.campaign_id WHERE command.public_id=%s AND command.initiator_reference=%s FOR UPDATE OF result""",(determination_command_public_id,initiator_reference)).fetchone()
        if row is None:raise ValueError("Natural healing determination does not exist")
        applied=connection.execute("SELECT healing_command_id FROM cmd_personal_natural_healing_determination_application WHERE determination_command_id=%s",(row[0],)).fetchone()
        if applied:
            existing=connection.execute("SELECT command_id,public_id FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s AND command_type='resolve_personal_natural_healing' AND command_status='completed'",(initiator_reference,idempotency_key)).fetchone()
            if existing and existing[0]==applied[0]:return _load(connection,existing[0],existing[1],True)
            raise ValueError("Natural healing determination has already been applied")
        if row[4]!=row[5] or row[6]!=row[7]:raise ValueError("Natural healing determination is stale because actor state or campaign day changed")
        result=resolve_personal_natural_healing_command(connection,initiator_reference=initiator_reference,idempotency_key=idempotency_key,actor_public_id=str(row[1]),lifestyle=row[2],allocations=allocations,random_source=_FixedDie(row[3]) if row[3] is not None else None)
        healing_id=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(result.command_public_id,)).fetchone()[0]
        connection.execute("INSERT INTO cmd_personal_natural_healing_determination_application VALUES (%s,%s)",(row[0],healing_id))
        return result
