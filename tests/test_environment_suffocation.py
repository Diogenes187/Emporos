import os,unittest,psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SuffocationTests(unittest.TestCase):
 def test_profiles_minute_damage_and_relief(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT exposure_code,damage_dice_count,damage_die_sides,interval_kind FROM rule_suffocation_profile ORDER BY exposure_code').fetchall(),[('limited-oxygen',1,6,'minute'),('utterly-airless',1,6,'personal-combat-round')])
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Suffocation test') RETURNING campaign_id").fetchone()[0];actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Breather','test') RETURNING actor_id",(campaign,)).fetchone()[0];profile=c.execute("SELECT suffocation_profile_id FROM rule_suffocation_profile WHERE exposure_code='limited-oxygen'").fetchone()[0]
    episode=c.execute('INSERT INTO env_suffocation_episode(actor_id,campaign_id,suffocation_profile_id,began_campaign_day,began_campaign_second) VALUES(%s,%s,%s,4,100) RETURNING suffocation_episode_id',(actor,campaign,profile)).fetchone()[0]
    tick=c.execute('INSERT INTO env_suffocation_tick_receipt(suffocation_episode_id,tick_sequence,campaign_day,campaign_second,damage_die_result,rolled_damage,episode_version_before,episode_version_after) VALUES(%s,1,4,160,6,6,1,2) RETURNING suffocation_tick_receipt_id',(episode,)).fetchone()[0]
    self.assertEqual(c.execute('SELECT penetrating_damage FROM health_damage_instance WHERE suffocation_tick_receipt_id=%s',(tick,)).fetchone()[0],6)
    c.execute('INSERT INTO env_suffocation_relief_receipt(suffocation_episode_id,episode_version_before,episode_version_after) VALUES(%s,2,3)',(episode,));self.assertEqual(c.execute('SELECT episode_status FROM env_suffocation_episode WHERE suffocation_episode_id=%s',(episode,)).fetchone()[0],'air-restored')
if __name__=='__main__':unittest.main()
