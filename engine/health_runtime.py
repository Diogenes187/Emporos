"""Campaign-safe personal fatigue and unconsciousness commands."""
from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class PersonalFatigueResult:
    command_public_id: str
    actor_public_id: str
    fatigue_sequence: int
    already_fatigued: bool
    endurance_modifier: int
    rest_required_hours: int
    check_modifier: int
    became_unconscious: bool
    replayed: bool


@dataclass(frozen=True)
class PersonalFatigueRestResult:
    command_public_id: str
    actor_public_id: str
    fatigue_sequence: int
    required_hours: int
    completed_hours: float
    fatigue_cleared: bool
    replayed: bool


@dataclass(frozen=True)
class PersonalUnconsciousRecoveryResult:
    command_public_id: str
    actor_public_id: str
    attempt_number: int
    minutes_elapsed: int
    dice: tuple[int, int]
    endurance_modifier: int
    prior_failure_modifier: int
    total: int
    target_number: int
    effect: int
    succeeded: bool
    remains_fatigued: bool
    replayed: bool


def _modifier(connection, characteristic_id, value):
    return connection.execute(
        """SELECT modifier FROM rule_characteristic_modifier_band
           WHERE (characteristic_rule_id IS NULL
                  OR characteristic_rule_id=%s)
             AND score_range @> %s::integer
           ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
        (characteristic_id, value),
    ).fetchone()[0]


def _existing(connection, initiator_reference, idempotency_key, command_type):
    row = connection.execute(
        """SELECT command_id,public_id,command_type,command_status
           FROM cmd_command WHERE initiator_reference=%s
             AND idempotency_key=%s FOR UPDATE""",
        (initiator_reference, idempotency_key),
    ).fetchone()
    if row and row[2:] != (command_type, "completed"):
        raise RuntimeError("Idempotency key belongs to another command")
    return row


def _condition(connection, actor_public_id, initiator_reference):
    actor = connection.execute(
        """SELECT actor.actor_id,endurance.rule_id,
                  endurance_state.current_value
           FROM actor_actor actor
           JOIN rule_rule endurance
             ON endurance.rule_code='characteristic.endurance'
           JOIN actor_characteristic endurance_state
             ON endurance_state.actor_id=actor.actor_id
            AND endurance_state.characteristic_rule_id=endurance.rule_id
           WHERE actor.public_id=%s
             AND actor.controller_reference=%s
           FOR UPDATE OF actor""",
        (actor_public_id, initiator_reference),
    ).fetchone()
    if actor is None:
        raise ValueError("Actor is not controlled by the initiator")
    connection.execute(
        """INSERT INTO actor_personal_condition (actor_id)
           VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
        (actor[0],))
    state = connection.execute(
        """SELECT fatigued,fatigue_sequence,fatigue_endurance_modifier,
                  fatigue_rest_required_hours,unconscious,
                  unconscious_recovery_failures,
                  unconscious_minutes_elapsed,condition_version,
                  unconscious_cause
           FROM actor_personal_condition WHERE actor_id=%s FOR UPDATE""",
        (actor[0],),
    ).fetchone()
    return actor, state


