import mcp_server

def test_initialize_and_safe_tool_surface():
 result=mcp_server.handle({'jsonrpc':'2.0','id':1,'method':'initialize','params':{}})
 assert result['serverInfo']['name']=='Emporos'
 tools=mcp_server.handle({'jsonrpc':'2.0','id':2,'method':'tools/list','params':{}})['tools']
 names={tool['name'] for tool in tools}
 assert names=={'emporos_status','list_campaigns','get_campaign_snapshot','search_campaign_sources','record_referee_narration','list_pending_referee_turns','complete_referee_turn','append_conversation_log_entry','list_conversation_logs','read_conversation_log','list_gameplay_tool_schemas','execute_gameplay_tool'}
 execute=next(tool for tool in tools if tool['name']=='execute_gameplay_tool')
 assert execute['inputSchema']['required']==['tool_name']
