import os
import unittest

import psycopg


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalFreeActionTests(unittest.TestCase):
    def test_mechanics_are_exact_relational_and_paired(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT performed_during_actor_turn,
                          below_minor_action_threshold,unbounded_by_default,
                          multiple_may_require_referee_escalation,
                          escalation_may_cost_minor_action,
                          escalation_may_cost_significant_action
                   FROM rule_personal_free_action""").fetchone()
            self.assertEqual(row, (True, True, True, True, True, True))
            examples = connection.execute(
                """SELECT example_code FROM rule_personal_free_action_example
                   ORDER BY example_order""").fetchall()
            self.assertEqual(examples, [("shout_warning",),
                                        ("push_button",),
                                        ("check_watch",)])
            provenance = connection.execute(
                """SELECT count(DISTINCT work.work_code),
                          count(*) FILTER (WHERE provenance.is_primary_citation)
                   FROM rule_personal_free_action mechanic
                   JOIN src_record_provenance provenance
                     ON provenance.rule_id=mechanic.rule_id
                   JOIN src_locator locator ON locator.source_locator_id=
                        provenance.source_locator_id
                   JOIN src_work work ON work.source_work_id=locator.source_work_id""").fetchone()
            self.assertEqual(provenance, (2, 1))


if __name__ == "__main__":
    unittest.main()
