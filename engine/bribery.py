"""Relational Bribery attempt and consequence lifecycle."""
from dataclasses import dataclass
import secrets
import psycopg
from engine.tasks import resolve_actor_task_command

@dataclass(frozen=True)
class BriberyResult:
    command_public_id:str; case_id:int; attempt_number:int; offer_credits:int
    minimum_bribe_credits:int; offer_modifier:int; automatic_failure:bool
    accepted:bool; status:str; replayed:bool

def _load(c,cid,pub,replayed):
    r=c.execute("""SELECT x.bribery_case_id,x.attempt_number,x.offer_credits,x.minimum_bribe_credits,
      x.offer_modifier,x.automatic_failure,x.accepted,k.case_status FROM cmd_bribery_attempt_receipt x
      JOIN camp_bribery_case k USING(bribery_case_id) WHERE x.command_id=%s""",(cid,)).fetchone()
    return BriberyResult(str(pub),*r,replayed)

def attempt_bribery_command(connection:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,
 actor_public_id:str,target_reference:str,incident_reference:str,offense_code:str,law_level:int,
 characteristic_rule_code:str,offer_credits:int,random_source=None)->BriberyResult:
    if not target_reference.strip() or not incident_reference.strip(): raise ValueError('Bribery target and incident references are required')
    if offer_credits<=0: raise ValueError('Bribe offer must be positive')
    rng=random_source or secrets.SystemRandom()
    with connection.transaction():
      old=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
      if old:
       if old[2:]!=('attempt_bribery','completed'): raise RuntimeError('Idempotency key belongs to another command')
       return _load(connection,old[0],old[1],True)
      actor=connection.execute("SELECT actor_id FROM actor_actor WHERE public_id=%s AND controller_reference=%s FOR UPDATE",(actor_public_id,initiator_reference)).fetchone()
      rule=connection.execute("SELECT rule_id,check_modifier,credits_per_die FROM rule_bribery_offense WHERE offense_code=%s",(offense_code,)).fetchone()
      if not actor or not rule: raise ValueError('Controlled actor or Bribery offense not found')
      case=connection.execute("""SELECT bribery_case_id,offense_rule_id,law_level,minimum_bribe_roll,minimum_bribe_credits,
        case_status,attempts_completed FROM camp_bribery_case WHERE actor_id=%s AND target_reference=%s AND incident_reference=%s FOR UPDATE""",(actor[0],target_reference.strip(),incident_reference.strip())).fetchone()
      first=case is None; roll=rng.randint(1,6) if first else case[3]; minimum=roll*rule[2] if first else case[4]
      if first:
       case_id=connection.execute("""INSERT INTO camp_bribery_case(actor_id,target_reference,incident_reference,offense_rule_id,law_level,minimum_bribe_roll,minimum_bribe_credits)
        VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING bribery_case_id""",(actor[0],target_reference.strip(),incident_reference.strip(),rule[0],law_level,roll,minimum)).fetchone()[0]; attempt=1
      else:
       if case[1]!=rule[0] or case[2]!=law_level: raise ValueError('Bribery case facts cannot change between attempts')
       if case[5]!='active' or case[6]!=1: raise ValueError('Bribery case does not permit another offer')
       prior=connection.execute("SELECT offer_credits FROM cmd_bribery_attempt_receipt WHERE bribery_case_id=%s AND attempt_number=1",(case[0],)).fetchone()[0]
       if offer_credits!=prior*2: raise ValueError('Second bribe offer must be twice the first offer')
       case_id=case[0]; attempt=2
      cid,pub=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('attempt_bribery',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
      if first: connection.execute("INSERT INTO cmd_random_draw(command_id,draw_group,draw_order,die_sides,result) VALUES(%s,'bribery_minimum',1,6,%s)",(cid,roll))
      auto=offer_credits<minimum; bonus=max(0,offer_credits//minimum-1); task_id=None; accepted=False
      if not auto:
       task=resolve_actor_task_command(connection,initiator_reference=initiator_reference,idempotency_key=idempotency_key+'-skill',actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code='skill.bribery',difficulty_rule_code='difficulty.average',circumstance_modifier=rule[1]+bonus,random_source=rng)
       task_id=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0]; accepted=task.succeeded
      status='accepted' if accepted else ('pending_social_check' if attempt==2 else 'active')
      connection.execute("UPDATE camp_bribery_case SET attempts_completed=%s,case_status=%s WHERE bribery_case_id=%s",(attempt,status,case_id))
      connection.execute("INSERT INTO cmd_bribery_attempt_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,case_id,task_id,attempt,offer_credits,roll,rule[2],minimum,rule[1],bonus,auto,accepted))
      connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
      return _load(connection,cid,pub,False)

def resolve_bribery_consequence_command(connection:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,target_reference:str,incident_reference:str,random_source=None)->bool:
    with connection.transaction():
      old=connection.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
      if old:
       if old[2:]!=('resolve_bribery_consequence','completed'): raise RuntimeError('Idempotency key belongs to another command')
       return bool(connection.execute("SELECT charged_with_attempted_bribery FROM cmd_bribery_consequence_receipt WHERE command_id=%s",(old[0],)).fetchone()[0])
      case=connection.execute("""SELECT k.bribery_case_id,k.law_level FROM camp_bribery_case k JOIN actor_actor a USING(actor_id)
       WHERE a.public_id=%s AND a.controller_reference=%s AND k.target_reference=%s AND k.incident_reference=%s AND k.case_status='pending_social_check' FOR UPDATE OF k""",(actor_public_id,initiator_reference,target_reference,incident_reference)).fetchone()
      if not case: raise ValueError('Bribery case does not require a Social Standing check')
      task=resolve_actor_task_command(connection,initiator_reference=initiator_reference,idempotency_key=idempotency_key+'-social',actor_public_id=actor_public_id,characteristic_rule_code='characteristic.social-standing',law_level=case[1],random_source=random_source)
      task_id=connection.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0]; charged=not task.succeeded
      cid,_=connection.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_bribery_consequence',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
      connection.execute("INSERT INTO cmd_bribery_consequence_receipt VALUES(%s,%s,%s,%s)",(cid,case[0],task_id,charged)); connection.execute("UPDATE camp_bribery_case SET case_status=%s WHERE bribery_case_id=%s",('charged' if charged else 'cleared',case[0])); connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,)); return charged
