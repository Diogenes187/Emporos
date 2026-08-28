import os,tempfile,unittest,uuid
from pathlib import Path
import psycopg
from engine.campaigns import create_campaign_command
from engine.source_library import ingest_campaign_source_command
from engine.source_review import review_campaign_source_page_command
from engine.adventure_modules import create_adventure_module_command,adventure_module_snapshot
from engine.adventure_indexing import begin_adventure_indexing_command,read_adventure_source_page_command,propose_adventure_location_command,review_adventure_location_proposal_command,adventure_index_snapshot

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class AdventureIndexingTests(unittest.TestCase):
 def test_full_read_exact_citation_and_human_approval(self):
  with tempfile.TemporaryDirectory() as uploads,psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    owner='index-'+str(uuid.uuid4());campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+str(uuid.uuid4()),name='Index Test',play_mode='ai_assisted')
    source=ingest_campaign_source_command(c,initiator_reference=owner,idempotency_key='source-'+str(uuid.uuid4()),campaign_public_id=campaign.campaign_public_id,title='Station Adventure',source_kind='adventure',original_filename='station.txt',media_type='text/plain',content=b'A1 Airlock. Four corsairs guard a sealed cargo case.',storage_root=Path(uploads))
    review_campaign_source_page_command(c,initiator_reference=owner,idempotency_key='review-'+str(uuid.uuid4()),document_public_id=source.document_public_id,page_number=1,text_verified=True,visual_verified=False)
    module=create_adventure_module_command(c,initiator_reference=owner,idempotency_key='module-'+str(uuid.uuid4()),campaign_public_id=campaign.campaign_public_id,name='Station Adventure',source_document_public_id=source.document_public_id)
    session=begin_adventure_indexing_command(c,initiator_reference=owner,idempotency_key='begin-'+str(uuid.uuid4()),module_public_id=module.module_public_id)
    with self.assertRaises(ValueError):propose_adventure_location_command(c,initiator_reference=owner,idempotency_key='too-soon-'+str(uuid.uuid4()),session_public_id=session.session_public_id,source_page_number=1,source_excerpt='A1 Airlock.',location_key='A1',name='Airlock',keyed_description='Airlock')
    page=read_adventure_source_page_command(c,initiator_reference=owner,idempotency_key='read-'+str(uuid.uuid4()),session_public_id=session.session_public_id,page_number=1)
    self.assertEqual(page['pages_remaining'],0)
    with self.assertRaises(ValueError):propose_adventure_location_command(c,initiator_reference=owner,idempotency_key='bad-quote-'+str(uuid.uuid4()),session_public_id=session.session_public_id,source_page_number=1,source_excerpt='Invented quotation',location_key='A1',name='Airlock',keyed_description='Airlock')
    proposal=propose_adventure_location_command(c,initiator_reference=owner,idempotency_key='propose-'+str(uuid.uuid4()),session_public_id=session.session_public_id,source_page_number=1,source_excerpt='Four corsairs guard a sealed cargo case.',location_key='A1',name='Airlock',keyed_description='Four corsairs guard a sealed cargo case.',occupants_initial='Four corsairs',treasure_initial='Sealed cargo case')
    self.assertEqual(adventure_module_snapshot(c,initiator_reference=owner,module_public_id=module.module_public_id)['locations'],[])
    approved=review_adventure_location_proposal_command(c,initiator_reference=owner,idempotency_key='approve-'+str(uuid.uuid4()),proposal_public_id=proposal.proposal_public_id,decision='approve')
    self.assertEqual(approved.result_code,'approved')
    self.assertEqual(adventure_module_snapshot(c,initiator_reference=owner,module_public_id=module.module_public_id)['locations'][0]['key'],'A1')
    self.assertEqual(adventure_index_snapshot(c,initiator_reference=owner,module_public_id=module.module_public_id)['status'],'complete')

if __name__=='__main__':unittest.main()
