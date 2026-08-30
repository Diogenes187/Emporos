"""Provider-neutral local Emporos MCP server."""
from __future__ import annotations
from dataclasses import asdict,is_dataclass
from datetime import date,datetime
from decimal import Decimal
import json,os,sys,threading,uuid
import psycopg
from app.database import database_url
from engine.orchestration import GameplayOrchestrator,available_tools
from engine.referee_modes import record_human_referee_turn_command
from engine.external_referee import complete_external_referee_turn_command
from engine.conversation_logs import append_external_conversation_entry_command
from engine.chronicle import record_campaign_chronicle_command,campaign_chronicle
from engine.adventure_modules import adventure_module_snapshot,create_adventure_module_command,key_adventure_location_command,enter_adventure_location_command,update_adventure_location_state_command,advance_adventure_exploration_command
from engine.adventure_indexing import adventure_index_snapshot,read_adventure_source_page_command,propose_adventure_location_command

PROTOCOL_VERSION='2025-03-26'
PROCESS_SESSION_ID=uuid.uuid4()
CLIENT_INFO={'name':'Desktop MCP Client','version':None}
HEARTBEAT_SECONDS=15
def _connect():
 dsn=database_url()
 if not dsn:raise RuntimeError('EMPOROS_DATABASE_URL or BASE_CEPHEUS_DATABASE_URL is required')
 return psycopg.connect(dsn)
def _authority():return os.environ.get('EMPOROS_AUTHORITY_REFERENCE','emporos-local-player')
def _record_presence(status='connected'):
 try:
  with _connect() as c:
   c.execute("""INSERT INTO sys_mcp_client_presence
    (process_session_id,authority_reference,client_name,client_version,presence_status,disconnected_at)
    VALUES(%s,%s,%s,%s,%s,CASE WHEN %s='disconnected' THEN clock_timestamp() END)
    ON CONFLICT(process_session_id) DO UPDATE SET
      client_name=excluded.client_name,client_version=excluded.client_version,
      presence_status=excluded.presence_status,last_seen_at=clock_timestamp(),
      disconnected_at=excluded.disconnected_at""",
    (PROCESS_SESSION_ID,_authority(),CLIENT_INFO['name'],CLIENT_INFO['version'],status,status))
 except Exception:
  pass
def _heartbeat(stop):
 while not stop.wait(HEARTBEAT_SECONDS):_record_presence()
def _plain(value):
 if is_dataclass(value):return _plain(asdict(value))
 if isinstance(value,dict):return {str(k):_plain(v) for k,v in value.items()}
 if isinstance(value,(list,tuple)):return [_plain(v) for v in value]
 if isinstance(value,(uuid.UUID,date,datetime,Decimal)):return str(value)
 return value
def _status(args=None):
 with _connect() as c:return {'connected':True,'schema_version':c.execute('SELECT max(version) FROM sys_schema_migration').fetchone()[0],'mutation_access':True,'private_content_access':True,'authority_reference':_authority()}
def _campaigns(args=None):
 with _connect() as c:return [{'public_id':r[0],'name':r[1],'play_mode':r[2],'status':r[3]} for r in c.execute("SELECT public_id::text,name,play_mode,campaign_status FROM camp_campaign WHERE owner_reference=%s ORDER BY created_at",(_authority(),))]
def _owned(c,public_id):
 row=c.execute("SELECT campaign_id,name,play_mode,campaign_status FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",(public_id,_authority())).fetchone()
 if not row:raise PermissionError('Campaign is absent or outside this MCP authority')
 return row
