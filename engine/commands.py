"""Transactional gameplay commands and recorded randomness."""

import secrets
from dataclasses import dataclass, replace
from typing import Protocol

import psycopg

from engine.personal_combat import (
    AttackReceipt, load_attack_specification, resolve_attack,
)


class RandomSource(Protocol):
    def randint(self, minimum: int, maximum: int) -> int: ...


@dataclass(frozen=True)
class CommittedAttack:
    command_public_id: str
    replayed: bool
    receipt: AttackReceipt
    damage_instance_public_id: str | None = None


@dataclass(frozen=True)
class CommittedDamage:
    command_public_id: str
    replayed: bool
    damage_instance_public_id: str
    allocations: tuple[tuple[str, int, int], ...]
    actor_version_before: int
    actor_version_after: int
    unapplied_lethal_overflow: int


def _load_committed_attack(
    connection: psycopg.Connection, command_id: int, public_id: str,
    *, replayed: bool,
) -> CommittedAttack:
    draws = connection.execute(
        """SELECT draw_group, result FROM cmd_random_draw
           WHERE command_id=%s ORDER BY draw_group, draw_order""",
        (command_id,),
    ).fetchall()
    attack_dice = tuple(row[1] for row in draws if row[0] == "attack")
    if connection.execute(
        """SELECT 1 FROM cmd_personal_blind_fire_receipt
           WHERE command_id=%s""", (command_id,)).fetchone():
        attack_dice = tuple(sorted(attack_dice)[:2])
    damage_dice = tuple(row[1] for row in draws if row[0] == "damage")
    modifiers = tuple(row[0] for row in connection.execute(
        """SELECT modifier_value FROM cmd_attack_modifier
           WHERE command_id=%s ORDER BY modifier_order""",
        (command_id,),
    ).fetchall())
    row = connection.execute(
        """SELECT skill_modifier, characteristic_modifier,
                  difficulty_modifier, circumstance_modifier_total,
                  attack_total, target_number, effect, hit, rolled_damage,
                  effect_damage,weapon_flat_damage_bonus,
                  raw_damage, armor_rating,
                  natural_armor_rating,penetrating_damage,
                  exceptional_minimum_applied
                  ,kill_aim_damage_bonus
                  ,burst_extra_damage_dice,burst_extra_damage_flat
                  ,panic_extra_damage_dice,panic_extra_damage_flat
           FROM cmd_attack_receipt WHERE command_id=%s""",
        (command_id,),
    ).fetchone()
    receipt = AttackReceipt(
        attack_dice=attack_dice,
        skill_modifier=row[0],
        characteristic_modifier=row[1],
        difficulty_modifier=row[2],
        circumstance_modifiers=modifiers,
        attack_total=row[4], target_number=row[5], effect=row[6], hit=row[7],
        damage_dice=damage_dice, rolled_damage=row[8], effect_damage=row[9],
        weapon_flat_damage_bonus=row[10],
        kill_aim_damage_bonus=row[16],
        burst_extra_damage_dice=row[17],
        burst_extra_damage_flat=row[18], raw_damage=row[11],
        panic_extra_damage_dice=row[19],
        panic_extra_damage_flat=row[20],
        natural_armor_rating=row[13], armor_rating=row[12],
        penetrating_damage=row[14], exceptional_minimum_applied=row[15],
    )
    damage = connection.execute(
        """SELECT damage.public_id FROM health_damage_instance damage
           JOIN cmd_attack_receipt receipt
             ON receipt.command_id=damage.attack_command_id
            AND receipt.target_actor_id=damage.target_actor_id
           WHERE damage.attack_command_id=%s""", (command_id,)
    ).fetchone()
    return CommittedAttack(
        str(public_id), replayed, receipt, str(damage[0]) if damage else None
    )


