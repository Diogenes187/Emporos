import os
import unittest

import psycopg
from psycopg.errors import RaiseException


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class AcidEnvironmentTests(unittest.TestCase):
    def test_acid_damage_immunity_fumes_and_suffocation_boundary_are_relational(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            rule = connection.execute(
                """SELECT contact_damage_dice,immersion_damage_dice,damage_die_sides,follow_up_delay_seconds,
                          caustic_immunity_prevents_acid_damage,immersion_suffocation_still_applies_when_breathing_required
                   FROM rule_environment_acid"""
            ).fetchone()
            self.assertEqual(rule, (1, 10, 6, 60, True, True))
            self.assertEqual(
                connection.execute(
                    """SELECT count(DISTINCT locator.source_work_id) FROM rule_rule rule
                       JOIN src_record_provenance provenance USING(rule_id)
                       JOIN src_locator locator USING(source_locator_id) WHERE rule.rule_code='environment.acid'"""
                ).fetchone()[0],
                2,
            )
            fume_validator = connection.execute(
                "SELECT pg_get_functiondef('env_finalize_acid_fume_check()'::regprocedure)"
            ).fetchone()[0]
            self.assertIn("acid.follow_up_delay_seconds", fume_validator)
            self.assertIn("acid_fume_task_command_id", fume_validator)
            with connection.transaction(force_rollback=True):
                campaign = connection.execute(
                    "INSERT INTO camp_campaign(name) VALUES('Acid test') RETURNING campaign_id"
                ).fetchone()[0]
                actor = connection.execute(
                    """INSERT INTO actor_actor(campaign_id,name,controller_reference)
                       VALUES(%s,'Hazard tester','test') RETURNING actor_id""",
                    (campaign,),
                ).fetchone()[0]
                exposure = connection.execute(
                    """INSERT INTO env_acid_exposure(actor_id,campaign_id,exposure_kind,breathing_required)
                       VALUES(%s,%s,'contact',false) RETURNING acid_exposure_id""",
                    (actor, campaign),
                ).fetchone()[0]
                attempt = connection.execute(
                    """INSERT INTO env_acid_damage_attempt(acid_exposure_id,exposure_round,actor_id,campaign_id,
                       exposure_kind,caustic_immunity,damage_dice_count,damage_die_sides,suffocation_resolution_required)
                       VALUES(%s,1,%s,%s,'contact',false,1,6,false) RETURNING acid_damage_attempt_id""",
                    (exposure, actor, campaign),
                ).fetchone()[0]
                connection.execute("INSERT INTO env_acid_damage_die VALUES(%s,1,5)", (attempt,))
                damage = connection.execute(
                    "INSERT INTO env_acid_damage_receipt(acid_damage_attempt_id,rolled_damage) VALUES(%s,5) RETURNING damage_instance_id",
                    (attempt,),
                ).fetchone()[0]
                self.assertEqual(
                    connection.execute(
                        "SELECT penetrating_damage FROM health_damage_instance WHERE damage_instance_id=%s", (damage,)
                    ).fetchone()[0],
                    5,
                )
                connection.execute(
                    "INSERT INTO actor_environmental_immunity(actor_id,hazard_code,source_reference) VALUES(%s,'acid','test species trait')",
                    (actor,),
                )
                immersion = connection.execute(
                    """INSERT INTO env_acid_exposure(actor_id,campaign_id,exposure_kind,breathing_required)
                       VALUES(%s,%s,'total-immersion',true) RETURNING acid_exposure_id""",
                    (actor, campaign),
                ).fetchone()[0]
                immune_attempt = connection.execute(
                    """INSERT INTO env_acid_damage_attempt(acid_exposure_id,exposure_round,actor_id,campaign_id,
                       exposure_kind,caustic_immunity,damage_dice_count,damage_die_sides,suffocation_resolution_required)
                       VALUES(%s,1,%s,%s,'total-immersion',true,0,6,true) RETURNING acid_damage_attempt_id""",
                    (immersion, actor, campaign),
                ).fetchone()[0]
                self.assertIsNone(
                    connection.execute(
                        "INSERT INTO env_acid_damage_receipt(acid_damage_attempt_id,rolled_damage) VALUES(%s,0) RETURNING damage_instance_id",
                        (immune_attempt,),
                    ).fetchone()[0]
                )
                with self.assertRaisesRegex(RaiseException, "immutable"):
                    with connection.transaction():
                        connection.execute("DELETE FROM env_acid_damage_receipt WHERE acid_damage_attempt_id=%s", (attempt,))


if __name__ == "__main__":
    unittest.main()
