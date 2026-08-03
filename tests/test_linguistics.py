import os,unittest,uuid
import psycopg
from engine.linguistics import assign_actor_language_command,decipher_preserved_language_command
class R:
 def randint(self,a,b):return 4
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class LinguisticsTests(unittest.TestCase):
 def test_native_is_free_and_additional_languages_are_level_bounded(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    camp=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES(%s,'p') RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Speaker','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("INSERT INTO camp_language(campaign_id,language_code,name) VALUES(%s,'anglic','Anglic'),(%s,'vilani','Vilani'),(%s,'zdetl','Zdetl')",(camp,camp,camp));native=assign_actor_language_command(c,initiator_reference='p',idempotency_key='native',actor_public_id=str(pub),language_code='anglic',proficiency_kind='native');self.assertEqual((native.can_speak,native.can_read,native.can_write),(True,True,False));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.linguistics'",(aid,));extra=assign_actor_language_command(c,initiator_reference='p',idempotency_key='extra',actor_public_id=str(pub),language_code='vilani',proficiency_kind='additional');self.assertEqual((extra.can_speak,extra.can_read,extra.can_write),(False,True,True))
    with self.assertRaises(psycopg.Error):
     with c.transaction():assign_actor_language_command(c,initiator_reference='p',idempotency_key='too-many',actor_public_id=str(pub),language_code='zdetl',proficiency_kind='additional')
    replay=assign_actor_language_command(c,initiator_reference='p',idempotency_key='extra',actor_public_id=str(pub),language_code='zdetl',proficiency_kind='additional');self.assertTrue(replay.replayed);self.assertEqual(replay.language_code,'vilani');c.execute("INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.education'",(aid,));decoded=decipher_preserved_language_command(c,initiator_reference='p',idempotency_key='decode',actor_public_id=str(pub),specimen_reference='vault inscription',specimen_medium='inscription',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average',language_code='zdetl',random_source=R());self.assertTrue(decoded.general_meaning_recovered);self.assertEqual(decoded.check_total,9)
