import os,unittest,psycopg
from psycopg.errors import RaiseException

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class FallingTests(unittest.TestCase):
 def test_complete_distance_gravity_rounding_and_receipt(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute('SELECT millimeters_per_damage_die,gravity_scaling_stage,rounding_policy FROM rule_falling_gravity').fetchone(),(2000,'after-roll-total','nearest-half-up'))
   with c.transaction(force_rollback=True):
    campaign=c.execute("INSERT INTO camp_campaign(name) VALUES('Fall test') RETURNING campaign_id").fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Faller','test') RETURNING actor_id",(campaign,)).fetchone()[0]
    attempt=c.execute('INSERT INTO env_fall_attempt(actor_id,campaign_id,distance_millimeters,gravity_milligee,damage_dice_count) VALUES(%s,%s,5000,700,2) RETURNING fall_attempt_id',(actor,campaign)).fetchone()[0]
    c.execute('INSERT INTO env_fall_damage_die VALUES(%s,1,3),(%s,2,4)',(attempt,attempt))
    receipt=c.execute('INSERT INTO env_fall_damage_receipt(fall_attempt_id,rolled_damage,scaled_damage_millipoints,applied_damage) VALUES(%s,7,4900,5) RETURNING damage_instance_id',(attempt,)).fetchone()[0]
    self.assertEqual(c.execute('SELECT penetrating_damage,fall_attempt_id FROM health_damage_instance WHERE damage_instance_id=%s',(receipt,)).fetchone(),(5,attempt))
    with self.assertRaisesRegex(RaiseException,'immutable'):
     with c.transaction():c.execute('DELETE FROM env_fall_damage_receipt WHERE fall_attempt_id=%s',(attempt,))

if __name__=='__main__':unittest.main()
