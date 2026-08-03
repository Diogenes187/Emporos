"""Campaign-safe Battlefield Conditions state transitions."""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class BattlefieldConditionResult:
    command_public_id: str
    encounter_public_id: str
    light_code: str
    obscurant_code: str
    extreme_weather: bool
    gravity_code: str
    concurrency_version: int
    replayed: bool


def _load_result(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT encounter.public_id,receipt.light_after,
                  receipt.obscurant_after,receipt.extreme_weather_after,
                  receipt.gravity_after,receipt.version_after
           FROM cmd_personal_battlefield_condition_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return BattlefieldConditionResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4], row[5],
        replayed)


def set_personal_battlefield_conditions_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    light_code: str, obscurant_code: str, extreme_weather: bool,
    expected_version: int,
    gravity_code: str = "normal-gravity",
) -> BattlefieldConditionResult:
    if light_code not in ("normal", "low-light", "complete-darkness"):
        raise ValueError("Unknown battlefield light state")
    if obscurant_code not in ("none", "smoke", "thick-smoke"):
        raise ValueError("Unknown battlefield obscurant state")
    if gravity_code not in ("normal-gravity", "zero-gravity"):
        raise ValueError("Unknown battlefield gravity state")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != (
                "set_personal_battlefield_conditions", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_result(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT condition.encounter_id,condition.light_code,
                      condition.obscurant_code,condition.extreme_weather,
                      condition.concurrency_version,condition.gravity_code
               FROM enc_personal_battlefield_condition condition
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=condition.encounter_id
               JOIN camp_campaign campaign
                 ON campaign.campaign_id=encounter.campaign_id
               JOIN enc_personal_combat combat
                 ON combat.encounter_id=encounter.encounter_id
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND campaign.owner_reference=%s
               FOR UPDATE OF condition""",
            (encounter_public_id, initiator_reference)).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not own this active personal combat")
        if state[4] != expected_version:
            raise RuntimeError("Battlefield condition version changed")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('set_personal_battlefield_conditions',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        after_version = state[4] + 1
        connection.execute(
            """UPDATE enc_personal_battlefield_condition
               SET light_code=%s,obscurant_code=%s,extreme_weather=%s,
                   gravity_code=%s,
                   concurrency_version=%s
               WHERE encounter_id=%s""",
            (light_code, obscurant_code, extreme_weather, gravity_code,
             after_version, state[0]))
        connection.execute(
            """INSERT INTO cmd_personal_battlefield_condition_receipt
               (command_id,encounter_id,light_before,light_after,
                obscurant_before,obscurant_after,extreme_weather_before,
                extreme_weather_after,version_before,version_after,
                gravity_before,gravity_after)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], light_code, state[2],
             obscurant_code, state[3], extreme_weather, state[4],
             after_version,state[5],gravity_code))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_result(connection, command_id, public_id, False)
