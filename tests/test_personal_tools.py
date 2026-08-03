import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalToolTests(unittest.TestCase):
    def test_catalogue_and_paired_provenance_are_exact(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT tool.tool_code,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams,
                          tool.catalogue_mass_is_unquantified
                   FROM inv_personal_tool_definition tool
                   JOIN inv_item_definition item
                     ON item.rule_id=tool.item_rule_id
                   ORDER BY item.minimum_tech_level,tool.tool_code"""
            ).fetchall()
            provenance = connection.execute(
                """SELECT count(*),count(*) FILTER (WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.personal-tools'
                      OR rule.rule_code LIKE 'equipment.tool.%'"""
            ).fetchone()
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0],
                         ("mechanical-toolkit", 4, 1000, 12000, False))
        self.assertIn(("lock-pick-set", 5, 10, None, True), rows)
        self.assertEqual(provenance, (18, 9, 9))

    def test_operations_preserve_required_and_open_skill_boundaries(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT tool.tool_code,operation.operation_code,
                          operation.required_for_operation,skill.rule_code
                   FROM rule_personal_tool_operation operation
                   JOIN inv_personal_tool_definition tool
                     ON tool.item_rule_id=operation.tool_rule_id
                   LEFT JOIN rule_rule skill
                     ON skill.rule_id=operation.skill_rule_id
                   ORDER BY tool.tool_code,operation.operation_code"""
            ).fetchall()
        self.assertEqual(len(rows), 14)
        self.assertIn(
            ("medical-kit", "field-medicine", False, "skill.medicine"), rows)
        self.assertIn(
            ("forensics-toolkit", "crime-scene-investigation", True, None),
            rows)
        self.assertIn(
            ("lock-pick-set", "ordinary-mechanical-lock-picking", False, None),
            rows)

    def test_lock_pick_law_price_is_a_floor(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT tool.tool_code,price.illegal_at_or_above_law_level,
                          price.minimum_illegal_market_cost_credits,
                          price.illegal_market_cost_is_floor
                   FROM rule_personal_tool_law_price price
                   JOIN inv_personal_tool_definition tool
                     ON tool.item_rule_id=price.tool_rule_id"""
            ).fetchone()
        self.assertEqual(row, ("lock-pick-set", 8, 100, True))


if __name__ == "__main__":
    unittest.main()