def _snapshot(args):
 with _connect() as c:
  campaign=_owned(c,args['campaign_public_id']);cid=campaign[0]
  clock=c.execute('SELECT day_number,second_of_day FROM camp_clock WHERE campaign_id=%s',(cid,)).fetchone()
  return {'campaign':{'public_id':args['campaign_public_id'],'name':campaign[1],'play_mode':campaign[2],'status':campaign[3]},'clock':{'day_number':clock[0],'second_of_day':clock[1]},'characters':[{'public_id':str(r[0]),'name':r[1]} for r in c.execute("SELECT public_id,name FROM actor_actor WHERE campaign_id=%s AND lifecycle_status='active' ORDER BY name",(cid,))],'ships':[{'public_id':str(r[0]),'name':r[1],'status':r[2],'location':r[3]} for r in c.execute("SELECT ship.public_id,ship.name,ship.lifecycle_status,location.name FROM ship_ship ship LEFT JOIN loc_location location ON location.location_id=ship.current_location_id WHERE ship.campaign_id=%s ORDER BY ship.name",(cid,))],'systems':[{'public_id':str(r[0]),'name':r[1],'hex':f'{r[2]:02d}{r[3]:02d}'} for r in c.execute("SELECT location.public_id,location.name,system.hex_column,system.hex_row FROM loc_star_system system JOIN loc_location location USING(location_id) WHERE system.campaign_id=%s ORDER BY system.hex_column,system.hex_row",(cid,))],'recent_narration':[{'speaker':r[0],'text':r[1]} for r in c.execute("SELECT message.speaker_kind,message.message_text FROM camp_referee_message message JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE message.campaign_id=%s AND turn.turn_status='completed' ORDER BY message.referee_message_id DESC LIMIT 20",(cid,)).fetchall()[::-1]]}
