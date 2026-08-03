import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1MeleeWeaponCapabilityTests(unittest.TestCase):
    def test_lengths_preserve_exact_approximate_and_range_bases(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT attack.entry_code,capability.minimum_length_mm,
                          capability.maximum_length_mm,
                          capability.length_measurement_basis
                   FROM rule_book1_melee_weapon_capability capability
                   JOIN rule_book1_melee_attack attack
                     ON attack.weapon_item_rule_id=
                        capability.weapon_item_rule_id
                   WHERE capability.minimum_length_mm IS NOT NULL
                   ORDER BY attack.entry_code"""
            ).fetchall()
        self.assertEqual(len(rows), 10)
        self.assertIn(("blade",300,300,"approximate"), rows)
        self.assertIn(("foil",800,800,"exact"), rows)
        self.assertIn(("pike",3000,4000,"range"), rows)

    def test_two_handed_and_dagger_load_rules_are_typed(self):
        with psycopg.connect(DSN) as connection:
            two_handed = connection.execute(
                """SELECT attack.entry_code
                   FROM rule_book1_melee_weapon_capability capability
                   JOIN rule_book1_melee_attack attack
                     ON attack.weapon_item_rule_id=
                        capability.weapon_item_rule_id
                   WHERE capability.requires_two_hands
                   ORDER BY attack.entry_code"""
            ).fetchall()
            dagger = connection.execute(
                """SELECT capability.worn_mass_ignored_for_load,
                          capability.utility_tool
                   FROM rule_book1_melee_weapon_capability capability
                   JOIN rule_book1_melee_attack attack
                     ON attack.weapon_item_rule_id=
                        capability.weapon_item_rule_id
                   WHERE attack.entry_code='dagger'"""
            ).fetchone()
        self.assertEqual(two_handed, [
            ("broadsword",),("halberd",),("pike",)])
        self.assertEqual(dagger, (True,True))

    def test_bayonet_equivalence_and_cudgel_boundaries_are_relational(self):
        with psycopg.connect(DSN) as connection:
            bayonet = connection.execute(
                """SELECT capability.frequently_attached_to_rifle,
                          equivalent.rule_code
                   FROM rule_book1_melee_weapon_capability capability
                   JOIN rule_book1_melee_attack attack
                     ON attack.weapon_item_rule_id=
                        capability.weapon_item_rule_id
                   JOIN rule_rule equivalent
                     ON equivalent.rule_id=
                        capability.unattached_equivalent_weapon_rule_id
                   WHERE attack.entry_code='bayonet'"""
            ).fetchone()
            cudgel = connection.execute(
                """SELECT capability.improvisable_from_standing_tree,
                          capability.improvisable_from_unloaded_long_gun,
                          capability.laser_long_gun_prohibited
                   FROM rule_book1_melee_weapon_capability capability
                   JOIN rule_book1_melee_attack attack
                     ON attack.weapon_item_rule_id=
                        capability.weapon_item_rule_id
                   WHERE attack.entry_code='cudgel'"""
            ).fetchone()
        self.assertEqual(bayonet, (True,"equipment.weapon.dagger"))
        self.assertEqual(cudgel, (True,True,True))

    def test_description_provenance_is_paired(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (WHERE p.is_primary_citation),
                          count(DISTINCT p.rule_id)
                   FROM src_record_provenance p
                   JOIN src_locator locator USING (source_locator_id)
                   WHERE locator.heading_path=
                     'Equipment > Weapons > Melee Weapon Descriptions'"""
            ).fetchone()
        self.assertEqual(row, (22,11,11))


if __name__ == "__main__":
    unittest.main()
