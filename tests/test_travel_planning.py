import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.sectors import import_sector_command
from engine.ships import acquire_ship_command
from engine.travel_planning import place_ship_command,plan_jump_journey_command
from engine.navigation import resolve_navigation_command
from engine.jump_attempts import resolve_jump_attempt_command
from engine.spacecraft_journeys import start_spacecraft_journey_leg_command,complete_spacecraft_journey_leg_command

class FixedRandom:
 def randint(self,a,b):return 6

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class TravelPlanningTests(unittest.TestCase):
 def test_place_and_plan_reserves_fuel_and_crew(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());camp=create_campaign_command(c,initiator_reference='travel-test',idempotency_key='camp-'+suffix,name='Travel')
    actor=initialize_character_command(c,initiator_reference='travel-test',idempotency_key='actor-'+suffix,campaign_public_id=camp.campaign_public_id,character_name='Master')
    sector=import_sector_command(c,initiator_reference='travel-test',idempotency_key='sector-'+suffix,campaign_public_id=camp.campaign_public_id,sector_name='Test',sector_x=0,sector_y=0,source_filename='test.tab',content=b'Name\tHex\tUWP\nAlpha\t0101\tA788899-C\nBeta\t0201\tC360757-A\n')
    systems=c.execute("SELECT location.public_id FROM loc_star_system system JOIN loc_location location ON location.location_id=system.location_id WHERE system.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s) ORDER BY system.hex_column",(camp.campaign_public_id,)).fetchall()
    ship=acquire_ship_command(c,initiator_reference='travel-test',idempotency_key='ship-'+suffix,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Wayfarer')
    place_ship_command(c,initiator_reference='travel-test',idempotency_key='place-'+suffix,campaign_public_id=camp.campaign_public_id,ship_public_id=ship.ship_public_id,system_public_id=systems[0][0])
    result=plan_jump_journey_command(c,initiator_reference='travel-test',idempotency_key='jump-'+suffix,campaign_public_id=camp.campaign_public_id,ship_public_id=ship.ship_public_id,destination_system_public_id=systems[1][0],journey_name='Alpha to Beta')
    self.assertEqual(result.distance_parsecs,1);self.assertEqual(result.fuel_quantity,20);self.assertEqual(result.crew_count,1)
    route=resolve_navigation_command(c,initiator_reference='travel-test',idempotency_key='nav-'+suffix,journey_public_id=result.journey_public_id,leg_order=1,actor_public_id=actor.actor_public_id,operation_kind='jump_route',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',random_source=FixedRandom())
    self.assertTrue(route.succeeded)
    attempt=resolve_jump_attempt_command(c,initiator_reference='travel-test',idempotency_key='attempt-'+suffix,journey_public_id=result.journey_public_id,engineer_actor_public_id=actor.actor_public_id,random_source=FixedRandom())
    self.assertEqual(attempt.outcome,'accurate')
    start=start_spacecraft_journey_leg_command(c,referee_reference='travel-test',idempotency_key='start-'+suffix,journey_public_id=result.journey_public_id,leg_order=1)
    self.assertEqual(start.status,'underway')
    finish=complete_spacecraft_journey_leg_command(c,referee_reference='travel-test',idempotency_key='finish-'+suffix,journey_public_id=result.journey_public_id,leg_order=1)
    self.assertTrue(finish.journey_completed)
    self.assertEqual(c.execute("SELECT location.public_id FROM ship_ship ship JOIN loc_location location ON location.location_id=ship.current_location_id WHERE ship.public_id=%s",(ship.ship_public_id,)).fetchone()[0],systems[1][0])

if __name__=='__main__':unittest.main()
