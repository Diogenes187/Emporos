"""Campaign-safe miscellaneous personal-combat actions."""

from dataclasses import dataclass

import psycopg

from engine.combat_runtime import spend_personal_action_command
from engine.tasks import resolve_actor_task_command


@dataclass(frozen=True)
class PersonalMiscellaneousActionResult:
    command_public_id: str
    action_tier: str
    task_command_public_id: str | None
    significant_after: int
    minor_after: int
    replayed: bool


def perform_personal_miscellaneous_action_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    referee_reference: str, idempotency_key: str,
    encounter_public_id: str, actor_public_id: str, action_tier: str,
    action_description: str, authorization_reason: str,
    characteristic_rule_code: str | None = None,
    skill_rule_code: str | None = None,
    difficulty_rule_code: str | None = None,
    task_context_code: str | None = None,
    circumstance_modifier: int = 0, random_source=None,
) -> PersonalMiscellaneousActionResult:
    if action_tier not in {"minor", "significant"}:
        raise ValueError("Miscellaneous action tier must be minor or significant")
    if not action_description or not action_description.strip():
        raise ValueError("Miscellaneous action requires a description")
    if not authorization_reason or not authorization_reason.strip():
        raise ValueError("Miscellaneous action requires a referee reason")
    task_fields = (
        characteristic_rule_code, skill_rule_code, difficulty_rule_code)
    if any(value is not None for value in task_fields) and not all(
        value is not None for value in task_fields
    ):
        raise ValueError("A miscellaneous task requires characteristic, skill, and difficulty")
    with connection.transaction():
        authority = connection.execute(
            """SELECT campaign.owner_reference
               FROM enc_encounter encounter
               JOIN camp_campaign campaign USING(campaign_id)
               JOIN actor_actor actor USING(campaign_id)
               WHERE encounter.public_id=%s AND actor.public_id=%s
                 AND actor.controller_reference=%s""",
            (encounter_public_id, actor_public_id, initiator_reference),
        ).fetchone()
        if authority is None or authority[0] != referee_reference:
            raise PermissionError("Campaign referee authorization is required")
        task = None
        if all(value is not None for value in task_fields):
            task = resolve_actor_task_command(
                connection, initiator_reference=initiator_reference,
                idempotency_key=f"{idempotency_key}:task",
                actor_public_id=actor_public_id,
                characteristic_rule_code=characteristic_rule_code,
                skill_rule_code=skill_rule_code,
                difficulty_rule_code=difficulty_rule_code,
                task_context_code=task_context_code,
                circumstance_modifier=circumstance_modifier,
                random_source=random_source)
            if (task.characteristic_rule_code, task.skill_rule_code,
                    task.difficulty_rule_code, task.task_context_code) != (
                    characteristic_rule_code, skill_rule_code,
                    difficulty_rule_code, task_context_code):
                raise RuntimeError("Idempotent miscellaneous task inputs differ")
        spent = spend_personal_action_command(
            connection, initiator_reference=initiator_reference,
            idempotency_key=idempotency_key,
            encounter_public_id=encounter_public_id,
            actor_public_id=actor_public_id,
            operation=("spend_minor" if action_tier == "minor"
                       else "spend_significant"))
        command_id = connection.execute(
            """SELECT command_id FROM cmd_command
               WHERE public_id=%s""", (spent.command_public_id,)).fetchone()[0]
        existing = connection.execute(
            """SELECT task.public_id,receipt.action_tier,
                      receipt.action_description,receipt.referee_reference,
                      receipt.authorization_reason
               FROM cmd_personal_miscellaneous_action_receipt receipt
               LEFT JOIN cmd_command task
                 ON task.command_id=receipt.task_command_id
               WHERE receipt.command_id=%s""", (command_id,)).fetchone()
        if existing is None:
            task_id = None
            if task:
                task_id = connection.execute(
                    "SELECT command_id FROM cmd_command WHERE public_id=%s",
                    (task.command_public_id,)).fetchone()[0]
            action_row = connection.execute(
                """SELECT encounter_id,actor_id,round_number,
                          significant_before,significant_after,
                          minor_before,minor_after
                   FROM cmd_personal_action_receipt WHERE command_id=%s""",
                (command_id,)).fetchone()
            connection.execute(
                """INSERT INTO cmd_personal_miscellaneous_action_receipt
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (command_id, task_id, action_row[0], action_row[1], action_row[2],
                 action_tier, action_description.strip(), referee_reference,
                 authorization_reason.strip(), *action_row[3:]))
        elif (
            (str(existing[0]) if existing[0] else None,
             existing[1], existing[2], existing[3], existing[4]) !=
            (task.command_public_id if task else None,
             action_tier, action_description.strip(), referee_reference,
             authorization_reason.strip())
        ):
            raise RuntimeError("Idempotent miscellaneous action inputs differ")
        return PersonalMiscellaneousActionResult(
            spent.command_public_id, action_tier,
            task.command_public_id if task else (str(existing[0]) if existing and existing[0] else None),
            spent.significant_after, spent.minor_after, spent.replayed)
