import os,unittest,uuid
import psycopg
from engine.navigation import resolve_navigation_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class NavigationTests(unittest.TestCase):
 def test_jump_route_is_task_backed_replayable_and_required_for_jump(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0]
    code='test-'+uuid.uuid4().hex;loc_type=c.execute("INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status) SELECT content_package_id,%s,'Test','world','approved' FROM sys_content_package WHERE package_code='cepheus-engine' RETURNING rule_id",('location.type.'+code,)).fetchone()[0];c.execute("INSERT INTO rule_location_type VALUES(%s,%s,true,true)",(loc_type,code))
    origin=c.execute("INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,'Origin') RETURNING location_id",(camp,loc_type)).fetchone()[0];destination=c.execute("INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,'Destination') RETURNING location_id",(camp,loc_type)).fetchone()[0]
    aid,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Navigator','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.education'",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.navigation'",(aid,))
    jid,jpub=c.execute("INSERT INTO journey_journey(campaign_id,journey_kind,name) VALUES(%s,'jump','Test Jump') RETURNING journey_id,public_id",(camp,)).fetchone();leg=c.execute("INSERT INTO journey_leg(journey_id,campaign_id,leg_order,origin_location_id,destination_location_id,travel_mode) VALUES(%s,%s,1,%s,%s,'jump') RETURNING journey_leg_id",(jid,camp,origin,destination)).fetchone()[0]
    route=resolve_navigation_command(c,initiator_reference='p',idempotency_key='route',journey_public_id=str(jpub),leg_order=1,actor_public_id=str(apub),operation_kind='jump_route',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(route.succeeded);self.assertEqual(route.check_total,9)
    with self.assertRaisesRegex(ValueError,'completed Jump leg'):resolve_navigation_command(c,initiator_reference='p',idempotency_key='early-fix',journey_public_id=str(jpub),leg_order=1,actor_public_id=str(apub),operation_kind='post_jump_fix',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',random_source=R())
    replay=resolve_navigation_command(c,initiator_reference='p',idempotency_key='route',journey_public_id=str(jpub),leg_order=1,actor_public_id=str(apub),operation_kind='post_jump_fix',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',random_source=R());self.assertTrue(replay.replayed);self.assertEqual(replay.operation_kind,'jump_route')
    solution_id=c.execute("SELECT navigation_solution_id FROM journey_navigation_solution WHERE public_id=%s",(route.solution_public_id,)).fetchone()[0]
    with self.assertRaises(psycopg.Error):
     with c.transaction():c.execute("INSERT INTO journey_jump_attempt(journey_leg_id,campaign_id,jump_system_code,jump_number,plotted_distance_parsecs,engineering_effect,fuel_type_code,within_safe_limit,natural_roll,modifier_total,final_result,jump_outcome,duration_hours) VALUES(%s,%s,'cepheus-standard',1,1,0,'refined',true,8,0,8,'accurate',168)",(leg,camp))
    c.execute("INSERT INTO journey_jump_attempt(journey_leg_id,campaign_id,jump_system_code,jump_number,plotted_distance_parsecs,engineering_effect,fuel_type_code,within_safe_limit,natural_roll,modifier_total,final_result,jump_outcome,duration_hours,navigation_solution_id) VALUES(%s,%s,'cepheus-standard',1,1,0,'refined',true,8,0,8,'accurate',168,%s)",(leg,camp,solution_id))
