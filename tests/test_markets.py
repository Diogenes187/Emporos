import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.sectors import import_sector_command
from engine.markets import open_trade_market_command
class Fixed:
 def randint(self,a,b):return min(3,b)
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class MarketTests(unittest.TestCase):
 def test_market_stock_is_fully_receipted(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());camp=create_campaign_command(c,initiator_reference='market-test',idempotency_key='camp-'+suffix,name='Market')
    import_sector_command(c,initiator_reference='market-test',idempotency_key='sector-'+suffix,campaign_public_id=camp.campaign_public_id,sector_name='Test',sector_x=0,sector_y=0,source_filename='x.tab',content=b'Name\tHex\tUWP\nAlpha\t0101\tA788899-C\n')
    system=c.execute("SELECT location.public_id FROM loc_star_system star JOIN loc_location location ON location.location_id=star.location_id WHERE star.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)",(camp.campaign_public_id,)).fetchone()[0]
    result=open_trade_market_command(c,initiator_reference='market-test',idempotency_key='market-'+suffix,campaign_public_id=camp.campaign_public_id,system_public_id=system,random_source=Fixed())
    self.assertGreaterEqual(result.distinct_stock_count,6);self.assertGreater(result.total_quantity_tons,0)
if __name__=='__main__':unittest.main()
