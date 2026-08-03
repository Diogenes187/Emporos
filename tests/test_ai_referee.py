import json,os,unittest,uuid
import psycopg
from ai.providers import ChatResult
from ai.referee import submit_referee_turn
from engine.campaigns import create_campaign_command
from engine.referee_tools import confirm_referee_tool_request

class FakeProvider:
 provider_code='fake';model='safe-narrator'
 def __init__(self,content=None):self.messages=None;self.content=content or '{"narration":"The docking bay doors stand open. What do you do?","tool_request":null}'
 def chat(self,*,messages,max_tokens,json_output=False):
  self.messages=messages
  return ChatResult(self.content,self.provider_code,self.model,22,11)

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class RefereeConversationTests(unittest.TestCase):
 def test_narration_is_relational_audited_and_idempotent(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());owner='referee-test';campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+suffix,name='Referee Test');provider=FakeProvider()
    result=submit_referee_turn(c,initiator_reference=owner,idempotency_key='turn-'+suffix,campaign_public_id=campaign.campaign_public_id,player_text='I enter the docking bay.',provider=provider)
    replay=submit_referee_turn(c,initiator_reference=owner,idempotency_key='turn-'+suffix,campaign_public_id=campaign.campaign_public_id,player_text='ignored on replay',provider=provider)
    self.assertEqual(result.command_public_id,replay.command_public_id);self.assertTrue(replay.replayed)
    self.assertEqual(c.execute("SELECT count(*) FROM camp_referee_message message JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE turn.public_id=%s",(result.turn_public_id,)).fetchone()[0],2)
    audit=c.execute("SELECT purpose_code,invocation_status,input_sha256,output_sha256 FROM ai_model_invocation invocation JOIN camp_referee_turn turn ON turn.source_command_id=invocation.source_command_id WHERE turn.public_id=%s",(result.turn_public_id,)).fetchone();self.assertEqual(audit[:2],('referee_narration','completed'));self.assertTrue(all(len(value)==64 for value in audit[2:]))
    self.assertIn('A proposed tool is not yet executed',provider.messages[0]['content'])
    proposed=FakeProvider('{"narration":"The ship is ready; departure awaits confirmation.","tool_request":{"name":"start_spacecraft_journey_leg","summary":"Begin the prepared jump","arguments":{"journey_public_id":"00000000-0000-0000-0000-000000000001","leg_order":1}}}')
    turn=submit_referee_turn(c,initiator_reference=owner,idempotency_key='proposal-'+suffix,campaign_public_id=campaign.campaign_public_id,player_text='Begin the prepared jump.',provider=proposed)
    stored=c.execute("SELECT request.tool_name,count(argument.argument_name) FROM camp_referee_tool_request request JOIN camp_referee_tool_argument argument USING(referee_tool_request_id) JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE turn.public_id=%s GROUP BY request.tool_name",(turn.turn_public_id,)).fetchone();self.assertEqual(stored,('start_spacecraft_journey_leg',2))

 def test_confirmed_proposal_executes_real_allowlisted_engine_command(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());owner='referee-confirm-test';campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+suffix,name='Confirmation Test');campaign_id=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s",(campaign.campaign_public_id,)).fetchone()[0];actor_id,actor_public=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Scout',%s) RETURNING actor_id,public_id",(campaign_id,owner)).fetchone();characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.intelligence'").fetchone()[0];skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.recon'").fetchone()[0];c.execute("INSERT INTO actor_characteristic VALUES(%s,%s,8,8)",(actor_id,characteristic));c.execute("INSERT INTO actor_skill VALUES(%s,%s,1)",(actor_id,skill))
    proposal={'narration':'You begin a careful sweep; the check awaits confirmation.','tool_request':{'name':'resolve_recon','summary':'Search the docking bay for threats','arguments':{'actor_public_id':str(actor_public),'operation_code':'spot-threat','subject_reference':'docking bay','characteristic_rule_code':'characteristic.intelligence','difficulty_rule_code':'difficulty.average'}}};provider=FakeProvider(json.dumps(proposal));turn=submit_referee_turn(c,initiator_reference=owner,idempotency_key='turn-'+suffix,campaign_public_id=campaign.campaign_public_id,player_text='I carefully search the docking bay for threats.',provider=provider);request_public=c.execute("SELECT request.public_id FROM camp_referee_tool_request request JOIN camp_referee_turn turn USING(referee_turn_id,campaign_id) WHERE turn.public_id=%s",(turn.turn_public_id,)).fetchone()[0]
    outcome=confirm_referee_tool_request(c,initiator_reference=owner,idempotency_key='confirm-'+suffix,request_public_id=str(request_public));self.assertEqual(outcome.tool_name,'resolve_recon');self.assertFalse(outcome.replayed);self.assertEqual(c.execute("SELECT request_status FROM camp_referee_tool_request WHERE public_id=%s",(request_public,)).fetchone()[0],'executed')

if __name__=='__main__':unittest.main()
