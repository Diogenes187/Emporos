import os,unittest,uuid
import psycopg
from engine.trade_work import start_trade_work_week_command,complete_trade_work_week_command
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class TradeWorkTests(unittest.TestCase):
 def setup(self,c):
  camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'player') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];actor,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Tech','player') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO actor_skill SELECT %s,rule_id,0 FROM rule_rule WHERE rule_code='skill.mechanics'",(actor,));emp,emppub=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','employer','Employer','external') RETURNING account_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO fin_external_account VALUES(%s,%s,'Workshop')",(emp,camp));worker,workpub=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR','wages','Wages','asset') RETURNING account_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO fin_actor_account VALUES(%s,%s,%s)",(worker,camp,actor));return camp,str(pub),str(emppub),str(workpub),worker,emp
 def test_completed_dedicated_week_posts_cr250_once(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp,actor,emp,worker,worker_id,emp_id=self.setup(c);start=start_trade_work_week_command(c,initiator_reference='player',idempotency_key='start-work',actor_public_id=actor,skill_rule_code='skill.mechanics',employer_account_public_id=emp,worker_account_public_id=worker);self.assertEqual(start.status,'active')
    with self.assertRaisesRegex(ValueError,'not complete'):complete_trade_work_week_command(c,initiator_reference='player',idempotency_key='early',work_week_public_id=start.work_week_public_id)
    c.execute("UPDATE camp_clock SET day_number=day_number+7 WHERE campaign_id=%s",(camp,));done=complete_trade_work_week_command(c,initiator_reference='player',idempotency_key='finish-work',work_week_public_id=start.work_week_public_id);self.assertEqual(done.wage_credits,250);self.assertEqual(done.status,'completed');balances=dict(c.execute("SELECT account_id,balance_minor FROM fin_account_balance WHERE account_id IN (%s,%s)",(worker_id,emp_id)).fetchall());self.assertEqual(balances[worker_id],250);self.assertEqual(balances[emp_id],-250)
    replay=complete_trade_work_week_command(c,initiator_reference='player',idempotency_key='finish-work',work_week_public_id=start.work_week_public_id);self.assertTrue(replay.replayed)
