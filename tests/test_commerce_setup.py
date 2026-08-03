import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.commerce_setup import prepare_trading_command
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CommerceSetupTests(unittest.TestCase):
 def test_balanced_account_and_item_owned_hold(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());camp=create_campaign_command(c,initiator_reference='commerce-test',idempotency_key='c'+x,name='Commerce');actor=initialize_character_command(c,initiator_reference='commerce-test',idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Trader');ship=acquire_ship_command(c,initiator_reference='commerce-test',idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Ledger')
    result=prepare_trading_command(c,initiator_reference='commerce-test',idempotency_key='t'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=100000)
    self.assertEqual(result.opening_balance,100000);self.assertEqual(c.execute("SELECT balance.balance_minor FROM fin_account_balance balance JOIN fin_account account USING(account_id) WHERE account.public_id=%s",(result.account_public_id,)).fetchone()[0],100000)
if __name__=='__main__':unittest.main()
