"""Audited handoff between Emporos and a user-owned desktop MCP client."""
from __future__ import annotations
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class ExternalTurnResult:
 command_public_id:str;turn_public_id:str;text:str;status:str;replayed:bool

def submit_external_referee_turn_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,player_text:str)->ExternalTurnResult:
 text=player_text.strip()
 if not text:raise ValueError('Player action is required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='submit_external_referee_turn':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT turn.public_id,message.message_text,turn.turn_status FROM cmd_referee_turn_receipt receipt JOIN camp_referee_turn turn ON turn.referee_turn_id=receipt.referee_turn_id JOIN camp_referee_message message ON message.referee_turn_id=turn.referee_turn_id AND message.speaker_kind='player' WHERE receipt.command_id=%s",(old[0],)).fetchone()
   return ExternalTurnResult(str(old[1]),str(row[0]),row[1],row[2],True)
  campaign=c.execute("SELECT campaign.campaign_id,clock.day_number,campaign.play_mode FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF campaign,clock",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  if campaign[2] not in ('ai_refereed','player_directed'):raise ValueError('Campaign is not using an external AI referee')
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('submit_external_referee_turn',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  turn_id,turn_public=c.execute("INSERT INTO camp_referee_turn(campaign_id,campaign_day,turn_status,source_command_id) VALUES(%s,%s,'pending',%s) RETURNING referee_turn_id,public_id",(campaign[0],campaign[1],command_id)).fetchone()
  c.execute("INSERT INTO camp_referee_message(referee_turn_id,campaign_id,message_order,speaker_kind,message_text) VALUES(%s,%s,1,'player',%s)",(turn_id,campaign[0],text));c.execute("INSERT INTO cmd_referee_turn_receipt VALUES(%s,%s,%s)",(command_id,campaign[0],turn_id));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'external_referee_turn_submitted')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return ExternalTurnResult(str(command_public),str(turn_public),text,'pending',False)

def complete_external_referee_turn_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,turn_public_id:str,narration:str)->ExternalTurnResult:
 text=narration.strip()
 if not text:raise ValueError('Referee narration is required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='complete_external_referee_turn':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT turn.public_id,message.message_text FROM cmd_external_referee_completion_receipt receipt JOIN camp_referee_turn turn USING(referee_turn_id) JOIN camp_referee_message message ON message.referee_turn_id=turn.referee_turn_id AND message.speaker_kind='referee' WHERE receipt.command_id=%s",(old[0],)).fetchone()
   return ExternalTurnResult(str(old[1]),str(row[0]),row[1],'completed',True)
  turn=c.execute("SELECT turn.referee_turn_id,turn.campaign_id FROM camp_referee_turn turn JOIN camp_campaign campaign USING(campaign_id) WHERE turn.public_id=%s AND campaign.owner_reference=%s AND turn.turn_status='pending' FOR UPDATE OF turn",(turn_public_id,initiator_reference)).fetchone()
  if not turn:raise ValueError('Pending external referee turn does not exist')
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('complete_external_referee_turn',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  c.execute("INSERT INTO camp_referee_message(referee_turn_id,campaign_id,message_order,speaker_kind,message_text) VALUES(%s,%s,2,'referee',%s)",(turn[0],turn[1],text));c.execute("UPDATE camp_referee_turn SET turn_status='completed',completed_at=clock_timestamp() WHERE referee_turn_id=%s",(turn[0],));c.execute("INSERT INTO cmd_external_referee_completion_receipt VALUES(%s,%s,%s)",(command_id,turn[1],turn[0]));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'external_referee_turn_completed')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return ExternalTurnResult(str(command_public),turn_public_id,text,'completed',False)
