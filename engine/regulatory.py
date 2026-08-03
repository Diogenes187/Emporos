"""Law-Level-derived Admin and Advocate task resolutions."""
from dataclasses import dataclass
import psycopg
from engine.tasks import resolve_actor_task_command
@dataclass(frozen=True)
class RegulatoryResult:
 command_public_id:str;actor_public_id:str;operation_code:str;skill_rule_code:str;law_level:int;illegal_modifier:int;check_total:int;effect:int;succeeded:bool;replayed:bool
def resolve_regulatory_task_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,operation_code:str,skill_rule_code:str,case_reference:str,authority_reference:str,law_level:int,characteristic_rule_code:str,illegal_material_present:bool=False,random_source=None)->RegulatoryResult:
 if not case_reference.strip() or not authority_reference.strip():raise ValueError('Regulatory case and authority are required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('resolve_regulatory_task','completed'):raise RuntimeError('Idempotency key belongs to another command')
   r=c.execute("SELECT a.public_id,x.operation_code,s.rule_code,x.law_level,x.illegal_modifier,x.check_total,x.effect,x.succeeded FROM cmd_regulatory_task_receipt x JOIN actor_actor a ON a.actor_id=x.actor_id JOIN rule_rule s ON s.rule_id=x.skill_rule_id WHERE x.command_id=%s",(old[0],)).fetchone();return RegulatoryResult(str(old[1]),str(r[0]),r[1],r[2],r[3],r[4],r[5],r[6],r[7],True)
  state=c.execute("SELECT a.actor_id,a.campaign_id,m.rule_id,s.rule_id FROM actor_actor a JOIN rule_regulatory_mechanic m ON true JOIN rule_rule s ON s.rule_code=%s JOIN rule_regulatory_operation_skill allowed ON allowed.rule_id=m.rule_id AND allowed.operation_code=%s AND allowed.skill_rule_id=s.rule_id WHERE a.public_id=%s AND a.controller_reference=%s FOR UPDATE OF a",(skill_rule_code,operation_code,actor_public_id,initiator_reference)).fetchone()
  if not state:raise ValueError('Skill is not allowed for this regulatory operation')
  if illegal_material_present and operation_code!='pass-ship-inspection':raise ValueError('Illegal-material modifier applies only to ship inspections')
  illegal_modifier=-2 if illegal_material_present else 0;task=resolve_actor_task_command(c,initiator_reference=initiator_reference,idempotency_key=f'regulatory:{idempotency_key}',actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code=skill_rule_code,law_level=law_level,circumstance_modifier=illegal_modifier,random_source=random_source);task_id=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0];cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_regulatory_task',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();c.execute("INSERT INTO cmd_regulatory_task_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,state[1],state[0],state[2],operation_code,state[3],case_reference.strip(),authority_reference.strip(),law_level,illegal_material_present,illegal_modifier,task_id,task.total,task.effect,task.succeeded));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return RegulatoryResult(str(pub),actor_public_id,operation_code,skill_rule_code,law_level,illegal_modifier,task.total,task.effect,task.succeeded,False)
