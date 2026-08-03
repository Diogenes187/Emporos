import os
import unittest

import psycopg


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalExtendedActionTests(unittest.TestCase):
    def test_mechanics_are_exact_relational_and_paired(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT timing_roll_required,
                          timing_result_determines_required_rounds,
                          combat_round_seconds,exclusive_activity,
                          may_abandon_any_time,hit_requires_interruption_check,
                          interruption_target_number,
                          interruption_uses_task_skill,
                          post_armor_damage_is_negative_dm,
                          failed_check_loses_current_round,
                          exceptional_failure_maximum_effect,
                          exceptional_failure_ruins_task,
                          ruined_task_restarts_from_beginning
                   FROM rule_personal_extended_action"""
            ).fetchone()
            self.assertEqual(
                row,
                (True, True, 6, True, True, True, 8, True, True, True,
                 -6, True, True),
            )
            provenance = connection.execute(
                """SELECT count(DISTINCT work.work_code),
                          count(*) FILTER (
                            WHERE provenance.is_primary_citation)
                   FROM rule_personal_extended_action mechanic
                   JOIN src_record_provenance provenance
                     ON provenance.rule_id=mechanic.rule_id
                   JOIN src_locator locator ON locator.source_locator_id=
                        provenance.source_locator_id
                   JOIN src_work work ON work.source_work_id=locator.source_work_id"""
            ).fetchone()
            self.assertEqual(provenance, (2, 1))


if __name__ == "__main__":
    unittest.main()
