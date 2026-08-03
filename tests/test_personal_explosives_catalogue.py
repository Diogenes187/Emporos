import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalExplosivesCatalogueTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_catalogue_profiles_are_exact_and_mass_is_unquantified(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT explosive.explosive_code,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams,
                          explosive.damage_dice_count,
                          explosive.damage_multiplier,
                          explosive.radius_dice_count,
                          explosive.source_mass_is_unquantified,
                          explosive.source_states_horizontal_axis_only,
                          explosive.source_states_too_large_for_grenade_launcher
                   FROM inv_personal_explosive_definition explosive
                   JOIN inv_item_definition item
                     ON item.rule_id=explosive.item_rule_id
                   ORDER BY explosive.explosive_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("plastic", 6, 200, None, 3, 1, 2, True, False, False),
            ("pocket-nuke", 12, 20000, None, 2, 20, 15, True, False, True),
            ("tdx", 12, 1000, None, 4, 1, 4, True, True, False),
        ])

    def test_use_rule_preserves_defined_and_undefined_effect_boundaries(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT skill.rule_code,use.effect_zero_multiplier,
                          use.effect_one_multiplier,
                          use.positive_effect_value_is_damage_multiplier,
                          use.negative_effect_outcome_is_unquantified,
                          use.unavailable_from_law_level
                   FROM rule_personal_explosive_use use
                   JOIN rule_rule skill
                     ON skill.rule_id=use.required_skill_rule_id"""
            ).fetchone()
        self.assertEqual(row, ("skill.demolitions", 1, 1, True, True, 1))

    def test_database_rejects_noncanonical_pocket_nuke_multiplier(self):
        with self.connect() as connection:
            with self.assertRaises(psycopg.errors.CheckViolation):
                connection.execute(
                    """UPDATE inv_personal_explosive_definition
                       SET damage_multiplier=19
                       WHERE explosive_code='pocket-nuke'"""
                )


if __name__ == "__main__":
    unittest.main()
