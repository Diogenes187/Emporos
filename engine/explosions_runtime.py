"""Relational personal-combat explosion declaration and resolution."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class ExplosionTargetResult:
    actor_public_id: str
    reaction_kind: str
    dodge_reduction: int
    damage_after_reaction: int
    armor_rating: int
    penetrating_damage: int
    damage_instance_public_id: str | None


@dataclass(frozen=True)
class PersonalExplosionResult:
    command_public_id: str
    explosion_public_id: str
    encounter_public_id: str
    round_number: int
    status: str
    shared_rolled_damage: int | None
    targets: tuple[ExplosionTargetResult, ...]
    replayed: bool


def _load_result(connection, command_id, public_id, replayed):
    declaration = connection.execute(
        """SELECT explosion.public_id,encounter.public_id,explosion.round_number,
                  explosion.explosion_status
           FROM enc_personal_explosion explosion
           JOIN enc_encounter encounter
             ON encounter.encounter_id=explosion.encounter_id
           WHERE explosion.explosion_id=COALESCE(
             (SELECT explosion_id
                FROM cmd_personal_explosion_declaration_receipt
               WHERE command_id=%s),
             (SELECT explosion_id
                FROM cmd_personal_explosion_reaction_receipt
               WHERE command_id=%s),
             (SELECT explosion_id
                FROM cmd_personal_explosion_resolution_receipt
               WHERE command_id=%s))""",
        (command_id, command_id, command_id),
    ).fetchone()
    resolution = connection.execute(
        """SELECT shared_rolled_damage
             FROM cmd_personal_explosion_resolution_receipt
            WHERE explosion_id=(
                SELECT explosion_id FROM enc_personal_explosion
                 WHERE public_id=%s)""",
        (declaration[0],),
    ).fetchone()
    rows = connection.execute(
        """SELECT actor.public_id,target.reaction_kind,
                  COALESCE(receipt.dodge_reduction,0),
                  COALESCE(receipt.damage_after_reaction,0),
                  COALESCE(receipt.armor_rating,0),
                  COALESCE(receipt.penetrating_damage,0),damage.public_id
           FROM enc_personal_explosion_target target
           JOIN enc_personal_explosion explosion
             ON explosion.explosion_id=target.explosion_id
           JOIN actor_actor actor ON actor.actor_id=target.actor_id
           LEFT JOIN cmd_personal_explosion_target_receipt receipt
             ON receipt.actor_id=target.actor_id
            AND receipt.command_id=(
                SELECT command_id
                  FROM cmd_personal_explosion_resolution_receipt
                 WHERE explosion_id=target.explosion_id)
           LEFT JOIN health_damage_instance damage
             ON damage.damage_instance_id=receipt.damage_instance_id
          WHERE explosion.public_id=%s
          ORDER BY target.target_order""",
        (declaration[0],),
    ).fetchall()
    targets = tuple(
        ExplosionTargetResult(
            str(row[0]), row[1] or "undeclared", row[2], row[3], row[4],
            row[5], str(row[6]) if row[6] else None,
        )
        for row in rows
    )
    return PersonalExplosionResult(
        str(public_id), str(declaration[0]), str(declaration[1]),
        declaration[2], declaration[3],
        resolution[0] if resolution else None, targets, replayed,
    )


def declare_personal_explosion_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, source_reference: str,
    damage_dice: int, damage_die_sides: int, flat_damage: int = 0,
    targets: tuple[tuple[str, str], ...],
) -> PersonalExplosionResult:
    if not source_reference.strip():
        raise ValueError("Explosion source reference is required")
    if damage_dice < 1 or damage_die_sides < 2 or flat_damage < 0:
        raise ValueError("Explosion damage expression is invalid")
    if not targets or len({actor for actor, _ in targets}) != len(targets):
        raise ValueError("Explosion targets must be nonempty and unique")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
                 FROM cmd_command
                WHERE initiator_reference=%s AND idempotency_key=%s
                FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("declare_personal_explosion", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_result(connection, existing[0], existing[1], True)
        combat = connection.execute(
            """SELECT combat.encounter_id,combat.current_round
                 FROM enc_personal_combat combat
                 JOIN enc_encounter encounter
                   ON encounter.encounter_id=combat.encounter_id
                 JOIN camp_campaign campaign
                   ON campaign.campaign_id=encounter.campaign_id
                WHERE encounter.public_id=%s
                  AND encounter.encounter_status='active'
                  AND combat.combat_status='active'
                  AND campaign.owner_reference=%s
                FOR UPDATE OF combat""",
            (encounter_public_id, initiator_reference),
        ).fetchone()
        if combat is None:
            raise PermissionError("Initiator does not own this active combat")
        resolved_targets = []
        for actor_public_id, armor_rule_code in targets:
            row = connection.execute(
                """SELECT actor.actor_id,armor.item_rule_id
                     FROM actor_actor actor
                     JOIN enc_personal_combatant combatant
                       ON combatant.actor_id=actor.actor_id
                      AND combatant.encounter_id=%s
                     CROSS JOIN rule_rule armor_rule
                     JOIN inv_armor_definition armor
                       ON armor.item_rule_id=armor_rule.rule_id
                    WHERE actor.public_id=%s
                      AND armor_rule.rule_code=%s""",
                (combat[0], actor_public_id, armor_rule_code),
            ).fetchone()
            if row is None:
                raise ValueError("Explosion target or armor rule is invalid")
            resolved_targets.append(row)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('declare_personal_explosion',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        explosion_id = connection.execute(
            """INSERT INTO enc_personal_explosion
               (encounter_id,round_number,source_reference,damage_dice,
                damage_die_sides,flat_damage)
               VALUES (%s,%s,%s,%s,%s,%s)
               RETURNING explosion_id""",
            (combat[0], combat[1], source_reference, damage_dice,
             damage_die_sides, flat_damage),
        ).fetchone()[0]
        for order, (actor_id, armor_id) in enumerate(resolved_targets, 1):
            connection.execute(
                """INSERT INTO enc_personal_explosion_target
                   (explosion_id,actor_id,target_order,armor_rule_id)
                   VALUES (%s,%s,%s,%s)""",
                (explosion_id, actor_id, order, armor_id),
            )
        connection.execute(
            """INSERT INTO cmd_personal_explosion_declaration_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, explosion_id, combat[0], combat[1],
             len(resolved_targets)),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_result(connection, command_id, public_id, False)


