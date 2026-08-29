import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command
from engine.commerce_setup import prepare_trading_command
from engine.careers import finish_character_creation_command
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CommerceSetupTests(unittest.TestCase):
 def test_balanced_account_and_item_owned_hold(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());camp=create_campaign_command(c,initiator_reference='commerce-test',idempotency_key='c'+x,name='Commerce');actor=initialize_character_command(c,initiator_reference='commerce-test',idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Trader');ship=acquire_ship_command(c,initiator_reference='commerce-test',idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Ledger')
    result=prepare_trading_command(c,initiator_reference='commerce-test',idempotency_key='t'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=100000)
    self.assertEqual(result.opening_balance,100000);self.assertEqual(c.execute("SELECT balance.balance_minor FROM fin_account_balance balance JOIN fin_account account USING(account_id) WHERE account.public_id=%s",(result.account_public_id,)).fetchone()[0],100000)
 def test_finished_character_personal_account_is_reused_for_trade(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='commerce-finished';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Commerce Finished');actor=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Trader');finish_character_creation_command(c,initiator_reference=owner,idempotency_key='f'+x,actor_public_id=actor.actor_public_id);ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Ledger')
    result=prepare_trading_command(c,initiator_reference=owner,idempotency_key='t'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=100)
    self.assertEqual(c.execute("SELECT count(*) FROM fin_actor_account ownership JOIN actor_actor actor USING(actor_id,campaign_id) WHERE actor.public_id=%s",(actor.actor_public_id,)).fetchone()[0],1);self.assertEqual(c.execute("SELECT balance_minor FROM fin_account_balance balance JOIN fin_account account USING(account_id) WHERE account.public_id=%s",(result.account_public_id,)).fetchone()[0],100)
 def test_finishing_credits_lifepath_cash_to_an_existing_account(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='commerce-before-finish';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Commerce Before Finish');actor=initialize_character_command(c,initiator_reference=owner,idempotency_key='a'+x,campaign_public_id=camp.campaign_public_id,character_name='Trader');ship=acquire_ship_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code='merchant-trader',ship_name='Ledger')
    result=prepare_trading_command(c,initiator_reference=owner,idempotency_key='t'+x,campaign_public_id=camp.campaign_public_id,actor_public_id=actor.actor_public_id,ship_public_id=ship.ship_public_id,opening_balance=100)
    c.execute("INSERT INTO actor_financial_state(actor_id,cash_credits) SELECT actor_id,500 FROM actor_actor WHERE public_id=%s",(actor.actor_public_id,))
    finish_character_creation_command(c,initiator_reference=owner,idempotency_key='f'+x,actor_public_id=actor.actor_public_id)
    self.assertEqual(c.execute("SELECT balance_minor FROM fin_account_balance balance JOIN fin_account account USING(account_id) WHERE account.public_id=%s",(result.account_public_id,)).fetchone()[0],600)
if __name__=='__main__':unittest.main()
