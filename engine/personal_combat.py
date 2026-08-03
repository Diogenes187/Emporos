"""Source-faithful personal attack calculation.

Random values are inputs. This module never rolls dice or mutates campaign
state; command infrastructure records randomness and commits state separately.
"""

from dataclasses import asdict, dataclass

import psycopg


@dataclass(frozen=True)
class AttackSpecification:
    item_rule_code: str
    attack_profile_code: str
    range_rule_code: str
    difficulty_modifier: int
    damage_dice_count: int
    damage_die_sides: int
    armor_rating: int
    weapon_flat_damage_bonus: int = 0
    exceptional_effect_threshold: int = 6
    exceptional_minimum_damage: int = 1


@dataclass(frozen=True)
class AttackReceipt:
    attack_dice: tuple[int, int]
    skill_modifier: int
    characteristic_modifier: int
    difficulty_modifier: int
    circumstance_modifiers: tuple[int, ...]
    attack_total: int
    target_number: int
    effect: int
    hit: bool
    damage_dice: tuple[int, ...]
    rolled_damage: int
    effect_damage: int
    weapon_flat_damage_bonus: int
    kill_aim_damage_bonus: int
    burst_extra_damage_dice: int
    burst_extra_damage_flat: int
    panic_extra_damage_dice: int
    panic_extra_damage_flat: int
    raw_damage: int
    natural_armor_rating: int
    armor_rating: int
    penetrating_damage: int
    exceptional_minimum_applied: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _validate_dice(values: tuple[int, ...], sides: int, label: str) -> None:
    if any(not isinstance(value, int) or value < 1 or value > sides
           for value in values):
        raise ValueError(f"{label} must contain integers from 1 through {sides}")


def resolve_attack(
    specification: AttackSpecification,
    attack_dice: tuple[int, int],
    damage_dice: tuple[int, ...],
    *,
    skill_modifier: int,
    characteristic_modifier: int,
    circumstance_modifiers: tuple[int, ...] = (),
    kill_aim_damage_bonus: int = 0,
    burst_extra_damage_dice: int = 0,
    burst_extra_damage_flat: int = 0,
    panic_extra_damage_dice: int = 0,
    panic_extra_damage_flat: int = 0,
    natural_armor_rating: int = 0,
    target_number: int = 8,
    inflicts_damage: bool = True,
    damage_dice_count_override: int | None = None,
    hit_override: bool | None = None,
) -> AttackReceipt:
    """Resolve hit and post-armor damage from already-recorded random values."""
    _validate_dice(attack_dice, 6, "attack_dice")
    total = (
        sum(attack_dice)
        + skill_modifier
        + characteristic_modifier
        + specification.difficulty_modifier
        + sum(circumstance_modifiers)
    )
    effect = total - target_number
    hit = total >= target_number if hit_override is None else hit_override
    if (burst_extra_damage_dice < 0 or burst_extra_damage_flat < 0
            or panic_extra_damage_dice < 0 or panic_extra_damage_flat < 0):
        raise ValueError("burst damage bonuses cannot be negative")
    expected_damage_dice = (
        (damage_dice_count_override
         if damage_dice_count_override is not None
         else specification.damage_dice_count)
        + burst_extra_damage_dice
        + panic_extra_damage_dice
        if hit and inflicts_damage else 0
    )
    if len(damage_dice) != expected_damage_dice:
        raise ValueError(
            "damage_dice count does not match the resolved attack result"
        )
    _validate_dice(damage_dice, specification.damage_die_sides, "damage_dice")
    rolled = sum(damage_dice) if hit else 0
    effect_damage = effect if hit and inflicts_damage else 0
    if kill_aim_damage_bonus < 0:
        raise ValueError("kill aim damage bonus cannot be negative")
    if natural_armor_rating < 0:
        raise ValueError("natural armor rating cannot be negative")
    flat_damage = (
        specification.weapon_flat_damage_bonus
        if hit and inflicts_damage else 0
    )
    raw = (
        rolled + effect_damage + flat_damage + kill_aim_damage_bonus
        + burst_extra_damage_flat + panic_extra_damage_flat
        if hit and inflicts_damage else 0
    )
    total_armor = specification.armor_rating + natural_armor_rating
    penetrating = max(0, raw - total_armor)
    minimum_applied = (
        hit and inflicts_damage
        and effect >= specification.exceptional_effect_threshold
        and penetrating < specification.exceptional_minimum_damage
    )
    if minimum_applied:
        penetrating = specification.exceptional_minimum_damage
    return AttackReceipt(
        attack_dice=attack_dice,
        skill_modifier=skill_modifier,
        characteristic_modifier=characteristic_modifier,
        difficulty_modifier=specification.difficulty_modifier,
        circumstance_modifiers=circumstance_modifiers,
        attack_total=total,
        target_number=target_number,
        effect=effect,
        hit=hit,
        damage_dice=damage_dice,
        rolled_damage=rolled,
        effect_damage=effect_damage,
        weapon_flat_damage_bonus=flat_damage,
        kill_aim_damage_bonus=(
            kill_aim_damage_bonus if hit and inflicts_damage else 0),
        burst_extra_damage_dice=(
            burst_extra_damage_dice if hit and inflicts_damage else 0),
        burst_extra_damage_flat=(
            burst_extra_damage_flat if hit and inflicts_damage else 0),
        panic_extra_damage_dice=(
            panic_extra_damage_dice if hit and inflicts_damage else 0),
        panic_extra_damage_flat=(
            panic_extra_damage_flat if hit and inflicts_damage else 0),
        raw_damage=raw, natural_armor_rating=natural_armor_rating,
        armor_rating=total_armor,
        penetrating_damage=penetrating,
        exceptional_minimum_applied=minimum_applied,
    )


def load_attack_specification(
    connection: psycopg.Connection,
    *,
    item_rule_code: str,
    attack_profile_code: str,
    range_rule_code: str,
    armor_rule_code: str,
) -> AttackSpecification:
    """Load a legal attack and armor definition from canonical PostgreSQL."""
    row = connection.execute(
        """
        SELECT weapon_rule.rule_code, mode.attack_profile_code,
               range_rule.rule_code, difficulty.modifier,
               weapon.damage_dice_count, weapon.damage_die_sides,
               armor.general_armor_rating,
               weapon.flat_damage_bonus,
               damage_system.exceptional_effect_threshold,
               damage_system.exceptional_minimum_damage
        FROM rule_rule weapon_rule
        JOIN inv_weapon_definition weapon
          ON weapon.item_rule_id = weapon_rule.rule_id
        JOIN inv_weapon_attack_mode mode
          ON mode.item_rule_id = weapon.item_rule_id
        JOIN combat_attack_profile_difficulty profile_difficulty
          ON profile_difficulty.attack_profile_code =
             mode.attack_profile_code
         AND profile_difficulty.permitted
        JOIN rule_rule range_rule
          ON range_rule.rule_id = profile_difficulty.range_band_rule_id
        JOIN rule_difficulty difficulty
          ON difficulty.rule_id = profile_difficulty.difficulty_rule_id
        JOIN rule_rule armor_rule ON armor_rule.rule_code = %s
        JOIN inv_armor_definition armor
          ON armor.item_rule_id = armor_rule.rule_id
        CROSS JOIN rule_personal_damage_system damage_system
        WHERE weapon_rule.rule_code = %s
          AND mode.attack_profile_code = %s
          AND range_rule.rule_code = %s
        """,
        (armor_rule_code, item_rule_code, attack_profile_code, range_rule_code),
    ).fetchone()
    if row is None:
        raise ValueError("No legal canonical attack specification matches")
    return AttackSpecification(*row)
