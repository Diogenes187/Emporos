"""Personal-combat Extended Action commitments and interruption checks."""

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import secrets

import psycopg


@dataclass(frozen=True)
class ExtendedActionResult:
    command_public_id: str
    extended_action_id: int
    actor_public_id: str
    operation: str
    status: str
    completed_rounds: int
    required_rounds: int
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """SELECT receipt.extended_action_id,actor.public_id,
                  receipt.operation,receipt.status_after,
                  receipt.completed_rounds_after,receipt.required_rounds
           FROM cmd_personal_extended_action_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return ExtendedActionResult(
        str(command_public_id), row[0], str(row[1]), row[2], row[3],
        row[4], row[5], replayed,
    )


def _existing(connection, initiator, key, expected):
    row = connection.execute(
        """SELECT command_id,public_id,command_type,command_status
           FROM cmd_command WHERE initiator_reference=%s
             AND idempotency_key=%s FOR UPDATE""",
        (initiator, key),
    ).fetchone()
    if row and row[2:] != (expected, "completed"):
        raise RuntimeError("Idempotency key belongs to another command")
    return row


def start_personal_extended_action_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    task_reference: str, characteristic_rule_code: str,
    skill_rule_code: str, time_frame_rule_code: str,
    random_source=None, started_at: datetime | None = None,
) -> ExtendedActionResult:
    if not task_reference or not task_reference.strip():
        raise ValueError("Extended Action requires a stable task reference")
    rng = random_source or secrets.SystemRandom()
    use_time = started_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "start_personal_extended_action")
        if existing:
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,actor.actor_id,
                      combatant.significant_actions_remaining,
                      combatant.minor_actions_remaining,
                      characteristic.rule_id,skill.rule_id,
                      frame.rule_id,frame.dice_count,frame.die_sides,
                      frame.exact_increment_seconds
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor actor
                 ON actor.public_id=%s
                AND actor.campaign_id=encounter.campaign_id
                AND actor.controller_reference=%s
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=actor.actor_id
               JOIN rule_rule characteristic
                 ON characteristic.rule_code=%s
               JOIN actor_characteristic characteristic_state
                 ON characteristic_state.actor_id=actor.actor_id
                AND characteristic_state.characteristic_rule_id=
                    characteristic.rule_id
               JOIN rule_rule skill ON skill.rule_code=%s
               JOIN rule_skill skill_definition
                 ON skill_definition.rule_id=skill.rule_id
               LEFT JOIN actor_skill actor_skill
                 ON actor_skill.actor_id=actor.actor_id
                AND actor_skill.skill_rule_id=skill.rule_id
               JOIN rule_rule frame_rule ON frame_rule.rule_code=%s
               JOIN rule_time_frame frame ON frame.rule_id=frame_rule.rule_id
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND combatant.turn_started_this_round
                 AND NOT combatant.acted_this_round
                 AND combatant.significant_actions_remaining>0
                 AND frame.exact_increment_seconds IS NOT NULL
                 AND (actor_skill.skill_level IS NOT NULL
                      OR skill_definition.permits_untrained)
                 AND NOT EXISTS (
                   SELECT 1 FROM enc_personal_extended_action active
                   WHERE active.encounter_id=combat.encounter_id
                     AND active.actor_id=actor.actor_id
                     AND active.action_status='active')
               FOR UPDATE OF combat,actor,combatant""",
            (
                actor_public_id, initiator_reference,
                characteristic_rule_code, skill_rule_code,
                time_frame_rule_code, encounter_public_id,
            ),
        ).fetchone()
        if state is None:
            raise ValueError("Extended Action cannot begin in this combat state")
        dice = tuple(rng.randint(1, state[9]) for _ in range(state[8]))
        required_rounds = max(
            1, math.ceil(sum(dice) * state[10] / 6))
        completed = 1
        status = "completed" if completed >= required_rounds else "active"
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('start_personal_extended_action',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'extended_action_timing',%s,%s,%s)""",
                (command_id, order, state[9], value),
            )
        action_id = connection.execute(
            """INSERT INTO enc_personal_extended_action
               (encounter_id,actor_id,task_reference,
                characteristic_rule_id,skill_rule_id,time_frame_rule_id,
                required_rounds,completed_rounds,last_progress_round,
                action_status,started_round,started_at,ended_at,
                source_command_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING extended_action_id""",
            (
                state[0], state[2], task_reference.strip(), state[5], state[6],
                state[7], required_rounds, completed, state[1], status,
                state[1], use_time, use_time if status == "completed" else None,
                command_id,
            ),
        ).fetchone()[0]
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=0,minor_actions_remaining=0,
                   acted_this_round=true
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[0], state[2]),
        )
        connection.execute(
            """INSERT INTO cmd_personal_extended_action_receipt
               VALUES (%s,%s,'start',%s,%s,%s,NULL,%s,0,%s,%s,true,%s)""",
            (
                command_id, action_id, state[0], state[2], state[1], status,
                completed, required_rounds, use_time,
            ),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public, False)


def advance_personal_extended_action_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    advanced_at: datetime | None = None,
) -> ExtendedActionResult:
    use_time = advanced_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "advance_personal_extended_action")
        if existing:
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT action.extended_action_id,action.encounter_id,
                      action.actor_id,combat.current_round,
                      action.completed_rounds,action.required_rounds,
                      action.work_lost_round
               FROM enc_personal_extended_action action
               JOIN enc_personal_combat combat
                 ON combat.encounter_id=action.encounter_id
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor actor ON actor.actor_id=action.actor_id
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=action.encounter_id
                AND combatant.actor_id=action.actor_id
               WHERE encounter.public_id=%s AND actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND action.action_status='active'
                 AND combatant.turn_started_this_round
                 AND NOT combatant.acted_this_round
                 AND action.last_progress_round<combat.current_round
               FOR UPDATE OF action,combat,combatant""",
            (encounter_public_id, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Extended Action cannot advance in this combat state")
        counted = state[6] != state[3]
        after = state[4] + (1 if counted else 0)
        status = "completed" if after >= state[5] else "active"
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('advance_personal_extended_action',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_extended_action
               SET completed_rounds=%s,last_progress_round=%s,
                   action_status=%s,ended_at=%s
               WHERE extended_action_id=%s""",
            (after, state[3], status,
             use_time if status == "completed" else None, state[0]),
        )
        connection.execute(
            """UPDATE enc_personal_combatant SET acted_this_round=true
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[1], state[2]),
        )
        connection.execute(
            """INSERT INTO cmd_personal_extended_action_receipt
               VALUES (%s,%s,'advance',%s,%s,%s,'active',%s,%s,%s,%s,%s,%s)""",
            (
                command_id, state[0], state[1], state[2], state[3], status,
                state[4], after, state[5], counted, use_time,
            ),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public, False)


def abandon_personal_extended_action_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    abandoned_at: datetime | None = None,
) -> ExtendedActionResult:
    use_time = abandoned_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "abandon_personal_extended_action")
        if existing:
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT action.extended_action_id,action.encounter_id,
                      action.actor_id,combat.current_round,
                      action.completed_rounds,action.required_rounds
               FROM enc_personal_extended_action action
               JOIN enc_personal_combat combat
                 ON combat.encounter_id=action.encounter_id
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor actor ON actor.actor_id=action.actor_id
               WHERE encounter.public_id=%s AND actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND action.action_status='active'
               FOR UPDATE OF action""",
            (encounter_public_id, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Actor has no active Extended Action")
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('abandon_personal_extended_action',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_extended_action
               SET action_status='abandoned',ended_at=%s
               WHERE extended_action_id=%s""",
            (use_time, state[0]),
        )
        connection.execute(
            """INSERT INTO cmd_personal_extended_action_receipt
               VALUES (%s,%s,'abandon',%s,%s,%s,'active','abandoned',
                       %s,%s,%s,false,%s)""",
            (command_id, state[0], state[1], state[2], state[3],
             state[4], state[4], state[5], use_time),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public, False)


