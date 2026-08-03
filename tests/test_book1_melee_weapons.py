import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1MeleeWeaponTests(unittest.TestCase):
    def test_catalogue_preserves_unarmed_inventory_boundary(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),count(weapon_item_rule_id),
                          count(*) FILTER (
                            WHERE source_tech_level_is_unquantified
                              AND source_cost_is_unquantified
                              AND source_mass_is_unquantified)
                   FROM rule_book1_melee_attack"""
            ).fetchone()
            unarmed = connection.execute(
                """SELECT rule.rule_code,attack.weapon_item_rule_id,
                          attack.damage_dice_count,
                          attack.illegal_at_law_level
                   FROM rule_book1_melee_attack attack
                   JOIN rule_rule rule USING (rule_id)
                   WHERE attack.entry_code='unarmed-strike'"""
            ).fetchone()
        self.assertEqual(row, (12,11,1))
        self.assertEqual(
            unarmed, ("combat.attack.unarmed-strike",None,1,None))

    def test_physical_weapons_use_canonical_inventory_and_damage_types(self):
        with psycopg.connect(DSN) as connection:
            sword = connection.execute(
                """SELECT item.minimum_tech_level,item.cost_credits,
                          item.mass_grams,weapon.damage_dice_count,
                          weapon.illegal_at_law_level,
                          array_agg(type.damage_type_code
                                    ORDER BY type.damage_type_code)
                   FROM rule_book1_melee_attack attack
                   JOIN inv_item_definition item
                     ON item.rule_id=attack.weapon_item_rule_id
                   JOIN inv_weapon_definition weapon
                     ON weapon.item_rule_id=item.rule_id
                   JOIN inv_weapon_damage_type type
                     ON type.item_rule_id=item.rule_id
                   WHERE attack.entry_code='sword'
                   GROUP BY item.rule_id,weapon.item_rule_id"""
            ).fetchone()
            totals = connection.execute(
                """SELECT (SELECT count(*) FROM
                           rule_book1_melee_attack_mode),
                          (SELECT count(*) FROM inv_weapon_damage_type type
                           JOIN rule_book1_melee_attack attack
                             ON attack.weapon_item_rule_id=type.item_rule_id)"""
            ).fetchone()
        self.assertEqual(sword, (1,150,1000,3,8,["piercing","slashing"]))
        self.assertEqual(totals, (14,12))

    def test_spear_and_dagger_have_two_typed_attack_modes(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT attack.entry_code,
                          array_agg(mode.attack_profile_code
                                    ORDER BY mode.display_order)
                   FROM rule_book1_melee_attack attack
                   JOIN rule_book1_melee_attack_mode mode
                     ON mode.melee_attack_rule_id=attack.rule_id
                   WHERE attack.entry_code IN ('dagger','spear')
                   GROUP BY attack.entry_code
                   ORDER BY attack.entry_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("dagger",["close-quarters","thrown"]),
            ("spear",["extended-reach","thrown"]),
        ])

    def test_paired_source_provenance_is_exact(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (WHERE p.is_primary_citation),
                          count(DISTINCT p.rule_id)
                   FROM src_record_provenance p
                   JOIN src_locator locator USING (source_locator_id)
                   WHERE locator.heading_path=
                     'Equipment > Weapons > Common Personal Melee Weapons'"""
            ).fetchone()
        self.assertEqual(row, (24,12,12))


if __name__ == "__main__":
    unittest.main()
