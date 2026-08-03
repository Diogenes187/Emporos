import os,unittest,psycopg
from psycopg.errors import RaiseException

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class PoisonTests(unittest.TestCase):
 def test_published_profiles(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT poison_code,dm_kind,fixed_dm,dm_dice_count,outcome_kind,damage_dice_count FROM rule_poison_profile ORDER BY poison_profile_id').fetchall(),[
    ('arsenic','fixed',-2,None,'physical-damage',2),('tranq-gas','negative-die',None,1,'unconsciousness',0),('neurotoxin','fixed',-4,None,'characteristic-damage',1)])

 def test_arsenic_failure_creates_immutable_health_origin(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Poison test') RETURNING campaign_id").fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Victim','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    endurance=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'").fetchone()[0]
    average=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'").fetchone()[0]
    profile=c.execute("SELECT poison_profile_id FROM rule_poison_profile WHERE poison_code='arsenic'").fetchone()[0]
    attempt=c.execute("INSERT INTO env_poison_attempt(actor_id,campaign_id,poison_profile_id,exposure_reference) VALUES(%s,%s,%s,'test dose') RETURNING poison_attempt_id",(actor,campaign,profile)).fetchone()[0]
    command=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at) VALUES('resolve_actor_task','test','arsenic-check','completed',clock_timestamp()) RETURNING command_id").fetchone()[0]
    c.execute('INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,species_modifier,check_total,target_number,effect,succeeded) VALUES(%s,%s,%s,NULL,%s,0,0,0,-2,0,6,8,-2,false)',(command,actor,endurance,average))
    receipt=c.execute('INSERT INTO env_poison_resolution_receipt(poison_attempt_id,task_command_id,effective_resistance_dm,task_succeeded,damage_die_1,damage_die_2,rolled_damage,became_unconscious) VALUES(%s,%s,-2,false,3,4,7,false) RETURNING damage_instance_id',(attempt,command)).fetchone()[0]
    self.assertEqual(c.execute('SELECT penetrating_damage,poison_attempt_id FROM health_damage_instance WHERE damage_instance_id=%s',(receipt,)).fetchone(),(7,attempt))
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction():c.execute('DELETE FROM env_poison_resolution_receipt WHERE poison_attempt_id=%s',(attempt,))

if __name__=='__main__':unittest.main()
