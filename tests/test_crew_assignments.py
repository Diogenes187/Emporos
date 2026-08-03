import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.crew_assignments import assign_ship_crew_command
class Fixed:
 def randint(self,a,b):return min(3,b)
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CrewAssignmentTests(unittest.TestCase):
 def test_assigns_actor_to_vacant_station(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='crew-test';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Crew');master=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Master',random_source=Fixed());crew=initialize_character_command(c,initiator_reference=owner,idempotency_key='b'+x,campaign_public_id=camp.campaign_public_id,character_name='Pilot',random_source=Fixed());ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=master.actor_public_id,class_code='merchant-trader',ship_name='Crewed')
    position=c.execute("SELECT position.ship_crew_position_id FROM ship_crew_position position JOIN ship_crew_position_definition definition ON definition.crew_position_rule_id=position.crew_position_rule_id WHERE position.ship_id=(SELECT ship_id FROM ship_ship WHERE public_id=%s) AND definition.position_code<>'master' AND NOT EXISTS(SELECT 1 FROM ship_crew_assignment assignment WHERE assignment.ship_crew_position_id=position.ship_crew_position_id AND assignment.duty_status='active') ORDER BY position.ship_crew_position_id LIMIT 1",(ship.ship_public_id,)).fetchone()[0]
    result=assign_ship_crew_command(c,initiator_reference=owner,idempotency_key='assign'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=crew.actor_public_id,ship_public_id=ship.ship_public_id,ship_crew_position_id=position);self.assertEqual(result.actor_public_id,crew.actor_public_id);self.assertFalse(result.replayed)
if __name__=='__main__':unittest.main()
