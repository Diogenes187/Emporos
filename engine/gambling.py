"""Audited non-competitive Gambling resolution."""
from dataclasses import dataclass
from decimal import Decimal
import psycopg
from engine.tasks import resolve_actor_task_command
@dataclass(frozen=True)
class HouseGamblingResult:
 command_public_id:str; odds_code:str; bet_credits:int; dice:tuple[int,...]
 natural_two:bool; won:bool; winnings_credits:Decimal|None; replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT o.odds_code,x.bet_credits,x.natural_two,x.won,x.winnings_credits,x.task_command_id FROM cmd_house_gambling_receipt x JOIN rule_gambling_house_odds o ON o.rule_id=x.odds_rule_id WHERE x.command_id=%s""",(cid,)).fetchone();dice=tuple(x[0] for x in c.execute("SELECT result FROM cmd_random_draw WHERE command_id=%s AND draw_group='task' ORDER BY draw_order",(r[5],)).fetchall());return HouseGamblingResult(str(pub),r[0],r[1],dice,r[2],r[3],r[4],replayed)
def resolve_house_gambling_command(connection:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,characteristic_rule_code:str,odds_code:str,venue_reference:str,game_reference:str,bet_credits:int,rigged_terms_reference:str|None=None,random_source=None)->HouseGamblingResult:
 if bet_credits<=0 or not venue_reference.strip() or not game_reference.strip():raise ValueError('House game requires positive bet, venue, and game references')
 with connection.transaction():
  old=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('resolve_house_gambling','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(connection,old[0],old[1],True)
  actor=connection.execute("SELECT actor_id FROM actor_actor WHERE public_id=%s AND controller_reference=%s FOR UPDATE",(actor_public_id,initiator_reference)).fetchone();rule=connection.execute("SELECT rule_id,check_modifier,payoff_numerator,payoff_denominator,maximum_bet_credits FROM rule_gambling_house_odds WHERE odds_code=%s",(odds_code,)).fetchone()
  if not actor or not rule:raise ValueError('Controlled gambler or odds band not found')
  if rule[4] is not None and bet_credits>rule[4]:raise ValueError('Bet exceeds the published maximum')
  if rule[2] is None and (not rigged_terms_reference or not rigged_terms_reference.strip()):raise ValueError('Rigged game requires referee-defined payoff terms')
  task=resolve_actor_task_command(connection,initiator_reference=initiator_reference,idempotency_key=idempotency_key+'-task',actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code='skill.gambling',difficulty_rule_code='difficulty.average',circumstance_modifier=rule[1],random_source=random_source)
  task_id=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0];natural=sum(task.dice)==2;won=task.succeeded and not natural
  winnings=None if won and rule[2] is None else (Decimal(bet_credits)*Decimal(rule[2])/Decimal(rule[3]) if won else Decimal(0))
  cid,pub=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_house_gambling',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  connection.execute("INSERT INTO cmd_house_gambling_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,task_id,actor[0],rule[0],venue_reference.strip(),game_reference.strip(),bet_credits,rule[1],natural,won,rule[2],rule[3],winnings,rigged_terms_reference.strip() if rigged_terms_reference else None))
  connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(connection,cid,pub,False)
