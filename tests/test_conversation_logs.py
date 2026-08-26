import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.conversation_logs import append_external_conversation_entry_command

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class ConversationLogTests(unittest.TestCase):
 def test_log_is_ordered_isolated_and_idempotent(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());owner='conversation-'+suffix
    campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+suffix,name='Log Test')
    other=create_campaign_command(c,initiator_reference=owner,idempotency_key='other-'+suffix,name='Other Log Test')
    first=append_external_conversation_entry_command(c,initiator_reference=owner,idempotency_key='entry-1-'+suffix,campaign_public_id=campaign.campaign_public_id,log_reference='session-001',title="Captain's Log: First Departure",client_name='Claude Desktop',speaker_kind='user',message_text='We break orbit.')
    replay=append_external_conversation_entry_command(c,initiator_reference=owner,idempotency_key='entry-1-'+suffix,campaign_public_id=campaign.campaign_public_id,log_reference='session-001',title="Captain's Log: First Departure",client_name='Claude Desktop',speaker_kind='user',message_text='Ignored on replay.')
    second=append_external_conversation_entry_command(c,initiator_reference=owner,idempotency_key='entry-2-'+suffix,campaign_public_id=campaign.campaign_public_id,log_reference='session-001',title="Captain's Log: First Departure",client_name='Claude Desktop',speaker_kind='assistant',message_text='The stars stretch into lines.')
    self.assertEqual(first.entry_order,1);self.assertTrue(replay.replayed);self.assertEqual(replay.entry_public_id,first.entry_public_id)
    self.assertEqual(second.entry_order,2);self.assertEqual(second.log_public_id,first.log_public_id)
    self.assertEqual(c.execute('SELECT count(*) FROM camp_external_conversation_entry').fetchone()[0],2)
    self.assertEqual(c.execute('SELECT count(*) FROM camp_external_conversation_log WHERE campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)',(other.campaign_public_id,)).fetchone()[0],0)
 def test_schema_has_no_json_columns(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   rows=c.execute("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name IN('camp_external_conversation_log','camp_external_conversation_entry') AND data_type IN('json','jsonb')").fetchall()
   self.assertEqual(rows,[])
if __name__=='__main__':unittest.main()
