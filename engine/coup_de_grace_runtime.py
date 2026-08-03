"""Campaign-safe personal Coup de Grace command."""

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass(frozen=True)
class CoupDeGraceResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    target_actor_public_id: str
    delivery_kind: str
    helpless_basis: str
    round_number: int
    resolved_at: datetime
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """SELECT encounter.public_id,actor.public_id,target.public_id,
                  receipt.delivery_kind,receipt.helpless_basis,
                  receipt.round_number,receipt.resolved_at
           FROM cmd_personal_coup_de_grace_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN actor_actor target ON target.actor_id=receipt.target_actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CoupDeGraceResult(
        str(command_public_id), str(row[0]), str(row[1]), str(row[2]),
        row[3], row[4], row[5], row[6], replayed,
    )


def resolve_personal_coup_de_grace_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    actor_public_id: str, target_actor_public_id: str,
    weapon_rule_code: str, delivery_kind: str,
    range_relationship: str, helpless_basis: str,
    helpless_evidence: str, resolved_at: datetime | None = None,
) -> CoupDeGraceResult:
    if delivery_kind not in {"melee", "ranged"}:
        raise ValueError("Coup de Grace delivery must be melee or ranged")
    expected_range = (
        "close-quarters" if delivery_kind == "melee" else "adjacent")
    if range_relationship != expected_range:
        raise ValueError(
            f"{delivery_kind.title()} Coup de Grace requires {expected_range}")
    if helpless_basis not in {
        "unconscious", "fully_restrained", "incapacitated",
        "referee_adjudication",
    }:
        raise ValueError("Unsupported helpless-target basis")
    if helpless_basis != "unconscious":
        raise ValueError(
            "This helpless basis lacks an authoritative runtime state")
    if not helpless_evidence or not helpless_evidence.strip():
        raise ValueError("Coup de Grace requires helpless-target evidence")
    use_time = resolved_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_personal_coup_de_grace", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,encounter.campaign_id,
                      combat.current_round,actor.actor_id,target.actor_id,
                      attacker.significant_actions_remaining,
                      actor.concurrency_version,target.concurrency_version,
                      COALESCE(condition.unconscious,false)
               FROM enc_encounter encounter
               JOIN enc_personal_combat combat
                 ON combat.encounter_id=encounter.encounter_id
               JOIN actor_actor actor
                 ON actor.public_id=%s
                AND actor.campaign_id=encounter.campaign_id
                AND actor.controller_reference=%s
               JOIN actor_actor target
                 ON target.public_id=%s
                AND target.campaign_id=encounter.campaign_id
               JOIN enc_personal_combatant attacker
                 ON attacker.encounter_id=combat.encounter_id
                AND attacker.actor_id=actor.actor_id
               JOIN enc_personal_combatant defender
                 ON defender.encounter_id=combat.encounter_id
                AND defender.actor_id=target.actor_id
               LEFT JOIN actor_personal_condition condition
                 ON condition.actor_id=target.actor_id
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND encounter.current_mode='personal_combat'
                 AND combat.combat_status='active'
                 AND attacker.turn_started_this_round
                 AND NOT attacker.acted_this_round
                 AND attacker.significant_actions_remaining>0
                 AND actor.actor_id<>target.actor_id
               FOR UPDATE OF combat,actor,target,attacker,defender""",
            (
                actor_public_id, initiator_reference,
                target_actor_public_id, encounter_public_id,
            ),
        ).fetchone()
        if state is None:
            raise ValueError(
                "Coup de Grace requires an active turn, action, and campaign opponent")
        if not state[8]:
            raise ValueError("Target is not authoritatively unconscious")
        weapon = connection.execute(
            """SELECT weapon.item_rule_id,
                      bool_or(mode.attack_profile_code='close-quarters'),
                      bool_or(mode.attack_profile_code<>'close-quarters')
               FROM rule_rule rule
               JOIN inv_weapon_definition weapon
                 ON weapon.item_rule_id=rule.rule_id
               JOIN inv_weapon_attack_mode mode
                 ON mode.item_rule_id=weapon.item_rule_id
               WHERE rule.rule_code=%s
               GROUP BY weapon.item_rule_id""",
            (weapon_rule_code,),
        ).fetchone()
        if weapon is None or not weapon[1 if delivery_kind == "melee" else 2]:
            raise ValueError("Weapon does not support the selected delivery")
        characteristic_rows = connection.execute(
            """SELECT rule.rule_code,state.characteristic_rule_id,
                      state.current_value
               FROM actor_characteristic state
               JOIN rule_rule rule ON rule.rule_id=state.characteristic_rule_id
               WHERE state.actor_id=%s AND rule.rule_code=ANY(%s)
               FOR UPDATE OF state""",
            (
                state[4],
                ["characteristic.strength", "characteristic.dexterity",
                 "characteristic.endurance"],
            ),
        ).fetchall()
        characteristics = {
            row[0]: (row[1], row[2]) for row in characteristic_rows}
        required = {
            "characteristic.strength", "characteristic.dexterity",
            "characteristic.endurance",
        }
        if set(characteristics) != required:
            raise ValueError("Target lacks the three physical characteristics")
        if all(value[1] == 0 for value in characteristics.values()):
            raise ValueError("Target is already dead")
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_coup_de_grace',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        significant_after = state[5] - 1
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=%s,
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (significant_after, state[0], state[3]),
        )
        connection.execute(
            """UPDATE actor_characteristic SET current_value=0
               WHERE actor_id=%s AND characteristic_rule_id=ANY(%s)""",
            (state[4], [value[0] for value in characteristics.values()]),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id IN (%s,%s)""",
            (state[3], state[4]),
        )
        before = {
            code: characteristics[code][1] for code in required}
        connection.execute(
            """INSERT INTO cmd_personal_coup_de_grace_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,0,%s,0,%s,0,%s,%s,%s,%s,%s)""",
            (
                command_id, state[1], state[0], state[3], state[4], state[2],
                weapon[0], delivery_kind, range_relationship, helpless_basis,
                helpless_evidence.strip(), state[5], significant_after,
                before["characteristic.strength"],
                before["characteristic.dexterity"],
                before["characteristic.endurance"],
                state[6], state[6] + 1, state[7], state[7] + 1, use_time,
            ),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp()
               WHERE command_id=%s""",
            (command_id,),
        )
        return _load(
            connection, command_id, command_public_id, False)
