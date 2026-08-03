import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.sectors import import_sector_command
from engine.travel_planning import place_ship_command
from engine.route_revenue import open_route_revenue_command
class Fixed:
 def randint(self,a,b):return min(3,b)
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class RouteRevenueTests(unittest.TestCase):
 def test_generates_all_route_opportunities_together(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='revenue-test';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Revenue');actor=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Master',random_source=Fixed());ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Carrier');import_sector_command(c,initiator_reference=owner,idempotency_key='sector'+x,campaign_public_id=camp.campaign_public_id,sector_name='Test',sector_x=0,sector_y=0,source_filename='x.tab',content=b'Name\tHex\tUWP\nAlpha\t0101\tA788899-C\nBeta\t0201\tB788899-C\n');systems=c.execute("SELECT location.public_id FROM loc_star_system star JOIN loc_location location ON location.location_id=star.location_id WHERE star.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s) ORDER BY star.hex_column",(camp.campaign_public_id,)).fetchall();place_ship_command(c,initiator_reference=owner,idempotency_key='place'+x,campaign_public_id=camp.campaign_public_id,ship_public_id=ship.ship_public_id,system_public_id=systems[0][0]);result=open_route_revenue_command(c,initiator_reference=owner,idempotency_key='open'+x,campaign_public_id=camp.campaign_public_id,ship_public_id=ship.ship_public_id,destination_system_public_id=systems[1][0],random_source=Fixed());self.assertGreaterEqual(result.freight_tons,0);self.assertEqual(c.execute("SELECT count(*) FROM journey_revenue_availability_draw WHERE revenue_availability_cycle_id=(SELECT revenue_availability_cycle_id FROM cmd_route_revenue_availability_receipt WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s))",(result.command_public_id,)).fetchone()[0],4)
if __name__=='__main__':unittest.main()
