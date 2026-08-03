import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.commerce_setup import prepare_trading_command
from engine.crew_assignments import assign_ship_crew_command
from engine.crew_payroll import pay_ship_crew_command
class Fixed:
 def randint(self,a,b):return min(3,b)
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CrewPayrollTests(unittest.TestCase):
 def test_assigned_crew_receives_salary(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='payroll-test';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Payroll');master=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Master',random_source=Fixed());pilot=initialize_character_command(c,initiator_reference=owner,idempotency_key='b'+x,campaign_public_id=camp.campaign_public_id,character_name='Pilot',random_source=Fixed());ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=master.actor_public_id,class_code='merchant-trader',ship_name='Payday');prepare_trading_command(c,initiator_reference=owner,idempotency_key='setup'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=master.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=100000)
    position=c.execute("SELECT position.ship_crew_position_id FROM ship_crew_position position JOIN ship_crew_position_definition definition ON definition.crew_position_rule_id=position.crew_position_rule_id WHERE position.ship_id=(SELECT ship_id FROM ship_ship WHERE public_id=%s) AND definition.standard_monthly_salary_minor IS NOT NULL ORDER BY position.ship_crew_position_id LIMIT 1",(ship.ship_public_id,)).fetchone()[0];assign_ship_crew_command(c,initiator_reference=owner,idempotency_key='assign'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=pilot.actor_public_id,ship_public_id=ship.ship_public_id,ship_crew_position_id=position)
    result=pay_ship_crew_command(c,initiator_reference=owner,idempotency_key='pay'+x,campaign_public_id=camp.campaign_public_id,payer_actor_public_id=master.actor_public_id,ship_public_id=ship.ship_public_id);self.assertEqual(result.crew_paid,1);self.assertLess(result.balance_after,100000)
if __name__=='__main__':unittest.main()