def _resume(args):
 """Return one compact, authoritative context packet for a desktop AI referee."""
 recent=min(max(int(args.get('recent',12)),1),40)
 with _connect() as c:
  requested=args.get('campaign_public_id')
  if requested:
   campaign=_owned(c,requested);campaign_public=str(requested)
  else:
   rows=c.execute("SELECT campaign_id,public_id::text,name,play_mode,campaign_status FROM camp_campaign WHERE owner_reference=%s AND campaign_status='active' ORDER BY created_at DESC",(_authority(),)).fetchall()
   if not rows:raise ValueError('No active campaign is available. Create one in Emporos first.')
   row=rows[0];campaign=(row[0],row[2],row[3],row[4]);campaign_public=row[1]
  cid=campaign[0]
  clock=c.execute('SELECT day_number,second_of_day FROM camp_clock WHERE campaign_id=%s',(cid,)).fetchone()
  characters=[]
  for actor in c.execute("SELECT actor_id,public_id::text,name FROM actor_actor WHERE campaign_id=%s AND lifecycle_status='active' ORDER BY name",(cid,)).fetchall():
   characteristics=c.execute("SELECT definition.abbreviation,state.current_value,state.maximum_value FROM actor_characteristic state JOIN rule_characteristic definition ON definition.rule_id=state.characteristic_rule_id WHERE state.actor_id=%s ORDER BY definition.display_order",(actor[0],)).fetchall()
   skills=c.execute("SELECT rule.name,state.skill_level FROM actor_skill state JOIN rule_rule rule ON rule.rule_id=state.skill_rule_id WHERE state.actor_id=%s ORDER BY rule.name",(actor[0],)).fetchall()
   characters.append({'public_id':actor[1],'name':actor[2],'characteristics':[{'name':r[0],'current':r[1],'maximum':r[2]} for r in characteristics],'skills':[{'name':r[0],'level':r[1]} for r in skills]})
  ships=[{'public_id':r[0],'name':r[1],'status':r[2],'location':r[3]} for r in c.execute("SELECT ship.public_id::text,ship.name,ship.lifecycle_status,location.name FROM ship_ship ship LEFT JOIN loc_location location ON location.location_id=ship.current_location_id WHERE ship.campaign_id=%s ORDER BY ship.name",(cid,)).fetchall()]
  pending=[{'turn_public_id':r[0],'campaign_day':r[1],'player_text':r[2],'submitted_at':r[3]} for r in c.execute("SELECT turn.public_id::text,turn.campaign_day,message.message_text,turn.created_at FROM camp_referee_turn turn JOIN camp_referee_message message ON message.referee_turn_id=turn.referee_turn_id AND message.speaker_kind='player' WHERE turn.campaign_id=%s AND turn.turn_status='pending' ORDER BY turn.created_at",(cid,)).fetchall()]
  narration=[{'speaker':r[0],'text':r[1]} for r in c.execute("SELECT message.speaker_kind,message.message_text FROM camp_referee_message message JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE message.campaign_id=%s AND turn.turn_status='completed' ORDER BY message.referee_message_id DESC LIMIT %s",(cid,recent)).fetchall()[::-1]]
  memory=[{'kind':r[0],'title':r[1],'text':r[2]} for r in c.execute("SELECT kind,title,body FROM (SELECT 'journal' AS kind,title,note_text AS body,created_at AS recorded_at FROM camp_journal_note WHERE campaign_id=%s AND ai_memory_enabled UNION ALL SELECT 'session',title,transcript_text,archived_at FROM camp_session_archive WHERE campaign_id=%s AND ai_memory_enabled) remembered ORDER BY recorded_at DESC LIMIT %s",(cid,cid,recent)).fetchall()]
  encounters=[{'public_id':r[0],'mode':r[1],'personal_combat_status':r[2],'round':r[3]} for r in c.execute("SELECT encounter.public_id::text,encounter.current_mode,combat.combat_status,combat.current_round FROM enc_encounter encounter LEFT JOIN enc_personal_combat combat USING(encounter_id) WHERE encounter.campaign_id=%s AND encounter.encounter_status='active' ORDER BY encounter.created_at",(cid,)).fetchall()]
  engagements=[{'public_id':r[0],'status':r[1],'round':r[2]} for r in c.execute("SELECT public_id::text,engagement_status,current_round FROM senc_engagement WHERE campaign_id=%s AND engagement_status IN('forming','active') ORDER BY engagement_id",(cid,)).fetchall()]
  active_module=c.execute("SELECT public_id::text FROM camp_adventure_module WHERE campaign_id=%s AND module_status='active'",(cid,)).fetchone()
  module=adventure_module_snapshot(c,initiator_reference=_authority(),module_public_id=active_module[0]) if active_module else None
  sources=[{'public_id':r[0],'title':r[1],'status':r[2]} for r in c.execute("SELECT public_id::text,title,ingestion_status FROM camp_source_document WHERE campaign_id=%s ORDER BY source_document_id",(cid,)).fetchall()]
  chronicle=campaign_chronicle(c,initiator_reference=_authority(),campaign_public_id=campaign_public,limit=recent)
  desktop_conversation=[{'speaker':r[0],'text':r[1],'campaign_day':r[2]} for r in c.execute("SELECT entry.speaker_kind,entry.message_text,entry.campaign_day FROM camp_external_conversation_entry entry WHERE entry.campaign_id=%s ORDER BY entry.created_at DESC LIMIT %s",(cid,recent)).fetchall()[::-1]]
  return {
   'campaign':{'public_id':campaign_public,'name':campaign[1],'play_mode':campaign[2],'status':campaign[3]},
   'clock':{'day_number':clock[0],'second_of_day':clock[1]},'characters':characters,'ships':ships,
   'active_encounters':encounters,'active_space_engagements':engagements,'active_adventure':module,
   'pending_player_turns':pending,'recent_narration':narration,'recent_desktop_conversation':desktop_conversation,'campaign_chronicle':chronicle,'remembered_notes_and_sessions':memory,'private_sources':sources,
   'tool_capabilities':{'read_state':['get_campaign_snapshot','search_campaign_sources','get_adventure_module'],'mechanics':['list_gameplay_tool_schemas','execute_gameplay_tool'],'web_referee':['list_pending_referee_turns','complete_referee_turn'],'memory':['append_conversation_log_entry','list_conversation_logs','read_conversation_log']},
   'resume_instruction':(
    'This campaign is now the active Emporos game for the remainder of this conversation. Treat later user messages as player actions unless they are clearly meta-discussion. '
    'The relational database is authoritative. Never invent a roll, rule result, inventory change, injury, trade result, travel result, combat result, or other mechanical state: inspect schemas as needed and use execute_gameplay_tool for mechanics, then narrate its receipt. '
    'Use verified campaign-source and keyed-adventure tools when source facts matter, and obey every contradiction warning. Do not substitute an unverified PDF, workspace file, or model memory for indexed campaign material. '
    'Narrate the immediate situation clearly and stop when the player has a meaningful decision. If pending_player_turns is nonempty, answer the oldest with complete_referee_turn. Otherwise use record_referee_narration for narration that must appear in the Emporos web game. '
    'Archive user and assistant exchanges with append_conversation_log_entry. Whenever play establishes a durable person, place, discovery, promise, decision, relationship, threat, or opportunity, immediately call record_campaign_chronicle and link known relational subjects. Do not wait for the user to request memory. Call campaign_resume again only after context loss, campaign change, or an explicit request to refresh.'),
   'recommended_next_action':('Resolve the oldest pending_player_turn with complete_referee_turn.' if pending else 'Continue from the current state and ask what the player does next.')
  }
