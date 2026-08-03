import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalComputerHardwareTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_standard_laptops_preserve_all_published_rows(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT computer.optimum_tech_level,
                          computer.model_rating,item.mass_grams,
                          item.cost_credits,
                          computer.battery_duration_seconds,
                          computer.battery_basis,
                          computer.storage_effectively_unlimited
                   FROM inv_personal_computer_definition computer
                   JOIN inv_item_definition item
                     ON item.rule_id=computer.item_rule_id
                   WHERE computer.computer_kind='laptop'
                   ORDER BY computer.optimum_tech_level"""
            ).fetchall()
        self.assertEqual(rows, [
            (7, 0, 10000, 50, 7200, "finite", False),
            (8, 1, 5000, 100, 28800, "finite", False),
            (9, 1, 5000, 250, None, "effectively-unlimited", True),
            (10, 2, 1000, 350, None, "effectively-unlimited", True),
            (11, 2, 1000, 500, None, "effectively-unlimited", True),
            (12, 3, 500, 1000, None, "effectively-unlimited", True),
            (13, 4, 500, 1500, None, "effectively-unlimited", True),
            (14, 5, 500, 5000, None, "effectively-unlimited", True),
        ])

    def test_handhelds_are_derived_without_inventing_mass(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT hand.optimum_tech_level,hand.model_rating,
                          hand_item.cost_credits,hand_item.mass_grams,
                          hand.cost_basis,hand.one_hand_operation,
                          laptop_item.cost_credits
                   FROM inv_personal_computer_definition hand
                   JOIN inv_item_definition hand_item
                     ON hand_item.rule_id=hand.item_rule_id
                   JOIN inv_personal_computer_definition laptop
                     ON laptop.optimum_tech_level=hand.optimum_tech_level
                    AND laptop.computer_kind='laptop'
                   JOIN inv_item_definition laptop_item
                     ON laptop_item.rule_id=laptop.item_rule_id
                   WHERE hand.computer_kind='hand-computer'
                   ORDER BY hand.optimum_tech_level"""
            ).fetchall()
        self.assertEqual(len(rows), 8)
        for tech, model, cost, mass, basis, one_hand, standard_cost in rows:
            self.assertEqual(cost, standard_cost*2)
            self.assertIsNone(mass)
            self.assertEqual(basis, "twice-standard-same-tl")
            self.assertTrue(one_hand)

    def test_terminal_catalogue_rule_and_desktop_are_typed(self):
        with self.connect() as connection:
            terminal = connection.execute(
                """SELECT computer.optimum_tech_level,
                          computer.model_rating,item.cost_credits,
                          item.mass_grams,computer.battery_basis,
                          computer.interface_only,
                          computer.operates_without_network
                   FROM inv_personal_computer_definition computer
                   JOIN inv_item_definition item
                     ON item.rule_id=computer.item_rule_id
                   WHERE computer.computer_kind='terminal'"""
            ).fetchone()
            catalogue = connection.execute(
                """SELECT simultaneous_program_capacity_equals_model,
                          unlimited_storage_minimum_tech_level,
                          desktop_mechanical_rating_bonus,
                          desktop_obsolete_during_tech_level
                   FROM rule_personal_computer_catalogue"""
            ).fetchone()
            desktop = connection.execute(
                """SELECT same_cost_as_laptop,mechanical_rating_modifier,
                          obsolete_during_tech_level
                   FROM rule_personal_computer_form_factor
                   WHERE form_factor_code='desktop'"""
            ).fetchone()
        self.assertEqual(terminal, (7, 0, 200, None, "not-stated",
                                    True, False))
        self.assertEqual(catalogue, (True, 9, 0, 8))
        self.assertEqual(desktop, (True, 0, 8))

    def test_dual_hand_computer_listing_and_provenance_are_explicit(self):
        with self.connect() as connection:
            issue = connection.execute(
                """SELECT issue_status,engine_disposition,
                          count(locator.source_locator_id)
                   FROM src_issue issue
                   JOIN src_issue_locator locator USING (source_issue_id)
                   WHERE issue_code=
                     'equipment.computer.hand-computer-dual-listing'
                   GROUP BY issue.source_issue_id"""
            ).fetchone()
            provenance = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.personal-computers'
                      OR rule.rule_code LIKE 'equipment.computer.%'"""
            ).fetchone()
        self.assertEqual(issue, ("accepted_as_published",
                                 "preserve_rule", 4))
        self.assertEqual(provenance, (36, 18, 18))

    def test_terminal_cannot_claim_unpublished_battery_duration(self):
        with self.connect() as connection:
            terminal = connection.execute(
                """SELECT item_rule_id FROM inv_personal_computer_definition
                   WHERE computer_kind='terminal'"""
            ).fetchone()[0]
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE inv_personal_computer_definition
                           SET battery_duration_seconds=7200
                           WHERE item_rule_id=%s""", (terminal,))


if __name__ == "__main__":
    unittest.main()
