import os,unittest,psycopg

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class DeprivationTests(unittest.TestCase):
 def test_profiles_and_failed_dehydration_check_relief(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT deprivation_code,normal_daily_requirement::text,requirement_unit,hot_climate_multiplier_min,hot_climate_multiplier_max,grace_base_seconds,grace_endurance_seconds,check_interval_seconds FROM rule_deprivation_profile ORDER BY deprivation_code').fetchall(),[('dehydration','1.00','gallon-fluid-per-day',2,3,72000,7200,3600),('starvation','1.00','pound-food-per-day',None,None,259200,0,86400)])
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Deprivation test') RETURNING campaign_id").fetchone()[0];actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Thirsty','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    endurance=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'").fetchone()[0];average=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.routine'").fetchone()[0]
    c.execute('INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) VALUES(%s,%s,7,7)',(actor,endurance));profile=c.execute("SELECT deprivation_profile_id FROM rule_deprivation_profile WHERE deprivation_code='dehydration'").fetchone()[0]
    episode=c.execute('INSERT INTO env_deprivation_episode(actor_id,campaign_id,deprivation_profile_id,endurance_snapshot,began_campaign_day,began_campaign_second,first_check_due_total_seconds,next_check_due_total_seconds) VALUES(%s,%s,%s,7,0,0,122400,122400) RETURNING deprivation_episode_id',(actor,campaign,profile)).fetchone()[0]
    command=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test','deprivation-fail','completed',clock_timestamp()) RETURNING command_id").fetchone()[0]
    c.execute('INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,NULL,%s,0,0,0,0,0,6,8,-2,false)',(command,actor,endurance,average))
    receipt=c.execute('INSERT INTO env_deprivation_check_receipt(deprivation_episode_id,check_sequence,task_command_id,campaign_day,campaign_second,cumulative_previous_check_dm,task_succeeded,damage_die_result,rolled_damage,episode_version_before,episode_version_after) VALUES(%s,1,%s,1,36000,0,false,5,5,1,2) RETURNING deprivation_check_receipt_id',(episode,command)).fetchone()[0]
    self.assertEqual(c.execute('SELECT damage.penetrating_damage,lock.released_at FROM health_damage_instance damage JOIN health_deprivation_recovery_lock lock USING(damage_instance_id) WHERE lock.deprivation_check_receipt_id=%s',(receipt,)).fetchone(),(5,None))
    relief=c.execute("INSERT INTO env_deprivation_relief_receipt(deprivation_episode_id,campaign_day,campaign_second,requirement_quantity,requirement_unit,episode_version_before,episode_version_after) VALUES(%s,1,36001,1,'gallon-fluid-per-day',2,3) RETURNING deprivation_relief_receipt_id",(episode,)).fetchone()[0]
    self.assertEqual(c.execute('SELECT episode_status FROM env_deprivation_episode WHERE deprivation_episode_id=%s',(episode,)).fetchone()[0],'relieved');self.assertEqual(c.execute('SELECT released_by_relief_receipt_id FROM health_deprivation_recovery_lock WHERE deprivation_check_receipt_id=%s',(receipt,)).fetchone()[0],relief)

if __name__=='__main__':unittest.main()