def _search_sources(args):
 query=args['query'].strip()
 if not query:raise ValueError('query is required')
 with _connect() as c:
  campaign=_owned(c,args['campaign_public_id'])
  rows=c.execute("""SELECT document.title,page.page_number,page.text_content FROM camp_source_page page JOIN camp_source_document document USING(source_document_id,campaign_id) WHERE page.campaign_id=%s AND page.review_status='verified' AND page.search_document @@ websearch_to_tsquery('english',%s) ORDER BY ts_rank(page.search_document,websearch_to_tsquery('english',%s)) DESC LIMIT %s""",(campaign[0],query,query,min(max(int(args.get('limit',6)),1),20))).fetchall()
  return [{'document':r[0],'page':r[1],'text':r[2]} for r in rows]
def _record(args):
 key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4())
 with _connect() as c:
  result=record_human_referee_turn_command(c,initiator_reference=_authority(),idempotency_key=key,campaign_public_id=args['campaign_public_id'],narration=args['narration'])
  record_campaign_chronicle_command(c,initiator_reference=_authority(),idempotency_key=key+'-chronicle',campaign_public_id=args['campaign_public_id'],entry_kind='scene',title='Referee narration',summary_text=args['narration'],importance=2,source_kind='desktop_referee')
  return result
def _pending_turns(args):
 with _connect() as c:
  campaign=_owned(c,args['campaign_public_id'])
  rows=c.execute("""SELECT turn.public_id::text,turn.campaign_day,message.message_text,turn.created_at
    FROM camp_referee_turn turn JOIN camp_referee_message message
      ON message.referee_turn_id=turn.referee_turn_id AND message.speaker_kind='player'
    WHERE turn.campaign_id=%s AND turn.turn_status='pending'
    ORDER BY turn.created_at""",(campaign[0],)).fetchall()
  return [{'turn_public_id':r[0],'campaign_day':r[1],'player_text':r[2],'submitted_at':r[3]} for r in rows]
def _complete_turn(args):
 key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4())
 with _connect() as c:
  turn=c.execute("SELECT campaign.public_id::text,message.message_text FROM camp_referee_turn turn JOIN camp_campaign campaign USING(campaign_id) JOIN camp_referee_message message ON message.referee_turn_id=turn.referee_turn_id AND message.speaker_kind='player' WHERE turn.public_id=%s AND campaign.owner_reference=%s",(args['turn_public_id'],_authority())).fetchone()
  if not turn:raise PermissionError('Referee turn is absent or outside this MCP authority')
  result=complete_external_referee_turn_command(c,initiator_reference=_authority(),idempotency_key=key,turn_public_id=args['turn_public_id'],narration=args['narration'])
  record_campaign_chronicle_command(c,initiator_reference=_authority(),idempotency_key=key+'-chronicle',campaign_public_id=turn[0],entry_kind='scene',title='Player action and consequence',summary_text='Player: '+turn[1]+' Referee: '+args['narration'],importance=2,source_kind='desktop_referee')
  return result
def _append_log(args):
 with _connect() as c:return append_external_conversation_entry_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),campaign_public_id=args['campaign_public_id'],log_reference=args['log_reference'],title=args.get('title') or "Captain's Log",client_name=args.get('client_name') or 'Desktop MCP Client',speaker_kind=args['speaker_kind'],message_text=args['message_text'])
