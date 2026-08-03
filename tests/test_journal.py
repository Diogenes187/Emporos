import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.journal import add_campaign_note_command,archive_play_session_command
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class JournalTests(unittest.TestCase):
 def test_notes_and_session_text_are_durable_memory_records(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    x=str(uuid.uuid4());owner='journal-test';camp=create_campaign_command(c,initiator_reference=owner,idempotency_key='c'+x,name='Journal')
    note=add_campaign_note_command(c,initiator_reference=owner,idempotency_key='n'+x,campaign_public_id=camp.campaign_public_id,title='Patron',note_kind='plot',note_text='The patron concealed the cargo origin.');self.assertFalse(note.replayed)
    session=archive_play_session_command(c,initiator_reference=owner,idempotency_key='s'+x,campaign_public_id=camp.campaign_public_id,title='First Run',transcript_text='PLAYER: We accept. REFEREE: The hold is sealed.');self.assertFalse(session.replayed)
    self.assertEqual(c.execute("SELECT count(*) FROM camp_journal_note WHERE campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s) AND ai_memory_enabled",(camp.campaign_public_id,)).fetchone()[0],1)
if __name__=='__main__':unittest.main()