def _transition(
    connection, command_id, actor_id, kind, state, *,
    fatigued_after, unconscious_after, failures_after, minutes_after,
):
    connection.execute(
        """INSERT INTO actor_personal_condition_transition
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (command_id, actor_id, kind, state[7], state[7] + 1,
         state[0], fatigued_after, state[4], unconscious_after,
         state[5], failures_after, state[6], minutes_after))


def apply_personal_fatigue_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
) -> PersonalFatigueResult:
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "apply_personal_fatigue")
        if existing:
            row = connection.execute(
                """SELECT actor.public_id,receipt.fatigue_sequence,
                          receipt.already_fatigued,
                          receipt.endurance_modifier,
                          receipt.rest_required_hours,
                          receipt.check_modifier,
                          receipt.became_unconscious
                   FROM cmd_personal_fatigue_receipt receipt
                   JOIN actor_actor actor USING (actor_id)
                   WHERE receipt.command_id=%s""",
                (existing[0],)).fetchone()
            return PersonalFatigueResult(
                str(existing[1]), str(row[0]), *row[1:], True)
        actor, state = _condition(
            connection, actor_public_id, initiator_reference)
        if state[4]:
            raise ValueError("Actor is already unconscious")
        endurance_modifier = _modifier(connection, actor[1], actor[2])
        already_fatigued = state[0]
        rest_required = (
            state[3] if already_fatigued
            else max(0, 3 - endurance_modifier))
        sequence = state[1] + 1
        became_unconscious = already_fatigued
        kind = (
            "fatigue_repeated_unconscious" if already_fatigued
            else "fatigue_started")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_personal_fatigue',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """INSERT INTO cmd_personal_fatigue_receipt
               VALUES (%s,%s,%s,%s,%s,%s,-2,%s,%s)""",
            (command_id, actor[0], sequence, already_fatigued,
             endurance_modifier, rest_required, became_unconscious, kind))
        _transition(
            connection, command_id, actor[0], kind, state,
            fatigued_after=True, unconscious_after=became_unconscious,
            failures_after=0, minutes_after=0)
        connection.execute(
            """UPDATE actor_personal_condition
               SET fatigued=true,fatigue_sequence=%s,
                   fatigue_endurance_modifier=%s,
                   fatigue_rest_required_hours=%s,
                   unconscious=%s,
                   unconscious_cause=%s,
                   unconscious_recovery_failures=0,
                   unconscious_minutes_elapsed=0,
                   condition_version=condition_version+1
               WHERE actor_id=%s""",
            (sequence, state[2] if already_fatigued else endurance_modifier,
             rest_required, became_unconscious,
             "repeated_fatigue" if became_unconscious else None, actor[0]))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return PersonalFatigueResult(
            str(public_id), actor_public_id, sequence, already_fatigued,
            endurance_modifier, rest_required, -2, became_unconscious, False)


def complete_personal_fatigue_rest_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, completed_hours: float,
) -> PersonalFatigueRestResult:
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "complete_personal_fatigue_rest")
        if existing:
            row = connection.execute(
                """SELECT actor.public_id,receipt.fatigue_sequence,
                          receipt.required_hours,receipt.completed_hours,
                          receipt.fatigue_cleared
                   FROM cmd_personal_fatigue_rest_receipt receipt
                   JOIN actor_actor actor USING (actor_id)
                   WHERE receipt.command_id=%s""",
                (existing[0],)).fetchone()
            return PersonalFatigueRestResult(
                str(existing[1]), str(row[0]), row[1], row[2],
                float(row[3]), row[4], True)
        actor, state = _condition(
            connection, actor_public_id, initiator_reference)
        if not state[0]:
            raise ValueError("Actor is not fatigued")
        if state[4]:
            raise ValueError("Unconscious actor must regain consciousness first")
        if completed_hours < state[3]:
            raise ValueError("Completed rest is shorter than required rest")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('complete_personal_fatigue_rest',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """INSERT INTO cmd_personal_fatigue_rest_receipt
               VALUES (%s,%s,%s,%s,%s,true)""",
            (command_id, actor[0], state[1], state[3], completed_hours))
        _transition(
            connection, command_id, actor[0], "fatigue_rest_completed", state,
            fatigued_after=False, unconscious_after=False,
            failures_after=0, minutes_after=0)
        connection.execute(
            """UPDATE actor_personal_condition
               SET fatigued=false,fatigue_endurance_modifier=NULL,
                   fatigue_rest_required_hours=NULL,
                   condition_version=condition_version+1
               WHERE actor_id=%s""", (actor[0],))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return PersonalFatigueRestResult(
            str(public_id), actor_public_id, state[1], state[3],
            float(completed_hours), True, False)


def resolve_personal_unconscious_recovery_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, minutes_elapsed: int,
    random_source=None,
) -> PersonalUnconsciousRecoveryResult:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "resolve_personal_unconscious_recovery")
        if existing:
            row = connection.execute(
                """SELECT actor.public_id,receipt.attempt_number,
                          receipt.minutes_elapsed,
                          receipt.endurance_modifier,
                          receipt.prior_failure_modifier,
                          receipt.check_total,receipt.target_number,
                          receipt.effect,receipt.succeeded,
                          receipt.remains_fatigued
                   FROM cmd_personal_unconscious_recovery_receipt receipt
                   JOIN actor_actor actor USING (actor_id)
                   WHERE receipt.command_id=%s""",
                (existing[0],)).fetchone()
            dice = tuple(item[0] for item in connection.execute(
                """SELECT result FROM cmd_random_draw
                   WHERE command_id=%s AND draw_group='task'
                   ORDER BY draw_order""", (existing[0],)).fetchall())
            return PersonalUnconsciousRecoveryResult(
                str(existing[1]), str(row[0]), row[1], row[2], dice,
                *row[3:], True)
        actor, state = _condition(
            connection, actor_public_id, initiator_reference)
        if not state[4]:
            raise ValueError("Actor is not unconscious")
        if minutes_elapsed < state[6] + 1:
            raise ValueError("One elapsed minute is required for each attempt")
        endurance_modifier = _modifier(connection, actor[1], actor[2])
        prior_failure_modifier = state[5]
        dice = (rng.randint(1, 6), rng.randint(1, 6))
        total = sum(dice) + endurance_modifier + prior_failure_modifier
        target_number = 8
        succeeded = total >= target_number
        effect = total - target_number
        failures_after = 0 if succeeded else state[5] + 1
        kind = (
            "consciousness_recovered" if succeeded
            else "consciousness_recovery_failed")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_unconscious_recovery',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,6,%s)""",
                (command_id, order, die))
        connection.execute(
            """INSERT INTO cmd_personal_unconscious_recovery_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,8,%s,%s,%s)""",
            (command_id, actor[0], state[5] + 1, minutes_elapsed,
             endurance_modifier, prior_failure_modifier, total,
             effect, succeeded, state[0]))
        _transition(
            connection, command_id, actor[0], kind, state,
            fatigued_after=state[0], unconscious_after=not succeeded,
            failures_after=failures_after,
            minutes_after=0 if succeeded else minutes_elapsed)
        connection.execute(
            """UPDATE actor_personal_condition
               SET unconscious=%s,unconscious_cause=%s,
                   unconscious_recovery_failures=%s,
                   unconscious_minutes_elapsed=%s,
                   condition_version=condition_version+1
               WHERE actor_id=%s""",
            (not succeeded, None if succeeded else state[8],
             failures_after, 0 if succeeded else minutes_elapsed, actor[0]))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return PersonalUnconsciousRecoveryResult(
            str(public_id), actor_public_id, state[5] + 1,
            minutes_elapsed, dice, endurance_modifier,
            prior_failure_modifier, total, target_number, effect,
            succeeded, state[0], False)
