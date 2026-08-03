import os, unittest, psycopg
from psycopg.errors import CheckViolation, RaiseException

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class TemperatureFireTests(unittest.TestCase):
 def test_published_profiles(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT count(*) FROM rule_extreme_temperature_band').fetchone()[0],11)
   self.assertEqual(c.execute("SELECT damage_dice_count,damage_interval FROM rule_extreme_temperature_band WHERE boundary_celsius=0").fetchone(),(0,None))
   self.assertEqual(c.execute('SELECT damage_dice_count,damage_die_sides,improvised_smothering_dm,automatic_extinguishing_allowed FROM rule_catching_fire').fetchone(),(2,6,2,True))

 def test_temperature_damage_and_automatic_extinguishing_runtime(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Temperature test') RETURNING campaign_id").fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Hot Stuff','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    band=c.execute("SELECT temperature_band_id FROM rule_extreme_temperature_band WHERE boundary_celsius=500 AND boundary_relation='above'").fetchone()[0]
    exposure=c.execute("INSERT INTO env_temperature_exposure(actor_id,campaign_id,temperature_band_id,suitably_protected) VALUES(%s,%s,%s,false) RETURNING temperature_exposure_id",(actor,campaign,band)).fetchone()[0]
    receipt=c.execute("INSERT INTO env_temperature_damage_receipt(temperature_exposure_id,exposure_tick,damage_interval,damage_dice_count,die_1,die_2,die_3,rolled_damage) VALUES(%s,1,'round',3,2,3,4,9) RETURNING temperature_damage_receipt_id,damage_instance_id",(exposure,)).fetchone()
    self.assertEqual(c.execute('SELECT target_actor_id,penetrating_damage,temperature_damage_receipt_id FROM health_damage_instance WHERE damage_instance_id=%s',(receipt[1],)).fetchone(),(actor,9,receipt[0]))
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction(): c.execute('DELETE FROM env_temperature_damage_receipt WHERE temperature_damage_receipt_id=%s',(receipt[0],))
    fire=c.execute("INSERT INTO env_fire_episode(actor_id,campaign_id,fire_status,current_round) VALUES(%s,%s,'burning',1) RETURNING fire_episode_id",(actor,campaign)).fetchone()[0]
    fire_receipt=c.execute("INSERT INTO env_fire_resolution_receipt(fire_episode_id,resolution_sequence,resolution_kind,automatic_method,rolled_damage,fire_status_after,state_version_before,state_version_after) VALUES(%s,1,'automatic-extinguish','water',0,'extinguished',1,2) RETURNING fire_resolution_receipt_id",(fire,)).fetchone()[0]
    self.assertEqual(c.execute('SELECT fire_status,concurrency_version FROM env_fire_episode WHERE fire_episode_id=%s',(fire,)).fetchone(),('extinguished',2))
    with self.assertRaisesRegex(CheckViolation,'require an immutable'):
     with c.transaction(): c.execute("UPDATE env_fire_episode SET fire_status='burning',ended_at=NULL WHERE fire_episode_id=%s",(fire,))
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction(): c.execute('DELETE FROM env_fire_resolution_receipt WHERE fire_resolution_receipt_id=%s',(fire_receipt,))

if __name__=='__main__': unittest.main()
