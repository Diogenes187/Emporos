"""Monthly payroll for assigned ship crew."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class CrewPayrollResult:
 command_public_id:str;ship_public_id:str;crew_paid:int;total_amount:int;balance_after:int;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT ship.public_id,count(line.line_order),receipt.total_amount_minor,balance.balance_minor FROM cmd_ship_crew_payroll_receipt receipt JOIN ship_ship ship USING(ship_id) JOIN cmd_ship_crew_payroll_line line USING(command_id) JOIN cmd_trading_preparation_receipt setup ON setup.actor_id=receipt.payer_actor_id AND setup.ship_id=receipt.ship_id JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id WHERE receipt.command_id=%s GROUP BY ship.public_id,receipt.total_amount_minor,balance.balance_minor""",(cid,)).fetchone();return CrewPayrollResult(str(pub),str(r[0]),r[1],r[2],r[3],replayed)
def pay_ship_crew_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,payer_actor_public_id:str,ship_public_id:str)->CrewPayrollResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('pay_ship_crew','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  state=c.execute("""SELECT campaign.campaign_id,payer.actor_id,ship.ship_id,ship.name,setup.trader_account_id,balance.balance_minor,clock.day_number FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) JOIN actor_actor payer USING(campaign_id) JOIN ship_ship ship USING(campaign_id) JOIN cmd_trading_preparation_receipt setup ON setup.campaign_id=campaign.campaign_id AND setup.actor_id=payer.actor_id AND setup.ship_id=ship.ship_id JOIN fin_account_balance balance ON balance.account_id=setup.trader_account_id WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND payer.public_id=%s AND ship.public_id=%s FOR UPDATE OF payer,ship,clock""",(campaign_public_id,initiator_reference,payer_actor_public_id,ship_public_id)).fetchone()
  if not state:raise ValueError('Ship or payroll account is unavailable')
  crew=c.execute("""SELECT assignment.crew_assignment_id,actor.actor_id,actor.name,definition.position_code,definition.position_name,definition.standard_monthly_salary_minor FROM ship_crew_assignment assignment JOIN actor_actor actor USING(actor_id) JOIN ship_crew_position position USING(ship_crew_position_id) JOIN ship_crew_position_definition definition ON definition.crew_position_rule_id=position.crew_position_rule_id WHERE assignment.ship_id=%s AND assignment.duty_status='active' AND definition.standard_monthly_salary_minor IS NOT NULL ORDER BY assignment.crew_assignment_id FOR UPDATE OF assignment,actor""",(state[2],)).fetchall()
  if not crew:raise ValueError('Ship has no assigned salaried crew')
  total=sum(row[5] for row in crew)
  if state[5]<total:raise ValueError(f'Payroll costs Cr {total}; account holds Cr {state[5]}')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('pay_ship_crew',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();c.execute("INSERT INTO cmd_ship_crew_payroll_receipt VALUES(%s,%s,%s,%s,%s,%s)",(cid,state[0],state[2],state[1],state[6],total))
  for order,row in enumerate(crew,1):
   account=c.execute("SELECT account.account_id FROM fin_actor_account owner JOIN fin_account account USING(account_id) WHERE owner.actor_id=%s AND account.account_code=%s AND account.account_status='open'",(row[1],'crew-pay-'+str(row[1]))).fetchone()
   if account:account=account[0]
   else:
    account=c.execute("INSERT INTO fin_account(campaign_id,currency_code,account_code,name,account_kind) VALUES(%s,'CR',%s,%s,'asset') RETURNING account_id",(state[0],'crew-pay-'+str(row[1]),row[2]+' Crew Pay')).fetchone()[0];c.execute("INSERT INTO fin_actor_account VALUES(%s,%s,%s)",(account,state[0],row[1]))
   description=f'{row[4]} salary aboard {state[3]}'
   tx=c.execute("INSERT INTO fin_transaction(campaign_id,currency_code,description,command_id) VALUES(%s,'CR',%s,%s) RETURNING transaction_id",(state[0],description,cid)).fetchone()[0]
   c.execute("INSERT INTO fin_entry(transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor) VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)",(tx,state[0],state[4],-row[5],tx,state[0],account,row[5]));c.execute("SELECT fin_post_transaction(%s)",(tx,))
   cost='salary-'+row[3];expense=c.execute("INSERT INTO ship_operating_expense(ship_id,campaign_id,operating_cost_code,financial_transaction_id,quantity,amount_minor,expense_day,description) VALUES(%s,%s,%s,%s,1,%s,%s,%s) RETURNING operating_expense_id",(state[2],state[0],cost,tx,row[5],state[6],description)).fetchone()[0]
   c.execute("INSERT INTO cmd_ship_crew_payroll_line VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,order,state[0],row[0],row[1],cost,row[5],account,tx,expense))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'ship_crew_paid')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
