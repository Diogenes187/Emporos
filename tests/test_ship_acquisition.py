import os
import unittest
import uuid
import psycopg

from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.ships import acquire_ship_command


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"),"requires PostgreSQL")
class ShipAcquisitionTests(unittest.TestCase):
    def test_acquisition_builds_audited_operational_vessel_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix=str(uuid.uuid4())
                campaign=create_campaign_command(connection,initiator_reference="ship-test",idempotency_key="campaign-"+suffix,name="Ship Test")
                actor=initialize_character_command(connection,initiator_reference="ship-test",idempotency_key="actor-"+suffix,campaign_public_id=campaign.campaign_public_id,character_name="Captain Venn")
                result=acquire_ship_command(connection,initiator_reference="ship-test",idempotency_key="ship-"+suffix,campaign_public_id=campaign.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code="merchant-trader",ship_name="Far Horizon",registration_identifier="FH-001")
                replay=acquire_ship_command(connection,initiator_reference="ship-test",idempotency_key="ship-"+suffix,campaign_public_id=campaign.campaign_public_id,owner_actor_public_id=actor.actor_public_id,class_code="merchant-trader",ship_name="Ignored")
                self.assertEqual(result.ship_public_id,replay.ship_public_id)
                self.assertTrue(replay.replayed)
                self.assertGreater(result.component_count,0)
                self.assertGreater(result.crew_position_count,0)
                self.assertGreater(result.resource_count,0)
                row=connection.execute("SELECT count(*),sum(share_basis_points) FROM ship_legal_interest WHERE ship_id=(SELECT ship_id FROM ship_ship WHERE public_id=%s)",(result.ship_public_id,)).fetchone()
                self.assertEqual(row,(1,10000))


if __name__ == "__main__": unittest.main()
