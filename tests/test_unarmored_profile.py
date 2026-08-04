import os
import unittest

import psycopg

from engine.personal_combat import load_attack_specification


class UnarmoredProfileDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database_url = os.environ.get("EMPOROS_DATABASE_URL")
        if not database_url:
            raise unittest.SkipTest("EMPOROS_DATABASE_URL is not configured")
        cls.connection = psycopg.connect(database_url)

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()

    def test_profile_is_zero_protection_and_not_catalog_equipment(self):
        row = self.connection.execute(
            """SELECT armor.general_armor_rating,armor.laser_armor_rating,
                      armor.catalogue_display_order,item.cost_credits
               FROM rule_rule rule
               JOIN inv_armor_definition armor ON armor.item_rule_id=rule.rule_id
               JOIN inv_item_definition item ON item.rule_id=rule.rule_id
               WHERE rule.rule_code='combat.armor.unarmored'"""
        ).fetchone()
        self.assertEqual(row, (0, 0, None, None))

    def test_profile_loads_as_canonical_attack_armor(self):
        weapon = self.connection.execute(
            """SELECT rule.rule_code,mode.attack_profile_code,range_rule.rule_code
               FROM rule_rule rule
               JOIN inv_weapon_definition weapon ON weapon.item_rule_id=rule.rule_id
               JOIN inv_weapon_attack_mode mode ON mode.item_rule_id=rule.rule_id
               JOIN combat_attack_profile_difficulty difficulty
                 ON difficulty.attack_profile_code=mode.attack_profile_code AND difficulty.permitted
               JOIN rule_rule range_rule ON range_rule.rule_id=difficulty.range_band_rule_id
               ORDER BY rule.rule_code LIMIT 1"""
        ).fetchone()
        specification = load_attack_specification(
            self.connection,item_rule_code=weapon[0],attack_profile_code=weapon[1],
            range_rule_code=weapon[2],armor_rule_code="combat.armor.unarmored")
        self.assertEqual(specification.armor_rating, 0)

    def test_adjudication_is_relational_and_resolved(self):
        row = self.connection.execute(
            """SELECT interpretation.decision_register_entry,issue.issue_status
               FROM rule_rule rule
               JOIN rule_interpretation interpretation USING(rule_id)
               CROSS JOIN src_issue issue
               WHERE rule.rule_code='combat.armor.unarmored'
                 AND issue.issue_code='combat.personal.unarmored-zero-protection'""").fetchone()
        self.assertEqual(row, ("CE-COMBAT-027", "resolved"))


if __name__ == "__main__":
    unittest.main()
