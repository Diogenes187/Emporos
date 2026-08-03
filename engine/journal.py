"""Campaign notes and session archives for durable, opt-in referee memory."""
from dataclasses import dataclass
import psycopg
@dataclass(frozen=True)
class JournalResult:
 command_public_id:str;record_public_id:str;title:str;replayed:bool
def _old(c,initiator,key,kind):
 row=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator,key)).fetchone()
 if row and row[2:]!=(kind,'completed'):raise RuntimeError('Idempotency key belongs to another command')
 return row
def add_campaign_note_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,title:str,note_kind:str,note_text:str,ai_memory_enabled:bool=True)->JournalResult:
 if not title.strip() or not note_text.strip():raise ValueError('Note title and text are required')
 with c.transaction():
  old=_old(c,initiator_reference,idempotency_key,'add_campaign_note')
  if old:
   r=c.execute("SELECT note.public_id,note.title FROM cmd_campaign_note_receipt receipt JOIN camp_journal_note note USING(journal_note_id) WHERE receipt.command_id=%s",(old[0],)).fetchone();return JournalResult(str(old[1]),str(r[0]),r[1],True)
  campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s FOR UPDATE",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('add_campaign_note',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();record,record_pub=c.execute("INSERT INTO camp_journal_note(campaign_id,title,note_kind,note_text,ai_memory_enabled,source_command_id) VALUES(%s,%s,%s,%s,%s,%s) RETURNING journal_note_id,public_id",(campaign[0],title.strip(),note_kind,note_text.strip(),ai_memory_enabled,cid)).fetchone();c.execute("INSERT INTO cmd_campaign_note_receipt VALUES(%s,%s,%s)",(cid,campaign[0],record));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'campaign_note_added')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return JournalResult(str(pub),str(record_pub),title.strip(),False)
def archive_play_session_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,title:str,transcript_text:str,ai_memory_enabled:bool=True)->JournalResult:
 if not title.strip() or not transcript_text.strip():raise ValueError('Session title and transcript are required')
 with c.transaction():
  old=_old(c,initiator_reference,idempotency_key,'archive_play_session')
  if old:
   r=c.execute("SELECT archive.public_id,archive.title FROM cmd_session_archive_receipt receipt JOIN camp_session_archive archive USING(session_archive_id) WHERE receipt.command_id=%s",(old[0],)).fetchone();return JournalResult(str(old[1]),str(r[0]),r[1],True)
  campaign=c.execute("SELECT campaign.campaign_id,clock.day_number FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF campaign,clock",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('archive_play_session',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();record,record_pub=c.execute("INSERT INTO camp_session_archive(campaign_id,title,campaign_day,transcript_text,ai_memory_enabled,source_command_id) VALUES(%s,%s,%s,%s,%s,%s) RETURNING session_archive_id,public_id",(campaign[0],title.strip(),campaign[1],transcript_text.strip(),ai_memory_enabled,cid)).fetchone();c.execute("INSERT INTO cmd_session_archive_receipt VALUES(%s,%s,%s)",(cid,campaign[0],record));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'play_session_archived')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,));return JournalResult(str(pub),str(record_pub),title.strip(),False)
