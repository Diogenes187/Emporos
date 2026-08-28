import os,unittest,uuid
import psycopg
from engine.campaigns import create_campaign_command
from engine.adventure_modules import create_adventure_module_command,key_adventure_location_command,enter_adventure_location_command,update_adventure_location_state_command,advance_adventure_exploration_command,adventure_module_snapshot

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class AdventureModuleTests(unittest.TestCase):
 def test_key_state_guard_clock_replay_and_isolation(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    owner='module-'+str(uuid.uuid4());other='other-'+str(uuid.uuid4())
    campaign=create_campaign_command(c,initiator_reference=owner,idempotency_key='campaign-'+str(uuid.uuid4()),name='Module Test',play_mode='human_refereed')
    module_key='module-'+str(uuid.uuid4())
    module=create_adventure_module_command(c,initiator_reference=owner,idempotency_key=module_key,campaign_public_id=campaign.campaign_public_id,name='Derelict Test')
    replay=create_adventure_module_command(c,initiator_reference=owner,idempotency_key=module_key,campaign_public_id=campaign.campaign_public_id,name='Ignored')
    self.assertTrue(replay.replayed);self.assertEqual(module.module_public_id,replay.module_public_id)
    location=key_adventure_location_command(c,initiator_reference=owner,idempotency_key='key-'+str(uuid.uuid4()),module_public_id=module.module_public_id,location_key='A1',name='Airlock',keyed_description='Four corsairs guard a sealed cargo case.',occupants_initial='Four corsairs',treasure_initial='Sealed cargo case')
    enter_adventure_location_command(c,initiator_reference=owner,idempotency_key='enter-'+str(uuid.uuid4()),location_public_id=location.location_public_id)
    update_adventure_location_state_command(c,initiator_reference=owner,idempotency_key='state-'+str(uuid.uuid4()),location_public_id=location.location_public_id,occupant_status='dead',treasure_status='taken',alert_status='alerted',current_note='Hull breach alarms are sounding.')
    advanced=advance_adventure_exploration_command(c,initiator_reference=owner,idempotency_key='clock-'+str(uuid.uuid4()),module_public_id=module.module_public_id,turns=6)
    self.assertEqual(advanced.result_code,'1_wander_checks_due')
    snapshot=adventure_module_snapshot(c,initiator_reference=owner,module_public_id=module.module_public_id)
    self.assertEqual(snapshot['current_location']['key'],'A1');self.assertEqual(snapshot['elapsed_minutes'],60)
    warning=snapshot['locations'][0]['contradiction_warning']
    self.assertIn('DEAD',warning);self.assertIn('TAKEN',warning);self.assertIn('ALERTED',warning)
    with self.assertRaises(PermissionError):adventure_module_snapshot(c,initiator_reference=other,module_public_id=module.module_public_id)

if __name__=='__main__':unittest.main()
