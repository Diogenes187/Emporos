"""Finalize personal combat through the general encounter aggregate."""
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class PersonalCombatResolutionResult:
 command_public_id:str; outcome_kind:str; replayed:bool

def resolve_personal_combat_command(connection:psycopg.Connection,*,
 initiator_reference:str,referee_reference:str,idempotency_key:str,
 encounter_public_id:str,outcome_kind:str,resolution_summary:str,
 winning_side_code:str|None=None,avoiding_side_code:str|None=None,
 opposing_side_code:str|None=None)->PersonalCombatResolutionResult:
 if not resolution_summary or not resolution_summary.strip():
  raise ValueError("Combat resolution requires a summary")
 with connection.transaction():
  existing=connection.execute("""SELECT command_id,public_id,command_type,command_status
   FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE""",
   (initiator_reference,idempotency_key)).fetchone()
  if existing:
   if existing[2:]!=("resolve_personal_combat","completed"): raise RuntimeError("Idempotency key belongs to another command")
   row=connection.execute("SELECT outcome_kind FROM cmd_personal_combat_resolution_receipt WHERE command_id=%s",(existing[0],)).fetchone()
   return PersonalCombatResolutionResult(str(existing[1]),row[0],True)
  state=connection.execute("""SELECT encounter.encounter_id,encounter.campaign_id,
    campaign.owner_reference FROM enc_encounter encounter JOIN camp_campaign campaign USING(campaign_id)
    JOIN enc_personal_combat combat USING(encounter_id)
    WHERE encounter.public_id=%s AND encounter.encounter_status='active'
      AND combat.combat_status='active' FOR UPDATE OF encounter,combat""",(encounter_public_id,)).fetchone()
  if state is None: raise ValueError("Active personal combat does not exist")
  if referee_reference!=state[2]: raise PermissionError("Campaign referee authorization is required")
  if outcome_kind=='avoided':
   if not avoiding_side_code or not opposing_side_code or avoiding_side_code==opposing_side_code or winning_side_code is not None:
    raise ValueError("Avoidance requires distinct avoiding and opposing sides")
   eligible=connection.execute("""SELECT
    EXISTS(SELECT 1 FROM enc_participant p JOIN actor_actor a USING(actor_id)
      JOIN enc_personal_combatant c USING(encounter_id,actor_id)
      WHERE p.encounter_id=%s AND p.side_code=%s AND a.controller_reference=%s),
    NOT EXISTS(SELECT 1 FROM enc_participant p JOIN actor_actor a USING(actor_id)
      JOIN enc_personal_combatant c USING(encounter_id,actor_id)
      WHERE p.encounter_id=%s AND p.side_code=%s
        AND (a.controller_reference<>%s OR NOT c.aware_at_start)),
    NOT EXISTS(SELECT 1 FROM enc_participant p JOIN enc_personal_combatant c USING(encounter_id,actor_id)
      WHERE p.encounter_id=%s AND p.side_code=%s AND c.aware_at_start)""",
    (state[0],avoiding_side_code,initiator_reference,state[0],avoiding_side_code,
     initiator_reference,state[0],opposing_side_code)).fetchone()
   if eligible!=(True,True,True): raise PermissionError("Only an aware group unseen by its opponents may avoid conflict")
  else:
   if initiator_reference!=state[2]: raise PermissionError("Only the referee may resolve ongoing combat")
   if avoiding_side_code is not None or opposing_side_code is not None: raise ValueError("Only avoided outcomes accept avoidance sides")
  command_id,public_id=connection.execute("""INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key)
   VALUES('resolve_personal_combat',%s,%s) RETURNING command_id,public_id""",(initiator_reference,idempotency_key)).fetchone()
  resolution_id=connection.execute("""INSERT INTO enc_resolution(encounter_id,campaign_id,outcome_kind,winning_side_code,resolution_summary,source_command_id)
   VALUES(%s,%s,%s,%s,%s,%s) RETURNING encounter_resolution_id""",
   (state[0],state[1],outcome_kind,winning_side_code,resolution_summary.strip(),command_id)).fetchone()[0]
  resolved_at=connection.execute("SELECT clock_timestamp()").fetchone()[0]
  connection.execute("UPDATE enc_resolution SET finalized=true,resolved_at=%s WHERE encounter_resolution_id=%s",(resolved_at,resolution_id))
  connection.execute("""INSERT INTO cmd_personal_combat_resolution_receipt VALUES
   (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(command_id,resolution_id,state[0],outcome_kind,
   winning_side_code,avoiding_side_code,opposing_side_code,initiator_reference,
   referee_reference,resolution_summary.strip(),resolved_at))
  connection.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'personal_combat_resolved')",(command_id,))
  connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return PersonalCombatResolutionResult(str(public_id),outcome_kind,False)