def resolve_personal_extended_action_interruption_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, damage_instance_id: int, random_source=None,
    resolved_at: datetime | None = None,
) -> ExtendedActionResult:
    rng = random_source or secrets.SystemRandom()
    use_time = resolved_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = _existing(
            connection, initiator_reference, idempotency_key,
            "resolve_personal_extended_action_interruption")
        if existing:
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT action.extended_action_id,action.encounter_id,
                      action.actor_id,combat.current_round,
                      action.completed_rounds,action.required_rounds,
                      action.last_progress_round,damage.penetrating_damage,
                      COALESCE(actor_skill.skill_level,
                               skill.untrained_modifier),campaign.owner_reference
               FROM health_damage_instance damage
               JOIN enc_personal_extended_action action
                 ON action.actor_id=damage.target_actor_id
                AND action.action_status='active'
               JOIN enc_personal_combat combat
                 ON combat.encounter_id=action.encounter_id
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN camp_campaign campaign
                 ON campaign.campaign_id=encounter.campaign_id
               JOIN rule_skill skill ON skill.rule_id=action.skill_rule_id
               LEFT JOIN actor_skill ON actor_skill.actor_id=action.actor_id
                AND actor_skill.skill_rule_id=action.skill_rule_id
               WHERE damage.damage_instance_id=%s
                 AND damage.allocation_status='applied'
               FOR UPDATE OF action,combat,damage""",
            (damage_instance_id,),
        ).fetchone()
        if state is None or state[9] != initiator_reference:
            raise ValueError("Damage does not interrupt an owned active task")
        dice = (rng.randint(1, 6), rng.randint(1, 6))
        total = sum(dice) + state[8] - state[7]
        effect = total - 8
        succeeded = total >= 8
        exceptional = effect <= -6
        after = state[4]
        status = "active"
        counted = False
        if exceptional:
            after, status = 0, "ruined"
        elif not succeeded and state[6] == state[3]:
            after = max(0, after - 1)
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_extended_action_interruption',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'extended_action_interruption',%s,6,%s)""",
                (command_id, order, value),
            )
        connection.execute(
            """UPDATE enc_personal_extended_action
               SET completed_rounds=%s,work_lost_round=CASE WHEN %s
                     THEN work_lost_round ELSE %s END,
                   action_status=%s,ended_at=%s
               WHERE extended_action_id=%s""",
            (after, succeeded, state[3], status,
             use_time if status == "ruined" else None, state[0]),
        )
        connection.execute(
            """INSERT INTO cmd_personal_extended_action_receipt
               (command_id,extended_action_id,operation,encounter_id,
                actor_id,round_number,status_before,status_after,
                completed_rounds_before,completed_rounds_after,
                required_rounds,work_counted,resolved_at)
               VALUES (%s,%s,'interrupt',%s,%s,%s,'active',%s,
                       %s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[2], state[3], status,
             state[4], after, state[5], counted, use_time),
        )
        connection.execute(
            """INSERT INTO cmd_personal_extended_action_interruption
               VALUES (%s,%s,%s,%s,%s,%s,8,%s,%s,%s)""",
            (command_id, damage_instance_id, state[7], state[8], -state[7],
             total, effect, succeeded, exceptional),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public, False)
