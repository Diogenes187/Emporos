import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.settings import initialize_campaign_setting_command


@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CampaignSettingStartupTests(unittest.TestCase):
    def _campaign(self,c,owner,label):
        return create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+label,name='Setting '+label)

    def test_ledger_reach_is_bundled_instantiated_isolated_and_replayable(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            with c.transaction(force_rollback=True):
                suffix=str(uuid.uuid4());owner='setting-test-'+suffix
                first=self._campaign(c,owner,suffix+'-a')
                result=initialize_campaign_setting_command(c,initiator_reference=owner,idempotency_key='setting-'+suffix+'-a',campaign_public_id=first.campaign_public_id,startup_choice='ledger_reach')
                replay=initialize_campaign_setting_command(c,initiator_reference=owner,idempotency_key='setting-'+suffix+'-a',campaign_public_id=first.campaign_public_id,startup_choice='ledger_reach')
                self.assertTrue(replay.replayed);self.assertEqual(result.sector_public_id,replay.sector_public_id)
                names=[r[0] for r in c.execute("SELECT location.name FROM loc_star_system system JOIN loc_location location USING(location_id) WHERE system.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s) ORDER BY system.hex_column,system.hex_row",(first.campaign_public_id,))]
                self.assertEqual(names,["Ledger's Rest",'Orison','Kestrel'])
                worlds=c.execute("SELECT starting.name,current.name FROM camp_campaign_setting setting JOIN loc_location starting ON starting.location_id=setting.starting_world_location_id JOIN loc_location current ON current.location_id=setting.current_world_location_id WHERE setting.campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s)",(first.campaign_public_id,)).fetchone()
                self.assertEqual(worlds,("Ledger's Rest","Ledger's Rest"))
                second=self._campaign(c,owner,suffix+'-b')
                other=initialize_campaign_setting_command(c,initiator_reference=owner,idempotency_key='setting-'+suffix+'-b',campaign_public_id=second.campaign_public_id,startup_choice='ledger_reach')
                self.assertNotEqual(result.sector_public_id,other.sector_public_id)

    def test_each_non_bundled_startup_choice_has_honest_relational_state(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            with c.transaction(force_rollback=True):
                suffix=str(uuid.uuid4());owner='choice-test-'+suffix
                expected={'generate_original':8,'import_own':0,'uncharted':0}
                for choice,count in expected.items():
                    campaign=self._campaign(c,owner,suffix+choice)
                    initialize_campaign_setting_command(c,initiator_reference=owner,idempotency_key='setting-'+suffix+choice,campaign_public_id=campaign.campaign_public_id,startup_choice=choice)
                    row=c.execute("SELECT selected.startup_choice,selected.rights_class,count(system.location_id) FROM camp_campaign_setting selected JOIN camp_campaign campaign USING(campaign_id) LEFT JOIN loc_star_system system ON system.campaign_id=campaign.campaign_id WHERE campaign.public_id=%s GROUP BY selected.startup_choice,selected.rights_class",(campaign.campaign_public_id,)).fetchone()
                    self.assertEqual(row[0],choice);self.assertEqual(row[2],count)
                    if choice=='import_own': self.assertEqual(row[1],'private_non_exportable')
                    world_count=c.execute("SELECT count(*) FROM camp_campaign_setting WHERE campaign_id=(SELECT campaign_id FROM camp_campaign WHERE public_id=%s) AND starting_world_location_id IS NOT NULL AND current_world_location_id IS NOT NULL",(campaign.campaign_public_id,)).fetchone()[0]
                    self.assertEqual(world_count,1 if choice=='generate_original' else 0)

    def test_bundled_setting_contains_no_protected_traveller_setting_names(self):
        with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
            forbidden=('spinward marches','charted space','traveller map','regina')
            text=' '.join(r[0] for r in c.execute("""SELECT value FROM (
              SELECT setting_name AS value FROM setting_package
              UNION ALL SELECT sector_name FROM setting_sector_template
              UNION ALL SELECT system_name FROM setting_system_template) bundled""")) .lower()
            for term in forbidden:self.assertNotIn(term,text)


if __name__=='__main__': unittest.main()
