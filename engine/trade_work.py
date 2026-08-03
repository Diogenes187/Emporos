"""Campaign-safe dedicated trade-work weeks and wage posting."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class TradeWorkResult:
 command_public_id:str; work_week_public_id:str; actor_public_id:str; skill_rule_code:str; status:str; started_day:int; completed_day:int|None; wage_credits:int; replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT w.public_id,a.public_id,s.rule_code,w.work_status,w.started_day,w.completed_day,COALESCE(x.wage_credits,0) FROM camp_trade_work_week w JOIN actor_actor a USING(actor_id) JOIN rule_rule s ON s.rule_id=w.skill_rule_id LEFT JOIN cmd_trade_work_complete_receipt x ON x.work_week_id=w.work_week_id WHERE w.source_command_id=%s OR w.completion_command_id=%s""",(cid,cid)).fetchone();return TradeWorkResult(str(pub),str(r[0]),str(r[1]),r[2],r[3],r[4],r[5],r[6],replayed)
def start_trade_work_week_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,skill_rule_code:str,employer_account_public_id:str,worker_account_public_id:str)->TradeWorkResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('start_trade_work_week','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  state=c.execute("""SELECT a.actor_id,a.campaign_id,clock.day_number,clock.second_of_day,sk.rule_id,s.skill_level,employer.account_id,worker.account_id FROM actor_actor a JOIN camp_clock clock USING(campaign_id) JOIN rule_rule sk ON sk.rule_code=%s JOIN rule_trade_work_skill eligible ON eligible.skill_rule_id=sk.rule_id JOIN actor_skill s ON s.actor_id=a.actor_id AND s.skill_rule_id=sk.rule_id JOIN fin_account employer ON employer.public_id=%s AND employer.campaign_id=a.campaign_id AND employer.account_status='open' AND employer.account_kind='external' JOIN fin_account worker ON worker.public_id=%s AND worker.campaign_id=a.campaign_id AND worker.account_status='open' JOIN fin_actor_account owner ON owner.account_id=worker.account_id AND owner.actor_id=a.actor_id WHERE a.public_id=%s AND a.controller_reference=%s FOR UPDATE OF a,clock,s,employer,worker""",(skill_rule_code,employer_account_public_id,worker_account_public_id,actor_public_id,initiator_reference)).fetchone()
  if state is None:raise ValueError('Trade work requires an eligible trained skill and legal wage accounts')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('start_trade_work_week',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();wid,wpub=c.execute("""INSERT INTO camp_trade_work_week(campaign_id,actor_id,skill_rule_id,employer_account_id,worker_account_id,started_day,started_second,work_status,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,'active',%s) RETURNING work_week_id,public_id""",(state[1],state[0],state[4],state[6],state[7],state[2],state[3],cid)).fetchone();c.execute("INSERT INTO cmd_trade_work_start_receipt VALUES(%s,%s,%s)",(cid,wid,state[5]));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
def complete_trade_work_week_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,work_week_public_id:str)->TradeWorkResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('complete_trade_work_week','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  w=c.execute("""SELECT w.work_week_id,w.campaign_id,w.actor_id,w.employer_account_id,w.worker_account_id,w.started_day,w.started_second,clock.day_number,clock.second_of_day FROM camp_trade_work_week w JOIN actor_actor a ON a.actor_id=w.actor_id JOIN camp_clock clock ON clock.campaign_id=w.campaign_id WHERE w.public_id=%s AND w.work_status='active' AND a.controller_reference=%s FOR UPDATE OF w,a,clock""",(work_week_public_id,initiator_reference)).fetchone()
  if w is None:raise ValueError('Active controlled trade-work week does not exist')
  elapsed=(w[7]-w[5])*86400+w[8]-w[6]
  if elapsed<604800:raise ValueError('Dedicated trade-work week is not complete')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('complete_trade_work_week',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();tx=c.execute("""INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id,occurred_day,occurred_second) VALUES(%s,'CR','Dedicated trade-work weekly wage',%s,%s,%s) RETURNING transaction_id""",(w[1],cid,w[7],w[8])).fetchone()[0]
  for order,(account,amount) in enumerate(((w[4],250),(w[3],-250)),1):c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,%s,%s)",(tx,w[1],account,order,amount))
  c.execute('SELECT fin_post_transaction(%s)',(tx,));c.execute("UPDATE camp_trade_work_week SET work_status='completed',completed_day=%s,completed_second=%s,payment_transaction_id=%s,completion_command_id=%s WHERE work_week_id=%s",(w[7],w[8],tx,cid,w[0]));c.execute("INSERT INTO cmd_trade_work_complete_receipt VALUES(%s,%s,%s,250,%s)",(cid,w[0],elapsed,tx));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
