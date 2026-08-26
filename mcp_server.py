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
def _catalog(args=None):return [asdict(spec) for spec in available_tools()]
def _execute(args):
 with _connect() as c:return GameplayOrchestrator(c,authority_reference=_authority()).invoke(args['tool_name'],idempotency_key=args.get('idempotency_key') or 'mcp-'+str(uuid.uuid4()),arguments=args.get('arguments') or {})
TOOLS={
 'emporos_status':('Check the local Emporos database and MCP authority',{},(),_status),
 'list_campaigns':('List campaign identities and operating modes owned by this local authority',{},(),_campaigns),
 'get_campaign_snapshot':('Read current relational campaign truth',{'campaign_public_id':{'type':'string'}},('campaign_public_id',),_snapshot),
 'search_campaign_sources':('Search verified private pages from this campaign library',{'campaign_public_id':{'type':'string'},'query':{'type':'string'},'limit':{'type':'integer','minimum':1,'maximum':20}},('campaign_public_id','query'),_search_sources),
 'record_referee_narration':('Publish narration from the connected external referee',{'campaign_public_id':{'type':'string'},'narration':{'type':'string'},'idempotency_key':{'type':'string'}},('campaign_public_id','narration'),_record),
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
