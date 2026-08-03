import os,unittest,psycopg
from psycopg.errors import RaiseException
from engine.combat_resolution_runtime import resolve_personal_combat_command
from tests import test_combat_runtime as combat_tests
DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")
@unittest.skipUnless(DSN,"requires PostgreSQL")
class PersonalCombatResolutionTests(unittest.TestCase):
 def test_aware_unseen_side_may_avoid_and_finalize(self):
  with psycopg.connect(DSN) as c:
   with c.transaction(force_rollback=True):
    encounter,_=combat_tests.PersonalCombatRuntimeIntegrationTests()._initialized_combat(c)
    result=resolve_personal_combat_command(c,initiator_reference="player",referee_reference="referee",idempotency_key="avoid",encounter_public_id=encounter,outcome_kind="avoided",resolution_summary="The aware party withdraws unseen.",avoiding_side_code="party",opposing_side_code="opposition")
    self.assertEqual(result.outcome_kind,"avoided")
    state=c.execute("""SELECT e.encounter_status,pc.combat_status,r.finalized FROM enc_encounter e JOIN enc_personal_combat pc USING(encounter_id) JOIN enc_resolution r USING(encounter_id) WHERE e.public_id=%s""",(encounter,)).fetchone()
    self.assertEqual(state,("resolved","completed",True))
    command_id=c.execute("SELECT command_id FROM cmd_command WHERE public_id=%s",(result.command_public_id,)).fetchone()[0]
    with self.assertRaises(RaiseException):
     with c.transaction():c.execute("UPDATE cmd_personal_combat_resolution_receipt SET resolution_summary='changed' WHERE command_id=%s",(command_id,))
 def test_unaware_side_cannot_claim_avoidance(self):
  with psycopg.connect(DSN) as c:
   with c.transaction(force_rollback=True):
    encounter,_=combat_tests.PersonalCombatRuntimeIntegrationTests()._initialized_combat(c)
    with self.assertRaises(PermissionError):resolve_personal_combat_command(c,initiator_reference="referee",referee_reference="referee",idempotency_key="bad-avoid",encounter_public_id=encounter,outcome_kind="avoided",resolution_summary="Opposition tries to leave.",avoiding_side_code="opposition",opposing_side_code="party")
if __name__=="__main__":unittest.main()
