"""Audited assignment of the six initial rolls before career entry."""
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class CharacteristicArrangementResult:
 command_public_id:str;actor_public_id:str;scores:tuple[tuple[str,str,int],...];replayed:bool

def _load(c,command_id,public_id,replayed):
 actor=c.execute("SELECT actor.public_id FROM cmd_characteristic_arrangement_receipt receipt JOIN actor_actor actor USING(actor_id) WHERE receipt.command_id=%s",(command_id,)).fetchone()[0]
 rows=c.execute("""SELECT target.rule_code,source.rule_code,line.resulting_score
  FROM cmd_characteristic_arrangement_score line
  JOIN rule_rule target ON target.rule_id=line.target_characteristic_rule_id
  JOIN rule_rule source ON source.rule_id=line.source_characteristic_rule_id
  WHERE line.command_id=%s ORDER BY line.display_order""",(command_id,)).fetchall()
 return CharacteristicArrangementResult(str(public_id),str(actor),tuple(rows),replayed)

def arrange_characteristics_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,source_characteristic_codes:tuple[str,...])->CharacteristicArrangementResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=("arrange_characteristics","completed"):raise RuntimeError("Idempotency key belongs to another command")
   return _load(c,old[0],old[1],True)
  actor=c.execute("""SELECT actor.actor_id,actor.concurrency_version,lifepath.lifepath_status
   FROM actor_actor actor LEFT JOIN actor_lifepath_state lifepath USING(actor_id)
   WHERE actor.public_id=%s AND actor.controller_reference=%s FOR UPDATE OF actor""",(actor_public_id,initiator_reference)).fetchone()
  if not actor:raise ValueError("Actor is absent or not controlled by this player")
  if actor[2] in ('completed','deceased') or c.execute("SELECT EXISTS(SELECT 1 FROM actor_career_stint WHERE actor_id=%s)",(actor[0],)).fetchone()[0]:raise ValueError("Rolls may be arranged only before entering a career")
  rows=c.execute("""SELECT state.characteristic_rule_id,rule.rule_code,definition.display_order,state.current_value
   FROM actor_characteristic state JOIN rule_characteristic definition ON definition.rule_id=state.characteristic_rule_id
   JOIN rule_rule rule ON rule.rule_id=state.characteristic_rule_id WHERE state.actor_id=%s ORDER BY definition.display_order""",(actor[0],)).fetchall()
  codes=tuple(row[1] for row in rows)
  if len(rows)!=6 or len(source_characteristic_codes)!=6 or set(source_characteristic_codes)!=set(codes):raise ValueError("Assign each of the six rolled values exactly once")
  by_code={row[1]:row for row in rows};snapshot={row[1]:row[3] for row in rows}
  command_id,public_id=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('arrange_characteristics',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  after=actor[1]+1;c.execute("INSERT INTO cmd_characteristic_arrangement_receipt VALUES(%s,%s,%s,%s)",(command_id,actor[0],actor[1],after))
  for target,source in zip(rows,source_characteristic_codes):
   value=snapshot[source];c.execute("UPDATE actor_characteristic SET current_value=%s,maximum_value=%s WHERE actor_id=%s AND characteristic_rule_id=%s",(value,value,actor[0],target[0]))
   c.execute("INSERT INTO cmd_characteristic_arrangement_score VALUES(%s,%s,%s,%s,%s,%s)",(command_id,target[0],by_code[source][0],target[2],target[3],value))
  c.execute("UPDATE actor_actor SET concurrency_version=%s WHERE actor_id=%s",(after,actor[0]));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'characteristics_arranged')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return _load(c,command_id,public_id,False)
