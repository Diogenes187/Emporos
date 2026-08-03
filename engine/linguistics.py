"""Relational Linguistics language proficiency commands."""
from dataclasses import dataclass
import psycopg
from engine.tasks import resolve_actor_task_command
@dataclass(frozen=True)
class ActorLanguageResult:
 command_public_id:str;actor_public_id:str;language_code:str;proficiency_kind:str;can_speak:bool;can_read:bool;can_write:bool;replayed:bool
@dataclass(frozen=True)
class LinguisticsDecipherResult:
 command_public_id:str;actor_public_id:str;specimen_reference:str;specimen_medium:str;check_total:int;effect:int;general_meaning_recovered:bool;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("""SELECT a.public_id,l.language_code,p.proficiency_kind,p.can_speak,p.can_read,p.can_write FROM actor_language_proficiency p JOIN actor_actor a USING(actor_id) JOIN camp_language l USING(language_id) WHERE p.source_command_id=%s""",(cid,)).fetchone();return ActorLanguageResult(str(pub),str(r[0]),r[1],r[2],r[3],r[4],r[5],replayed)
def assign_actor_language_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,language_code:str,proficiency_kind:str)->ActorLanguageResult:
 if proficiency_kind not in ('native','additional'):raise ValueError('Language proficiency must be native or additional')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('assign_actor_language','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  state=c.execute("""SELECT a.actor_id,l.language_id,ling.skill_level FROM actor_actor a JOIN camp_language l ON l.campaign_id=a.campaign_id AND l.language_code=%s LEFT JOIN rule_linguistics_mechanic rule ON true LEFT JOIN actor_skill ling ON ling.actor_id=a.actor_id AND ling.skill_rule_id=rule.skill_rule_id WHERE a.public_id=%s AND a.controller_reference=%s FOR UPDATE OF a,l""",(language_code,actor_public_id,initiator_reference)).fetchone()
  if state is None:raise ValueError('Controlled actor or campaign language does not exist')
  if proficiency_kind=='additional' and (state[2] is None or state[2]<1):raise ValueError('Additional language requires available Linguistics level')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('assign_actor_language',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();flags=(True,True,False) if proficiency_kind=='native' else (False,True,True);c.execute("INSERT INTO actor_language_proficiency VALUES(%s,%s,(SELECT campaign_id FROM actor_actor WHERE actor_id=%s),%s,%s,%s,%s,%s)",(state[0],state[1],state[0],proficiency_kind,*flags,cid));c.execute("INSERT INTO cmd_actor_language_receipt VALUES(%s,%s,%s,%s,%s)",(cid,state[0],state[1],proficiency_kind,None if proficiency_kind=='native' else state[2]));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return _load(c,cid,pub,False)
def decipher_preserved_language_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,specimen_reference:str,specimen_medium:str,characteristic_rule_code:str,difficulty_rule_code:str,language_code:str|None=None,random_source=None)->LinguisticsDecipherResult:
 if specimen_medium not in ('inscription','recorded-message','other') or not specimen_reference.strip():raise ValueError('Deciphering requires a preserved specimen and valid medium')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('decipher_preserved_language','completed'):raise RuntimeError('Idempotency key belongs to another command')
   r=c.execute("SELECT a.public_id,x.specimen_reference,x.specimen_medium,x.check_total,x.effect,x.general_meaning_recovered FROM cmd_linguistics_decipher_receipt x JOIN actor_actor a USING(actor_id) WHERE x.command_id=%s",(old[0],)).fetchone();return LinguisticsDecipherResult(str(old[1]),str(r[0]),r[1],r[2],r[3],r[4],r[5],True)
  actor=c.execute("SELECT actor_id,campaign_id FROM actor_actor WHERE public_id=%s AND controller_reference=%s",(actor_public_id,initiator_reference)).fetchone()
  if actor is None:raise ValueError('Controlled deciphering actor does not exist')
  language_id=None
  if language_code is not None:
   row=c.execute("SELECT language_id FROM camp_language WHERE campaign_id=%s AND language_code=%s",(actor[1],language_code)).fetchone()
   if row is None:raise ValueError('Specimen language is not registered in this campaign')
   language_id=row[0]
  task=resolve_actor_task_command(c,initiator_reference=initiator_reference,idempotency_key=f'linguistics-decipher:{idempotency_key}',actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code='skill.linguistics',difficulty_rule_code=difficulty_rule_code,random_source=random_source);task_id=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0];cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('decipher_preserved_language',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();c.execute("INSERT INTO cmd_linguistics_decipher_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,actor[0],language_id,specimen_reference.strip(),specimen_medium,task_id,task.total,task.effect,task.succeeded));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return LinguisticsDecipherResult(str(pub),actor_public_id,specimen_reference.strip(),specimen_medium,task.total,task.effect,task.succeeded,False)
