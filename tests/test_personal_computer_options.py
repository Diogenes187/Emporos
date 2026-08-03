import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalComputerOptionTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_catalogue_items_preserve_exact_published_values(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT option.option_kind,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams,
                          option.source_mass_is_unquantified,
                          option.wearable_headpiece,
                          option.transparent_display,
                          option.displays_linked_system_data,
                          option.information_storage_medium
                   FROM inv_personal_computer_option_definition option
                   JOIN inv_item_definition item
                     ON item.rule_id=option.item_rule_id
                   ORDER BY option.option_kind"""
            ).fetchall()
        self.assertEqual(rows, [
            ("data-display-recorder", 13, 5000, None,
             True, True, True, True, False),
            ("data-wafer", 10, 5, None,
             True, False, False, False, True),
        ])

    def test_specialization_formula_and_capacity_rule_are_typed(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT minimum_added_rating,maximum_added_rating,
                          cost_increase_basis_points_per_rating,
                          applies_to_one_program,
                          specialized_program_capacity_cost
                   FROM rule_personal_computer_specialization"""
            ).fetchone()
        self.assertEqual(row, (1, 2, 2500, True, 0))

    def test_option_provenance_is_paired(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code LIKE
                         'equipment.computer-option.%'"""
            ).fetchone()
        self.assertEqual(row, (6, 3, 3))

    def test_specialization_receipt_is_exact_and_immutable(self):
        with self.connect() as connection:
            campaign = connection.execute(
                """INSERT INTO camp_campaign (name,owner_reference)
                   VALUES ('Computer option test','referee')
                   RETURNING campaign_id"""
            ).fetchone()[0]
            computer_rule, base_rating, base_cost = connection.execute(
                """SELECT computer.item_rule_id,computer.model_rating,
                          item.cost_credits
                   FROM inv_personal_computer_definition computer
                   JOIN inv_item_definition item
                     ON item.rule_id=computer.item_rule_id
                   WHERE computer.computer_kind='laptop'
                     AND computer.optimum_tech_level=10"""
            ).fetchone()
            computer = connection.execute(
                """INSERT INTO inv_item_instance
                   (campaign_id,item_rule_id,instance_name)
                   VALUES (%s,%s,'Specialized laptop')
                   RETURNING item_instance_id""",
                (campaign, computer_rule),
            ).fetchone()[0]
            program = connection.execute(
                "SELECT rule_id FROM rule_personal_computer_specialization"
            ).fetchone()[0]
            command = connection.execute(
                """INSERT INTO cmd_command
                   (command_type,initiator_reference,idempotency_key)
                   VALUES ('specialize_personal_computer','test',%s)
                   RETURNING command_id""",
                (f"computer-specialization-test-{campaign}",),
            ).fetchone()[0]
            receipt = connection.execute(
                """INSERT INTO cmd_personal_computer_specialization_receipt
                   (command_id,campaign_id,computer_item_instance_id,
                    specialized_program_rule_id,added_rating,
                    base_computer_rating,specialized_program_rating,
                    base_computer_cost_credits,surcharge_quarter_credits)
                   VALUES (%s,%s,%s,%s,1,%s,%s,%s,%s)
                   RETURNING specialization_receipt_id""",
                (command, campaign, computer, program, base_rating,
                 base_rating + 1, base_cost, base_cost),
            ).fetchone()[0]
            stored = connection.execute(
                """SELECT base_computer_cost_credits,
                          surcharge_quarter_credits,
                          specialized_program_rating
                   FROM cmd_personal_computer_specialization_receipt
                   WHERE specialization_receipt_id=%s""",
                (receipt,),
            ).fetchone()
            self.assertEqual(stored, (350, 350, 3))
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """UPDATE cmd_personal_computer_specialization_receipt
                           SET added_rating=2
                           WHERE specialization_receipt_id=%s""", (receipt,))
            connection.rollback()


if __name__ == "__main__":
    unittest.main()
