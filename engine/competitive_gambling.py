"""Competitive Gambling pots and cheating resolution."""
from dataclasses import dataclass
import psycopg
from engine.tasks import resolve_actor_task_command
@dataclass(frozen=True)
class CompetitiveGamblingResult:
 command_public_id:str; game_public_id:str; status:str; basis:str; winner_actor_public_id:str|None; winning_score:int|None; replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT g.public_id,g.game_status,g.resolution_basis,a.public_id,x.winning_score FROM cmd_competitive_gambling_receipt x JOIN camp_competitive_gambling_game g USING(game_id) LEFT JOIN actor_actor a ON a.actor_id=g.winner_actor_id WHERE x.command_id=%s""",(cid,)).fetchone();return CompetitiveGamblingResult(str(pub),str(r[0]),r[1],r[2],str(r[3]) if r[3] else None,r[4],replayed)
def resolve_competitive_gambling_command(connection:psycopg.Connection,*,referee_reference:str,idempotency_key:str,venue_reference:str,game_reference:str,pot_reference:str,participants:list[dict],random_source=None)->CompetitiveGamblingResult:
 if len(participants)<2:raise ValueError('Competitive Gambling requires at least two players')
 if len({p['actor_public_id'] for p in participants})!=len(participants):raise ValueError('Competitive Gambling participants must be distinct')
 with connection.transaction():
  old=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(referee_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('resolve_competitive_gambling','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(connection,old[0],old[1],True)
  rows=[];campaign=None
  for order,p in enumerate(participants,1):
   actor=connection.execute("SELECT actor_id,campaign_id,controller_reference FROM actor_actor WHERE public_id=%s FOR UPDATE",(p['actor_public_id'],)).fetchone()
   if not actor:raise ValueError('Gambling participant not found')
   if campaign is None:campaign=actor[1]
   if actor[1]!=campaign:raise ValueError('All Gambling participants must share a campaign')
   normal=resolve_actor_task_command(connection,initiator_reference=actor[2],idempotency_key=f'{idempotency_key}-normal-{order}',actor_public_id=p['actor_public_id'],characteristic_rule_code=p['characteristic_rule_code'],skill_rule_code='skill.gambling',difficulty_rule_code='difficulty.average',random_source=random_source)
   normal_id=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(normal.command_public_id,)).fetchone()[0];rows.append({'order':order,'actor_id':actor[0],'public':p['actor_public_id'],'controller':actor[2],'normal':normal,'normal_id':normal_id,'cheat':bool(p.get('cheating'))})
  for r in rows:
   r['cheat_result']=None;r['cheat_id']=None
   if r['cheat']:
    q=resolve_actor_task_command(connection,initiator_reference=r['controller'],idempotency_key=f'{idempotency_key}-cheat-{r["order"]}',actor_public_id=r['public'],characteristic_rule_code=participants[r['order']-1]['characteristic_rule_code'],skill_rule_code='skill.gambling',difficulty_rule_code='difficulty.average',random_source=random_source);r['cheat_result']=q;r['cheat_id']=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(q.command_public_id,)).fetchone()[0]
  for r in rows:r['caught']=r['cheat'] and any(o is not r and o['normal'].succeeded for o in rows)
  uncaught=[r for r in rows if r['cheat'] and not r['caught']];eligible=[r for r in rows if not r['caught']]
  candidates=uncaught if uncaught else eligible;basis='cheating' if uncaught else 'normal'
  if not candidates:status='no_eligible_winner';basis='none';winner=None;score=None;tied=False
  else:
   key=(lambda r:r['cheat_result'].total) if uncaught else (lambda r:r['normal'].total);score=max(key(r) for r in candidates);top=[r for r in candidates if key(r)==score];tied=len(top)>1;winner=None if tied else top[0];status='tied' if tied else 'resolved';basis='tie' if tied else basis
  cid,pub=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_competitive_gambling',%s,%s) RETURNING command_id,public_id",(referee_reference,idempotency_key)).fetchone();rule=connection.execute("SELECT rule_id FROM rule_competitive_gambling").fetchone()[0]
  game_id,game_pub=connection.execute("""INSERT INTO camp_competitive_gambling_game(campaign_id,venue_reference,game_reference,pot_reference,game_status,resolution_basis,winner_actor_id,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING game_id,public_id""",(campaign,venue_reference,game_reference,pot_reference,status,basis,winner['actor_id'] if winner else None,cid)).fetchone();connection.execute("INSERT INTO cmd_competitive_gambling_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,game_id,rule,referee_reference,len(rows),sum(r['cheat'] for r in rows),len(uncaught),score,tied))
  for r in rows:connection.execute("INSERT INTO cmd_competitive_gambling_participant VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,r['order'],r['actor_id'],r['normal_id'],r['normal'].total,r['normal'].succeeded,r['cheat'],r['cheat_id'],r['cheat_result'].total if r['cheat_result'] else None,r['caught'],not r['caught'],winner is r))
  connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(connection,cid,pub,False)