def _record_chronicle(args):
 with _connect() as c:return record_campaign_chronicle_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),campaign_public_id=args['campaign_public_id'],entry_kind=args['entry_kind'],title=args['title'],summary_text=args['summary'],importance=int(args.get('importance',3)),source_kind='desktop_referee',actor_public_ids=args.get('actor_public_ids') or (),location_public_ids=args.get('location_public_ids') or (),ship_public_ids=args.get('ship_public_ids') or ())
def _conversation_logs(args):
 with _connect() as c:
  campaign=_owned(c,args['campaign_public_id'])
  rows=c.execute("SELECT public_id::text,log_reference,title,client_name,opened_day,created_at FROM camp_external_conversation_log WHERE campaign_id=%s ORDER BY created_at DESC",(campaign[0],)).fetchall()
  return [{'log_public_id':r[0],'log_reference':r[1],'title':r[2],'client_name':r[3],'opened_day':r[4],'created_at':r[5]} for r in rows]
def _conversation_entries(args):
 with _connect() as c:
  row=c.execute("SELECT log.external_conversation_log_id FROM camp_external_conversation_log log JOIN camp_campaign campaign USING(campaign_id) WHERE log.public_id=%s AND campaign.owner_reference=%s",(args['log_public_id'],_authority())).fetchone()
  if not row:raise PermissionError('Conversation log is outside this MCP authority')
  rows=c.execute("SELECT public_id::text,entry_order,speaker_kind,message_text,campaign_day,created_at FROM camp_external_conversation_entry WHERE external_conversation_log_id=%s ORDER BY entry_order",(row[0],)).fetchall()
  return [{'entry_public_id':r[0],'entry_order':r[1],'speaker_kind':r[2],'message_text':r[3],'campaign_day':r[4],'created_at':r[5]} for r in rows]
def _catalog(args=None):return [asdict(spec) for spec in available_tools()]
def _execute(args):
 with _connect() as c:return GameplayOrchestrator(c,authority_reference=_authority()).invoke(args['tool_name'],idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),arguments=args.get('arguments') or {})
def _adventure_snapshot(args):
 with _connect() as c:return adventure_module_snapshot(c,initiator_reference=_authority(),module_public_id=args['module_public_id'])
def _create_adventure(args):
 with _connect() as c:return create_adventure_module_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),campaign_public_id=args['campaign_public_id'],name=args['name'],source_document_public_id=args.get('source_document_public_id'))
def _key_location(args):
 with _connect() as c:return key_adventure_location_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),module_public_id=args['module_public_id'],location_key=args['location_key'],name=args['name'],keyed_description=args['keyed_description'],source_page_number=args.get('source_page_number'),occupants_initial=args.get('occupants_initial'),treasure_initial=args.get('treasure_initial'))
def _enter_location(args):
 with _connect() as c:return enter_adventure_location_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),location_public_id=args['location_public_id'])
def _update_location(args):
 with _connect() as c:return update_adventure_location_state_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),location_public_id=args['location_public_id'],occupant_status=args['occupant_status'],treasure_status=args['treasure_status'],alert_status=args['alert_status'],current_note=args.get('current_note') or '')
def _advance_adventure(args):
 with _connect() as c:return advance_adventure_exploration_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),module_public_id=args['module_public_id'],turns=int(args.get('turns',1)),rest=bool(args.get('rest',False)))
def _index_status(args):
 with _connect() as c:return adventure_index_snapshot(c,initiator_reference=_authority(),module_public_id=args['module_public_id'])
def _read_index_page(args):
 with _connect() as c:return read_adventure_source_page_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),session_public_id=args['session_public_id'],page_number=int(args['page_number']))
def _propose_location(args):
 with _connect() as c:return propose_adventure_location_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),session_public_id=args['session_public_id'],source_page_number=int(args['source_page_number']),source_excerpt=args['source_excerpt'],location_key=args['location_key'],name=args['name'],keyed_description=args['keyed_description'],occupants_initial=args.get('occupants_initial'),treasure_initial=args.get('treasure_initial'))