def declare_personal_explosion_reaction_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, explosion_public_id: str, actor_public_id: str,
    reaction_kind: str,
) -> PersonalExplosionResult:
    if reaction_kind not in {"none", "dodge", "dive"}:
        raise ValueError("Unknown explosion reaction")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
                 FROM cmd_command
                WHERE initiator_reference=%s AND idempotency_key=%s
                FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                    "declare_personal_explosion_reaction", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_result(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT explosion.explosion_id,explosion.encounter_id,
                      explosion.round_number,target.actor_id,
                      combatant.aware_at_start,combatant.reactions_this_round,
                      combatant.initiative_current,
                      combatant.reaction_check_modifier,
                      combatant.acted_this_round,
                      combatant.next_round_initiative_adjustment,
                      stance.may_dodge,combatant.kill_aim_damage_bonus
                 FROM enc_personal_explosion explosion
                 JOIN enc_personal_explosion_target target
                   ON target.explosion_id=explosion.explosion_id
                 JOIN actor_actor actor ON actor.actor_id=target.actor_id
                 JOIN enc_personal_combatant combatant
                   ON combatant.encounter_id=explosion.encounter_id
                  AND combatant.actor_id=target.actor_id
                 JOIN rule_personal_stance stance
                   ON stance.rule_id=combatant.stance_rule_id
                WHERE explosion.public_id=%s
                  AND explosion.explosion_status='awaiting_reactions'
                  AND actor.public_id=%s
                  AND actor.controller_reference=%s
                  AND NOT target.reaction_declared
                FOR UPDATE OF explosion,target,combatant""",
            (explosion_public_id, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator cannot declare this target's explosion reaction")
        rules = connection.execute(
            """SELECT initiative_cost_per_reaction,
                      check_modifier_per_reaction,maximum_per_round,
                      requires_awareness
                 FROM rule_personal_reaction_system"""
        ).fetchone()
        paid = reaction_kind != "none"
        if paid and rules[3] and not state[4]:
            raise ValueError("Unaware combatant cannot react")
        if paid and rules[2] is not None and state[5] >= rules[2]:
            raise ValueError("No reactions remain this round")
        if paid and (not state[10] or state[11]):
            raise ValueError("Current combat state forbids dodging or diving")
        reactions_after = state[5] + int(paid)
        follows = state[8]
        initiative_after = (
            state[6] if not paid or follows else state[6] + rules[0])
        next_after = (
            state[9] + rules[0] if paid and follows else state[9])
        check_after = state[7] + (rules[1] if paid else 0)
        timing = (
            "none" if not paid else
            "following_round" if follows else "current_round")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('declare_personal_explosion_reaction',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
                  SET reactions_this_round=%s,initiative_current=%s,
                      reaction_check_modifier=%s,
                      next_round_initiative_adjustment=%s,
                      aim_target_actor_id=NULL,aim_modifier=0,
                      kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
                WHERE encounter_id=%s AND actor_id=%s""",
            (reactions_after, initiative_after, check_after, next_after,
             state[1], state[3]),
        )
        connection.execute(
            """UPDATE enc_personal_explosion_target
                  SET reaction_declared=true,reaction_kind=%s
                WHERE explosion_id=%s AND actor_id=%s""",
            (reaction_kind, state[0], state[3]),
        )
        connection.execute(
            """INSERT INTO cmd_personal_explosion_reaction_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[3], reaction_kind, state[5],
             reactions_after, state[6], initiative_after, state[7],
             check_after, timing, state[9], next_after),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_result(connection, command_id, public_id, False)


def resolve_personal_explosion_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, explosion_public_id: str,
    random_source=None,
) -> PersonalExplosionResult:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
                 FROM cmd_command
                WHERE initiator_reference=%s AND idempotency_key=%s
                FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_personal_explosion", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_result(connection, existing[0], existing[1], True)
        explosion = connection.execute(
            """SELECT explosion.explosion_id,explosion.damage_dice,
                      explosion.damage_die_sides,explosion.flat_damage
                 FROM enc_personal_explosion explosion
                 JOIN enc_encounter encounter
                   ON encounter.encounter_id=explosion.encounter_id
                 JOIN camp_campaign campaign
                   ON campaign.campaign_id=encounter.campaign_id
                WHERE explosion.public_id=%s
                  AND explosion.explosion_status='awaiting_reactions'
                  AND campaign.owner_reference=%s
                  AND NOT EXISTS (
                    SELECT 1 FROM enc_personal_explosion_target target
                     WHERE target.explosion_id=explosion.explosion_id
                       AND NOT target.reaction_declared)
                FOR UPDATE OF explosion""",
            (explosion_public_id, initiator_reference),
        ).fetchone()
        if explosion is None:
            raise PermissionError(
                "Explosion is unavailable, incomplete, or not controlled")
        targets = connection.execute(
            """SELECT target.actor_id,target.target_order,target.armor_rule_id,
                      target.reaction_kind,armor.general_armor_rating,
                      actor.public_id,combatant.significant_actions_remaining
                 FROM enc_personal_explosion_target target
                 JOIN inv_armor_definition armor
                   ON armor.item_rule_id=target.armor_rule_id
                 JOIN actor_actor actor ON actor.actor_id=target.actor_id
                 JOIN enc_personal_explosion explosion
                   ON explosion.explosion_id=target.explosion_id
                 JOIN enc_personal_combatant combatant
                   ON combatant.encounter_id=explosion.encounter_id
                  AND combatant.actor_id=target.actor_id
                WHERE target.explosion_id=%s ORDER BY target.target_order
                FOR UPDATE OF combatant""",
            (explosion[0],),
        ).fetchall()
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_explosion',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        rolls = [
            rng.randint(1, explosion[2]) for _ in range(explosion[1])]
        for order, die in enumerate(rolls, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'explosion_damage',%s,%s,%s)""",
                (command_id, order, explosion[2], die),
            )
        shared = sum(rolls) + explosion[3]
        connection.execute(
            """INSERT INTO cmd_personal_explosion_resolution_receipt
               VALUES (%s,%s,%s,%s)""",
            (command_id, explosion[0], shared, len(targets)),
        )
        dodge_order = 0
        for actor_id, order, armor_id, reaction, armor, _, actions in targets:
            reduction = 0
            after = shared
            if reaction == "dodge":
                dodge_order += 1
                reduction = rng.randint(1, 6)
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (%s,'explosion_dodge',%s,6,%s)""",
                    (command_id, dodge_order, reduction),
                )
                after = max(0, shared - reduction)
            elif reaction == "dive":
                after = shared // 2
                connection.execute(
                    """UPDATE enc_personal_combatant
                          SET stance_rule_id=(
                                SELECT rule_id FROM rule_rule
                                 WHERE rule_code='combat.stance.prone'),
                              significant_actions_remaining=
                                GREATEST(significant_actions_remaining-1,0),
                              significant_action_losses_pending=
                                significant_action_losses_pending+
                                CASE WHEN significant_actions_remaining=0
                                     THEN 1 ELSE 0 END
                        WHERE actor_id=%s AND encounter_id=(
                            SELECT encounter_id FROM enc_personal_explosion
                             WHERE explosion_id=%s)""",
                    (actor_id, explosion[0]),
                )
            natural = connection.execute(
                """SELECT CASE WHEN EXISTS (
                       SELECT 1 FROM actor_current_species current_species
                       JOIN rule_species_trait_assignment assignment
                         ON assignment.species_rule_id=
                            current_species.species_rule_id
                       JOIN rule_species_trait trait
                         ON trait.species_trait_rule_id=
                            assignment.species_trait_rule_id
                      WHERE current_species.actor_id=%s
                        AND trait.trait_code='armored')
                   THEN 1 ELSE 0 END""",
                (actor_id,),
            ).fetchone()[0]
            total_armor = armor + natural
            penetrating = max(0, after - total_armor)
            damage_id = None
            if penetrating:
                damage_id = connection.execute(
                    """INSERT INTO health_damage_instance
                       (explosion_command_id,target_actor_id,
                        penetrating_damage)
                       VALUES (%s,%s,%s) RETURNING damage_instance_id""",
                    (command_id, actor_id, penetrating),
                ).fetchone()[0]
            connection.execute(
                """INSERT INTO cmd_personal_explosion_target_receipt
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (command_id, actor_id, order, armor_id, reaction, reduction,
                 after, total_armor, penetrating, damage_id),
            )
        connection.execute(
            """UPDATE enc_personal_explosion SET explosion_status='resolved'
                WHERE explosion_id=%s""",
            (explosion[0],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_result(connection, command_id, public_id, False)
