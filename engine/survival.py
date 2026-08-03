"""Campaign-safe Survival tasks with source-defined availability gates."""
from dataclasses import dataclass
import psycopg
from engine.tasks import resolve_actor_task_command
@dataclass(frozen=True)
class SurvivalResult:
 command_public_id:str;actor_public_id:str;operation_code:str;objective_reference:str;opportunity_available:bool;automatic_failure:bool;check_total:int|None;effect:int|None;succeeded:bool;replayed:bool
def resolve_survival_task_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,actor_public_id:str,operation_code:str,objective_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,location_public_id:str|None=None,opportunity_available:bool=True,random_source=None)->SurvivalResult:
 if not objective_reference.strip():raise ValueError('Survival objective is required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('resolve_survival_task','completed'):raise RuntimeError('Idempotency key belongs to another command')
   r=c.execute("SELECT a.public_id,x.operation_code,x.objective_reference,x.opportunity_available,x.automatic_failure,x.check_total,x.effect,x.succeeded FROM cmd_survival_task_receipt x JOIN actor_actor a ON a.actor_id=x.actor_id WHERE x.command_id=%s",(old[0],)).fetchone();return SurvivalResult(str(old[1]),str(r[0]),r[1],r[2],r[3],r[4],r[5],r[6],r[7],True)
  state=c.execute("SELECT a.actor_id,a.campaign_id,m.rule_id,o.availability_required,l.location_id FROM actor_actor a JOIN rule_survival_mechanic m ON true JOIN rule_survival_operation o ON o.rule_id=m.rule_id AND o.operation_code=%s LEFT JOIN loc_location l ON l.public_id=%s AND l.campaign_id=a.campaign_id WHERE a.public_id=%s AND a.controller_reference=%s FOR UPDATE OF a",(operation_code,location_public_id,actor_public_id,initiator_reference)).fetchone()
  if not state or (location_public_id is not None and state[4] is None):raise ValueError('Survival context is not legal for this campaign')
  if not state[3] and not opportunity_available:raise ValueError('Availability gates only food, water, and fire operations')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_survival_task',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();automatic=state[3] and not opportunity_available;task_id=total=effect=None;succeeded=False
  if not automatic:
   task=resolve_actor_task_command(c,initiator_reference=initiator_reference,idempotency_key=f'survival:{idempotency_key}',actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,skill_rule_code='skill.survival',difficulty_rule_code=difficulty_rule_code,random_source=random_source);task_id=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0];total,effect,succeeded=task.total,task.effect,task.succeeded
  c.execute("INSERT INTO cmd_survival_task_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,state[1],state[0],state[2],operation_code,objective_reference.strip(),state[4],opportunity_available,automatic,task_id,total,effect,succeeded));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return SurvivalResult(str(pub),actor_public_id,operation_code,objective_reference.strip(),opportunity_available,automatic,total,effect,succeeded,False)
