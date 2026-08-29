"""Audited, structured campaign memory for local and desktop referees."""
from __future__ import annotations
from dataclasses import dataclass
import psycopg

KINDS={'scene','person','place','discovery','promise','decision','relationship','threat','opportunity','other'}
SOURCES={'desktop_referee','web_referee','human_referee','player_note'}

@dataclass(frozen=True)
class ChronicleResult:
 command_public_id:str;entry_public_id:str;replayed:bool

def record_campaign_chronicle_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,entry_kind:str,title:str,summary_text:str,importance:int=3,source_kind:str='desktop_referee',actor_public_ids=(),location_public_ids=(),ship_public_ids=())->ChronicleResult:
 title=title.strip();summary_text=summary_text.strip();actor_public_ids=tuple(dict.fromkeys(actor_public_ids or ()));location_public_ids=tuple(dict.fromkeys(location_public_ids or ()));ship_public_ids=tuple(dict.fromkeys(ship_public_ids or ()))
 if entry_kind not in KINDS:raise ValueError('Unknown chronicle entry kind')
 if source_kind not in SOURCES:raise ValueError('Unknown chronicle source kind')
 if not title or not summary_text:raise ValueError('Chronicle title and summary are required')
 if not 1<=int(importance)<=5:raise ValueError('Chronicle importance must be from 1 to 5')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='record_campaign_chronicle':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT entry.public_id FROM cmd_campaign_chronicle_receipt receipt JOIN camp_chronicle_entry entry USING(chronicle_entry_id,campaign_id) WHERE receipt.command_id=%s",(old[0],)).fetchone();return ChronicleResult(str(old[1]),str(row[0]),True)
  campaign=c.execute("SELECT campaign.campaign_id,clock.day_number FROM camp_campaign campaign JOIN camp_clock clock USING(campaign_id) WHERE campaign.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF campaign,clock",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  def resolve(table,identifier,values):
   if not values:return []
   rows=c.execute(f"SELECT {identifier} FROM {table} WHERE campaign_id=%s AND public_id=ANY(%s)",(campaign[0],list(values))).fetchall()
   if len(rows)!=len(values):raise PermissionError('A chronicle subject is absent or outside this campaign')
   return [row[0] for row in rows]
  actors=resolve('actor_actor','actor_id',actor_public_ids);locations=resolve('loc_location','location_id',location_public_ids);ships=resolve('ship_ship','ship_id',ship_public_ids)
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('record_campaign_chronicle',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  entry_id,entry_public=c.execute("INSERT INTO camp_chronicle_entry(campaign_id,entry_kind,title,summary_text,campaign_day,importance,source_kind,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING chronicle_entry_id,public_id",(campaign[0],entry_kind,title,summary_text,campaign[1],int(importance),source_kind,command_id)).fetchone()
  for actor_id in actors:c.execute("INSERT INTO camp_chronicle_actor VALUES(%s,%s,%s)",(entry_id,campaign[0],actor_id))
  for location_id in locations:c.execute("INSERT INTO camp_chronicle_location VALUES(%s,%s,%s)",(entry_id,campaign[0],location_id))
  for ship_id in ships:c.execute("INSERT INTO camp_chronicle_ship VALUES(%s,%s,%s)",(entry_id,campaign[0],ship_id))
  c.execute("INSERT INTO cmd_campaign_chronicle_receipt VALUES(%s,%s,%s)",(command_id,campaign[0],entry_id));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'campaign_chronicle_recorded')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
  return ChronicleResult(str(command_public),str(entry_public),False)

def campaign_chronicle(c:psycopg.Connection,*,initiator_reference:str,campaign_public_id:str,limit:int=20)->list[dict]:
 campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",(campaign_public_id,initiator_reference)).fetchone()
 if not campaign:raise PermissionError('Campaign is outside this authority')
 rows=c.execute("""SELECT entry.chronicle_entry_id,entry.public_id::text,entry.entry_kind,entry.title,entry.summary_text,entry.campaign_day,entry.importance,entry.source_kind FROM camp_chronicle_entry entry WHERE entry.campaign_id=%s AND entry.ai_memory_enabled ORDER BY entry.importance DESC,entry.created_at DESC LIMIT %s""",(campaign[0],min(max(int(limit),1),100))).fetchall()
 result=[]
 for row in rows:
  actors=[r[0] for r in c.execute("SELECT actor.name FROM camp_chronicle_actor link JOIN actor_actor actor USING(actor_id,campaign_id) WHERE link.chronicle_entry_id=%s ORDER BY actor.name",(row[0],))];locations=[r[0] for r in c.execute("SELECT location.name FROM camp_chronicle_location link JOIN loc_location location USING(location_id,campaign_id) WHERE link.chronicle_entry_id=%s ORDER BY location.name",(row[0],))];ships=[r[0] for r in c.execute("SELECT ship.name FROM camp_chronicle_ship link JOIN ship_ship ship USING(ship_id,campaign_id) WHERE link.chronicle_entry_id=%s ORDER BY ship.name",(row[0],))]
  result.append({'public_id':row[1],'kind':row[2],'title':row[3],'summary':row[4],'campaign_day':row[5],'importance':row[6],'source':row[7],'people':actors,'places':locations,'ships':ships})
 return result
