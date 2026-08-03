import os,unittest
import psycopg
from psycopg.errors import RaiseException
DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")
@unittest.skipUnless(DSN,"BASE_CEPHEUS_DATABASE_URL is required")
class PsionicTrainingTests(unittest.TestCase):
 def test_rule_and_immutable_eligible_sequence(self):
  with psycopg.connect(DSN) as c:
   rule=c.execute("SELECT * FROM rule_psionic_training").fetchone()
   campaign=c.execute("INSERT INTO camp_campaign(name) VALUES ('Psi training') RETURNING campaign_id").fetchone()[0]
   actor=c.execute("""INSERT INTO actor_actor(campaign_id,name,controller_reference)
    VALUES (%s,'Student','player') RETURNING actor_id""",(campaign,)).fetchone()[0]
   determination=c.execute("""INSERT INTO cmd_psionic_strength_determination_receipt
    (idempotency_key,actor_id,career_terms_served,die_one,die_two,
     raw_psionic_strength,eligible_for_training)
    VALUES (%s,%s,0,4,3,7,true) RETURNING receipt_id""",
    (f"psi-det-{actor}",actor)).fetchone()[0]
   training=c.execute("""INSERT INTO camp_psionic_training
    (actor_id,determination_receipt_id,training_months,paid_credits,training_status)
    VALUES (%s,%s,4,100000,'active') RETURNING training_id""",
    (actor,determination)).fetchone()[0]
   talent,learning=c.execute("""SELECT talent_rule_id,learning_modifier
    FROM psi_talent ORDER BY display_order LIMIT 1""").fetchone()
   receipt=c.execute("""INSERT INTO cmd_psionic_talent_learning_receipt
    (idempotency_key,training_id,talent_rule_id,attempt_number,
     psionic_strength_value,characteristic_modifier,talent_learning_modifier,
     prior_attempt_modifier,die_one,die_two,check_total,target_number,
     succeeded,learned_level)
    VALUES (%s,%s,%s,1,7,0,%s,0,4,4,%s,8,true,0) RETURNING receipt_id""",
    (f"psi-learn-{actor}",training,talent,learning,8+learning)).fetchone()[0]
   with self.assertRaises(RaiseException):
    with c.transaction():
     c.execute("DELETE FROM cmd_psionic_talent_learning_receipt WHERE receipt_id=%s",(receipt,))
  self.assertEqual(tuple(rule[1:]),(2,6,-1,4,100000,8,-1,0,True))
 def test_false_term_snapshot_is_rejected(self):
  with psycopg.connect(DSN) as c:
   campaign=c.execute("INSERT INTO camp_campaign(name) VALUES ('Psi invalid') RETURNING campaign_id").fetchone()[0]
   actor=c.execute("""INSERT INTO actor_actor(campaign_id,name,controller_reference)
    VALUES (%s,'Invalid','player') RETURNING actor_id""",(campaign,)).fetchone()[0]
   with self.assertRaises(RaiseException):
    with c.transaction():
     c.execute("""INSERT INTO cmd_psionic_strength_determination_receipt
      (idempotency_key,actor_id,career_terms_served,die_one,die_two,
       raw_psionic_strength,eligible_for_training)
      VALUES (%s,%s,1,3,3,5,true)""",(f"bad-psi-{actor}",actor))
if __name__=="__main__":unittest.main()
