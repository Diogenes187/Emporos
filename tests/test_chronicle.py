import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.chronicle import record_campaign_chronicle_command,campaign_chronicle

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class ChronicleTests(unittest.TestCase):
 def test_structured_memory_is_scoped_linked_and_idempotent(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    key=uuid.uuid4().hex;owner='chronicle-'+key;campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+key,name='Chronicle Test')
    cid=c.execute('SELECT campaign_id FROM camp_campaign WHERE public_id=%s',(campaign.campaign_public_id,)).fetchone()[0]
    actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Patron Vey',%s) RETURNING public_id::text",(cid,owner)).fetchone()[0]
    first=record_campaign_chronicle_command(c,initiator_reference=owner,idempotency_key='memory-'+key,campaign_public_id=campaign.campaign_public_id,entry_kind='promise',title='Delivery owed',summary_text='Patron Vey expects the sealed case at Orison.',importance=5,actor_public_ids=[actor])
    replay=record_campaign_chronicle_command(c,initiator_reference=owner,idempotency_key='memory-'+key,campaign_public_id=campaign.campaign_public_id,entry_kind='promise',title='Changed',summary_text='Changed',importance=1)
    self.assertFalse(first.replayed);self.assertTrue(replay.replayed)
    memory=campaign_chronicle(c,initiator_reference=owner,campaign_public_id=campaign.campaign_public_id)
    self.assertEqual(memory[0]['people'],['Patron Vey']);self.assertEqual(memory[0]['importance'],5);self.assertEqual(memory[0]['summary'],'Patron Vey expects the sealed case at Orison.')
if __name__=='__main__':unittest.main()
