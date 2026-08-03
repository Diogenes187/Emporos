import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.sectors import import_sector_command

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SectorImportTests(unittest.TestCase):
 def test_import_is_atomic_audited_and_replayable(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());campaign=create_campaign_command(c,initiator_reference='sector-test',idempotency_key='camp-'+suffix,name='Sector Test')
    content=b'Name\tHex\tUWP\nRegina\t1910\tA788899-C\nYori\t2110\tC360757-A\n'
    result=import_sector_command(c,initiator_reference='sector-test',idempotency_key='sector-'+suffix,campaign_public_id=campaign.campaign_public_id,sector_name='Spinward Marches',sector_x=0,sector_y=0,source_filename='spinward.tab',content=content)
    replay=import_sector_command(c,initiator_reference='sector-test',idempotency_key='sector-'+suffix,campaign_public_id=campaign.campaign_public_id,sector_name='Ignored',sector_x=9,sector_y=9,source_filename='ignored.tab',content=content)
    self.assertEqual(result.sector_public_id,replay.sector_public_id);self.assertTrue(replay.replayed);self.assertEqual(result.system_count,2)
    self.assertEqual(c.execute("SELECT count(*) FROM cmd_sector_import_system WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(result.command_public_id,)).fetchone()[0],2)

if __name__=='__main__': unittest.main()
