"""Audited CE-COMBAT-014 personal medical treatment."""
from dataclasses import dataclass
import secrets

import psycopg

from engine.injury_runtime import PHYSICAL, _injury_status


@dataclass(frozen=True)
class MedicalTreatmentResult:
    command_public_id: str
    procedure_code: str
    patient_actor_public_id: str
    doctor_actor_public_id: str
    campaign_day_number: int
    dice: tuple[int, ...]
    effect: int | None
    signed_points: int
    allocations: tuple[tuple[str, int, int, int], ...]
    injury_status_before: str
    injury_status_after: str
    replayed: bool


@dataclass(frozen=True)
class FirstAidDeterminationResult:
    command_public_id: str
    patient_actor_public_id: str
    doctor_actor_public_id: str
    damage_instance_public_id: str
    dice: tuple[int, int]
    check_total: int
    effect: int
    effectiveness_tier: str
    effect_multiplier: int
    available_points: int
    applied_treatment_command_public_id: str | None
    replayed: bool


def _load_first_aid_determination(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT patient.public_id,doctor.public_id,damage.public_id,
                  result.die_one,result.die_two,result.check_total,result.effect,
                  result.effectiveness_tier,result.effect_multiplier,
                  result.available_points,treatment.public_id
           FROM cmd_personal_first_aid_determination result
           JOIN actor_actor patient ON patient.actor_id=result.patient_actor_id
           JOIN actor_actor doctor ON doctor.actor_id=result.doctor_actor_id
           JOIN health_damage_instance damage
             ON damage.damage_instance_id=result.damage_instance_id
           LEFT JOIN cmd_personal_first_aid_determination_application applied
             ON applied.determination_command_id=result.command_id
           LEFT JOIN cmd_command treatment
             ON treatment.command_id=applied.treatment_command_id
           WHERE result.command_id=%s""", (command_id,)).fetchone()
    return FirstAidDeterminationResult(
        str(public_id), str(row[0]), str(row[1]), str(row[2]),
        (row[3], row[4]), row[5], row[6], row[7], row[8], row[9],
        str(row[10]) if row[10] else None, replayed)


class _FixedDice:
    def __init__(self, dice):
        self._dice = iter(dice)

    def randint(self, minimum, maximum):
        return next(self._dice)


def _load(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT receipt.procedure_code,patient.public_id,doctor.public_id,
                  receipt.campaign_day_number,receipt.effect,
                  receipt.signed_points,receipt.injury_status_before,
                  receipt.injury_status_after
           FROM cmd_personal_medical_treatment_receipt receipt
           JOIN actor_actor patient
             ON patient.actor_id=receipt.patient_actor_id
           JOIN actor_actor doctor
             ON doctor.actor_id=receipt.doctor_actor_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    dice = tuple(item[0] for item in connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group='task'
           ORDER BY draw_order""", (command_id,)).fetchall())
    allocations = tuple(connection.execute(
        """SELECT rule.rule_code,allocation.point_change,
                  allocation.value_before,allocation.value_after
           FROM cmd_personal_medical_treatment_allocation allocation
           JOIN rule_rule rule
             ON rule.rule_id=allocation.characteristic_rule_id
           WHERE allocation.command_id=%s
           ORDER BY allocation.allocation_order""",
        (command_id,)).fetchall())
    return MedicalTreatmentResult(
        str(public_id), row[0], str(row[1]), str(row[2]), row[3],
        dice, row[4], row[5], allocations, row[6], row[7], replayed)


