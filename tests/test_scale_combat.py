import unittest

from engine.scale_combat import resolve_ground_starship_damage


class GroundForceStarshipScaleTests(unittest.TestCase):
    def test_aggregates_half_dice_then_floors_both_conversions(self):
        result = resolve_ground_starship_damage(
            primary_damage_dice=17,
            additional_successful_damage_dice=(1, 1, 3),
            damage_rolls=(6,) * 19,
            armor_rating=1,
        )
        self.assertEqual(result.additional_damage_dice, 5)
        self.assertEqual(result.contributed_additional_dice, 2)
        self.assertEqual(result.combined_damage_dice, 19)
        self.assertEqual(result.personal_scale_damage, 114)
        self.assertEqual(result.converted_damage, 2)
        self.assertEqual(result.hull_damage, 1)

    def test_armor_can_stop_converted_damage_without_minimum(self):
        result = resolve_ground_starship_damage(
            primary_damage_dice=10,
            additional_successful_damage_dice=(),
            damage_rolls=(5,) * 10,
            armor_rating=1,
        )
        self.assertEqual(result.converted_damage, 1)
        self.assertEqual(result.hull_damage, 0)

    def test_rejects_fractional_or_unrecorded_dice_shortcuts(self):
        with self.assertRaisesRegex(ValueError, "match contributed"):
            resolve_ground_starship_damage(
                primary_damage_dice=1,
                additional_successful_damage_dice=(1,),
                damage_rolls=(6, 6),
                armor_rating=0,
            )


if __name__ == "__main__":
    unittest.main()