TOOLS={
 'emporos_status':('Check the local Emporos database and MCP authority',{},(),_status),
 'list_campaigns':('List campaign identities and operating modes owned by this local authority',{},(),_campaigns),
 'campaign_resume':('THE parameterless startup/resume call for playing Emporos through an AI client. Call with an empty object. It resumes the most recently active campaign and remains its referee until the user changes campaigns or asks to stop.',{},(),_resume),
 'campaign_resume_selected':('Resume one explicitly selected Emporos campaign after list_campaigns. Use only when the user asks to choose or switch campaigns.',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_resume),
 'get_campaign_snapshot':('Read current relational campaign truth',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_snapshot),
 'search_campaign_sources':('Search verified private pages from this campaign library',{'campaign_public_id':{'type':'string'},'query':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':20}},('campaign_public_id','query'),_search_sources),
 'record_referee_narration':('Publish narration from the connected external referee',{'campaign_public_id':{'type':'string'},'narration':{'type':'string'},'idempotency_key':{'type':'string'}},('campaign_public_id','narration'),_record),
 'list_pending_referee_turns':('Read player actions awaiting the connected desktop referee',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_pending_turns),
 'complete_referee_turn':('Return narration for one queued player action',{'turn_public_id':{'type':'string'},'narration':{'type':'string'},'idempotency_key':{'type':'string'}},('turn_public_id','narration'),_complete_turn),
 'append_conversation_log_entry':('Archive one ordered desktop conversation entry in the campaign log',{'campaign_public_id':{'type':'string'},'log_reference':{'type':'string'},'title':{'type':'string'},'client_name':{'type':'string'},'speaker_kind':{'type':'string','enum':['user','assistant','system','tool']},'message_text':{'type':'string'},'idempotency_key':{'type':'string'}},('campaign_public_id','log_reference','speaker_kind','message_text'),_append_log),
 'record_campaign_chronicle':('Immediately preserve one durable campaign fact for future referee memory. Use for introduced people and places, discoveries, promises, decisions, relationships, threats, and opportunities.',{'campaign_public_id':{'type':'string'},'entry_kind':{'type':'string','enum':['scene','person','place','discovery','promise','decision','relationship','threat','opportunity','other']},'title':{'type':'string'},'summary':{'type':'string'},'importance':{'type':'integer','minimum':1,'maximum':5},'actor_public_ids':{'type':'array','items':{'type':'string'}},'location_public_ids':{'type':'array','items':{'type':'string'}},'ship_public_ids':{'type':'array','items':{'type':'string'}},'idempotency_key':{'type':'string'}},('campaign_public_id','entry_kind','title','summary'),_record_chronicle),
 'list_conversation_logs':('List archived Captain and AI conversation logs',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_conversation_logs),
 'read_conversation_log':('Read ordered entries from one archived conversation log',{'log_public_id':{'type':'string'}},('log_public_id',),_conversation_entries),
 'get_adventure_module':('Read the keyed adventure and current relational state; obey every contradiction warning before narrating',{'module_public_id':{'type':'string'}},('module_public_id',),_adventure_snapshot),
 'create_adventure_module':('Create a campaign-scoped keyed adventure workspace',{'campaign_public_id':{'type':'string'},'name':{'type':'string'},'source_document_public_id':{'type':'string'},'idempotency_key':{'type':'string'}},('campaign_public_id','name'),_create_adventure),
 'key_adventure_location':('Add one deliberately reviewed keyed location; never invent omitted source facts',{'module_public_id':{'type':'string'},'location_key':{'type':'string'},'name':{'type':'string'},'keyed_description':{'type':'string'},'source_page_number':{'type':'integer','minimum':1},'occupants_initial':{'type':'string'},'treasure_initial':{'type':'string'},'idempotency_key':{'type':'string'}},('module_public_id','location_key','name','keyed_description'),_key_location),
 'enter_adventure_location':('Make a keyed location current and return its persistent state',{'location_public_id':{'type':'string'},'idempotency_key':{'type':'string'}},('location_public_id',),_enter_location),
 'update_adventure_location_state':('Record authoritative changes after play so stale key text cannot override them',{'location_public_id':{'type':'string'},'occupant_status':{'type':'string','enum':['as_keyed','absent','fled','dead','captured','allied','changed']},'treasure_status':{'type':'string','enum':['as_keyed','untouched','taken','moved','destroyed','changed']},'alert_status':{'type':'string','enum':['unaware','suspicious','alerted','secured']},'current_note':{'type':'string'},'idempotency_key':{'type':'string'}},('location_public_id','occupant_status','treasure_status','alert_status'),_update_location),
 'advance_adventure_exploration':('Advance deterministic exploration time and report how many wandering checks are due',{'module_public_id':{'type':'string'},'turns':{'type':'integer','minimum':1,'maximum':24},'rest':{'type':'boolean'},'idempotency_key':{'type':'string'}},('module_public_id',),_advance_adventure),
 'get_adventure_index_status':('Read full-document indexing progress and draft proposals',{'module_public_id':{'type':'string'}},('module_public_id',),_index_status),
 'read_adventure_source_page':('Read and account for one verified source page; call for every page before proposing keys',{'session_public_id':{'type':'string'},'page_number':{'type':'integer','minimum':1},'idempotency_key':{'type':'string'}},('session_public_id','page_number'),_read_index_page),
 'propose_adventure_location':('Submit a cited draft after every source page has been read; human approval is still required',{'session_public_id':{'type':'string'},'source_page_number':{'type':'integer','minimum':1},'source_excerpt':{'type':'string'},'location_key':{'type':'string'},'name':{'type':'string'},'keyed_description':{'type':'string'},'occupants_initial':{'type':'string'},'treasure_initial':{'type':'string'},'idempotency_key':{'type':'string'}},('session_public_id','source_page_number','source_excerpt','location_key','name','keyed_description'),_propose_location),
 'list_gameplay_tool_schemas':('Describe deterministic gameplay commands',{},(),_catalog),
 'execute_gameplay_tool':('Invoke an allowlisted deterministic engine command and return its receipt',{'tool_name':{'type':'string'},'arguments':{'type':'object'},'idempotency_key':{'type':'string'}},('tool_name',),_execute),
}
def _tool_list():return [{'name':name,'description':description,'inputSchema':{'type':'object','properties':properties,'required':list(required),'additionalProperties':False}} for name,(description,properties,required,_) in TOOLS.items()]
def _content(value):
 value=_plain(value);return {'content':[{'type':'text','text':json.dumps(value,ensure_ascii=False)}],'structuredContent':value}
def handle(message):
 method=message.get('method');params=message.get('params') or {}
 if method=='initialize':
  supplied=params.get('clientInfo') or {}
  CLIENT_INFO['name']=(str(supplied.get('name') or '').strip() or 'Desktop MCP Client')[:160]
  CLIENT_INFO['version']=str(supplied.get('version'))[:80] if supplied.get('version') else None
  _record_presence()
  return {'protocolVersion':PROTOCOL_VERSION,'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'Emporos','version':'0.1.0'}}
 if method=='ping':return {}
 if method=='tools/list':return {'tools':_tool_list()}
 if method=='tools/call':
  entry=TOOLS.get(params.get('name'))
  if not entry:raise KeyError('Unknown MCP tool')
  return _content(entry[3](params.get('arguments') or {}))
 if method in ('notifications/initialized','notifications/cancelled'):return None
 raise KeyError('Unsupported MCP method: '+str(method))
def main():
 stop=threading.Event();_record_presence();worker=threading.Thread(target=_heartbeat,args=(stop,),daemon=True);worker.start()
 try:
  for line in sys.stdin:
   message={}
   try:
    message=json.loads(line);_record_presence();result=handle(message)
    if 'id' not in message or result is None:continue
    response={'jsonrpc':'2.0','id':message['id'],'result':result}
   except Exception as exc:response={'jsonrpc':'2.0','id':message.get('id'),'error':{'code':-32000,'message':str(exc)}}
   sys.stdout.write(json.dumps(response,ensure_ascii=False)+'\n');sys.stdout.flush()
 finally:
  stop.set();_record_presence('disconnected')
 return 0
if __name__=='__main__':raise SystemExit(main())