def _context(connection, patient_public, doctor_public, initiator):
    row = connection.execute(
        """SELECT patient.actor_id,patient.campaign_id,
                  patient.concurrency_version,doctor.actor_id,
                  clock.day_number,clock.second_of_day,
                  COALESCE(doctor_skill.skill_level,
                           medicine.untrained_modifier),
                  patient_species.species_rule_id,
                  doctor_species.species_rule_id
           FROM actor_actor patient
           JOIN actor_actor doctor
             ON doctor.public_id=%s
            AND doctor.campaign_id=patient.campaign_id
           JOIN camp_clock clock
             ON clock.campaign_id=patient.campaign_id
           JOIN rule_rule medicine_rule
             ON medicine_rule.rule_code='skill.medicine'
           JOIN rule_skill medicine
             ON medicine.rule_id=medicine_rule.rule_id
           LEFT JOIN actor_skill doctor_skill
             ON doctor_skill.actor_id=doctor.actor_id
            AND doctor_skill.skill_rule_id=medicine_rule.rule_id
           LEFT JOIN actor_current_species patient_species
             ON patient_species.actor_id=patient.actor_id
           LEFT JOIN actor_current_species doctor_species
             ON doctor_species.actor_id=doctor.actor_id
           WHERE patient.public_id=%s
             AND patient.controller_reference=%s
           FOR UPDATE OF patient,doctor,clock""",
        (doctor_public, patient_public, initiator)).fetchone()
    if row is None:
        raise ValueError("Treatment actors are not legal in this campaign")
    states = {
        code: [current, maximum, rule_id]
        for code, current, maximum, rule_id in connection.execute(
            """SELECT rule.rule_code,state.current_value,state.maximum_value,
                      rule.rule_id
               FROM actor_characteristic state
               JOIN rule_rule rule
                 ON rule.rule_id=state.characteristic_rule_id
               WHERE state.actor_id=%s AND rule.rule_code=ANY(%s)
               FOR UPDATE OF state""",
            (row[0], list(PHYSICAL))).fetchall()
    }
    if set(states) != set(PHYSICAL):
        raise ValueError("Patient lacks complete physical characteristics")
    return row, states


def _facility(connection, public_id, campaign_id):
    if public_id is None:
        return None
    row = connection.execute(
        """SELECT medical_facility_id FROM health_medical_facility
           WHERE public_id=%s AND campaign_id=%s AND active""",
        (public_id, campaign_id)).fetchone()
    if row is None:
        raise ValueError("Active hospital or sickbay does not exist")
    return row[0]


def _allocate(states, signed_points, allocations, *, even=False):
    allocation_map = dict(allocations)
    if len(allocation_map) != len(allocations):
        raise ValueError("A characteristic may be allocated only once")
    if not set(allocation_map) <= set(PHYSICAL):
        raise ValueError("Treatment uses only physical characteristics")
    if any(value <= 0 for value in allocation_map.values()):
        raise ValueError("Allocation magnitudes must be positive")
    capacities = {
        code: (maximum-current if signed_points>0 else current)
        for code, (current, maximum, _) in states.items()
    }
    applicable = min(abs(signed_points), sum(capacities.values()))
    if sum(allocation_map.values()) != applicable:
        raise ValueError("Allocations must equal applicable treatment points")
    if any(allocation_map.get(code, 0)>capacities[code] for code in PHYSICAL):
        raise ValueError("Allocation exceeds a characteristic boundary")
    damaged = [code for code in PHYSICAL if states[code][0]<states[code][1]]
    if even and applicable:
        values = [allocation_map.get(code, 0) for code in damaged]
        uncapped = [
            allocation_map.get(code, 0) for code in damaged
            if capacities[code] >= max(values, default=0)
        ]
        if uncapped and max(uncapped)-min(uncapped)>1:
            raise ValueError("Medical Care must be divided evenly")
    sign = 1 if signed_points>0 else -1
    results = []
    for code, magnitude in allocations:
        before = states[code][0]
        change = sign*magnitude
        after = before+change
        states[code][0] = after
        results.append((code, change, before, after, states[code][2]))
    return applicable, results


