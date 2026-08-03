"""Personal-combat weapon drawing and readying progress."""

from dataclasses import dataclass
from datetime import datetime, timezone
import psycopg


@dataclass(frozen=True)
class WeaponReadyResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    weapon_rule_code: str
    ready_basis: str
    required_minor_actions: int
    progress_after: int
    completed: bool
    minor_actions_after: int
    replayed: bool


def _load(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT encounter.public_id,actor.public_id,rule.rule_code,
                  receipt.ready_basis,receipt.required_minor_actions,
                  receipt.progress_after,receipt.completed,
                  receipt.minor_actions_after
           FROM cmd_personal_weapon_ready_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule rule ON rule.rule_id=receipt.weapon_rule_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return WeaponReadyResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], row[6], row[7], replayed)


def advance_personal_weapon_ready_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    weapon_rule_code: str, referee_ready_minor_actions: int | None = None,
    referee_adjudicator_reference: str | None = None,
    referee_override_reason: str | None = None,
    resolved_at: datetime | None = None,
) -> WeaponReadyResult:
    use_time = resolved_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("advance_personal_weapon_ready", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,actor.actor_id,
                      combatant.minor_actions_remaining,weapon.rule_id,
                      weapon_state.ready,weapon_state.ready_progress,
                      weapon_state.ready_required_actions,
                      weapon_state.ready_basis,
                      weapon_state.ready_referee_reference,
                      weapon_state.ready_override_reason,
                      profile.ready_minor_actions,campaign.owner_reference,
                      mechanic.default_minor_actions
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN camp_campaign campaign
                 ON campaign.campaign_id=encounter.campaign_id
               JOIN actor_actor actor ON actor.public_id=%s
                AND actor.campaign_id=encounter.campaign_id
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=actor.actor_id
               JOIN rule_rule weapon ON weapon.rule_code=%s
               JOIN actor_weapon_state weapon_state
                 ON weapon_state.actor_id=actor.actor_id
                AND weapon_state.weapon_rule_id=weapon.rule_id
               LEFT JOIN inv_weapon_ready_profile profile
                 ON profile.weapon_rule_id=weapon.rule_id
               CROSS JOIN rule_personal_weapon_readying mechanic
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND actor.controller_reference=%s
                 AND combatant.turn_started_this_round
                 AND NOT combatant.acted_this_round
                 AND combatant.minor_actions_remaining>0
                 AND NOT EXISTS (
                   SELECT 1 FROM enc_personal_extended_action extended
                   WHERE extended.encounter_id=combat.encounter_id
                     AND extended.actor_id=actor.actor_id
                     AND extended.action_status='active')
               FOR UPDATE OF combat,combatant,weapon_state""",
            (actor_public_id, weapon_rule_code, encounter_public_id,
             initiator_reference)).fetchone()
        if state is None:
            raise PermissionError("Weapon cannot be readied in this turn state")
        if state[5]:
            raise ValueError("Weapon is already ready")
        if state[6] > 0:
            required, basis = state[7], state[8]
            referee_reference, override_reason = state[9], state[10]
            if referee_ready_minor_actions is not None:
                raise ValueError("Cannot change an in-progress ready procedure")
        elif referee_ready_minor_actions is not None:
            if referee_ready_minor_actions < 1:
                raise ValueError("Referee ready time must be positive")
            if (referee_adjudicator_reference != state[12]
                    or not referee_override_reason
                    or not referee_override_reason.strip()):
                raise PermissionError("Ready-time override requires campaign referee")
            required, basis = referee_ready_minor_actions, "referee_override"
            referee_reference = referee_adjudicator_reference
            override_reason = referee_override_reason.strip()
        elif state[11] is not None:
            required, basis = state[11], "explicit_profile"
            referee_reference = override_reason = None
        else:
            required, basis = state[13], "source_default"
            referee_reference = override_reason = None
        before, after = state[6], state[6] + 1
        completed = after >= required
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('advance_personal_weapon_ready',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET minor_actions_remaining=minor_actions_remaining-1
               WHERE encounter_id=%s AND actor_id=%s""", (state[0], state[2]))
        connection.execute(
            """UPDATE actor_weapon_state SET ready=%s,ready_progress=%s,
                 ready_required_actions=%s,ready_basis=%s,
                 ready_referee_reference=%s,ready_override_reason=%s
               WHERE actor_id=%s AND weapon_rule_id=%s""",
            (completed, 0 if completed else after,
             None if completed else required, None if completed else basis,
             None if completed else referee_reference,
             None if completed else override_reason, state[2], state[4]))
        connection.execute(
            """INSERT INTO cmd_personal_weapon_ready_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[4], state[1], basis,
             required, before, after, completed, state[3], state[3]-1,
             referee_reference, override_reason, use_time))
        connection.execute("""UPDATE cmd_command SET command_status='completed',
            completed_at=clock_timestamp() WHERE command_id=%s""", (command_id,))
        return _load(connection, command_id, public_id, False)
