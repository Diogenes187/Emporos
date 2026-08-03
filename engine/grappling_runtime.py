"""Transactional Personal Combat grappling under CE-COMBAT-010."""

from dataclasses import dataclass
import secrets
from typing import Protocol

import psycopg


class RandomSource(Protocol):
    def randint(self, minimum: int, maximum: int) -> int: ...


@dataclass(frozen=True)
class GrappleCheckResult:
    command_public_id: str
    grapple_public_id: str
    challenger_actor_public_id: str
    opponent_actor_public_id: str
    challenger_dice: tuple[int, int]
    opponent_dice: tuple[int, int]
    challenger_total: int
    opponent_total: int
    winner_actor_public_id: str | None
    effect: int
    grapple_status: str
    replayed: bool


@dataclass(frozen=True)
class GrappleOptionResult:
    command_public_id: str
    grapple_public_id: str
    winner_actor_public_id: str
    loser_actor_public_id: str
    option_code: str
    effect: int
    continue_grapple: bool
    displacement_metres: float
    raw_damage: int
    damage_instance_public_id: str | None
    grapple_status: str
    replayed: bool


def _load_check(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT grapple.public_id,challenger.public_id,opponent.public_id,
                  receipt.challenger_total,receipt.opponent_total,
                  winner.public_id,receipt.effect,grapple.grapple_status
           FROM cmd_personal_grapple_check_receipt receipt
           JOIN enc_personal_grapple grapple
             ON grapple.grapple_id=receipt.grapple_id
           JOIN actor_actor challenger
             ON challenger.actor_id=receipt.challenger_actor_id
           JOIN actor_actor opponent
             ON opponent.actor_id=receipt.opponent_actor_id
           LEFT JOIN actor_actor winner
             ON winner.actor_id=receipt.winner_actor_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    draws = connection.execute(
        """SELECT draw_group,result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group IN (
             'grapple_challenger','grapple_opponent')
           ORDER BY draw_group,draw_order""", (command_id,)).fetchall()
    challenger_dice = tuple(v for g, v in draws if g == "grapple_challenger")
    opponent_dice = tuple(v for g, v in draws if g == "grapple_opponent")
    return GrappleCheckResult(
        str(public_id), str(row[0]), str(row[1]), str(row[2]),
        challenger_dice, opponent_dice, row[3], row[4],
        str(row[5]) if row[5] else None, row[6], row[7], replayed)


def _load_option(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT grapple.public_id,winner.public_id,loser.public_id,
                  receipt.option_code,receipt.effect,
                  receipt.continue_grapple,receipt.displacement_metres,
                  receipt.raw_damage,damage.public_id,
                  receipt.grapple_status_after
           FROM cmd_personal_grapple_option_receipt receipt
           JOIN enc_personal_grapple grapple
             ON grapple.grapple_id=receipt.grapple_id
           JOIN actor_actor winner
             ON winner.actor_id=receipt.winner_actor_id
           JOIN actor_actor loser ON loser.actor_id=receipt.loser_actor_id
           LEFT JOIN health_damage_instance damage
             ON damage.damage_instance_id=receipt.damage_instance_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return GrappleOptionResult(
        str(public_id), str(row[0]), str(row[1]), str(row[2]), row[3],
        row[4], row[5], float(row[6]), row[7],
        str(row[8]) if row[8] else None, row[9], replayed)


def _actor_check_facts(
    connection, encounter_id, actor_id, characteristic_rule_code
):
    if characteristic_rule_code not in {
        "characteristic.strength", "characteristic.dexterity"
    }:
        raise ValueError("Grappling uses Strength or Dexterity")
    row = connection.execute(
        """SELECT characteristic.rule_id,state.current_value,
                  skill.rule_id,skill_rule.permits_untrained,
                  skill_rule.untrained_modifier,actor_skill.skill_level,
                  combatant.reaction_check_modifier
           FROM rule_rule characteristic
           JOIN actor_characteristic state
             ON state.characteristic_rule_id=characteristic.rule_id
            AND state.actor_id=%s
           JOIN rule_rule skill
             ON skill.rule_code='skill.natural-weapons'
           JOIN rule_skill skill_rule ON skill_rule.rule_id=skill.rule_id
           LEFT JOIN actor_skill
             ON actor_skill.actor_id=%s
            AND actor_skill.skill_rule_id=skill.rule_id
           JOIN enc_personal_combatant combatant
             ON combatant.encounter_id=%s AND combatant.actor_id=%s
           WHERE characteristic.rule_code=%s""",
        (actor_id, actor_id, encounter_id, actor_id,
         characteristic_rule_code),
    ).fetchone()
    if row is None or (row[5] is None and not row[3]):
        raise ValueError("Actor cannot make the Natural Weapons check")
    characteristic_modifier = connection.execute(
        """SELECT modifier FROM rule_characteristic_modifier_band
           WHERE (characteristic_rule_id IS NULL
                  OR characteristic_rule_id=%s)
             AND score_range @> %s::integer
           ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
        (row[0], row[1])).fetchone()[0]
    skill_modifier = row[5] if row[5] is not None else row[4]
    return row[0], row[5], skill_modifier, characteristic_modifier, row[6]


def resolve_personal_grapple_check_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    challenger_actor_public_id: str, opponent_actor_public_id: str,
    challenger_characteristic_rule_code: str = "characteristic.strength",
    opponent_characteristic_rule_code: str = "characteristic.strength",
    personal_range_confirmed: bool = False,
    challenger_circumstance_modifier: int = 0,
    opponent_circumstance_modifier: int = 0,
    random_source: RandomSource | None = None,
) -> GrappleCheckResult:
    rng = random_source or secrets.SystemRandom()
    if challenger_actor_public_id == opponent_actor_public_id:
        raise ValueError("A character cannot grapple themself")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("resolve_personal_grapple_check", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_check(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,
                      challenger.actor_id,opponent.actor_id,
                      challenger_state.significant_actions_remaining
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor challenger
                 ON challenger.public_id=%s
                AND challenger.controller_reference=%s
               JOIN actor_actor opponent ON opponent.public_id=%s
               JOIN enc_personal_combatant challenger_state
                 ON challenger_state.encounter_id=combat.encounter_id
                AND challenger_state.actor_id=challenger.actor_id
               JOIN enc_personal_combatant opponent_state
                 ON opponent_state.encounter_id=combat.encounter_id
                AND opponent_state.actor_id=opponent.actor_id
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND challenger_state.turn_started_this_round
                 AND challenger_state.significant_actions_remaining>0
               FOR UPDATE OF combat,challenger_state,opponent_state""",
            (challenger_actor_public_id, initiator_reference,
             opponent_actor_public_id, encounter_public_id)).fetchone()
        if state is None:
            raise PermissionError("Grapple challenger is not eligible")
        active = connection.execute(
            """SELECT grapple.grapple_id,grapple.public_id,
                      grapple.grapple_status,grapple.check_sequence,
                      grapple.participant_a_actor_id,
                      grapple.participant_b_actor_id
               FROM enc_personal_grapple_active_actor active
               JOIN enc_personal_grapple grapple
                 ON grapple.grapple_id=active.grapple_id
               WHERE active.actor_id=%s FOR UPDATE OF grapple""",
            (state[2],)).fetchone()
        initial = active is None
        if initial:
            if not personal_range_confirmed:
                raise ValueError("Initial grapple requires Personal range")
            if connection.execute(
                """SELECT 1 FROM enc_personal_grapple_active_actor
                   WHERE actor_id=%s""", (state[3],)).fetchone():
                raise ValueError("Opponent is already in a grapple")
            status_before, sequence = "none", 1
        else:
            if active[2] != "active":
                raise ValueError("Prior grapple option is still pending")
            if state[3] not in (active[4], active[5]):
                raise ValueError("Opponent is not the other grapple participant")
            status_before, sequence = "active", active[3] + 1
        challenger = _actor_check_facts(
            connection, state[0], state[2],
            challenger_characteristic_rule_code)
        opponent = _actor_check_facts(
            connection, state[0], state[3],
            opponent_characteristic_rule_code)
        challenger_dice = (rng.randint(1, 6), rng.randint(1, 6))
        opponent_dice = (rng.randint(1, 6), rng.randint(1, 6))
        challenger_total = (
            sum(challenger_dice) + challenger[2] + challenger[3]
            + challenger[4] + challenger_circumstance_modifier)
        opponent_total = (
            sum(opponent_dice) + opponent[2] + opponent[3]
            + opponent[4] + opponent_circumstance_modifier)
        winner_id = (
            state[2] if challenger_total > opponent_total else
            state[3] if opponent_total > challenger_total else None)
        effect = abs(challenger_total - opponent_total)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_grapple_check',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        if initial:
            a_id, b_id = sorted((state[2], state[3]))
            grapple_status = "pending_option" if winner_id else "ended"
            grapple = connection.execute(
                """INSERT INTO enc_personal_grapple
                   (encounter_id,participant_a_actor_id,
                    participant_b_actor_id,grapple_status,
                    pending_check_command_id,pending_winner_actor_id,
                    check_sequence,started_round,ended_round,ended_at)
                   VALUES (%s,%s,%s,%s,%s,%s,1,%s,%s,
                           CASE WHEN %s IS NULL THEN clock_timestamp() END)
                   RETURNING grapple_id,public_id""",
                (state[0], a_id, b_id, grapple_status,
                 command_id if winner_id else None, winner_id, state[1],
                 state[1] if winner_id is None else None, winner_id)).fetchone()
        else:
            grapple = (active[0], active[1])
            grapple_status = "pending_option" if winner_id else "active"
            connection.execute(
                """UPDATE enc_personal_grapple
                   SET grapple_status=%s,pending_check_command_id=%s,
                       pending_winner_actor_id=%s,check_sequence=%s
                   WHERE grapple_id=%s""",
                (grapple_status, command_id if winner_id else None,
                 winner_id, sequence, grapple[0]))
        if winner_id and initial:
            for actor_id in (state[2], state[3]):
                connection.execute(
                    """INSERT INTO enc_personal_grapple_active_actor
                       VALUES (%s,%s,%s)""",
                    (actor_id, state[0], grapple[0]))
        significant_after = state[4] - 1
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=%s,
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (significant_after, state[0], state[2]))
        for group, dice in (
            ("grapple_challenger", challenger_dice),
            ("grapple_opponent", opponent_dice),
        ):
            for order, value in enumerate(dice, 1):
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (%s,%s,%s,6,%s)""",
                    (command_id, group, order, value))
        connection.execute(
            """INSERT INTO cmd_personal_grapple_check_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, grapple[0], state[0], state[1], sequence, initial,
             state[2], state[3], challenger[0], opponent[0], challenger[1],
             opponent[1], challenger[2], opponent[2], challenger[3],
             opponent[3], challenger[4] + challenger_circumstance_modifier,
             opponent[4] + opponent_circumstance_modifier,
             challenger_total, opponent_total, winner_id, effect,
             state[4], significant_after, status_before,
             "pending_option" if winner_id else status_before))
        transition_order = connection.execute(
            """SELECT COALESCE(max(transition_order),0)+1
               FROM enc_personal_grapple_state_transition
               WHERE grapple_id=%s""", (grapple[0],)).fetchone()[0]
        connection.execute(
            """INSERT INTO enc_personal_grapple_state_transition
               VALUES (%s,%s,%s,%s,%s)""",
            (grapple[0], transition_order, command_id, status_before,
             "pending_option" if winner_id else status_before))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_check(connection, command_id, public_id, False)


