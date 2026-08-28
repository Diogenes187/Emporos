"""Provider-neutral local Emporos MCP server."""
from __future__ import annotations
from dataclasses import asdict,is_dataclass
from datetime import date,datetime
from decimal import Decimal
import json,os,sys,uuid
import psycopg
from app.database import database_url
from engine.orchestration import GameplayOrchestrator,available_tools
from engine.referee_modes import record_human_referee_turn_command
from engine.external_referee import complete_external_referee_turn_command
from engine.conversation_logs import append_external_conversation_entry_command
from engine.adventure_modules import adventure_module_snapshot,create_adventure_module_command,key_adventure_location_command,enter_adventure_location_command,update_adventure_location_state_command,advance_adventure_exploration_command
from engine.adventure_indexing import adventure_index_snapshot,read_adventure_source_page_command,propose_adventure_location_command

PROTOCOL_VERSION='2025-03-26'
def _connect():
 dsn=database_url()
 if not dsn:raise RuntimeError('EMPOROS_DATABASE_URL or BASE_CEPHEUS_DATABASE_URL is required')
 return psycopg.connect(dsn)
def _authority():return os.environ.get('EMPOROS_AUTHORITY_REFERENCE','emporos-local-player')
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
def _search_sources(args):
 query=args['query'].strip()
 if not query:raise ValueError('query is required')
 with _connect() as c:
  campaign=_owned(c,args['campaign_public_id'])
  rows=c.execute("""SELECT document.title,page.page_number,page.text_content FROM camp_source_page page JOIN camp_source_document document USING(source_document_id,campaign_id) WHERE page.campaign_id=%s AND page.review_status='verified' AND page.search_document @@ websearch_to_tsquery('english',%s) ORDER BY ts_rank(page.search_document,websearch_to_tsquery('english',%s)) DESC LIMIT %s""",(campaign[0],query,query,min(max(int(args.get('limit',6)),1),20))).fetchall()
  return [{'document':r[0],'page':r[1],'text':r[2]} for r in rows]
def _record(args):
 with _connect() as c:return record_human_referee_turn_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),campaign_public_id=args['campaign_public_id'],narration=args['narration'])
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
 with _connect() as c:return complete_external_referee_turn_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),turn_public_id=args['turn_public_id'],narration=args['narration'])
def _append_log(args):
 with _connect() as c:return append_external_conversation_entry_command(c,initiator_reference=_authority(),idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),campaign_public_id=args['campaign_public_id'],log_reference=args['log_reference'],title=args.get('title') or "Captain's Log",client_name=args.get('client_name') or 'Desktop MCP Client',speaker_kind=args['speaker_kind'],message_text=args['message_text'])
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
 'get_campaign_snapshot':('Read current relational campaign truth',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_snapshot),
 'search_campaign_sources':('Search verified private pages from this campaign library',{'campaign_public_id':{'type':'string'},'query':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':20}},('campaign_public_id','query'),_search_sources),
 'record_referee_narration':('Publish narration from the connected external referee',{'campaign_public_id':{'type':'string'},'narration':{'type':'string'},'idempotency_key':{'type':'string'}},('campaign_public_id','narration'),_record),
 'list_pending_referee_turns':('Read player actions awaiting the connected desktop referee',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_pending_turns),
 'complete_referee_turn':('Return narration for one queued player action',{'turn_public_id':{'type':'string'},'narration':{'type':'string'},'idempotency_key':{'type':'string'}},('turn_public_id','narration'),_complete_turn),
 'append_conversation_log_entry':('Archive one ordered desktop conversation entry in the campaign log',{'campaign_public_id':{'type':'string'},'log_reference':{'type':'string'},'title':{'type':'string'},'client_name':{'type':'string'},'speaker_kind':{'type':'string','enum':['user','assistant','system','tool']},'message_text':{'type':'string'},'idempotency_key':{'type':'string'}},('campaign_public_id','log_reference','speaker_kind','message_text'),_append_log),
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
 if method=='initialize':return {'protocolVersion':PROTOCOL_VERSION,'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'Emporos','version':'0.1.0'}}
 if method=='ping':return {}
 if method=='tools/list':return {'tools':_tool_list()}
 if method=='tools/call':
  entry=TOOLS.get(params.get('name'))
  if not entry:raise KeyError('Unknown MCP tool')
  return _content(entry[3](params.get('arguments') or {}))
 if method in ('notifications/initialized','notifications/cancelled'):return None
 raise KeyError('Unsupported MCP method: '+str(method))
def main():
 for line in sys.stdin:
  message={}
  try:
   message=json.loads(line);result=handle(message)
   if 'id' not in message or result is None:continue
   response={'jsonrpc':'2.0','id':message['id'],'result':result}
  except Exception as exc:response={'jsonrpc':'2.0','id':message.get('id'),'error':{'code':-32000,'message':str(exc)}}
  sys.stdout.write(json.dumps(response,ensure_ascii=False)+'\n');sys.stdout.flush()
 return 0
if __name__=='__main__':raise SystemExit(main())
