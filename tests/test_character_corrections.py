import os,unittest,uuid
import psycopg
from engine.character_corrections import correct_character_state_command

class CharacterCorrectionTests(unittest.TestCase):
 def test_owner_corrections_are_audited_idempotent_and_typed(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    owner='correction-'+uuid.uuid4().hex
    campaign,cpub=c.execute("INSERT INTO camp_campaign(name,owner_reference) VALUES('Correction test',%s) RETURNING campaign_id,public_id",(owner,)).fetchone()
    actor,apub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Correctable',%s) RETURNING actor_id,public_id",(campaign,owner)).fetchone()
    c.execute("INSERT INTO actor_financial_state(actor_id,cash_credits) VALUES(%s,10)",(actor,))
    skill=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.bludgeoning-weapons'").fetchone()[0]
    characteristic=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.strength'").fetchone()[0]
    c.execute("INSERT INTO actor_characteristic VALUES(%s,%s,8,8)",(actor,characteristic))
    location_type=c.execute("SELECT location_type_rule_id FROM rule_location_type WHERE permits_actor_position ORDER BY location_type_rule_id LIMIT 1").fetchone()[0]
    location,lpub=c.execute("INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,'Correction Port') RETURNING location_id,public_id",(campaign,location_type)).fetchone()
    result=correct_character_state_command(c,initiator_reference=owner,idempotency_key='skill',actor_public_id=str(apub),correction_kind='skill',target_code='skill.bludgeoning-weapons',resulting_value=2,reason='Restore agreed training')
    replay=correct_character_state_command(c,initiator_reference=owner,idempotency_key='skill',actor_public_id=str(apub),correction_kind='skill',target_code='skill.bludgeoning-weapons',resulting_value=2,reason='Restore agreed training')
    self.assertEqual((result.prior_value,result.resulting_value,replay.replayed),(None,2,True))
    correct_character_state_command(c,initiator_reference=owner,idempotency_key='stat',actor_public_id=str(apub),correction_kind='characteristic',target_code='characteristic.strength',resulting_value=10,resulting_maximum=11,reason='Repair incorrect injury')
    correct_character_state_command(c,initiator_reference=owner,idempotency_key='cash',actor_public_id=str(apub),correction_kind='finance',target_code='cash_credits',resulting_value=500,reason='Restore missing award')
    correct_character_state_command(c,initiator_reference=owner,idempotency_key='location',actor_public_id=str(apub),correction_kind='location',location_public_id=str(lpub),reason='Place party at agreed port')
    self.assertEqual(c.execute('SELECT skill_level FROM actor_skill WHERE actor_id=%s AND skill_rule_id=%s',(actor,skill)).fetchone()[0],2)
    self.assertEqual(c.execute('SELECT current_value,maximum_value FROM actor_characteristic WHERE actor_id=%s AND characteristic_rule_id=%s',(actor,characteristic)).fetchone(),(10,11))
    self.assertEqual(c.execute('SELECT cash_credits FROM actor_financial_state WHERE actor_id=%s',(actor,)).fetchone()[0],500)
    self.assertEqual(c.execute("SELECT location_id FROM loc_actor_position WHERE actor_id=%s AND position_status='current'",(actor,)).fetchone()[0],location)
    self.assertEqual(c.execute('SELECT count(*) FROM cmd_character_correction_receipt WHERE actor_id=%s',(actor,)).fetchone()[0],4)
    with self.assertRaises(PermissionError):correct_character_state_command(c,initiator_reference='intruder',idempotency_key='denied',actor_public_id=str(apub),correction_kind='skill',target_code='skill.bludgeoning-weapons',resulting_value=3,reason='Not authorized')

if __name__=='__main__':unittest.main()