def resolve_personal_attack_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    item_rule_code: str,
    attack_profile_code: str,
    range_rule_code: str,
    armor_rule_code: str,
    skill_modifier: int | None = None,
    characteristic_modifier: int | None = None,
    circumstance_modifiers: tuple[int, ...] = (),
    target_actor_public_id: str | None = None,
    personal_attack_public_id: str | None = None,
    shotgun_spread_armor_rule_codes: tuple[tuple[str, str], ...] = (),
    blind_fire_armor_rule_codes: tuple[tuple[str, str], ...] = (),
    firing_into_combat_armor_rule_codes: tuple[tuple[str, str], ...] = (),
    random_source: RandomSource | None = None,
) -> CommittedAttack:
    """Commit one attack or replay its prior committed result."""
    rng = random_source or secrets.SystemRandom()
    if (
        item_rule_code == "equipment.weapon.species-natural-weapon"
        and personal_attack_public_id is None
    ):
        raise ValueError(
            "Species natural weapons require an actor-bound declared attack")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id, public_id, command_status
               FROM cmd_command
               WHERE initiator_reference=%s AND idempotency_key=%s
               FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2] != "completed":
                raise RuntimeError("Idempotent command exists but is not completed")
            return _load_committed_attack(
                connection, existing[0], existing[1], replayed=True)

        personal_attack = None
        engine_modifiers = ()
        if personal_attack_public_id is not None:
            personal_attack = connection.execute(
                """SELECT attack.personal_attack_id,weapon.rule_code,
                          attack.attack_profile_code,range_rule.rule_code,
                          target.public_id,attacker.controller_reference,
                          attacker_state.reaction_check_modifier
                            + attacker_state.hasten_check_modifier
                            + attacker_state.suppression_check_modifier,
                          COALESCE(actor_skill.skill_level,
                                   required_skill.untrained_modifier),
                          characteristic_band.modifier,
                          attack.aim_modifier,attack.cover_modifier,
                          attack.stance_modifier,
                          attack.target_movement_modifier,
                          attack.kill_aim_damage_bonus,
                          attack.burst_attack_modifier,
                          attack.burst_extra_damage_dice,
                          attack.burst_extra_damage_flat,
                          attack.burst_size_rule_id,
                          attack.burst_option_rule_id
                          ,attack.suppression_fire
                          ,attack.suppression_attack_modifier
                          ,attack.panic_fire
                          ,attack.panic_attack_modifier
                          ,attack.panic_damage_burst_size_rule_id
                          ,attack.panic_extra_damage_dice
                          ,attack.panic_extra_damage_flat
                          ,attack.shotgun_spread
                          ,attack.shotgun_spread_attack_modifier
                          ,attack.shotgun_spread_damage_dice
                          ,attack.environmental_attack_modifier
                          ,attack.blind_fire
                          ,attack.extreme_range
                          ,attack.extreme_range_attack_modifier
                          ,attack.extreme_range_energy_weapon
                          ,attack.zero_gravity
                          ,attack.zero_gravity_weapon_skill_level
                          ,attack.zero_gravity_trained
                          ,attack.zero_gravity_skill_level
                          ,attack.zero_gravity_effective_skill_level
                          ,attack.zero_gravity_weapon_has_recoil
                          ,attack.zero_gravity_recoil_modifier
                          ,attack.firing_into_combat
                          ,attack.firing_into_combat_attack_modifier
                          ,attack.thrown_delivery_type
                          ,attack.thrown_target_point_reference
                          ,attack.fatigue_attack_modifier
                          ,COALESCE(assistance.laser_sight_modifier,0)
                          ,COALESCE(assistance.intelligent_weapon_modifier,0)
                   FROM enc_personal_attack attack
                   JOIN rule_rule weapon
                     ON weapon.rule_id=attack.weapon_rule_id
                   JOIN rule_rule range_rule
                     ON range_rule.rule_id=attack.range_band_rule_id
                   JOIN actor_actor target
                     ON target.actor_id=attack.target_actor_id
                   JOIN actor_actor attacker
                     ON attacker.actor_id=attack.attacker_actor_id
                   JOIN enc_personal_combatant attacker_state
                     ON attacker_state.encounter_id=attack.encounter_id
                    AND attacker_state.actor_id=attack.attacker_actor_id
                   JOIN combat_attack_profile profile
                     ON profile.attack_profile_code=
                        attack.attack_profile_code
                   JOIN inv_weapon_attack_mode mode
                     ON mode.item_rule_id=attack.weapon_rule_id
                    AND mode.attack_profile_code=attack.attack_profile_code
                   JOIN rule_skill required_skill
                     ON required_skill.rule_id=COALESCE(
                        mode.required_skill_rule_id,
                        profile.required_skill_rule_id)
                   LEFT JOIN actor_skill
                     ON actor_skill.actor_id=attack.attacker_actor_id
                    AND actor_skill.skill_rule_id=COALESCE(
                        mode.required_skill_rule_id,
                        profile.required_skill_rule_id)
                   JOIN actor_characteristic characteristic
                     ON characteristic.actor_id=attack.attacker_actor_id
                    AND characteristic.characteristic_rule_id=
                        attack.characteristic_rule_id
                   JOIN rule_characteristic_modifier_band characteristic_band
                     ON characteristic_band.characteristic_rule_id IS NULL
                    AND characteristic_band.score_range
                        @> characteristic.current_value::integer
                   LEFT JOIN enc_personal_attack_weapon_assistance assistance
                     ON assistance.personal_attack_id=attack.personal_attack_id
                   WHERE attack.public_id::text=%s
                     AND attack.attack_status='awaiting_reactions'
                   FOR UPDATE OF attack,attacker_state""",
                (personal_attack_public_id,),
            ).fetchone()
            if personal_attack is None:
                raise ValueError("Declared attack is not awaiting resolution")
            expected = (
                item_rule_code, attack_profile_code, range_rule_code,
                target_actor_public_id, initiator_reference)
            declared = (
                personal_attack[1], personal_attack[2], personal_attack[3],
                str(personal_attack[4]), personal_attack[5])
            if declared != expected:
                raise ValueError(
                    "Resolution does not match the declared attack")
            skill_modifier = personal_attack[7]
            characteristic_modifier = personal_attack[8]
            if skill_modifier is None:
                raise ValueError("Required skill does not permit untrained use")
            reaction_rows = connection.execute(
                """SELECT reaction_kind,parry_skill_modifier
                   FROM cmd_personal_reaction_receipt
                   WHERE personal_attack_id=%s ORDER BY command_id""",
                (personal_attack[0],),
            ).fetchall()
            reaction_modifiers = []
            for kind, parry_skill_modifier in reaction_rows:
                if kind == "dodge":
                    reaction_modifiers.append(-1)
                elif kind == "dodge_with_cover":
                    reaction_modifiers.append(-2)
                else:
                    reaction_modifiers.append(-parry_skill_modifier)
            engine_modifiers = (
                (personal_attack[6],) if personal_attack[6] else ()
            ) + (
                (personal_attack[9],) if personal_attack[9] else ()
            ) + (
                (personal_attack[10],) if personal_attack[10] else ()
            ) + (
                (personal_attack[11],) if personal_attack[11] else ()
            ) + (
                (personal_attack[12],) if personal_attack[12] else ()
            ) + (
                (personal_attack[14],) if personal_attack[14] else ()
            ) + (
                (personal_attack[20],) if personal_attack[20] else ()
            ) + (
                (personal_attack[22],) if personal_attack[22] else ()
            ) + (
                (personal_attack[27],) if personal_attack[27] else ()
            ) + (
                (personal_attack[29],) if personal_attack[29] else ()
            ) + (
                (personal_attack[32],) if personal_attack[32] else ()
            ) + (
                (personal_attack[42],) if personal_attack[42] else ()
            ) + tuple(reaction_modifiers)
            kill_aim_damage_bonus = personal_attack[13]
            burst_extra_damage_dice = personal_attack[15]
            burst_extra_damage_flat = personal_attack[16]
            burst_size_rule_id = personal_attack[17]
            burst_option_rule_id = personal_attack[18]
            suppression_fire = personal_attack[19]
            suppression_attack_modifier = personal_attack[20]
            panic_fire = personal_attack[21]
            panic_attack_modifier = personal_attack[22]
            panic_damage_burst_size_rule_id = personal_attack[23]
            panic_extra_damage_dice = personal_attack[24]
            panic_extra_damage_flat = personal_attack[25]
            shotgun_spread = personal_attack[26]
            shotgun_spread_attack_modifier = personal_attack[27]
            shotgun_spread_damage_dice = personal_attack[28]
            blind_fire = personal_attack[30]
            extreme_range = personal_attack[31]
            extreme_range_energy_weapon = personal_attack[33]
            zero_gravity = personal_attack[34]
            if zero_gravity:
                skill_modifier = personal_attack[38]
                if personal_attack[40]:
                    engine_modifiers += (personal_attack[40],)
            firing_into_combat = personal_attack[41]
            thrown_delivery_type = personal_attack[43]
            thrown_target_point_reference = personal_attack[44]
            if personal_attack[45]:
                engine_modifiers += (personal_attack[45],)
            if personal_attack[46]:
                engine_modifiers += (personal_attack[46],)
            if personal_attack[47]:
                engine_modifiers += (personal_attack[47],)
            if blind_fire:
                skill_modifier = 0
            ammunition_required = connection.execute(
                """SELECT ammunition_consumed
                   FROM enc_personal_attack
                   WHERE personal_attack_id=%s""",
                (personal_attack[0],),
            ).fetchone()[0]
            if ammunition_required:
                consumed = connection.execute(
                    """UPDATE actor_weapon_state weapon_state
                       SET rounds_loaded=rounds_loaded-%s
                       FROM enc_personal_attack attack
                       WHERE attack.personal_attack_id=%s
                         AND weapon_state.actor_id=attack.attacker_actor_id
                         AND weapon_state.weapon_rule_id=attack.weapon_rule_id
                         AND weapon_state.ready
                         AND weapon_state.rounds_loaded >= %s
                         AND EXISTS (
                             SELECT 1
                             FROM inv_ammunition_definition ammunition
                             WHERE ammunition.weapon_rule_id=
                                   attack.weapon_rule_id
                               AND ammunition.ammunition_rule_id=
                                   weapon_state.loaded_ammunition_rule_id
                         )
                       RETURNING weapon_state.rounds_loaded""",
                    (ammunition_required, personal_attack[0],
                     ammunition_required),
                ).fetchone()
                if consumed is None:
                    raise ValueError(
                        "Declared weapon no longer has its required ammunition")
        elif skill_modifier is None or characteristic_modifier is None:
            raise ValueError(
                "Standalone attacks require explicit skill and characteristic modifiers")
        else:
            kill_aim_damage_bonus = 0
            burst_extra_damage_dice = 0
            burst_extra_damage_flat = 0
            burst_size_rule_id = None
            burst_option_rule_id = None
            suppression_fire = False
            suppression_attack_modifier = 0
            panic_fire = False
            panic_attack_modifier = 0
            panic_damage_burst_size_rule_id = None
            panic_extra_damage_dice = 0
            panic_extra_damage_flat = 0
            shotgun_spread = False
            shotgun_spread_attack_modifier = 0
            shotgun_spread_damage_dice = None
            blind_fire = False
            extreme_range = False
            extreme_range_energy_weapon = False
            zero_gravity = False
            firing_into_combat = False
            thrown_delivery_type = None
            thrown_target_point_reference = None
        all_circumstance_modifiers = (
            tuple(circumstance_modifiers) + engine_modifiers)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_personal_attack',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        specification = load_attack_specification(
            connection, item_rule_code=item_rule_code,
            attack_profile_code=attack_profile_code,
            range_rule_code=range_rule_code, armor_rule_code=armor_rule_code)
        core = connection.execute(
            """SELECT dice_count,die_sides,target_number
               FROM rule_check_system""").fetchone()
        raw_attack_dice = tuple(
            rng.randint(1, core[1])
            for _ in range(3 if blind_fire else core[0]))
        attack_dice = (
            tuple(sorted(raw_attack_dice)[:core[0]])
            if blind_fire else raw_attack_dice)
        predicted_total = (
            sum(attack_dice) + skill_modifier + characteristic_modifier
            + specification.difficulty_modifier
            + sum(all_circumstance_modifiers)
        )
        original_attack_hit = predicted_total >= core[2]
        original_target_public_id = target_actor_public_id
        combat_scatter = None
        combat_nearest_tier = None
        combat_nearest_count = None
        combat_tie_selection = None
        combat_selected_actor_id = None
        combat_kill_aim_excluded = 0
        redirected_hit = False
        thrown_scatter_draw = None
        thrown_scatter_bearing = None
        thrown_scatter_distance = 0
        blind_targets = ()
        blind_selection = None
        if blind_fire:
            blind_targets = connection.execute(
                """SELECT actor.public_id,target.target_actor_id,
                          target.target_order
                   FROM enc_personal_blind_fire_target target
                   JOIN actor_actor actor
                     ON actor.actor_id=target.target_actor_id
                   WHERE target.personal_attack_id=%s
                   ORDER BY target.target_order""",
                (personal_attack[0],)).fetchall()
            armor_by_target = dict(blind_fire_armor_rule_codes)
            if set(armor_by_target) != {
                str(row[0]) for row in blind_targets
            }:
                raise ValueError(
                    "Blind fire requires armor for every eligible target")
            if predicted_total >= core[2]:
                blind_selection = rng.randint(1, len(blind_targets))
                selected = blind_targets[blind_selection - 1]
                target_actor_public_id = str(selected[0])
                armor_rule_code = armor_by_target[target_actor_public_id]
                specification = load_attack_specification(
                    connection, item_rule_code=item_rule_code,
                    attack_profile_code=attack_profile_code,
                    range_rule_code=range_rule_code,
                    armor_rule_code=armor_rule_code)
            else:
                target_actor_public_id = None
        if firing_into_combat and not original_attack_hit:
            combat_scatter = rng.randint(1, 6)
            if combat_scatter >= 4:
                combat_targets = connection.execute(
                    """SELECT target.target_actor_id,actor.public_id,
                              target.proximity_tier,target.target_order
                       FROM enc_personal_firing_into_combat_target target
                       JOIN actor_actor actor
                         ON actor.actor_id=target.target_actor_id
                       WHERE target.personal_attack_id=%s
                       ORDER BY target.proximity_tier,target.target_order""",
                    (personal_attack[0],)).fetchall()
                combat_nearest_tier = combat_targets[0][2]
                nearest = [
                    row for row in combat_targets
                    if row[2] == combat_nearest_tier]
                combat_nearest_count = len(nearest)
                if len(nearest) > 1:
                    combat_tie_selection = rng.randint(1, len(nearest))
                    selected = nearest[combat_tie_selection - 1]
                else:
                    selected = nearest[0]
                combat_selected_actor_id = selected[0]
                target_actor_public_id = str(selected[1])
                armor_by_target = dict(
                    firing_into_combat_armor_rule_codes)
                expected_targets = {
                    str(row[1]) for row in combat_targets}
                if set(armor_by_target) != expected_targets:
                    raise ValueError(
                        "Firing into Combat requires armor for every roster target")
                armor_rule_code = armor_by_target[target_actor_public_id]
                specification = load_attack_specification(
                    connection,item_rule_code=item_rule_code,
                    attack_profile_code=attack_profile_code,
                    range_rule_code=range_rule_code,
                    armor_rule_code=armor_rule_code)
                redirected_hit = True
                combat_kill_aim_excluded = kill_aim_damage_bonus
                kill_aim_damage_bonus = 0
        natural_armor_rating = 0
        if target_actor_public_id is not None:
            natural_armor_rating = connection.execute(
                """SELECT CASE WHEN EXISTS (
                       SELECT 1
                       FROM actor_current_species current_species
                       JOIN rule_species_trait_assignment assignment
                         ON assignment.species_rule_id=
                            current_species.species_rule_id
                       JOIN rule_species_trait trait
                         ON trait.species_trait_rule_id=
                            assignment.species_trait_rule_id
                       JOIN actor_actor actor
                         ON actor.actor_id=current_species.actor_id
                       WHERE actor.public_id=%s
                         AND trait.trait_code='armored'
                   ) THEN 1 ELSE 0 END""",
                (target_actor_public_id,),
            ).fetchone()[0]
        inflicts_direct_damage = (
            not suppression_fire and thrown_delivery_type != "payload")
        damage_dice = (
            tuple(rng.randint(1, specification.damage_die_sides)
                  for _ in range(
                      (shotgun_spread_damage_dice
                       if shotgun_spread_damage_dice is not None
                       else specification.damage_dice_count)
                      + burst_extra_damage_dice
                      + panic_extra_damage_dice))
            if (predicted_total >= core[2] or redirected_hit)
            and inflicts_direct_damage else ()
        )
        receipt = resolve_attack(
            specification, attack_dice, damage_dice,
            skill_modifier=skill_modifier,
            characteristic_modifier=characteristic_modifier,
            circumstance_modifiers=all_circumstance_modifiers,
            kill_aim_damage_bonus=kill_aim_damage_bonus,
            burst_extra_damage_dice=burst_extra_damage_dice,
            burst_extra_damage_flat=burst_extra_damage_flat,
            panic_extra_damage_dice=panic_extra_damage_dice,
            panic_extra_damage_flat=panic_extra_damage_flat,
            natural_armor_rating=natural_armor_rating,
            target_number=core[2], inflicts_damage=inflicts_direct_damage,
            damage_dice_count_override=shotgun_spread_damage_dice,
            hit_override=True if redirected_hit else None)
        if thrown_delivery_type is not None and not receipt.hit:
            thrown_scatter_draw = rng.randint(1, 360)
            thrown_scatter_bearing = thrown_scatter_draw - 1
            thrown_scatter_distance = max(0, 6 + receipt.effect)
        damage_before_extreme_reduction = receipt.raw_damage
        extreme_energy_reduction = 0
        if extreme_range and extreme_range_energy_weapon and receipt.hit:
            reduced_damage = (receipt.raw_damage + 1) // 2
            extreme_energy_reduction = receipt.raw_damage - reduced_damage
            penetrating = max(0, reduced_damage - receipt.armor_rating)
            minimum_applied = (
                receipt.effect >= specification.exceptional_effect_threshold
                and penetrating < specification.exceptional_minimum_damage
            )
            if minimum_applied:
                penetrating = specification.exceptional_minimum_damage
            receipt = replace(
                receipt, raw_damage=reduced_damage,
                penetrating_damage=penetrating,
                exceptional_minimum_applied=minimum_applied,
            )
        for group, values, sides in (
            ("attack", raw_attack_dice, core[1]),
            ("damage", damage_dice, specification.damage_die_sides),
        ):
            for order, value in enumerate(values, 1):
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (command_id, group, order, sides, value))
        if blind_selection is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'blind_target',1,%s,%s)""",
                (command_id, len(blind_targets), blind_selection))
        if combat_scatter is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'combat_scatter',1,6,%s)""",
                (command_id,combat_scatter))
        if combat_tie_selection is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'combat_nearest_tie',1,%s,%s)""",
                (command_id,combat_nearest_count,combat_tie_selection))
        if thrown_scatter_draw is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'thrown_scatter_direction',1,360,%s)""",
                (command_id,thrown_scatter_draw))
        weapon_id, armor_id, range_id = connection.execute(
            """SELECT
                 (SELECT rule_id FROM rule_rule WHERE rule_code=%s),
                 (SELECT rule_id FROM rule_rule WHERE rule_code=%s),
                 (SELECT rule_id FROM rule_rule WHERE rule_code=%s)""",
            (item_rule_code, armor_rule_code, range_rule_code),
        ).fetchone()
        target_actor_id = None
        if target_actor_public_id is not None:
            get_actor = connection.execute(
                "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                (target_actor_public_id,),
            ).fetchone()
            if get_actor is None:
                raise ValueError("Target actor does not exist")
            target_actor_id = get_actor[0]
        original_target_actor_id = connection.execute(
            "SELECT actor_id FROM actor_actor WHERE public_id=%s",
            (original_target_public_id,)).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_attack_receipt
               (command_id,weapon_rule_id,armor_rule_id,attack_profile_code,
                range_band_rule_id,skill_modifier,characteristic_modifier,
                circumstance_modifier_total,difficulty_modifier,attack_total,
                target_number,effect,hit,rolled_damage,effect_damage,raw_damage,
                armor_rating,penetrating_damage,
                exceptional_minimum_applied,target_actor_id,
                kill_aim_damage_bonus,natural_armor_rating,
                weapon_flat_damage_bonus,burst_size_rule_id,
                burst_option_rule_id,burst_attack_modifier,
                burst_extra_damage_dice,burst_extra_damage_flat,
                suppression_fire,suppression_attack_modifier,
                panic_fire,panic_attack_modifier,
                panic_damage_burst_size_rule_id,
                panic_extra_damage_dice,panic_extra_damage_flat,
                shotgun_spread,shotgun_spread_attack_modifier,
                shotgun_spread_damage_dice,extreme_range_energy_reduction)
               VALUES
               (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s)""",
            (command_id, weapon_id, armor_id, attack_profile_code, range_id,
             skill_modifier, characteristic_modifier,
             sum(all_circumstance_modifiers), specification.difficulty_modifier,
             receipt.attack_total, receipt.target_number, receipt.effect,
             receipt.hit, receipt.rolled_damage, receipt.effect_damage,
             receipt.raw_damage, receipt.armor_rating,
             receipt.penetrating_damage,
             receipt.exceptional_minimum_applied, target_actor_id,
             receipt.kill_aim_damage_bonus,receipt.natural_armor_rating,
             receipt.weapon_flat_damage_bonus,burst_size_rule_id,
             burst_option_rule_id,
             personal_attack[14] if personal_attack is not None else 0,
             receipt.burst_extra_damage_dice,
             receipt.burst_extra_damage_flat,suppression_fire,
             suppression_attack_modifier,panic_fire,panic_attack_modifier,
             panic_damage_burst_size_rule_id,
             receipt.panic_extra_damage_dice,
             receipt.panic_extra_damage_flat,shotgun_spread,
             shotgun_spread_attack_modifier,shotgun_spread_damage_dice,
             extreme_energy_reduction))
        if thrown_delivery_type is not None:
            connection.execute(
                """INSERT INTO cmd_personal_thrown_weapon_receipt
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (command_id,personal_attack[0],thrown_delivery_type,
                 receipt.hit,receipt.effect,thrown_target_point_reference,
                 thrown_scatter_draw,thrown_scatter_bearing,
                 thrown_scatter_distance,
                 thrown_delivery_type=="payload",
                 thrown_delivery_type=="impact" and receipt.hit))
        if blind_fire:
            selected_actor_id = (
                blind_targets[blind_selection - 1][1]
                if blind_selection is not None else None)
            connection.execute(
                """INSERT INTO cmd_personal_blind_fire_receipt
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (command_id, personal_attack[0], max(raw_attack_dice),
                 len(blind_targets), blind_selection, selected_actor_id))
            if selected_actor_id is not None:
                connection.execute(
                    """UPDATE enc_personal_attack SET target_actor_id=%s
                       WHERE personal_attack_id=%s""",
                    (selected_actor_id, personal_attack[0]))
        if extreme_range:
            connection.execute(
                """INSERT INTO cmd_personal_extreme_range_receipt
                   (command_id,personal_attack_id,energy_reduction_applied,
                    damage_before_energy_reduction,
                    damage_after_energy_reduction)
                   VALUES (%s,%s,%s,%s,%s)""",
                (command_id, personal_attack[0],
                 extreme_range_energy_weapon,
                 damage_before_extreme_reduction, receipt.raw_damage),
            )
        if firing_into_combat:
            connection.execute(
                """INSERT INTO cmd_personal_firing_into_combat_receipt
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (command_id,personal_attack[0],original_target_actor_id,
                 original_attack_hit,combat_scatter,redirected_hit,
                 combat_nearest_tier,combat_nearest_count,
                 combat_tie_selection,combat_selected_actor_id,
                 receipt.effect,combat_kill_aim_excluded))
        if zero_gravity:
            connection.execute(
                """INSERT INTO cmd_personal_zero_gravity_receipt
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (command_id,personal_attack[0],personal_attack[35],
                 personal_attack[36],personal_attack[37],
                 personal_attack[38],personal_attack[39],
                 personal_attack[40]))
        damage_public_id = None
        if target_actor_id is not None and receipt.penetrating_damage > 0:
            damage_public_id = connection.execute(
                """INSERT INTO health_damage_instance
                   (attack_command_id,target_actor_id,penetrating_damage)
                   VALUES (%s,%s,%s) RETURNING public_id""",
                (command_id, target_actor_id, receipt.penetrating_damage),
            ).fetchone()[0]
        if shotgun_spread:
            armor_by_target = dict(shotgun_spread_armor_rule_codes)
            spread_targets = connection.execute(
                """SELECT target.target_actor_id,actor.public_id,
                          target.target_order,target.is_primary
                   FROM enc_personal_shotgun_spread_target target
                   JOIN actor_actor actor
                     ON actor.actor_id=target.target_actor_id
                   WHERE target.personal_attack_id=%s
                   ORDER BY target.target_order""",
                (personal_attack[0],),
            ).fetchall()
            expected_secondary = {
                str(row[1]) for row in spread_targets if not row[3]}
            if set(armor_by_target) != expected_secondary:
                raise ValueError(
                    "Shotgun spread requires armor for every nearby target")
            connection.execute(
                """INSERT INTO cmd_personal_shotgun_spread_receipt
                   VALUES (%s,%s,true,true,%s)""",
                (command_id, personal_attack[0], len(spread_targets)))
            for actor_id, actor_public, order, is_primary in spread_targets:
                selected_armor = (
                    armor_rule_code if is_primary
                    else armor_by_target[str(actor_public)])
                armor_row = connection.execute(
                    """SELECT armor.item_rule_id,armor.general_armor_rating
                       FROM rule_rule rule
                       JOIN inv_armor_definition armor
                         ON armor.item_rule_id=rule.rule_id
                       WHERE rule.rule_code=%s""",
                    (selected_armor,),
                ).fetchone()
                if armor_row is None:
                    raise ValueError("Shotgun spread target armor does not exist")
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
                           AND trait.trait_code='armored'
                       ) THEN 1 ELSE 0 END""",
                    (actor_id,),
                ).fetchone()[0]
                total_armor = armor_row[1] + natural
                penetrating = max(0, receipt.raw_damage - total_armor)
                if (receipt.hit
                        and receipt.effect >=
                            specification.exceptional_effect_threshold
                        and penetrating <
                            specification.exceptional_minimum_damage):
                    penetrating = specification.exceptional_minimum_damage
                damage_id = None
                if is_primary and damage_public_id is not None:
                    damage_id = connection.execute(
                        """SELECT damage_instance_id
                           FROM health_damage_instance
                           WHERE attack_command_id=%s
                             AND target_actor_id=%s""",
                        (command_id, actor_id),
                    ).fetchone()[0]
                elif penetrating > 0:
                    damage_id = connection.execute(
                        """INSERT INTO health_damage_instance
                           (attack_command_id,target_actor_id,
                            penetrating_damage)
                           VALUES (%s,%s,%s) RETURNING damage_instance_id""",
                        (command_id, actor_id, penetrating),
                    ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_personal_shotgun_spread_target_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (command_id, actor_id, order, is_primary, armor_row[0],
                     total_armor, receipt.raw_damage, penetrating, damage_id))
        for order, modifier in enumerate(all_circumstance_modifiers, 1):
            connection.execute(
                """INSERT INTO cmd_attack_modifier
                   (command_id,modifier_order,modifier_value)
                   VALUES (%s,%s,%s)""",
                (command_id, order, modifier))
        if personal_attack is not None:
            connection.execute(
                """UPDATE cmd_attack_receipt SET personal_attack_id=%s
                   WHERE command_id=%s""",
                (personal_attack[0], command_id))
            connection.execute(
                """UPDATE enc_personal_attack SET attack_status='resolved',
                   resolved_at=clock_timestamp()
                   WHERE personal_attack_id=%s""", (personal_attack[0],))
            if suppression_fire:
                rule = connection.execute(
                    """SELECT check_modifier,duration_rounds
                       FROM rule_personal_suppression_fire"""
                ).fetchone()
                target_state = connection.execute(
                    """SELECT attack.target_actor_id,combatant.initiative_current,
                              combatant.suppression_check_modifier,
                              EXISTS (
                                SELECT 1 FROM enc_personal_suppression_immunity i
                                WHERE i.encounter_id=attack.encounter_id
                                  AND i.actor_id=attack.target_actor_id
                              )
                       FROM enc_personal_attack attack
                       JOIN enc_personal_combatant combatant
                         ON combatant.encounter_id=attack.encounter_id
                        AND combatant.actor_id=attack.target_actor_id
                       WHERE attack.personal_attack_id=%s
                       FOR UPDATE OF combatant""",
                    (personal_attack[0],),
                ).fetchone()
                applied = receipt.hit and not target_state[3]
                initiative_after = (
                    target_state[1] - max(receipt.effect, 0)
                    if applied else target_state[1])
                check_after = rule[0] if applied else target_state[2]
                expires = None
                if applied:
                    round_number = connection.execute(
                        """SELECT round_number FROM enc_personal_attack
                           WHERE personal_attack_id=%s""",
                        (personal_attack[0],),
                    ).fetchone()[0]
                    expires = round_number + rule[1]
                    connection.execute(
                        """UPDATE enc_personal_combatant
                           SET initiative_current=%s,
                               suppression_check_modifier=%s,
                               suppression_expires_after_round=%s,
                               suppression_action_required=true
                           WHERE encounter_id=(
                               SELECT encounter_id FROM enc_personal_attack
                               WHERE personal_attack_id=%s)
                             AND actor_id=%s""",
                        (initiative_after, check_after, expires,
                         personal_attack[0], target_state[0]))
                connection.execute(
                    """INSERT INTO cmd_personal_suppression_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (command_id, personal_attack[0], target_state[0],
                     target_state[3], applied, receipt.effect,
                     target_state[1], initiative_after, target_state[2],
                     check_after, expires))
            elif receipt.hit:
                connection.execute(
                    """UPDATE enc_personal_combatant combatant
                       SET kill_aim_target_actor_id=NULL,
                           kill_aim_damage_bonus=0
                       FROM enc_personal_attack attack
                       WHERE attack.personal_attack_id=%s
                         AND combatant.encounter_id=attack.encounter_id
                         AND combatant.actor_id=attack.target_actor_id""",
                    (personal_attack[0],))
            if panic_fire:
                ammunition_used = connection.execute(
                    """SELECT ammunition_consumed FROM enc_personal_attack
                       WHERE personal_attack_id=%s""",
                    (personal_attack[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_personal_panic_fire_receipt
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (command_id, personal_attack[0], ammunition_used,
                     panic_damage_burst_size_rule_id,
                     receipt.panic_extra_damage_dice,
                     receipt.panic_extra_damage_flat))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "personal_attack_hit" if receipt.hit
             else "personal_attack_missed"))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedAttack(
            str(public_id), False, receipt,
            str(damage_public_id) if damage_public_id else None,
        )


def apply_personal_damage_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    damage_instance_public_id: str,
    allocations: tuple[tuple[str, int], ...],
) -> CommittedDamage:
    """Apply a player's legal Str/Dex/End allocation exactly once."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("apply_personal_damage", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            rows = connection.execute(
                """SELECT r.rule_code,a.allocated_damage,a.resulting_value
                   FROM cmd_damage_receipt receipt
                   JOIN health_damage_allocation a
                     ON a.damage_instance_id=receipt.damage_instance_id
                   JOIN rule_rule r ON r.rule_id=a.characteristic_rule_id
                   WHERE receipt.command_id=%s ORDER BY a.allocation_order""",
                (existing[0],),
            ).fetchall()
            receipt = connection.execute(
                """SELECT d.public_id,r.actor_version_before,
                          r.actor_version_after,r.unapplied_lethal_overflow
                   FROM cmd_damage_receipt r JOIN health_damage_instance d
                     ON d.damage_instance_id=r.damage_instance_id
                   WHERE r.command_id=%s""", (existing[0],)
            ).fetchone()
            return CommittedDamage(
                str(existing[1]), True, str(receipt[0]),
                tuple(rows), receipt[1], receipt[2], receipt[3])

        damage = connection.execute(
            """SELECT d.damage_instance_id,d.target_actor_id,
                      d.penetrating_damage,d.allocation_status,
                      a.controller_reference,a.damage_sequence_started,
                      a.concurrency_version
               FROM health_damage_instance d JOIN actor_actor a
                 ON a.actor_id=d.target_actor_id
               WHERE d.public_id=%s FOR UPDATE OF d,a""",
            (damage_instance_public_id,),
        ).fetchone()
        if damage is None:
            raise ValueError("Damage instance does not exist")
        if damage[3] != "pending":
            raise ValueError("Damage has already been allocated")
        if damage[4] != initiator_reference:
            raise PermissionError("Initiator does not control the target actor")
        allocation_map = dict(allocations)
        if len(allocation_map) != len(allocations):
            raise ValueError("A characteristic may be allocated only once")
        if any(value <= 0 for value in allocation_map.values()):
            raise ValueError("Allocated damage must be positive")
        allowed = {
            "characteristic.strength", "characteristic.dexterity",
            "characteristic.endurance",
        }
        if not set(allocation_map) <= allowed:
            raise ValueError("Damage may use only physical characteristics")
        states = dict(connection.execute(
            """SELECT r.rule_code,c.current_value
               FROM actor_characteristic c JOIN rule_rule r
                 ON r.rule_id=c.characteristic_rule_id
               WHERE c.actor_id=%s AND r.rule_code=ANY(%s)""",
            (damage[1], list(allowed)),
        ).fetchall())
        if set(states) != allowed:
            raise ValueError("Target lacks complete physical characteristics")
        remaining_physical = sum(states.values())
        applicable_damage = min(damage[2], remaining_physical)
        lethal_overflow = damage[2] - applicable_damage
        if sum(allocation_map.values()) != applicable_damage:
            raise ValueError(
                "Allocations must equal damage up to the remaining physical "
                "characteristics")
        if any(allocation_map.get(code, 0) > states[code] for code in allowed):
            raise ValueError("Allocation cannot reduce a characteristic below zero")
        if not damage[5]:
            required_endurance = min(
                applicable_damage, states["characteristic.endurance"])
            if allocation_map.get("characteristic.endurance", 0) != required_endurance:
                raise ValueError("First damage must be applied to Endurance")

        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_personal_damage',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        results = []
        for order, (code, amount) in enumerate(allocations, 1):
            resulting = states[code] - amount
            characteristic_id = connection.execute(
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (code,)
            ).fetchone()[0]
            connection.execute(
                """UPDATE actor_characteristic SET current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (resulting, damage[1], characteristic_id))
            connection.execute(
                """INSERT INTO health_damage_allocation
                   (damage_instance_id,characteristic_rule_id,allocated_damage,
                    resulting_value,allocation_order)
                   VALUES (%s,%s,%s,%s,%s)""",
                (damage[0], characteristic_id, amount, resulting, order))
            results.append((code, amount, resulting))
        connection.execute(
            """UPDATE health_damage_instance damage
               SET allocation_status='applied',
                   applied_at=clock_timestamp(),
                   applied_campaign_day=clock.day_number,
                   applied_campaign_second=clock.second_of_day
               FROM actor_actor actor
               JOIN camp_clock clock
                 ON clock.campaign_id=actor.campaign_id
               WHERE damage.damage_instance_id=%s
                 AND actor.actor_id=damage.target_actor_id""",
            (damage[0],))
        connection.execute(
            """UPDATE actor_actor SET damage_sequence_started=true,
               concurrency_version=concurrency_version+1 WHERE actor_id=%s""",
            (damage[1],))
        connection.execute(
            """INSERT INTO cmd_damage_receipt
               (command_id,damage_instance_id,target_actor_id,total_damage,
                actor_version_before,actor_version_after,
                unapplied_lethal_overflow)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, damage[0], damage[1], damage[2], damage[6],
             damage[6]+1, lethal_overflow))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_damage_applied')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedDamage(
            str(public_id), False, damage_instance_public_id,
            tuple(results), damage[6], damage[6]+1, lethal_overflow)
