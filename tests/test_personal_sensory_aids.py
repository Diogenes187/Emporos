import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalSensoryAidTests(unittest.TestCase):
    def test_catalogue_values_and_unknown_mass_are_exact(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT aid.sensory_aid_code,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams,
                          aid.catalogue_mass_is_unquantified
                   FROM inv_personal_sensory_aid_definition aid
                   JOIN inv_item_definition item
                     ON item.rule_id=aid.item_rule_id
                   ORDER BY item.minimum_tech_level,aid.sensory_aid_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("torch", 1, 1, 250, False),
            ("lamp-oil", 2, 2, None, True),
            ("oil-lamp", 2, 10, 500, False),
            ("binoculars", 3, 75, 1000, False),
            ("electric-torch", 5, 10, 500, False),
            ("cold-light-lantern", 6, 20, 250, False),
            ("infrared-goggles", 6, 500, None, True),
            ("light-intensifier-goggles", 7, 500, None, True),
        ])

    def test_catalogue_and_items_have_paired_provenance(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.personal-sensory-aids'
                      OR rule.rule_code LIKE 'equipment.sensory-aid.%'"""
            ).fetchone()
        self.assertEqual(row, (18, 9, 9))


if __name__ == "__main__":
    unittest.main()
