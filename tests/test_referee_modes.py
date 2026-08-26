import os,unittest,uuid
import psycopg
from ai.providers import ChatResult
from engine.campaigns import create_campaign_command
from engine.referee_modes import record_human_referee_turn_command,request_gm_assistance_command

class FakeProvider:
 provider_code='test';model='test-model'
 def chat(self,**kwargs):return ChatResult('Consider presenting two rival cargo patrons.',self.provider_code,self.model,12,7)

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class RefereeModeTests(unittest.TestCase):
 def campaign(self,c,owner,mode):return create_campaign_command(c,initiator_reference=owner,idempotency_key='camp-'+str(uuid.uuid4()),name='Mode Test',play_mode=mode)
 def test_human_referee_records_narration_without_model_invocation(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    owner='human-'+str(uuid.uuid4());campaign=self.campaign(c,owner,'human_refereed');key='turn-'+str(uuid.uuid4())
    result=record_human_referee_turn_command(c,initiator_reference=owner,idempotency_key=key,campaign_public_id=campaign.campaign_public_id,narration='The dockmaster opens the sealed ledger.')
    replay=record_human_referee_turn_command(c,initiator_reference=owner,idempotency_key=key,campaign_public_id=campaign.campaign_public_id,narration='ignored')
    self.assertTrue(replay.replayed);self.assertEqual(result.narration,replay.narration)
    self.assertEqual(c.execute('SELECT count(*) FROM ai_model_invocation WHERE source_command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)',(result.command_public_id,)).fetchone()[0],0)
 def test_ai_assistance_is_private_audited_and_does_not_publish(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    owner='assist-'+str(uuid.uuid4());campaign=self.campaign(c,owner,'ai_assisted');key='assist-'+str(uuid.uuid4())
    result=request_gm_assistance_command(c,initiator_reference=owner,idempotency_key=key,campaign_public_id=campaign.campaign_public_id,prompt_text='Give me two hooks.',provider=FakeProvider())
    self.assertIn('two rival',result.suggestion)
    self.assertEqual(c.execute('SELECT count(*) FROM camp_referee_message WHERE campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)',(campaign.campaign_public_id,)).fetchone()[0],0)
    self.assertEqual(c.execute("SELECT purpose_code FROM ai_model_invocation WHERE source_command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(result.command_public_id,)).fetchone()[0],'gm_assistance')
 def test_external_referee_can_record_in_ai_refereed_campaign(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    owner='reject-'+str(uuid.uuid4());campaign=self.campaign(c,owner,'ai_refereed')
    result=record_human_referee_turn_command(c,initiator_reference=owner,idempotency_key='external-'+str(uuid.uuid4()),campaign_public_id=campaign.campaign_public_id,narration='External MCP referee narration.')
    self.assertEqual(result.narration,'External MCP referee narration.')

if __name__=='__main__':unittest.main()
