import os,unittest,uuid
import psycopg
from ai.providers import ChatResult
from ai.referee import submit_referee_turn
from engine.campaigns import create_campaign_command

class FakeProvider:
 provider_code='fake';model='safe-narrator'
 def __init__(self):self.messages=None
 def chat(self,*,messages,max_tokens):
  self.messages=messages
  return ChatResult('The docking bay doors stand open. What do you do?',self.provider_code,self.model,22,11)

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
    self.assertIn('Never change or claim to resolve mechanics',provider.messages[0]['content'])

if __name__=='__main__':unittest.main()
