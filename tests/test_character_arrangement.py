import os,unittest,uuid,psycopg
from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.character_arrangement import arrange_characteristics_command

class FixedRandom:
 def __init__(self):self.value=0
 def randint(self,lower,upper):self.value+=1;return min(self.value,upper)

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class CharacterArrangementTests(unittest.TestCase):
 def test_precareer_rolls_are_permuted_once_and_replay(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    suffix=str(uuid.uuid4());owner='arrange-'+suffix
    campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='c-'+suffix,name='Arrange Test')
    actor=initialize_character_command(c,initiator_reference=owner,idempotency_key='a-'+suffix,campaign_public_id=campaign.campaign_public_id,character_name='Unnamed Traveller',random_source=FixedRandom())
    codes=tuple(row[0] for row in c.execute("SELECT rule.rule_code FROM actor_characteristic score JOIN rule_characteristic definition ON definition.rule_id=score.characteristic_rule_id JOIN rule_rule rule ON rule.rule_id=definition.rule_id WHERE score.actor_id=(SELECT actor_id FROM actor_actor WHERE public_id=%s) ORDER BY definition.display_order",(actor.actor_public_id,)).fetchall())
    before=tuple(row[0] for row in c.execute("SELECT current_value FROM actor_characteristic score JOIN rule_characteristic definition ON definition.rule_id=score.characteristic_rule_id WHERE actor_id=(SELECT actor_id FROM actor_actor WHERE public_id=%s) ORDER BY definition.display_order",(actor.actor_public_id,)).fetchall())
    result=arrange_characteristics_command(c,initiator_reference=owner,idempotency_key='r-'+suffix,actor_public_id=actor.actor_public_id,source_characteristic_codes=tuple(reversed(codes)))
    after=tuple(row[0] for row in c.execute("SELECT current_value FROM actor_characteristic score JOIN rule_characteristic definition ON definition.rule_id=score.characteristic_rule_id WHERE actor_id=(SELECT actor_id FROM actor_actor WHERE public_id=%s) ORDER BY definition.display_order",(actor.actor_public_id,)).fetchall())
    self.assertEqual(after,tuple(reversed(before)));self.assertFalse(result.replayed)
    replay=arrange_characteristics_command(c,initiator_reference=owner,idempotency_key='r-'+suffix,actor_public_id=actor.actor_public_id,source_characteristic_codes=codes)
    self.assertTrue(replay.replayed);self.assertEqual(replay.scores,result.scores)
if __name__=='__main__':unittest.main()
