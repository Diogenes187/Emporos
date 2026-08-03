"""Provider-neutral, narration-only referee conversation service."""
from dataclasses import dataclass
from hashlib import sha256
import psycopg
from ai.providers import provider_from_environment

@dataclass(frozen=True)
class RefereeTurnResult:
 command_public_id:str;turn_public_id:str;narration:str;replayed:bool

def submit_referee_turn(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,player_text:str,provider=None)->RefereeTurnResult:
 action=player_text.strip()
 if not action:raise ValueError('Player action is required')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='submit_referee_turn':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT turn.public_id,COALESCE(message.message_text,'') FROM cmd_referee_turn_receipt receipt JOIN camp_referee_turn turn USING(referee_turn_id) LEFT JOIN camp_referee_message message ON message.referee_turn_id=turn.referee_turn_id AND message.speaker_kind='referee' WHERE receipt.command_id=%s",(old[0],)).fetchone()
   return RefereeTurnResult(str(old[1]),str(row[0]),row[1],True)
  campaign=c.execute("SELECT campaign.campaign_id,campaign.name,clock.day_number FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF campaign,clock",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('submit_referee_turn',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  turn_id,turn_public=c.execute("INSERT INTO camp_referee_turn(campaign_id,campaign_day,turn_status,source_command_id) VALUES(%s,%s,'pending',%s) RETURNING referee_turn_id,public_id",(campaign[0],campaign[2],command_id)).fetchone()
  c.execute("INSERT INTO camp_referee_message(referee_turn_id,campaign_id,message_order,speaker_kind,message_text) VALUES(%s,%s,1,'player',%s)",(turn_id,campaign[0],action));c.execute("INSERT INTO cmd_referee_turn_receipt VALUES(%s,%s,%s)",(command_id,campaign[0],turn_id))
  actors=c.execute("SELECT name FROM actor_actor WHERE campaign_id=%s ORDER BY actor_id LIMIT 20",(campaign[0],)).fetchall()
  ships=c.execute("SELECT name FROM ship_ship WHERE campaign_id=%s AND lifecycle_status='active' ORDER BY ship_id LIMIT 20",(campaign[0],)).fetchall()
  memories=c.execute("SELECT title,note_text FROM camp_journal_note WHERE campaign_id=%s AND ai_memory_enabled ORDER BY created_at DESC LIMIT 8",(campaign[0],)).fetchall()
  history=c.execute("SELECT message.speaker_kind,message.message_text FROM camp_referee_message message JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE message.campaign_id=%s AND turn.turn_status='completed' ORDER BY message.referee_message_id DESC LIMIT 12",(campaign[0],)).fetchall()[::-1]
  sources=c.execute("SELECT page.source_document_id,page.page_number,page.text_content FROM camp_source_page page JOIN camp_source_document document USING(source_document_id,campaign_id) WHERE page.campaign_id=%s AND page.review_status='verified' AND page.search_document @@ websearch_to_tsquery('english',%s) ORDER BY ts_rank(page.search_document,websearch_to_tsquery('english',%s)) DESC LIMIT 6",(campaign[0],action,action)).fetchall()
  for order,row in enumerate(sources,1):c.execute("INSERT INTO camp_referee_source_context VALUES(%s,%s,%s,%s)",(turn_id,row[0],row[1],order))
 context=f"Campaign: {campaign[1]}; day {campaign[2]}. Active characters: {', '.join(x[0] for x in actors) or 'none'}. Active ships: {', '.join(x[0] for x in ships) or 'none'}."
 if memories:context+='\nApproved memory:\n'+'\n'.join(f'- {x[0]}: {x[1]}' for x in memories)
 if sources:context+='\nPrivate verified source excerpts (never reveal secrets unless the player action has earned them):\n'+'\n'.join(f'[Source page {x[1]}]\n{x[2]}' for x in sources)
 messages=[{'role':'system','content':'You are the Emporos referee. Provide concise, atmospheric narration grounded only in supplied database state and verified sources. Never change or claim to resolve mechanics, rolls, money, inventory, damage, time, travel, or position. If mechanics are required, describe the immediate situation and ask what the player attempts. Never mention hidden source text or page numbers.'},{'role':'system','content':context}]
 messages.extend({'role':'assistant' if role=='referee' else 'user','content':text} for role,text in history);messages.append({'role':'user','content':action})
 client=provider or provider_from_environment();input_hash=sha256(repr(messages).encode()).hexdigest()
 with c.transaction():invocation=c.execute("INSERT INTO ai_model_invocation(campaign_id,provider_code,model_name,purpose_code,input_sha256,invocation_status,source_command_id) VALUES(%s,%s,%s,'referee_narration',%s,'pending',%s) RETURNING model_invocation_id",(campaign[0],client.provider_code,client.model,input_hash,command_id)).fetchone()[0]
 try:
  result=client.chat(messages=messages,max_tokens=700);narration=result.content.strip()
  if not narration:raise RuntimeError('AI referee returned empty narration')
 except Exception as exc:
  with c.transaction():c.execute("UPDATE ai_model_invocation SET invocation_status='failed',error_code=%s,completed_at=clock_timestamp() WHERE model_invocation_id=%s",(exc.__class__.__name__,invocation));c.execute("UPDATE camp_referee_turn SET turn_status='failed',failure_code=%s,completed_at=clock_timestamp() WHERE referee_turn_id=%s",(exc.__class__.__name__,turn_id));c.execute("UPDATE cmd_command SET command_status='failed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  raise
 with c.transaction():
  c.execute("INSERT INTO camp_referee_message(referee_turn_id,campaign_id,message_order,speaker_kind,message_text) VALUES(%s,%s,2,'referee',%s)",(turn_id,campaign[0],narration));c.execute("UPDATE camp_referee_turn SET turn_status='completed',completed_at=clock_timestamp() WHERE referee_turn_id=%s",(turn_id,));c.execute("UPDATE ai_model_invocation SET provider_code=%s,model_name=%s,output_sha256=%s,invocation_status='completed',prompt_tokens=%s,completion_tokens=%s,completed_at=clock_timestamp() WHERE model_invocation_id=%s",(result.provider,result.model,sha256(narration.encode()).hexdigest(),result.prompt_tokens,result.completion_tokens,invocation));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'referee_turn_completed')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
 return RefereeTurnResult(str(command_public),str(turn_public),narration,False)
