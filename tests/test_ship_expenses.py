import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.sectors import import_sector_command
from engine.travel_planning import place_ship_command
from engine.commerce_setup import prepare_trading_command
from engine.ship_expenses import pay_ship_operating_expense_command
class Fixed:
 def randint(self,a,b):return min(3,b)
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class ShipExpenseTests(unittest.TestCase):
 def test_berthing_and_maintenance_are_posted(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='expense-test';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Expense');actor=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Payer',random_source=Fixed());ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Cost Centre');prepare_trading_command(c,initiator_reference=owner,idempotency_key='setup'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=1000000)
    import_sector_command(c,initiator_reference=owner,idempotency_key='sector'+x,campaign_public_id=camp.campaign_public_id,sector_name='Test',sector_x=0,sector_y=0,source_filename='x.tab',content=b'Name\tHex\tUWP\nAlpha\t0101\tA788899-C\n');system=c.execute("SELECT location.public_id FROM loc_star_system star JOIN loc_location location ON location.location_id=star.location_id WHERE star.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)",(camp.campaign_public_id,)).fetchone()[0];place_ship_command(c,initiator_reference=owner,idempotency_key='place'+x,campaign_public_id=camp.campaign_public_id,ship_public_id=ship.ship_public_id,system_public_id=system)
    berth=pay_ship_operating_expense_command(c,initiator_reference=owner,idempotency_key='berth'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,operating_cost_code='berthing-first-six-days');self.assertEqual(berth.amount,100)
    support=pay_ship_operating_expense_command(c,initiator_reference=owner,idempotency_key='support'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,operating_cost_code='life-support-stateroom',quantity=2);self.assertEqual(support.amount,4000)
    service=pay_ship_operating_expense_command(c,initiator_reference=owner,idempotency_key='maint'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,operating_cost_code='maintenance-annual');self.assertIsNotNone(service.maintenance_cycle_id);self.assertLess(service.balance_after,support.balance_after)
if __name__=='__main__':unittest.main()