def _commit(
    connection, *, command_type, procedure, initiator, key,
    patient_public, doctor_public, context, states, dice, effect,
    signed_points, allocations, facility_id=None, endurance_modifier=None,
    self_modifier=0, cross_modifier=0, link_sql=None, link_values=(),
    even=False,
):
    before = _injury_status({
        code: values[:2] for code, values in states.items()})
    applicable, results = _allocate(
        states, signed_points, allocations, even=even)
    after = _injury_status({
        code: values[:2] for code, values in states.items()})
    command_id, public_id = connection.execute(
        """INSERT INTO cmd_command
           (command_type,initiator_reference,idempotency_key)
           VALUES (%s,%s,%s) RETURNING command_id,public_id""",
        (command_type, initiator, key)).fetchone()
    for order, die in enumerate(dice, 1):
        connection.execute(
            """INSERT INTO cmd_random_draw
               (command_id,draw_group,draw_order,die_sides,result)
               VALUES (%s,'task',%s,6,%s)""", (command_id, order, die))
    total = (
        sum(dice)+context[6]+self_modifier+cross_modifier
        if dice else None)
    connection.execute(
        """INSERT INTO cmd_personal_medical_treatment_receipt
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                   %s,%s,%s,%s,%s,%s)""",
        (command_id, procedure, context[0], context[3], facility_id,
         context[4], context[5], before, context[6], endurance_modifier,
         self_modifier, cross_modifier, total, 8 if dice else None,
         effect, total>=8 if dice else None, signed_points, applicable,
         abs(signed_points)-applicable, after, context[2], context[2]+1))
    if link_sql:
        connection.execute(link_sql, (command_id, *link_values))
    for order, (_, change, before_value, after_value, rule_id) in enumerate(
        results, 1
    ):
        connection.execute(
            """UPDATE actor_characteristic SET current_value=%s
               WHERE actor_id=%s AND characteristic_rule_id=%s""",
            (after_value, context[0], rule_id))
        connection.execute(
            """INSERT INTO cmd_personal_medical_treatment_allocation
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, order, rule_id, change, before_value, after_value))
    connection.execute(
        """UPDATE actor_actor SET concurrency_version=concurrency_version+1
           WHERE actor_id=%s""", (context[0],))
    connection.execute(
        """UPDATE enc_personal_combatant combatant
           SET seriously_wounded=%s,
               minor_actions_remaining=CASE WHEN %s THEN 0
                                            ELSE minor_actions_remaining END
           FROM enc_personal_combat combat
           WHERE combat.encounter_id=combatant.encounter_id
             AND combat.combat_status='active'
             AND combatant.actor_id=%s""",
        (after=="seriously_wounded", after=="seriously_wounded", context[0]))
    connection.execute(
        """UPDATE cmd_command SET command_status='completed',
                  completed_at=clock_timestamp() WHERE command_id=%s""",
        (command_id,))
    return _load(connection, command_id, public_id, False)


def _begin(connection, initiator, key, command_type):
    existing = connection.execute(
        """SELECT command_id,public_id,command_type,command_status
           FROM cmd_command WHERE initiator_reference=%s
             AND idempotency_key=%s FOR UPDATE""",
        (initiator, key)).fetchone()
    if existing:
        if existing[2:] != (command_type, "completed"):
            raise RuntimeError("Idempotency key belongs to another command")
        return _load(connection, existing[0], existing[1], True)
    return None


def apply_personal_first_aid_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, patient_actor_public_id: str,
    doctor_actor_public_id: str, damage_instance_public_id: str,
    allocations: tuple[tuple[str, int], ...], random_source=None,
):
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        replay = _begin(connection, initiator_reference, idempotency_key,
                        "apply_personal_first_aid")
        if replay:
            return replay
        context, states = _context(
            connection, patient_actor_public_id, doctor_actor_public_id,
            initiator_reference)
        damage = connection.execute(
            """SELECT damage_instance_id,target_actor_id,
                      applied_campaign_day,applied_campaign_second
               FROM health_damage_instance WHERE public_id=%s
                 AND allocation_status='applied' FOR UPDATE""",
            (damage_instance_public_id,)).fetchone()
        if damage is None or damage[1] != context[0]:
            raise ValueError("Applied injury does not belong to patient")
        elapsed = (
            (context[4]-damage[2])*86400+context[5]-damage[3])
        if elapsed < 0:
            raise ValueError("Campaign clock precedes the injury")
        if elapsed<=300:
            tier,multiplier="full",2
        elif elapsed<=3600:
            tier,multiplier="late",1
        else:
            tier,multiplier="expired",0
        dice=(rng.randint(1,6),rng.randint(1,6))
        self_mod=-2 if context[0]==context[3] else 0
        cross=-2 if (
            context[7] is not None and context[8] is not None
            and context[7]!=context[8]) else 0
        total=sum(dice)+context[6]+self_mod+cross
        effect=total-8
        points=max(0,effect)*multiplier
        return _commit(
            connection,command_type="apply_personal_first_aid",
            procedure="first_aid",initiator=initiator_reference,
            key=idempotency_key,patient_public=patient_actor_public_id,
            doctor_public=doctor_actor_public_id,context=context,states=states,
            dice=dice,effect=effect,signed_points=points,
            allocations=allocations,self_modifier=self_mod,
            cross_modifier=cross,link_sql=
            """INSERT INTO cmd_personal_first_aid_link
               VALUES (%s,%s,%s,%s,%s)""",
            link_values=(damage[0],elapsed,tier,multiplier))


def determine_personal_first_aid_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, patient_actor_public_id: str,
    doctor_actor_public_id: str, damage_instance_public_id: str,
    random_source=None,
):
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("determine_personal_first_aid", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_first_aid_determination(
                connection, existing[0], existing[1], True)
        context, _ = _context(
            connection, patient_actor_public_id, doctor_actor_public_id,
            initiator_reference)
        damage = connection.execute(
            """SELECT damage_instance_id,target_actor_id,
                      applied_campaign_day,applied_campaign_second
               FROM health_damage_instance WHERE public_id=%s
                 AND allocation_status='applied' FOR UPDATE""",
            (damage_instance_public_id,)).fetchone()
        if damage is None or damage[1] != context[0]:
            raise ValueError("Applied injury does not belong to patient")
        if connection.execute(
            """SELECT 1 FROM cmd_personal_first_aid_link
               WHERE damage_instance_id=%s""", (damage[0],)).fetchone():
            raise ValueError("First Aid has already been applied to this injury")
        elapsed = (context[4]-damage[2])*86400+context[5]-damage[3]
        if elapsed < 0:
            raise ValueError("Campaign clock precedes the injury")
        if elapsed <= 300:
            tier, multiplier = "full", 2
        elif elapsed <= 3600:
            tier, multiplier = "late", 1
        else:
            tier, multiplier = "expired", 0
        dice = (rng.randint(1, 6), rng.randint(1, 6))
        self_mod = -2 if context[0] == context[3] else 0
        cross = -2 if (
            context[7] is not None and context[8] is not None
            and context[7] != context[8]) else 0
        total = sum(dice)+context[6]+self_mod+cross
        effect = total-8
        points = max(0, effect)*multiplier
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_personal_first_aid',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """INSERT INTO cmd_personal_first_aid_determination
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,8,%s,%s,%s,%s,%s)""",
            (command_id, context[1], context[0], context[3], damage[0],
             context[4], context[5], context[2], context[6], self_mod, cross,
             dice[0], dice[1], total, effect, elapsed, tier, multiplier, points))
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,6,%s)""", (command_id, order, die))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_first_aid_determined')""",
            (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_first_aid_determination(
            connection, command_id, public_id, False)


def apply_determined_personal_first_aid_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, determination_command_public_id: str,
    allocations: tuple[tuple[str, int], ...],
):
    with connection.transaction():
        determination = connection.execute(
            """SELECT result.command_id,patient.public_id,doctor.public_id,
                      damage.public_id,result.die_one,result.die_two,
                      result.patient_version,patient.concurrency_version,
                      result.campaign_day_number,result.campaign_second_of_day,
                      clock.day_number,clock.second_of_day
               FROM cmd_personal_first_aid_determination result
               JOIN cmd_command command ON command.command_id=result.command_id
               JOIN actor_actor patient ON patient.actor_id=result.patient_actor_id
               JOIN actor_actor doctor ON doctor.actor_id=result.doctor_actor_id
               JOIN health_damage_instance damage
                 ON damage.damage_instance_id=result.damage_instance_id
               JOIN camp_clock clock ON clock.campaign_id=result.campaign_id
               WHERE command.public_id=%s
                 AND command.initiator_reference=%s FOR UPDATE OF result""",
            (determination_command_public_id, initiator_reference)).fetchone()
        if determination is None:
            raise ValueError("First Aid determination does not exist")
        applied = connection.execute(
            """SELECT treatment.public_id
               FROM cmd_personal_first_aid_determination_application link
               JOIN cmd_command treatment
                 ON treatment.command_id=link.treatment_command_id
               WHERE link.determination_command_id=%s""",
            (determination[0],)).fetchone()
        if applied:
            existing = connection.execute(
                """SELECT command_id,public_id FROM cmd_command
                   WHERE initiator_reference=%s AND idempotency_key=%s
                     AND command_type='apply_personal_first_aid'
                     AND command_status='completed'""",
                (initiator_reference, idempotency_key)).fetchone()
            if existing and str(existing[1]) == str(applied[0]):
                return _load(connection, existing[0], existing[1], True)
            raise ValueError("First Aid determination has already been applied")
        if determination[6] != determination[7] or (
            determination[8], determination[9]
        ) != (determination[10], determination[11]):
            raise ValueError(
                "First Aid determination is stale because patient state or "
                "campaign time changed")
        result = apply_personal_first_aid_command(
            connection, initiator_reference=initiator_reference,
            idempotency_key=idempotency_key,
            patient_actor_public_id=str(determination[1]),
            doctor_actor_public_id=str(determination[2]),
            damage_instance_public_id=str(determination[3]),
            allocations=allocations,
            random_source=_FixedDice((determination[4], determination[5])))
        treatment_id = connection.execute(
            "SELECT command_id FROM cmd_command WHERE public_id=%s",
            (result.command_public_id,)).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_personal_first_aid_determination_application
               VALUES (%s,%s)""", (determination[0], treatment_id))
        return result


def resolve_personal_surgery_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, patient_actor_public_id: str,
    doctor_actor_public_id: str, first_aid_command_public_id: str,
    medical_facility_public_id: str,
    allocations: tuple[tuple[str, int], ...], random_source=None,
):
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        replay = _begin(connection, initiator_reference, idempotency_key,
                        "resolve_personal_surgery")
        if replay:
            return replay
        context, states = _context(
            connection, patient_actor_public_id, doctor_actor_public_id,
            initiator_reference)
        if _injury_status({
            code:value[:2] for code,value in states.items()
        })!="seriously_wounded":
            raise ValueError("Surgery requires a seriously wounded patient")
        first_aid = connection.execute(
            """SELECT command.command_id,receipt.patient_actor_id
               FROM cmd_command command
               JOIN cmd_personal_medical_treatment_receipt receipt
                 ON receipt.command_id=command.command_id
               JOIN cmd_personal_first_aid_link link
                 ON link.command_id=command.command_id
               WHERE command.public_id=%s""",
            (first_aid_command_public_id,)).fetchone()
        if first_aid is None or first_aid[1]!=context[0]:
            raise ValueError("Surgery requires patient First Aid")
        facility=_facility(
            connection,medical_facility_public_id,context[1])
        dice=(rng.randint(1,6),rng.randint(1,6))
        self_mod=-4 if context[0]==context[3] else 0
        cross=-2 if (
            context[7] is not None and context[8] is not None
            and context[7]!=context[8]) else 0
        total=sum(dice)+context[6]+self_mod+cross
        effect=total-8
        points=2*effect if effect>0 else effect
        return _commit(
            connection,command_type="resolve_personal_surgery",
            procedure="surgery",initiator=initiator_reference,
            key=idempotency_key,patient_public=patient_actor_public_id,
            doctor_public=doctor_actor_public_id,context=context,states=states,
            dice=dice,effect=effect,signed_points=points,
            allocations=allocations,facility_id=facility,
            self_modifier=self_mod,cross_modifier=cross,
            link_sql="""INSERT INTO cmd_personal_surgery_link
                        VALUES (%s,%s)""",
            link_values=(first_aid[0],))


def apply_personal_medical_care_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, patient_actor_public_id: str,
    doctor_actor_public_id: str, medical_facility_public_id: str,
    allocations: tuple[tuple[str, int], ...],
):
    with connection.transaction():
        replay = _begin(connection, initiator_reference, idempotency_key,
                        "apply_personal_medical_care")
        if replay:
            return replay
        context, states = _context(
            connection, patient_actor_public_id, doctor_actor_public_id,
            initiator_reference)
        if connection.execute(
            """SELECT 1 FROM cmd_personal_medical_treatment_receipt
               WHERE procedure_code='medical_care'
                 AND patient_actor_id=%s AND campaign_day_number=%s""",
            (context[0],context[4])).fetchone():
            raise ValueError("Medical Care is already applied this campaign day")
        status=_injury_status({
            code:value[:2] for code,value in states.items()})
        if status=="seriously_wounded":
            raise ValueError(
                "Surgery must restore a characteristic before Medical Care")
        endurance=states["characteristic.endurance"]
        end_mod=connection.execute(
            """SELECT modifier FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (endurance[2],endurance[0])).fetchone()[0]
        points=max(0,2+end_mod+context[6])
        damaged=sum(
            value[0]<value[1] for value in states.values())
        base=points//damaged if damaged else 0
        remainder=points%damaged if damaged else 0
        facility=_facility(
            connection,medical_facility_public_id,context[1])
        return _commit(
            connection,command_type="apply_personal_medical_care",
            procedure="medical_care",initiator=initiator_reference,
            key=idempotency_key,patient_public=patient_actor_public_id,
            doctor_public=doctor_actor_public_id,context=context,states=states,
            dice=(),effect=None,signed_points=points,
            allocations=allocations,facility_id=facility,
            endurance_modifier=end_mod,even=True,
            link_sql="""INSERT INTO cmd_personal_medical_care_link
                        VALUES (%s,true,%s,%s)""",
            link_values=(base,remainder))
