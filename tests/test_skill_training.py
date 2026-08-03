import os, unittest, uuid
import psycopg
from engine.skill_training import allocate_skill_training_week_command

class SkillTrainingTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): cls.dsn=os.environ['BASE_CEPHEUS_DATABASE_URL']
 def actor(self,c,controller='trainer'):
  campaign=c.execute("INSERT INTO camp_campaign(name) VALUES (%s) RETURNING campaign_id",(f'Train {uuid.uuid4()}',)).fetchone()[0]
  actor=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES (%s,'Student',%s) RETURNING actor_id,public_id",(campaign,controller)).fetchone()
  return campaign,actor
 def test_new_level_zero_requires_one_week_and_receipt_is_immutable(self):
  with psycopg.connect(self.dsn) as c:
   key=f'new-zero-{uuid.uuid4()}'
   campaign,(aid,pub)=self.actor(c);c.commit()
   r=allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=key,actor_public_id=str(pub),skill_rule_code='skill.mechanics')
   self.assertEqual((r.completed_weeks,r.required_weeks,r.skill_level_after),(1,1,0))
   replay=allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=key,actor_public_id=str(pub),skill_rule_code='skill.mechanics');self.assertTrue(replay.replayed)
   with self.assertRaises(psycopg.Error):
    with c.transaction():c.execute("DELETE FROM cmd_skill_training_week_receipt WHERE command_id=(SELECT command_id FROM cmd_command WHERE idempotency_key=%s AND initiator_reference='trainer')",(key,))
 def test_formula_week_exclusivity_and_jot_prohibition(self):
  with psycopg.connect(self.dsn) as c:
   suffix=str(uuid.uuid4())
   campaign,(aid,pub)=self.actor(c)
   mechanics=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='skill.mechanics'").fetchone()[0]
   c.execute("INSERT INTO actor_skill VALUES (%s,%s,1)",(aid,mechanics));c.commit()
   first=allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=f'm1-{suffix}',actor_public_id=str(pub),skill_rule_code='skill.mechanics')
   self.assertEqual(first.required_weeks,3)
   with self.assertRaises(ValueError):allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=f'same-week-{suffix}',actor_public_id=str(pub),skill_rule_code='skill.mechanics')
   c.execute("UPDATE camp_clock SET day_number=day_number+7 WHERE campaign_id=%s",(campaign,));c.commit()
   second=allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=f'm2-{suffix}',actor_public_id=str(pub),skill_rule_code='skill.mechanics');self.assertIsNone(second.skill_level_after)
   c.execute("UPDATE camp_clock SET day_number=day_number+7 WHERE campaign_id=%s",(campaign,));c.commit()
   third=allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=f'm3-{suffix}',actor_public_id=str(pub),skill_rule_code='skill.mechanics');self.assertEqual(third.skill_level_after,2)
   with self.assertRaises(ValueError):allocate_skill_training_week_command(c,initiator_reference='trainer',idempotency_key=f'jot-{suffix}',actor_public_id=str(pub),skill_rule_code='skill.jack-of-all-trades')
