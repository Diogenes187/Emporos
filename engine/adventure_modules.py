"""Relational keyed-adventure state and deterministic stale-key guards."""
from __future__ import annotations
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class AdventureResult:
 command_public_id:str;module_public_id:str;location_public_id:str|None;result_code:str;replayed:bool

def _result(c,command_id,command_public,replayed):
 row=c.execute("SELECT module.public_id,location.public_id,receipt.result_code FROM cmd_adventure_module_receipt receipt JOIN camp_adventure_module module USING(adventure_module_id) LEFT JOIN camp_adventure_location location USING(adventure_location_id) WHERE receipt.command_id=%s",(command_id,)).fetchone()
 return AdventureResult(str(command_public),str(row[0]),str(row[1]) if row[1] else None,row[2],replayed)

def _begin(c,authority,key,kind):
 old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(authority,key)).fetchone()
 if old:
  if old[2]!=kind:raise ValueError('Idempotency key belongs to another command')
  return old
 return c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES(%s,%s,%s) RETURNING command_id,public_id,command_type",(kind,authority,key)).fetchone()

def _finish(c,command,campaign_id,module_id,location_id,result,event):
 c.execute("INSERT INTO cmd_adventure_module_receipt(command_id,campaign_id,adventure_module_id,adventure_location_id,result_code) VALUES(%s,%s,%s,%s,%s)",(command[0],campaign_id,module_id,location_id,result));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,%s)",(command[0],event));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command[0],))

def create_adventure_module_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,name:str,source_document_public_id:str|None=None)->AdventureResult:
 if not name.strip():raise ValueError('Adventure name is required')
 with c.transaction():
  command=_begin(c,initiator_reference,idempotency_key,'create_adventure_module')
  if c.execute("SELECT 1 FROM cmd_adventure_module_receipt WHERE command_id=%s",(command[0],)).fetchone():return _result(c,*command[:2],True)
  campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is outside this authority')
  source=None
  if source_document_public_id:
   source=c.execute("SELECT source_document_id FROM camp_source_document WHERE public_id=%s AND campaign_id=%s AND source_kind='adventure'",(source_document_public_id,campaign[0])).fetchone()
   if not source:raise ValueError('Adventure source is absent or not an adventure')
  c.execute("UPDATE camp_adventure_module SET module_status='archived' WHERE campaign_id=%s AND module_status='active'",(campaign[0],))
  module_id,module_public=c.execute("INSERT INTO camp_adventure_module(campaign_id,source_document_id,name,source_command_id) VALUES(%s,%s,%s,%s) RETURNING adventure_module_id,public_id",(campaign[0],source[0] if source else None,name.strip(),command[0])).fetchone()
  _finish(c,command,campaign[0],module_id,None,'created','adventure_module_created');return AdventureResult(str(command[1]),str(module_public),None,'created',False)

def key_adventure_location_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,module_public_id:str,location_key:str,name:str,keyed_description:str,source_page_number:int|None=None,occupants_initial:str|None=None,treasure_initial:str|None=None)->AdventureResult:
 if not all((location_key.strip(),name.strip(),keyed_description.strip())):raise ValueError('Key, name, and keyed description are required')
 with c.transaction():
  command=_begin(c,initiator_reference,idempotency_key,'key_adventure_location')
  if c.execute("SELECT 1 FROM cmd_adventure_module_receipt WHERE command_id=%s",(command[0],)).fetchone():return _result(c,*command[:2],True)
  module=c.execute("SELECT module.adventure_module_id,module.campaign_id,module.source_document_id FROM camp_adventure_module module JOIN camp_campaign campaign USING(campaign_id) WHERE module.public_id=%s AND campaign.owner_reference=%s",(module_public_id,initiator_reference)).fetchone()
  if not module:raise PermissionError('Adventure is outside this authority')
  if source_page_number and (not module[2] or not c.execute("SELECT 1 FROM camp_source_page WHERE source_document_id=%s AND page_number=%s AND review_status='verified'",(module[2],source_page_number)).fetchone()):raise ValueError('Source page must be verified and belong to this adventure')
  location_id,location_public=c.execute("INSERT INTO camp_adventure_location(adventure_module_id,campaign_id,location_key,name,keyed_description,source_page_number,occupants_initial,treasure_initial,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING adventure_location_id,public_id",(module[0],module[1],location_key.strip(),name.strip(),keyed_description.strip(),source_page_number,occupants_initial.strip() if occupants_initial else None,treasure_initial.strip() if treasure_initial else None,command[0])).fetchone()
  _finish(c,command,module[1],module[0],location_id,'keyed','adventure_location_keyed');return AdventureResult(str(command[1]),str(module_public_id),str(location_public),'keyed',False)

