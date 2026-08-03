import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class DiseaseTests(unittest.TestCase):
    def test_profiles_repeated_failure_and_success(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(connection.execute(
                "SELECT disease_code,resistance_dm,damage_flat_modifier,interval_dice_count,interval_unit FROM rule_disease_profile ORDER BY disease_profile_id"
            ).fetchall(), [("pneumonia",0,4,1,"weeks"),("anthrax",-3,2,1,"days"),("regina-flu",1,-2,1,"days"),("biological-weapon",-6,8,1,"hours")])
            with connection.transaction(force_rollback=True):
                campaign=connection.execute("INSERT INTO camp_campaign(name) VALUES('Disease test') RETURNING campaign_id").fetchone()[0]
                actor=connection.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Patient','test') RETURNING actor_id",(campaign,)).fetchone()[0]
                endurance=connection.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'").fetchone()[0]
                connection.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) VALUES(%s,%s,10,10)",(actor,endurance))
                profile=connection.execute("SELECT disease_profile_id FROM rule_disease_profile WHERE disease_code='regina-flu'").fetchone()[0]
                case=connection.execute("INSERT INTO env_disease_case(actor_id,campaign_id,disease_profile_id) VALUES(%s,%s,%s) RETURNING disease_case_id",(actor,campaign,profile)).fetchone()[0]
                task=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test','disease-failure','completed',clock_timestamp()) RETURNING command_id").fetchone()[0]
                average=connection.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
                connection.execute("INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,NULL,%s,0,0,0,1,0,6,8,-2,false)",(task,actor,endurance,average))
                receipt=connection.execute("INSERT INTO env_disease_check_receipt(disease_case_id,check_sequence,task_command_id,task_succeeded,damage_die_result,rolled_damage,interval_die_total,interval_seconds,characteristic_value_before,characteristic_value_after,case_version_before,case_version_after) VALUES(%s,1,%s,false,1,0,3,259200,10,10,1,2) RETURNING disease_check_receipt_id",(case,task)).fetchone()[0]
                self.assertEqual(connection.execute("SELECT current_value FROM actor_characteristic WHERE actor_id=%s AND characteristic_rule_id=%s",(actor,endurance)).fetchone()[0],10)
                with self.assertRaisesRegex(RaiseException,"immutable"):
                    with connection.transaction(): connection.execute("DELETE FROM env_disease_check_receipt WHERE disease_check_receipt_id=%s",(receipt,))
                with self.assertRaisesRegex(CheckViolation,"require an immutable"):
                    with connection.transaction(): connection.execute("UPDATE env_disease_case SET concurrency_version=9 WHERE disease_case_id=%s",(case,))


if __name__ == "__main__":
    unittest.main()
