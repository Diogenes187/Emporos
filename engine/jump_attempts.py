"""Task-backed jump initiation check and audited duration roll."""
from dataclasses import dataclass
import secrets
import psycopg
from engine.tasks import resolve_actor_task_command

@dataclass(frozen=True)
class JumpAttemptResult:
 command_public_id:str;journey_public_id:str;engineer_actor_public_id:str
 final_result:int;outcome:str;duration_hours:int;replayed:bool

def _load(c,cid,pub,replayed):
 row=c.execute("SELECT journey.public_id,actor.public_id,receipt.final_result,receipt.jump_outcome,receipt.duration_hours FROM cmd_jump_attempt_receipt receipt JOIN journey_journey journey ON journey.journey_id=receipt.journey_id JOIN actor_actor actor ON actor.actor_id=receipt.engineer_actor_id WHERE receipt.command_id=%s",(cid,)).fetchone()
 return JumpAttemptResult(str(pub),str(row[0]),str(row[1]),row[2],row[3],row[4],replayed)

def resolve_jump_attempt_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,journey_public_id:str,engineer_actor_public_id:str,within_safe_limit:bool=True,fuel_type_code:str='refined',random_source=None)->JumpAttemptResult:
 rng=random_source or secrets.SystemRandom()
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('resolve_jump_attempt','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  state=c.execute("""SELECT journey.journey_id,journey.campaign_id,leg.journey_leg_id,
  plan.distance_parsecs,plan.jump_number,actor.actor_id,navigation.navigation_solution_id,
  system.duration_base_hours,system.duration_dice_count,system.duration_die_sides,
  system.success_target,system.misjump_maximum_result,system.fuel_unrefined_modifier,system.within_limit_modifier
  FROM journey_journey journey JOIN journey_leg leg ON leg.journey_id=journey.journey_id AND leg.leg_order=1
  JOIN cmd_jump_journey_planning_receipt plan ON plan.journey_id=journey.journey_id
  JOIN camp_campaign campaign ON campaign.campaign_id=journey.campaign_id
  JOIN actor_actor actor ON actor.campaign_id=journey.campaign_id
  JOIN journey_navigation_solution navigation ON navigation.journey_leg_id=leg.journey_leg_id AND navigation.operation_kind='jump_route' AND navigation.succeeded
  JOIN rule_jump_travel_system system ON system.jump_system_code='cepheus-standard'
  WHERE journey.public_id=%s AND campaign.owner_reference=%s AND actor.public_id=%s
    AND journey.journey_status='planning' AND leg.leg_status='planned'
    AND NOT EXISTS(SELECT 1 FROM journey_jump_attempt attempt WHERE attempt.journey_leg_id=leg.journey_leg_id)
  FOR UPDATE OF journey,leg,actor""",(journey_public_id,initiator_reference,engineer_actor_public_id)).fetchone()
  if not state:raise ValueError('Jump needs a successful route and an available engineer')
  task=resolve_actor_task_command(c,initiator_reference=initiator_reference,idempotency_key='engineering:'+idempotency_key,actor_public_id=engineer_actor_public_id,characteristic_rule_code='characteristic.education',skill_rule_code='skill.engineering',difficulty_rule_code='difficulty.average',random_source=rng)
  task_id=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(task.command_public_id,)).fetchone()[0]
  modifier=(state[12] if fuel_type_code=='unrefined' else 0)+(state[13] if not within_safe_limit else 0)
  final=task.total+modifier
  outcome='accurate' if final>=state[10] else ('misjump' if final<=state[11] else 'inaccurate')
  duration=state[7];duration_dice=[]
  for _ in range(state[8]):duration_dice.append(rng.randint(1,state[9]))
  duration+=sum(duration_dice)
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('resolve_jump_attempt',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  for order,value in enumerate(duration_dice,1):c.execute("INSERT INTO cmd_random_draw(command_id,draw_group,draw_order,die_sides,result) VALUES(%s,'jump_duration',%s,%s,%s)",(cid,order,state[9],value))
  attempt=c.execute("""INSERT INTO journey_jump_attempt(journey_leg_id,campaign_id,jump_system_code,jump_number,plotted_distance_parsecs,engineering_effect,fuel_type_code,within_safe_limit,natural_roll,modifier_total,final_result,jump_outcome,duration_hours,emergence_distance_parsecs,command_id,navigation_solution_id,engineering_task_command_id)
  VALUES(%s,%s,'cepheus-standard',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING jump_attempt_id""",(state[2],state[1],state[4],state[3],task.effect,fuel_type_code,within_safe_limit,sum(task.dice),modifier,final,outcome,duration,(state[3] if outcome=='misjump' else None),cid,state[6],task_id)).fetchone()[0]
  c.execute("INSERT INTO cmd_jump_attempt_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,state[1],state[0],state[2],attempt,state[5],task_id,state[6],sum(task.dice),modifier,final,outcome,duration))
  c.execute("UPDATE journey_journey SET journey_status='ready' WHERE journey_id=%s",(state[0],));c.execute("UPDATE journey_leg SET leg_status='committed' WHERE journey_leg_id=%s",(state[2],))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'jump_attempt_resolved')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load(c,cid,pub,False)