def enter_adventure_location_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,location_public_id:str)->AdventureResult:
 with c.transaction():
  command=_begin(c,initiator_reference,idempotency_key,'enter_adventure_location')
  if c.execute("SELECT 1 FROM cmd_adventure_module_receipt WHERE command_id=%s",(command[0],)).fetchone():return _result(c,*command[:2],True)
  row=c.execute("SELECT location.adventure_location_id,location.adventure_module_id,location.campaign_id,module.public_id FROM camp_adventure_location location JOIN camp_adventure_module module USING(adventure_module_id,campaign_id) JOIN camp_campaign campaign USING(campaign_id) WHERE location.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF location,module",(location_public_id,initiator_reference)).fetchone()
  if not row:raise PermissionError('Location is outside this authority')
  c.execute("UPDATE camp_adventure_location SET discovered=true,entered_count=entered_count+1,last_entered_at=clock_timestamp() WHERE adventure_location_id=%s",(row[0],));c.execute("UPDATE camp_adventure_module SET current_location_id=%s WHERE adventure_module_id=%s",(row[0],row[1]));order=c.execute("SELECT COALESCE(max(event_order),0)+1 FROM camp_adventure_exploration_event WHERE adventure_module_id=%s",(row[1],)).fetchone()[0];turns=c.execute("SELECT elapsed_turns FROM camp_adventure_module WHERE adventure_module_id=%s",(row[1],)).fetchone()[0];c.execute("INSERT INTO camp_adventure_exploration_event(adventure_module_id,campaign_id,event_order,event_kind,event_text,elapsed_turns,source_command_id) VALUES(%s,%s,%s,'location_entered',%s,%s,%s)",(row[1],row[2],order,'Entered keyed location',turns,command[0]));_finish(c,command,row[2],row[1],row[0],'entered','adventure_location_entered');return AdventureResult(str(command[1]),str(row[3]),str(location_public_id),'entered',False)

def update_adventure_location_state_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,location_public_id:str,occupant_status:str,treasure_status:str,alert_status:str,current_note:str='')->AdventureResult:
 allowed=(('as_keyed','absent','fled','dead','captured','allied','changed'),('as_keyed','untouched','taken','moved','destroyed','changed'),('unaware','suspicious','alerted','secured'))
 if occupant_status not in allowed[0] or treasure_status not in allowed[1] or alert_status not in allowed[2]:raise ValueError('Unknown location state')
 with c.transaction():
  command=_begin(c,initiator_reference,idempotency_key,'update_adventure_location_state')
  if c.execute("SELECT 1 FROM cmd_adventure_module_receipt WHERE command_id=%s",(command[0],)).fetchone():return _result(c,*command[:2],True)
  row=c.execute("SELECT location.adventure_location_id,location.adventure_module_id,location.campaign_id,module.public_id FROM camp_adventure_location location JOIN camp_adventure_module module USING(adventure_module_id,campaign_id) JOIN camp_campaign campaign USING(campaign_id) WHERE location.public_id=%s AND campaign.owner_reference=%s",(location_public_id,initiator_reference)).fetchone()
  if not row:raise PermissionError('Location is outside this authority')
  c.execute("UPDATE camp_adventure_location SET occupant_status=%s,treasure_status=%s,alert_status=%s,current_note=NULLIF(btrim(%s),'') WHERE adventure_location_id=%s",(occupant_status,treasure_status,alert_status,current_note,row[0]));_finish(c,command,row[2],row[1],row[0],'state_updated','adventure_location_state_updated');return AdventureResult(str(command[1]),str(row[3]),str(location_public_id),'state_updated',False)