def apply_personal_grapple_option_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, grapple_public_id: str, option_code: str,
    continue_grapple: bool = False, displacement_metres: float = 0,
    item_instance_public_id: str | None = None,
    item_outcome: str | None = None,
    target_container_public_id: str | None = None,
    target_location_public_id: str | None = None,
    random_source: RandomSource | None = None,
) -> GrappleOptionResult:
    rng = random_source or secrets.SystemRandom()
    if option_code not in {
        "continue", "disarm", "drag", "escape", "damage",
        "knock_prone", "throw",
    }:
        raise ValueError("Unknown grapple option")
    if displacement_metres < 0 or displacement_metres > 3:
        raise ValueError("Grapple displacement must be from zero to three metres")
    if option_code == "continue":
        continue_grapple = True
    if option_code in {"escape", "throw"}:
        continue_grapple = False
    if option_code not in {"drag", "throw"} and displacement_metres:
        raise ValueError("This grapple option cannot displace a participant")
    if option_code != "disarm" and any((
        item_instance_public_id, item_outcome,
        target_container_public_id, target_location_public_id,
    )):
        raise ValueError("Only disarm accepts an item outcome")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("apply_personal_grapple_option", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_option(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT grapple.grapple_id,grapple.encounter_id,
                      grapple.pending_check_command_id,
                      grapple.pending_winner_actor_id,
                      grapple.participant_a_actor_id,
                      grapple.participant_b_actor_id,
                      combat.current_round,winner.public_id,
                      checked.effect,encounter.campaign_id
               FROM enc_personal_grapple grapple
               JOIN enc_personal_combat combat
                 ON combat.encounter_id=grapple.encounter_id
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=grapple.encounter_id
               JOIN actor_actor winner
                 ON winner.actor_id=grapple.pending_winner_actor_id
                AND winner.controller_reference=%s
               JOIN cmd_personal_grapple_check_receipt checked
                 ON checked.command_id=grapple.pending_check_command_id
               WHERE grapple.public_id=%s
                 AND grapple.grapple_status='pending_option'
               FOR UPDATE OF grapple""",
            (initiator_reference, grapple_public_id)).fetchone()
        if state is None:
            raise PermissionError("Initiator is not the pending grapple winner")
        winner_id = state[3]
        loser_id = (
            state[5] if winner_id == state[4] else state[4])
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_personal_grapple_option',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        raw_damage = 0
        if option_code == "damage":
            raw_damage = 2 + state[8]
        elif option_code == "throw":
            raw_damage = rng.randint(1, 6)
            connection.execute(
                """INSERT INTO cmd_random_draw VALUES
                   (DEFAULT,%s,'grapple_throw_damage',1,6,%s)""",
                (command_id, raw_damage))
        damage_id = None
        if raw_damage:
            damage_id = connection.execute(
                """INSERT INTO health_damage_instance
                   (grapple_option_command_id,target_actor_id,
                    penetrating_damage)
                   VALUES (%s,%s,%s) RETURNING damage_instance_id""",
                (command_id, loser_id, raw_damage)).fetchone()[0]
        stance_before = stance_after = None
        if option_code == "knock_prone":
            stance_before = connection.execute(
                """SELECT stance_rule_id FROM enc_personal_combatant
                   WHERE encounter_id=%s AND actor_id=%s FOR UPDATE""",
                (state[1], loser_id)).fetchone()[0]
            stance_after = connection.execute(
                """SELECT rule_id FROM rule_personal_stance
                   WHERE stance_code='prone'""").fetchone()[0]
            connection.execute(
                """UPDATE enc_personal_combatant SET stance_rule_id=%s
                   WHERE encounter_id=%s AND actor_id=%s""",
                (stance_after, state[1], loser_id))
        if option_code == "drag":
            connection.execute(
                """UPDATE enc_personal_combatant
                   SET metres_moved_this_round=
                       metres_moved_this_round+%s
                   WHERE encounter_id=%s AND actor_id IN (%s,%s)""",
                (displacement_metres, state[1], winner_id, loser_id))
        elif option_code == "throw":
            connection.execute(
                """UPDATE enc_personal_combatant
                   SET metres_moved_this_round=
                       metres_moved_this_round+%s
                   WHERE encounter_id=%s AND actor_id=%s""",
                (displacement_metres, state[1], loser_id))
        item_id = transfer_id = None
        if option_code == "disarm":
            if not item_instance_public_id or item_outcome not in {
                "taken", "floor"
            }:
                raise ValueError("Disarm requires a declared item outcome")
            item = connection.execute(
                """SELECT item.item_instance_id,item.campaign_id,
                          owner.actor_id,owner.faction_id
                   FROM inv_item_instance item
                   JOIN inv_item_owner owner
                     ON owner.item_instance_id=item.item_instance_id
                   WHERE item.public_id=%s AND item.campaign_id=%s
                     AND item.item_status='active' FOR UPDATE OF item""",
                (item_instance_public_id, state[9])).fetchone()
            if item is None or item[2] != loser_id:
                raise ValueError("Disarmed item must be owned by the loser")
            expected_outcome = "taken" if state[8] >= 6 else "floor"
            if item_outcome != expected_outcome:
                raise ValueError("Disarm outcome does not match Effect")
            container_id = location_id = None
            if item_outcome == "taken":
                if not target_container_public_id:
                    raise ValueError("Taken weapon requires winner container")
                container_id = connection.execute(
                    """SELECT container.container_id
                       FROM inv_container container
                       JOIN inv_actor_container actor_container
                         ON actor_container.container_id=container.container_id
                       WHERE container.public_id=%s
                         AND actor_container.actor_id=%s""",
                    (target_container_public_id, winner_id)).fetchone()
                if container_id is None:
                    raise ValueError("Target container is not held by winner")
                container_id = container_id[0]
            else:
                if not target_location_public_id:
                    raise ValueError("Dropped weapon requires encounter location")
                location_id = connection.execute(
                    """SELECT location_id FROM loc_location
                       WHERE public_id=%s AND campaign_id=%s""",
                    (target_location_public_id, state[9])).fetchone()
                if location_id is None:
                    raise ValueError("Drop location is outside campaign")
                location_id = location_id[0]
            transfer_id = connection.execute(
                """SELECT inv_transfer_item_atomic(
                   %s,%s,%s,%s,%s,%s,%s,%s)""",
                (state[9], item[0], container_id, location_id,
                 item[2], item[3], command_id, "Grapple disarm")).fetchone()[0]
            item_id = item[0]
        status_after = "active" if continue_grapple else "ended"
        connection.execute(
            """UPDATE enc_personal_grapple
               SET grapple_status=%s,pending_check_command_id=NULL,
                   pending_winner_actor_id=NULL,
                   ended_round=CASE WHEN %s='ended' THEN %s END,
                   ended_at=CASE WHEN %s='ended'
                                 THEN clock_timestamp() END
               WHERE grapple_id=%s""",
            (status_after, status_after, state[6],
             status_after, state[0]))
        if not continue_grapple:
            connection.execute(
                """DELETE FROM enc_personal_grapple_active_actor
                   WHERE grapple_id=%s""", (state[0],))
        connection.execute(
            """INSERT INTO cmd_personal_grapple_option_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s)""",
            (command_id, state[2], state[0], state[1], state[6],
             winner_id, loser_id, option_code, state[8], continue_grapple,
             displacement_metres, raw_damage, damage_id,
             stance_before, stance_after, item_id, item_outcome,
             transfer_id, status_after))
        transition_order = connection.execute(
            """SELECT COALESCE(max(transition_order),0)+1
               FROM enc_personal_grapple_state_transition
               WHERE grapple_id=%s""", (state[0],)).fetchone()[0]
        connection.execute(
            """INSERT INTO enc_personal_grapple_state_transition
               VALUES (%s,%s,%s,'pending_option',%s)""",
            (state[0], transition_order, command_id, status_after))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_option(connection, command_id, public_id, False)
