import os
import unittest

import psycopg
from psycopg.errors import CheckViolation

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalComputerSoftwareTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_all_families_and_profiles_are_normalized(self):
        with self.connect() as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*) FROM rule_personal_software_family),
                    (SELECT count(*) FROM rule_personal_software_profile),
                    (SELECT count(*) FROM rule_personal_software_family
                      WHERE ranked),
                    (SELECT count(*) FROM rule_personal_software_family
                      WHERE maximum_is_open_ended)"""
            ).fetchone()
        self.assertEqual(counts, (9, 25, 8, 1))

    def test_non_fixed_cost_states_preserve_source_boundaries(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT family.software_code,profile.rating,
                          profile.rating_or_higher,
                          profile.minimum_tech_level,profile.cost_basis,
                          profile.minimum_cost_credits,
                          profile.maximum_cost_credits
                   FROM rule_personal_software_profile profile
                   JOIN rule_personal_software_family family
                     ON family.rule_id=profile.software_rule_id
                   WHERE profile.cost_basis<>'fixed'
                   ORDER BY family.software_code,profile.rating
                          NULLS FIRST"""
            ).fetchall()
        self.assertEqual(rows, [
            ("database", None, False, 7, "range", 10, 10000),
            ("intellect", 3, True, 14, "not-stated", None, None),
            ("interface", 0, False, 7, "included", 0, 0),
            ("intrusion", 4, False, 15, "unavailable", None, None),
            ("security", 0, False, 7, "included", 0, 0),
        ])

    def test_downrating_and_copy_threshold_are_exact(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT permits_lower_rating_use,
                          minimum_usable_rating_is_family_minimum,
                          difficult_copy_above_rating,
                          transfer_bandwidth_is_unquantified
                   FROM rule_personal_software_catalogue"""
            ).fetchone()
        self.assertEqual(row, (True, True, 1, True))

    def test_cost_state_constraints_reject_invented_intellect_price(self):
        with self.connect() as connection:
            intellect = connection.execute(
                """SELECT family.rule_id
                   FROM rule_personal_software_family family
                   WHERE family.software_code='intellect'"""
            ).fetchone()[0]
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE rule_personal_software_profile
                           SET minimum_cost_credits=100000
                           WHERE software_rule_id=%s AND rating=3""",
                        (intellect,))

    def test_family_rating_shape_is_a_database_invariant(self):
        with self.connect() as connection:
            database = connection.execute(
                """SELECT rule_id FROM rule_personal_software_family
                   WHERE software_code='database'"""
            ).fetchone()[0]
            with self.assertRaisesRegex(
                psycopg.errors.RaiseException,
                "does not match family rating bounds",
            ):
                with connection.transaction():
                    connection.execute(
                        """UPDATE rule_personal_software_profile
                           SET rating=0
                           WHERE software_rule_id=%s""", (database,))

    def test_family_provenance_is_paired(self):
        with self.connect() as connection:
            row = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code=
                         'equipment.personal-computer-software'
                      OR rule.rule_code LIKE 'software.personal.%'"""
            ).fetchone()
        self.assertEqual(row, (20, 10, 10))


if __name__ == "__main__":
    unittest.main()
