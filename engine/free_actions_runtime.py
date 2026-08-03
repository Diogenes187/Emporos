"""Personal-combat Free Action execution and escalation receipts."""

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass(frozen=True)
class PersonalFreeActionResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    action_reference: str
    assessed_cost: str
    free_action_ordinal: int
    significant_actions_after: int
    minor_actions_after: int
    replayed: bool


def _load(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT encounter.public_id,actor.public_id,receipt.round_number,
                  receipt.action_reference,receipt.assessed_cost,
                  receipt.free_action_ordinal,
                  receipt.significant_actions_after,
                  receipt.minor_actions_after
           FROM cmd_personal_free_action_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return PersonalFreeActionResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], row[6], row[7], replayed)


def perform_personal_free_action_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    action_reference: str, assessed_cost: str = "free",
    referee_adjudicator_reference: str | None = None,
    performed_at: datetime | None = None,
) -> PersonalFreeActionResult:
    if assessed_cost not in {"free", "minor", "significant"}:
        raise ValueError("Unknown Free Action assessed cost")
    if not action_reference or not action_reference.strip():
        raise ValueError("Free Action requires an action reference")
    use_time = performed_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("perform_personal_free_action", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,actor.actor_id,
                      combatant.significant_actions_remaining,
                      combatant.minor_actions_remaining,
                      campaign.owner_reference
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN camp_campaign campaign
                 ON campaign.campaign_id=encounter.campaign_id
               JOIN actor_actor actor
                 ON actor.public_id=%s
                AND actor.campaign_id=encounter.campaign_id
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=actor.actor_id
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND actor.controller_reference=%s
                 AND combatant.turn_started_this_round
                 AND NOT combatant.acted_this_round
                 AND NOT EXISTS (
                   SELECT 1 FROM enc_personal_extended_action extended
                   WHERE extended.encounter_id=combat.encounter_id
                     AND extended.actor_id=actor.actor_id
                     AND extended.action_status='active')
               FOR UPDATE OF combat,combatant""",
            (actor_public_id, encounter_public_id,
             initiator_reference)).fetchone()
        if state is None:
            raise PermissionError("Free Action is not legal in this turn state")
        if assessed_cost == "minor" and state[4] < 1:
            raise ValueError("No minor action remains for escalation")
        if assessed_cost == "significant" and state[3] < 1:
            raise ValueError("No significant action remains for escalation")
        if assessed_cost != "free" and (
            not referee_adjudicator_reference
            or referee_adjudicator_reference != state[5]
        ):
            raise PermissionError(
                "Escalated Free Action requires campaign referee adjudication")
        ordinal = connection.execute(
            """SELECT count(*)+1 FROM cmd_personal_free_action_receipt
               WHERE encounter_id=%s AND actor_id=%s AND round_number=%s""",
            (state[0], state[2], state[1])).fetchone()[0]
        significant_after = state[3] - (assessed_cost == "significant")
        minor_after = state[4] - (assessed_cost == "minor")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('perform_personal_free_action',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=%s,
                   minor_actions_remaining=%s
               WHERE encounter_id=%s AND actor_id=%s""",
            (significant_after, minor_after, state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_free_action_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1],
             action_reference.strip(), assessed_cost, ordinal,
             state[3], significant_after, state[4], minor_after,
             referee_adjudicator_reference, use_time))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load(connection, command_id, public_id, False)
