"""Audited, ordered logs supplied by a connected desktop MCP client."""
from __future__ import annotations
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class ConversationEntryResult:
 command_public_id:str;log_public_id:str;entry_public_id:str;entry_order:int;replayed:bool

def append_external_conversation_entry_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,log_reference:str,title:str,client_name:str,speaker_kind:str,message_text:str)->ConversationEntryResult:
 reference=log_reference.strip();clean_title=title.strip();client=client_name.strip();text=message_text.strip()
 if not all((reference,clean_title,client,text)):raise ValueError('Log reference, title, client, and message are required')
 if speaker_kind not in ('user','assistant','system','tool'):raise ValueError('Unknown conversation speaker kind')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='append_external_conversation_entry':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT log.public_id,entry.public_id,entry.entry_order FROM cmd_external_conversation_entry_receipt receipt JOIN camp_external_conversation_log log USING(external_conversation_log_id) JOIN camp_external_conversation_entry entry USING(external_conversation_entry_id) WHERE receipt.command_id=%s",(old[0],)).fetchone()
   return ConversationEntryResult(str(old[1]),str(row[0]),str(row[1]),row[2],True)
  campaign=c.execute("SELECT campaign.campaign_id,clock.day_number FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF campaign,clock",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  log=c.execute("SELECT external_conversation_log_id,public_id FROM camp_external_conversation_log WHERE campaign_id=%s AND log_reference=%s FOR UPDATE",(campaign[0],reference)).fetchone()
  if not log:
   log=c.execute("INSERT INTO camp_external_conversation_log(campaign_id,log_reference,title,client_name,opened_day) VALUES(%s,%s,%s,%s,%s) RETURNING external_conversation_log_id,public_id",(campaign[0],reference,clean_title,client,campaign[1])).fetchone()
  next_order=c.execute("SELECT COALESCE(max(entry_order),0)+1 FROM camp_external_conversation_entry WHERE external_conversation_log_id=%s",(log[0],)).fetchone()[0]
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('append_external_conversation_entry',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  entry_id,entry_public=c.execute("INSERT INTO camp_external_conversation_entry(external_conversation_log_id,campaign_id,entry_order,speaker_kind,message_text,campaign_day) VALUES(%s,%s,%s,%s,%s,%s) RETURNING external_conversation_entry_id,public_id",(log[0],campaign[0],next_order,speaker_kind,text,campaign[1])).fetchone()
  c.execute("INSERT INTO cmd_external_conversation_entry_receipt VALUES(%s,%s,%s,%s)",(command_id,campaign[0],log[0],entry_id));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'external_conversation_entry_appended')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return ConversationEntryResult(str(command_public),str(log[1]),str(entry_public),next_order,False)
