"""Audited owner/referee corrections without rewriting mechanical history."""
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class CharacterCorrectionResult:
 command_public_id:str;actor_public_id:str;correction_kind:str;target_code:str
 prior_value:int|None;resulting_value:int|None;prior_maximum:int|None
 resulting_maximum:int|None;reason:str;replayed:bool

def _load(c,command_id,public_id,replayed):
 row=c.execute("""SELECT actor.public_id,receipt.correction_kind,
  COALESCE(rule.rule_code,receipt.finance_field,location.public_id::text),
  receipt.prior_value,receipt.resulting_value,receipt.prior_maximum,
  receipt.resulting_maximum,receipt.reason
  FROM cmd_character_correction_receipt receipt
  JOIN actor_actor actor USING(actor_id)
  LEFT JOIN rule_rule rule ON rule.rule_id=receipt.target_rule_id
  LEFT JOIN loc_location location ON location.location_id=receipt.resulting_location_id
  WHERE receipt.command_id=%s""",(command_id,)).fetchone()
 return CharacterCorrectionResult(str(public_id),str(row[0]),row[1],row[2],row[3],row[4],row[5],row[6],row[7],replayed)

def correct_character_state_command(c:psycopg.Connection,*,initiator_reference:str,
 idempotency_key:str,actor_public_id:str,correction_kind:str,target_code:str|None=None,
 resulting_value:int|None=None,resulting_maximum:int|None=None,
 location_public_id:str|None=None,reason:str)->CharacterCorrectionResult:
 reason=(reason or '').strip()
 if not reason:raise ValueError('A correction reason is required')
 if correction_kind not in ('skill','characteristic','finance','location'):
  raise ValueError('Unknown character correction kind')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('correct_character_state','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  actor=c.execute("""SELECT actor.actor_id,actor.campaign_id,actor.concurrency_version
   FROM actor_actor actor JOIN camp_campaign campaign USING(campaign_id)
   WHERE actor.public_id=%s AND campaign.owner_reference=%s
   AND actor.lifecycle_status='active' FOR UPDATE OF actor""",(actor_public_id,initiator_reference)).fetchone()
  if not actor:raise PermissionError('Character is absent or outside this referee authority')
  command_id,public_id=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('correct_character_state',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  rule_id=finance_field=prior=prior_max=old_location=new_location=None
  if correction_kind=='skill':
   if resulting_value is None or not 0<=resulting_value<=15:raise ValueError('Corrected skill level must be between 0 and 15')
   rule=c.execute("SELECT skill.rule_id FROM rule_skill skill JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code=%s",(target_code,)).fetchone()
   if not rule:raise ValueError('Unknown skill correction target')
   rule_id=rule[0];state=c.execute("SELECT skill_level FROM actor_skill WHERE actor_id=%s AND skill_rule_id=%s FOR UPDATE",(actor[0],rule_id)).fetchone();prior=state[0] if state else None
   c.execute("""INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level) VALUES(%s,%s,%s)
    ON CONFLICT(actor_id,skill_rule_id) DO UPDATE SET skill_level=excluded.skill_level""",(actor[0],rule_id,resulting_value))
  elif correction_kind=='characteristic':
   if resulting_value is None or resulting_maximum is None or resulting_maximum<1 or resulting_value<0 or resulting_value>resulting_maximum:raise ValueError('Corrected characteristic must satisfy 0 <= current <= maximum')
   state=c.execute("""SELECT score.characteristic_rule_id,score.current_value,score.maximum_value FROM actor_characteristic score JOIN rule_rule rule ON rule.rule_id=score.characteristic_rule_id WHERE score.actor_id=%s AND rule.rule_code=%s FOR UPDATE OF score""",(actor[0],target_code)).fetchone()
   if not state:raise ValueError('Unknown characteristic correction target')
   rule_id,prior,prior_max=state;c.execute("UPDATE actor_characteristic SET current_value=%s,maximum_value=%s WHERE actor_id=%s AND characteristic_rule_id=%s",(resulting_value,resulting_maximum,actor[0],rule_id))
  elif correction_kind=='finance':
   allowed=('cash_credits','debt_credits','medical_debt_credits','anagathic_debt_credits')
   if target_code not in allowed or resulting_value is None or resulting_value<0:raise ValueError('Corrected financial value must be a nonnegative legal field')
   finance_field=target_code;c.execute("INSERT INTO actor_financial_state(actor_id) VALUES(%s) ON CONFLICT(actor_id) DO NOTHING",(actor[0],))
   prior=c.execute(f'SELECT {finance_field} FROM actor_financial_state WHERE actor_id=%s FOR UPDATE',(actor[0],)).fetchone()[0]
   c.execute(f'UPDATE actor_financial_state SET {finance_field}=%s WHERE actor_id=%s',(resulting_value,actor[0]))
  else:
   location=c.execute("""SELECT location.location_id FROM loc_location location
    JOIN rule_location_type type ON type.location_type_rule_id=location.location_type_rule_id
    WHERE location.public_id=%s AND location.campaign_id=%s AND type.permits_actor_position""",(location_public_id,actor[1])).fetchone()
   if not location:raise ValueError('Correction location is absent from this campaign')
   new_location=location[0];current=c.execute("SELECT actor_position_id,location_id FROM loc_actor_position WHERE actor_id=%s AND position_status='current' FOR UPDATE",(actor[0],)).fetchone();old_location=current[1] if current else None
   if current:c.execute("UPDATE loc_actor_position SET position_status='ended',ended_at=clock_timestamp() WHERE actor_position_id=%s",(current[0],))
   c.execute("INSERT INTO loc_actor_position(campaign_id,actor_id,location_id,source_command_id) VALUES(%s,%s,%s,%s)",(actor[1],actor[0],new_location,command_id))
  c.execute("""INSERT INTO cmd_character_correction_receipt
   (command_id,campaign_id,actor_id,correction_kind,target_rule_id,finance_field,
    prior_value,resulting_value,prior_maximum,resulting_maximum,prior_location_id,
    resulting_location_id,reason) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
   (command_id,actor[1],actor[0],correction_kind,rule_id,finance_field,prior,resulting_value,prior_max,resulting_maximum,old_location,new_location,reason))
  c.execute("UPDATE actor_actor SET concurrency_version=concurrency_version+1 WHERE actor_id=%s",(actor[0],))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'character_state_corrected')",(command_id,))
  c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return _load(c,command_id,public_id,False)
