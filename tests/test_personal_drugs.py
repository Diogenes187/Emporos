import os
import unittest

import psycopg
from psycopg.errors import CheckViolation

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalDrugTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_nine_published_catalogue_rows_are_exact(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT drug.drug_code,drug.catalogue_tech_level,
                          drug.cost_basis,drug.minimum_cost_credits,
                          drug.fixed_cost_credits,item.mass_grams
                   FROM inv_personal_drug_definition drug
                   JOIN inv_item_definition item
                     ON item.rule_id=drug.item_rule_id
                   ORDER BY drug.catalogue_tech_level,drug.drug_code"""
            ).fetchall()
        self.assertEqual(len(rows), 9)
        self.assertIn(
            ("medicinal", 5, "minimum-plus-variable", 5, None, None), rows)
        self.assertIn(("anagathic", 11, "fixed", 2000, 2000, None), rows)
        self.assertTrue(all(row[5] is None for row in rows))

    def test_medicinal_variable_cost_is_not_flattened(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT variable_cost_dice_count,variable_cost_die_sides,
                          variable_cost_multiplier_credits
                   FROM inv_personal_drug_definition
                   WHERE drug_code='medicinal'"""
            ).fetchone()
        self.assertEqual(row, (1, 6, 1000))

    def test_anagathic_availability_preserves_all_three_tl_facts(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT catalogue_tech_level,synthetic_minimum_tech_level,
                          natural_forms_all_tech_levels,
                          illegal_or_heavily_controlled_on_many_worlds
                   FROM rule_anagathic_availability"""
            ).fetchone()
        self.assertEqual(row, (11, 15, True, True))

    def test_cost_constraints_reject_invented_fixed_medicinal_price(self):
        with self.connect() as connection:
            medicinal = connection.execute(
                """SELECT item_rule_id FROM inv_personal_drug_definition
                   WHERE drug_code='medicinal'"""
            ).fetchone()[0]
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE inv_personal_drug_definition
                           SET fixed_cost_credits=5
                           WHERE item_rule_id=%s""", (medicinal,))

    def test_drug_provenance_is_paired(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.personal-drugs'
                      OR rule.rule_code LIKE 'equipment.drug.%'"""
            ).fetchone()
        self.assertEqual(row, (20, 10, 10))


if __name__ == "__main__":
    unittest.main()
