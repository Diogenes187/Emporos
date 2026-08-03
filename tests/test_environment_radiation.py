import os,unittest,psycopg

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class RadiationTests(unittest.TestCase):
 def test_source_and_effect_profiles(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT count(*) FROM rule_radiation_source_profile').fetchone()[0],8)
   self.assertEqual(c.execute('SELECT band_code,minimum_rads,maximum_rads,effective_endurance_penalty,resistance_dm,damage_flat_modifier,interval_dice_count,interval_unit FROM rule_radiation_effect_band ORDER BY display_order').fetchall(),[
    ('mild',0,99,0,None,0,0,None),('low',100,199,1,1,0,1,'weeks'),('moderate',200,599,3,0,2,2,'days'),('high',600,999,6,-1,4,1,'days'),('severe',1000,None,10,-2,6,1,'hours')])
   self.assertEqual(c.execute("SELECT issue_status FROM src_issue WHERE issue_code='environment.radiation.below-mild-wording'").fetchone()[0],'resolved')

 def test_cumulative_exposure_state(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Radiation test') RETURNING campaign_id").fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Rad Test','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    endurance=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'").fetchone()[0]
    c.execute('INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) VALUES(%s,%s,7,7)',(actor,endurance))
    profile=c.execute("SELECT radiation_source_profile_id FROM rule_radiation_source_profile WHERE source_code='active-moderate'").fetchone()[0]
    attempt=c.execute("INSERT INTO env_radiation_exposure_attempt(actor_id,campaign_id,radiation_source_profile_id,exposure_mode,damage_dice_count,rad_multiplier,state_version_before,state_version_after) VALUES(%s,%s,%s,'instant',1,10,0,1) RETURNING radiation_exposure_attempt_id",(actor,campaign,profile)).fetchone()[0]
    c.execute('INSERT INTO env_radiation_exposure_die VALUES(%s,1,6)',(attempt,))
    c.execute("INSERT INTO env_radiation_exposure_receipt(radiation_exposure_attempt_id,rolled_total,rads_added,rads_before,rads_after,band_code_before,band_code_after,effective_endurance_before,effective_endurance_after,radiation_unconscious_before,radiation_unconscious_after) VALUES(%s,6,60,0,60,'mild','mild',7,7,false,false)",(attempt,))
    self.assertEqual(c.execute('SELECT total_rads,effective_endurance_penalty,radiation_unconscious,concurrency_version FROM actor_radiation_state WHERE actor_id=%s',(actor,)).fetchone(),(60,0,False,1))

 def test_post_exposure_antiradiation_dose_reduces_rads_and_is_immutable(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Rad drug test') RETURNING campaign_id").fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Rad Drug','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    endurance=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'").fetchone()[0]
    c.execute('INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) VALUES(%s,%s,7,7)',(actor,endurance))
    profile=c.execute("SELECT radiation_source_profile_id FROM rule_radiation_source_profile WHERE source_code='active-high'").fetchone()[0]
    attempt=c.execute("INSERT INTO env_radiation_exposure_attempt(actor_id,campaign_id,radiation_source_profile_id,exposure_mode,damage_dice_count,rad_multiplier,state_version_before,state_version_after) VALUES(%s,%s,%s,'instant',2,10,0,1) RETURNING radiation_exposure_attempt_id",(actor,campaign,profile)).fetchone()[0]
    c.execute('INSERT INTO env_radiation_exposure_die VALUES(%s,1,6)',(attempt,));c.execute('INSERT INTO env_radiation_exposure_die VALUES(%s,2,6)',(attempt,))
    c.execute("INSERT INTO env_radiation_exposure_receipt(radiation_exposure_attempt_id,rolled_total,rads_added,rads_before,rads_after,band_code_before,band_code_after,effective_endurance_before,effective_endurance_after,radiation_unconscious_before,radiation_unconscious_after) VALUES(%s,12,120,0,120,'mild','low',7,6,false,false)",(attempt,))
    drug=c.execute('SELECT drug_rule_id FROM rule_personal_antiradiation_drug').fetchone()[0]
    dose=c.execute("INSERT INTO env_antiradiation_dose_receipt(actor_id,campaign_id,drug_rule_id,radiation_exposure_attempt_id,prophylactic,dose_number_in_rolling_day,rads_before,rads_removed,rads_after,band_code_before,band_code_after,recovery_entitlement_points,overdose_endurance_damage,state_version_before,state_version_after) VALUES(%s,%s,%s,%s,false,1,120,100,20,'low','mild',1,0,1,2) RETURNING antiradiation_dose_receipt_id",(actor,campaign,drug,attempt)).fetchone()[0]
    c.execute('SET CONSTRAINTS ALL IMMEDIATE')
    self.assertEqual(c.execute('SELECT total_rads,effective_endurance_penalty,concurrency_version FROM actor_radiation_state WHERE actor_id=%s',(actor,)).fetchone(),(20,0,2))
    self.assertEqual(c.execute('SELECT recoverable_points,recovery_kind FROM health_radiation_recovery_entitlement WHERE antiradiation_dose_receipt_id=%s',(dose,)).fetchone(),(1,'physical-healing-over-time'))
    with self.assertRaises(psycopg.errors.RaiseException): c.execute('DELETE FROM env_antiradiation_dose_receipt WHERE antiradiation_dose_receipt_id=%s',(dose,))

 def test_failed_radiation_sickness_check_creates_damage_and_schedule(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Sickness test') RETURNING campaign_id").fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Sick','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    endurance=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'").fetchone()[0];average=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
    c.execute('INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) VALUES(%s,%s,7,7)',(actor,endurance))
    profile=c.execute("SELECT radiation_source_profile_id FROM rule_radiation_source_profile WHERE source_code='active-high'").fetchone()[0]
    attempt=c.execute("INSERT INTO env_radiation_exposure_attempt(actor_id,campaign_id,radiation_source_profile_id,exposure_mode,damage_dice_count,rad_multiplier,state_version_before,state_version_after) VALUES(%s,%s,%s,'instant',2,10,0,1) RETURNING radiation_exposure_attempt_id",(actor,campaign,profile)).fetchone()[0]
    c.execute('INSERT INTO env_radiation_exposure_die VALUES(%s,1,6)',(attempt,));c.execute('INSERT INTO env_radiation_exposure_die VALUES(%s,2,6)',(attempt,))
    c.execute("INSERT INTO env_radiation_exposure_receipt(radiation_exposure_attempt_id,rolled_total,rads_added,rads_before,rads_after,band_code_before,band_code_after,effective_endurance_before,effective_endurance_after,radiation_unconscious_before,radiation_unconscious_after) VALUES(%s,12,120,0,120,'mild','low',7,6,false,false)",(attempt,))
    case=c.execute('SELECT radiation_sickness_case_id FROM env_radiation_sickness_case WHERE radiation_exposure_attempt_id=%s',(attempt,)).fetchone()[0]
    command=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test','rad-sickness-fail','completed',clock_timestamp()) RETURNING command_id").fetchone()[0]
    c.execute('INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,NULL,%s,0,0,0,1,0,6,8,-2,false)',(command,actor,endurance,average))
    band=c.execute("SELECT radiation_effect_band_id FROM rule_radiation_effect_band WHERE band_code='low'").fetchone()[0]
    receipt=c.execute('INSERT INTO env_radiation_sickness_check_receipt(radiation_sickness_case_id,check_sequence,task_command_id,radiation_effect_band_id,task_succeeded,damage_die_result,rolled_damage,interval_die_total,interval_seconds,case_version_before,case_version_after) VALUES(%s,1,%s,%s,false,4,4,3,1814400,1,2) RETURNING radiation_sickness_check_receipt_id',(case,command,band)).fetchone()[0]
    self.assertEqual(c.execute('SELECT penetrating_damage FROM health_damage_instance WHERE radiation_sickness_check_receipt_id=%s',(receipt,)).fetchone()[0],4)
    self.assertIsNotNone(c.execute('SELECT next_check_at FROM env_radiation_sickness_case WHERE radiation_sickness_case_id=%s',(case,)).fetchone()[0])

if __name__=='__main__':unittest.main()
