import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command


class FixedRandom:
    def __init__(self,values): self.values=iter(values)
    def randint(self,minimum,maximum): return next(self.values)


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"),"requires PostgreSQL")
class CharacterInitializationTests(unittest.TestCase):
    def test_initialization_records_characteristics_dice_event_and_replay(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix=str(uuid.uuid4())
                campaign=create_campaign_command(connection,initiator_reference="character-test",idempotency_key="campaign-"+suffix,name="Character Test")
                result=initialize_character_command(connection,initiator_reference="character-test",idempotency_key="actor-"+suffix,campaign_public_id=campaign.campaign_public_id,character_name="  Elara Venn  ",random_source=FixedRandom([1,2,2,3,3,4,4,5,5,6,6,1]))
                replay=initialize_character_command(connection,initiator_reference="character-test",idempotency_key="actor-"+suffix,campaign_public_id=campaign.campaign_public_id,character_name="Ignored")
                self.assertEqual(result.character_name,"Elara Venn")
                self.assertEqual([item.score for item in result.characteristics],[3,5,7,9,11,7])
                self.assertEqual(result.characteristics[0].dice,(1,2))
                self.assertEqual(result.actor_public_id,replay.actor_public_id)
                self.assertTrue(replay.replayed)
                self.assertEqual(connection.execute("SELECT count(*) FROM cmd_random_draw WHERE command_id=(SELECT command_id FROM cmd_command WHERE public_id=%s)",(result.command_public_id,)).fetchone()[0],12)


if __name__ == "__main__": unittest.main()
