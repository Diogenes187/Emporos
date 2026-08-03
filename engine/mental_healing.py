"""Campaign-safe daily healing for Intelligence and Education."""
from dataclasses import dataclass

import psycopg


MENTAL = (
    "characteristic.intelligence",
    "characteristic.education",
)


@dataclass(frozen=True)
class MentalHealingResult:
    command_public_id: str
    actor_public_id: str
    campaign_day_number: int
    allocations: tuple[tuple[str, int, int, int], ...]
    replayed: bool


def _load(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.campaign_day_number
           FROM cmd_personal_mental_healing_receipt receipt
           JOIN actor_actor actor USING (actor_id)
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    allocations = tuple(connection.execute(
        """SELECT rule.rule_code,allocation.point_change,
                  allocation.value_before,allocation.value_after
           FROM cmd_personal_mental_healing_allocation allocation
           JOIN rule_rule rule
             ON rule.rule_id=allocation.characteristic_rule_id
           WHERE allocation.command_id=%s
           ORDER BY allocation.allocation_order""",
        (command_id,)).fetchall())
    return MentalHealingResult(
        str(public_id), str(row[0]), row[1], allocations, replayed)


def resolve_personal_mental_healing_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
) -> MentalHealingResult:
    """Restore one point to each damaged Intelligence/Education per day."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_personal_mental_healing", "completed"
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
            """SELECT 1 FROM cmd_personal_mental_healing_receipt
               WHERE actor_id=%s AND campaign_day_number=%s""",
            (actor[0], actor[2])).fetchone():
            raise ValueError(
                "Mental healing is already resolved this campaign day")
        rows = connection.execute(
            """SELECT rule.rule_code,state.current_value,state.maximum_value,
                      rule.rule_id
               FROM actor_characteristic state
               JOIN rule_rule rule
                 ON rule.rule_id=state.characteristic_rule_id
               WHERE state.actor_id=%s AND rule.rule_code=ANY(%s)
               FOR UPDATE OF state""",
            (actor[0], list(MENTAL))).fetchall()
        states = {row[0]: row[1:] for row in rows}
        if set(states) != set(MENTAL):
            raise ValueError(
                "Actor lacks Intelligence or Education characteristic state")
        damaged = [
            (code, *states[code])
            for code in MENTAL if states[code][0] < states[code][1]
        ]
        if not damaged:
            raise ValueError("Actor has no damaged mental characteristic")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_mental_healing',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """INSERT INTO cmd_personal_mental_healing_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, actor[0], actor[1], actor[2], len(damaged),
             len(damaged), actor[3], actor[3]+1))
        for order, (code, before, _maximum, rule_id) in enumerate(damaged, 1):
            after = before+1
            connection.execute(
                """UPDATE actor_characteristic SET current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (after, actor[0], rule_id))
            connection.execute(
                """INSERT INTO cmd_personal_mental_healing_allocation
                   VALUES (%s,%s,%s,1,%s,%s)""",
                (command_id, order, rule_id, before, after))
        connection.execute(
            """UPDATE actor_actor
               SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""", (actor[0],))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load(connection, command_id, public_id, False)
