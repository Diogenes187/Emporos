import os
import unittest

import psycopg


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalCoupDeGraceTests(unittest.TestCase):
    def test_published_mechanics_are_exact_and_paired(self):
        with psycopg.connect(DSN) as connection:
            mechanic = connection.execute(
                """SELECT helpless_target_required,melee_weapon_permitted,
                          melee_maximum_range_code,ranged_weapon_permitted,
                          ranged_requires_adjacency,attack_roll_required,
                          automatic_hit,target_dies
                   FROM rule_personal_coup_de_grace"""
            ).fetchone()
            self.assertEqual(
                mechanic,
                (True, True, "close-quarters", True, True, False, True, True),
            )
            provenance = connection.execute(
                """SELECT count(DISTINCT work.work_code),
                          count(*) FILTER (
                            WHERE provenance.is_primary_citation)
                   FROM rule_personal_coup_de_grace mechanic
                   JOIN src_record_provenance provenance
                     ON provenance.rule_id=mechanic.rule_id
                   JOIN src_locator locator ON locator.source_locator_id=
                        provenance.source_locator_id
                   JOIN src_work work ON work.source_work_id=locator.source_work_id"""
            ).fetchone()
            self.assertEqual(provenance, (2, 1))


if __name__ == "__main__":
    unittest.main()
