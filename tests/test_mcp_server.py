import mcp_server

def test_initialize_and_safe_tool_surface():
 result=mcp_server.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'clientInfo':{'name':'Test Desktop','version':'1.2'}}})
 assert result['serverInfo']['name']=='Emporos'
 assert mcp_server.CLIENT_INFO=={'name':'Test Desktop','version':'1.2'}
 tools=mcp_server.handle({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})['tools']
 names={tool['name'] for tool in tools}
 assert names=={'emporos_status','list_campaigns','campaign_resume','get_campaign_snapshot','search_campaign_sources','record_referee_narration','list_pending_referee_turns','complete_referee_turn','append_conversation_log_entry','record_campaign_chronicle','list_conversation_logs','read_conversation_log','list_gameplay_tool_schemas','execute_gameplay_tool','get_adventure_module','create_adventure_module','key_adventure_location','enter_adventure_location','update_adventure_location_state','advance_adventure_exploration','get_adventure_index_status','read_adventure_source_page','propose_adventure_location'}
 execute=next(tool for tool in tools if tool['name']=='execute_gameplay_tool')
 assert execute['inputSchema']['required']==['tool_name']
 module=next(tool for tool in tools if tool['name']=='get_adventure_module')
 assert 'contradiction warning' in module['description']
 resume=next(tool for tool in tools if tool['name']=='campaign_resume')
 assert resume['inputSchema']['required']==[]
 assert 'single startup/resume call' in resume['description']