def advance_adventure_exploration_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,module_public_id:str,turns:int=1,rest:bool=False)->AdventureResult:
 if turns<1 or turns>24:raise ValueError('Advance between 1 and 24 turns')
 with c.transaction():
  command=_begin(c,initiator_reference,idempotency_key,'advance_adventure_exploration')
  if c.execute("SELECT 1 FROM cmd_adventure_module_receipt WHERE command_id=%s",(command[0],)).fetchone():return _result(c,*command[:2],True)
  module=c.execute("SELECT module.adventure_module_id,module.campaign_id,module.elapsed_turns,module.turns_since_wander,module.wander_frequency FROM camp_adventure_module module JOIN camp_campaign campaign USING(campaign_id) WHERE module.public_id=%s AND campaign.owner_reference=%s FOR UPDATE OF module",(module_public_id,initiator_reference)).fetchone()
  if not module:raise PermissionError('Adventure is outside this authority')
  elapsed=module[2]+turns;since=module[3]+turns;checks=since//module[4];since%=module[4]
  c.execute("UPDATE camp_adventure_module SET elapsed_turns=%s,turns_since_rest=%s,turns_since_wander=%s WHERE adventure_module_id=%s",(elapsed,0 if rest else c.execute("SELECT turns_since_rest FROM camp_adventure_module WHERE adventure_module_id=%s",(module[0],)).fetchone()[0]+turns,since,module[0]));c.execute("UPDATE camp_adventure_light_source SET turns_remaining=greatest(0,turns_remaining-%s),active=turns_remaining>%s WHERE adventure_module_id=%s AND active",(turns,turns,module[0]));order=c.execute("SELECT COALESCE(max(event_order),0)+1 FROM camp_adventure_exploration_event WHERE adventure_module_id=%s",(module[0],)).fetchone()[0];text=('Rest completed. ' if rest else '')+f'{turns} exploration turn(s) elapsed; {checks} wandering check(s) due.';c.execute("INSERT INTO camp_adventure_exploration_event(adventure_module_id,campaign_id,event_order,event_kind,event_text,elapsed_turns,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s)",(module[0],module[1],order,'rest' if rest else 'turn_advanced',text,elapsed,command[0]));_finish(c,command,module[1],module[0],None,f'{checks}_wander_checks_due','adventure_exploration_advanced');return AdventureResult(str(command[1]),str(module_public_id),None,f'{checks}_wander_checks_due',False)

def adventure_module_snapshot(c:psycopg.Connection,*,initiator_reference:str,module_public_id:str)->dict:
 module=c.execute("SELECT module.adventure_module_id,module.name,module.module_status,module.elapsed_turns,module.turn_minutes,module.turns_since_rest,module.turns_since_wander,module.wander_frequency,module.global_alert,current.public_id,current.location_key,current.name FROM camp_adventure_module module JOIN camp_campaign campaign USING(campaign_id) LEFT JOIN camp_adventure_location current ON current.adventure_location_id=module.current_location_id WHERE module.public_id=%s AND campaign.owner_reference=%s",(module_public_id,initiator_reference)).fetchone()
 if not module:raise PermissionError('Adventure is outside this authority')
 locations=c.execute("SELECT location.public_id,location.location_key,location.name,location.keyed_description,location.source_page_number,location.occupants_initial,location.treasure_initial,location.occupant_status,location.treasure_status,location.alert_status,location.discovered,location.current_note,guard.warning_text FROM camp_adventure_location location JOIN camp_adventure_location_contradiction guard USING(adventure_location_id) WHERE location.adventure_module_id=%s ORDER BY location.location_key",(module[0],)).fetchall()
 return {'name':module[1],'status':module[2],'elapsed_turns':module[3],'elapsed_minutes':module[3]*module[4],'turns_since_rest':module[5],'turns_until_wander':module[7]-module[6],'global_alert':module[8],'current_location':{'public_id':str(module[9]),'key':module[10],'name':module[11]} if module[9] else None,'locations':[{'public_id':str(r[0]),'key':r[1],'name':r[2],'keyed_description':r[3],'source_page':r[4],'occupants_initial':r[5],'treasure_initial':r[6],'occupant_status':r[7],'treasure_status':r[8],'alert_status':r[9],'discovered':r[10],'current_note':r[11],'contradiction_warning':r[12]} for r in locations]}

def campaign_adventure_modules(c:psycopg.Connection,*,initiator_reference:str,campaign_public_id:str)->list[dict]:
 campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",(campaign_public_id,initiator_reference)).fetchone()
 if not campaign:raise PermissionError('Campaign is outside this authority')
 rows=c.execute("SELECT public_id FROM camp_adventure_module WHERE campaign_id=%s ORDER BY (module_status='active') DESC,created_at DESC",(campaign[0],)).fetchall()
 return [dict(public_id=str(row[0]),**adventure_module_snapshot(c,initiator_reference=initiator_reference,module_public_id=str(row[0]))) for row in rows]
