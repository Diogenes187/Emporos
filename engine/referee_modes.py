"""Human referee recording and private AI assistance."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import psycopg
from ai.providers import provider_from_environment

@dataclass(frozen=True)
class HumanRefereeResult:
 command_public_id:str;turn_public_id:str;narration:str;replayed:bool

@dataclass(frozen=True)
class GMAssistanceResult:
 command_public_id:str;assistance_public_id:str;suggestion:str;replayed:bool

def record_human_referee_turn_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,narration:str)->HumanRefereeResult:
 text=narration.strip()
 if not text:raise ValueError('Referee narration is required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='record_human_referee_turn':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT turn.public_id,message.message_text FROM cmd_referee_turn_receipt receipt JOIN camp_referee_turn turn ON turn.referee_turn_id=receipt.referee_turn_id JOIN camp_referee_message message ON message.referee_turn_id=turn.referee_turn_id AND message.campaign_id=receipt.campaign_id WHERE receipt.command_id=%s AND message.speaker_kind='referee'",(old[0],)).fetchone()
   return HumanRefereeResult(str(old[1]),str(row[0]),row[1],True)
  campaign=c.execute("SELECT campaign.campaign_id,campaign.play_mode,clock.day_number FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF campaign,clock",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  if campaign[1] not in ('human_refereed','ai_assisted','ai_refereed','player_directed'):raise ValueError('Unknown campaign referee mode')
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('record_human_referee_turn',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  turn_id,turn_public=c.execute("INSERT INTO camp_referee_turn(campaign_id,campaign_day,turn_status,source_command_id,completed_at) VALUES(%s,%s,'completed',%s,clock_timestamp()) RETURNING referee_turn_id,public_id",(campaign[0],campaign[2],command_id)).fetchone()
  c.execute("INSERT INTO camp_referee_message(referee_turn_id,campaign_id,message_order,speaker_kind,message_text) VALUES(%s,%s,2,'referee',%s)",(turn_id,campaign[0],text))
  c.execute("INSERT INTO cmd_referee_turn_receipt VALUES(%s,%s,%s)",(command_id,campaign[0],turn_id))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'human_referee_turn_recorded')",(command_id,))
  c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return HumanRefereeResult(str(command_public),str(turn_public),text,False)

def request_gm_assistance_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,prompt_text:str,provider=None)->GMAssistanceResult:
 prompt=prompt_text.strip()
 if not prompt:raise ValueError('A GM assistance request is required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='request_gm_assistance':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT help.public_id,help.suggestion_text FROM cmd_gm_assistance_receipt receipt JOIN camp_gm_assistance help USING(gm_assistance_id) WHERE receipt.command_id=%s",(old[0],)).fetchone()
   return GMAssistanceResult(str(old[1]),str(row[0]),row[1],True)
  campaign=c.execute("SELECT campaign_id,name,play_mode FROM camp_campaign WHERE public_id=%s AND owner_reference=%s FOR UPDATE",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  if campaign[2]!='ai_assisted':raise ValueError('Private AI assistance is available only in AI-assisted campaigns')
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('request_gm_assistance',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  facts=c.execute("SELECT 'Character: '||name FROM actor_actor WHERE campaign_id=%s AND lifecycle_status='active' UNION ALL SELECT 'Ship: '||name FROM ship_ship WHERE campaign_id=%s AND lifecycle_status='active' UNION ALL SELECT 'System: '||location.name FROM loc_star_system system JOIN loc_location location USING(location_id) WHERE system.campaign_id=%s LIMIT 60",(campaign[0],campaign[0],campaign[0])).fetchall()
  memories=c.execute("SELECT title||': '||note_text FROM camp_journal_note WHERE campaign_id=%s AND ai_memory_enabled ORDER BY created_at DESC LIMIT 8",(campaign[0],)).fetchall()
  context='\n'.join(row[0] for row in facts+memories)
  messages=[{'role':'system','content':'You are a private assistant to a human game referee. Offer concise options, phrasing, or preparation help. Do not address players, reveal hidden source material, calculate mechanics, or alter game state. The human referee remains final authority.'},{'role':'system','content':f'Campaign: {campaign[1]}\nRelational facts:\n{context}'},{'role':'user','content':prompt}]
  client=provider or provider_from_environment();input_hash=sha256(repr(messages).encode()).hexdigest()
  invocation=c.execute("INSERT INTO ai_model_invocation(campaign_id,provider_code,model_name,purpose_code,input_sha256,invocation_status,source_command_id) VALUES(%s,%s,%s,'gm_assistance',%s,'pending',%s) RETURNING model_invocation_id",(campaign[0],client.provider_code,client.model,input_hash,command_id)).fetchone()[0]
 try:
  response=client.chat(messages=messages,json_output=False,max_tokens=700);suggestion=response.content.strip()
  if not suggestion:raise RuntimeError('AI assistant returned an empty suggestion')
 except Exception as exc:
  with c.transaction():
   c.execute("UPDATE ai_model_invocation SET invocation_status='failed',error_code=%s,completed_at=clock_timestamp() WHERE model_invocation_id=%s",(exc.__class__.__name__,invocation));c.execute("UPDATE cmd_command SET command_status='failed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  raise
 with c.transaction():
  assistance_id,assistance_public=c.execute("INSERT INTO camp_gm_assistance(campaign_id,prompt_text,suggestion_text,model_invocation_id,source_command_id) VALUES(%s,%s,%s,%s,%s) RETURNING gm_assistance_id,public_id",(campaign[0],prompt,suggestion,invocation,command_id)).fetchone()
  c.execute("INSERT INTO cmd_gm_assistance_receipt VALUES(%s,%s,%s)",(command_id,campaign[0],assistance_id));c.execute("UPDATE ai_model_invocation SET provider_code=%s,model_name=%s,output_sha256=%s,invocation_status='completed',prompt_tokens=%s,completion_tokens=%s,completed_at=clock_timestamp() WHERE model_invocation_id=%s",(response.provider,response.model,sha256(suggestion.encode()).hexdigest(),response.prompt_tokens,response.completion_tokens,invocation));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'gm_assistance_completed')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return GMAssistanceResult(str(command_public),str(assistance_public),suggestion,False)
