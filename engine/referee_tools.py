"""Player-confirmed execution of AI-proposed, allowlisted gameplay tools."""
from dataclasses import dataclass
import psycopg
from engine.orchestration import GameplayOrchestrator,available_tools

@dataclass(frozen=True)
class RefereeToolResult:
 command_public_id:str;gameplay_command_public_id:str;tool_name:str;replayed:bool

def _decode(value,kind):
 if kind=='null':return None
 if kind=='boolean':return value.lower()=='true'
 if kind=='integer':return int(value)
 if kind=='number':return float(value)
 return value

def confirm_referee_tool_request(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,request_public_id:str)->RefereeToolResult:
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2]!='confirm_referee_tool_request':raise ValueError('Idempotency key belongs to another command')
   row=c.execute("SELECT request.tool_name,gameplay.public_id FROM cmd_referee_tool_confirmation_receipt receipt JOIN camp_referee_tool_request request USING(referee_tool_request_id) JOIN cmd_command gameplay ON gameplay.command_id=receipt.gameplay_command_id WHERE receipt.command_id=%s",(old[0],)).fetchone();return RefereeToolResult(str(old[1]),str(row[1]),row[0],True)
  request=c.execute("SELECT request.referee_tool_request_id,request.campaign_id,request.tool_name FROM camp_referee_tool_request request JOIN camp_campaign campaign USING(campaign_id) WHERE request.public_id=%s AND campaign.owner_reference=%s AND request.request_status='proposed' FOR UPDATE OF request",(request_public_id,initiator_reference)).fetchone()
  if not request:raise ValueError('Proposed referee action does not exist')
  allowed={spec.name:spec for spec in available_tools()};spec=allowed.get(request[2])
  if not spec:raise ValueError('Proposed referee action is not allowlisted')
  rows=c.execute("SELECT argument_name,argument_value,value_kind FROM camp_referee_tool_argument WHERE referee_tool_request_id=%s ORDER BY argument_order",(request[0],)).fetchall();arguments={name:_decode(value,kind) for name,value,kind in rows}
  outcome=GameplayOrchestrator(c,authority_reference=initiator_reference).invoke(request[2],idempotency_key=idempotency_key+'-gameplay',arguments=arguments)
  gameplay=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(outcome.command_public_id,)).fetchone()
  if not gameplay:raise RuntimeError('Gameplay command did not produce an auditable command')
  command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('confirm_referee_tool_request',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();c.execute("UPDATE camp_referee_tool_request SET request_status='executed',executed_command_id=%s,decided_at=clock_timestamp() WHERE referee_tool_request_id=%s",(gameplay[0],request[0]));c.execute("INSERT INTO cmd_referee_tool_confirmation_receipt VALUES(%s,%s,%s,%s)",(command_id,request[1],request[0],gameplay[0]));c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'referee_tool_request_confirmed')",(command_id,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,));return RefereeToolResult(str(command_public),str(outcome.command_public_id),request[2],False)
