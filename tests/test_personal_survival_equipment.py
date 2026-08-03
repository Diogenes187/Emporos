import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalSurvivalEquipmentTests(unittest.TestCase):
    def test_catalogue_values_and_unknown_mass_are_exact(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT survival.survival_equipment_code,
                          item.minimum_tech_level,item.cost_credits,
                          item.mass_grams,
                          survival.catalogue_mass_is_unquantified
                   FROM inv_personal_survival_equipment_definition survival
                   JOIN inv_item_definition item
                     ON item.rule_id=survival.item_rule_id
                   ORDER BY item.minimum_tech_level,
                            survival.survival_equipment_code"""
            ).fetchall()
        self.assertEqual(len(rows), 12)
        self.assertEqual(
            rows[0], ("cold-weather-clothing", 1, 200, 2000, False))
        self.assertIn(("combination-mask", 5, 150, None, True), rows)
        self.assertIn(("environment-suit", 8, 500, None, True), rows)
        self.assertEqual(
            rows[-1], ("portable-generator", 10, 500000, 15000, False))

    def test_catalogue_and_items_have_paired_provenance(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code=
                         'equipment.personal-survival-equipment'
                      OR rule.rule_code LIKE 'equipment.survival.%'"""
            ).fetchone()
        self.assertEqual(row, (26, 13, 13))


if __name__ == "__main__":
    unittest.main()
