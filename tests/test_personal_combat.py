import unittest

from engine.personal_combat import AttackSpecification, resolve_attack


SPEC = AttackSpecification(
    "equipment.weapon.dagger", "close-quarters", "combat.range.personal",
    0, 1, 6, 3,
)


class PersonalCombatResolutionTests(unittest.TestCase):
    def test_hit_adds_effect_then_subtracts_armor(self):
        receipt = resolve_attack(
            SPEC, (4, 4), (5,), skill_modifier=1,
            characteristic_modifier=0,
        )
        self.assertEqual(receipt.attack_total, 9)
        self.assertEqual(receipt.effect, 1)
        self.assertEqual(receipt.raw_damage, 6)
        self.assertEqual(receipt.penetrating_damage, 3)

    def test_miss_inflicts_no_damage(self):
        receipt = resolve_attack(
            SPEC, (1, 2), (), skill_modifier=0,
            characteristic_modifier=0,
        )
        self.assertFalse(receipt.hit)
        self.assertEqual(receipt.penetrating_damage, 0)

    def test_effect_six_hit_always_penetrates_for_one(self):
        heavy_armor = AttackSpecification(
            "equipment.weapon.dagger", "close-quarters",
            "combat.range.personal", 0, 1, 6, 99,
        )
        receipt = resolve_attack(
            heavy_armor, (6, 6), (1,), skill_modifier=2,
            characteristic_modifier=0,
        )
        self.assertEqual(receipt.effect, 6)
        self.assertEqual(receipt.penetrating_damage, 1)
        self.assertTrue(receipt.exceptional_minimum_applied)

    def test_rejects_unrecordable_die_values(self):
        with self.assertRaises(ValueError):
            resolve_attack(
                SPEC, (0, 7), (3,), skill_modifier=0,
                characteristic_modifier=0,
            )

    def test_grouped_burst_adds_recorded_dice_and_flat_damage(self):
        receipt = resolve_attack(
            SPEC, (4, 4), (2, 3), skill_modifier=0,
            characteristic_modifier=0,
            burst_extra_damage_dice=1,
            burst_extra_damage_flat=1,
        )
        self.assertEqual(receipt.rolled_damage, 5)
        self.assertEqual(receipt.burst_extra_damage_dice, 1)
        self.assertEqual(receipt.burst_extra_damage_flat, 1)
        self.assertEqual(receipt.raw_damage, 6)
