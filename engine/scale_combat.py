"""Pure CE-COMBAT-016 ground-force to starship scale conversion."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GroundStarshipDamage:
    primary_damage_dice: int
    additional_damage_dice: int
    contributed_additional_dice: int
    combined_damage_dice: int
    damage_rolls: tuple[int, ...]
    personal_scale_damage: int
    converted_damage: int
    armor_rating: int
    hull_damage: int


def resolve_ground_starship_damage(
    *, primary_damage_dice: int,
    additional_successful_damage_dice: tuple[int, ...],
    damage_rolls: tuple[int, ...],
    armor_rating: int,
) -> GroundStarshipDamage:
    """Resolve the agreed cumulative-dice conversion after successful hits."""
    if primary_damage_dice <= 0:
        raise ValueError("Primary successful weapon must contribute damage dice")
    if any(value <= 0 for value in additional_successful_damage_dice):
        raise ValueError("Additional successful weapon dice must be positive")
    if armor_rating < 0:
        raise ValueError("Starship armor cannot be negative")
    additional = sum(additional_successful_damage_dice)
    contributed = additional // 2
    combined = primary_damage_dice + contributed
    if len(damage_rolls) != combined:
        raise ValueError("Damage rolls must match contributed volley dice")
    if any(value < 1 or value > 6 for value in damage_rolls):
        raise ValueError("Ground-force damage dice are D6")
    personal = sum(damage_rolls)
    converted = personal // 50
    return GroundStarshipDamage(
        primary_damage_dice, additional, contributed, combined,
        damage_rolls, personal, converted, armor_rating,
        max(0, converted-armor_rating),
    )
