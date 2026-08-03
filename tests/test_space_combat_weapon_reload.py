import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatWeaponReloadTests(unittest.TestCase):
 def test_rule_state_consumption_and_reload_are_relational(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT action_code,systems_per_action,requires_spent_system FROM rule_space_combat_weapon_reload").fetchone(),('reload-weapons',1,True))
   self.assertEqual(c.execute("SELECT count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='combat.space.reload-weapon-system'").fetchone()[0],2)
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_weapon_readiness_state','senc_weapon_ammunition_consumption_receipt','senc_weapon_reload_receipt')").fetchone()[0],3)
   consume=c.execute("SELECT pg_get_functiondef('senc_consume_mount_attack_ammunition()'::regprocedure)").fetchone()[0]
   self.assertIn("readiness_status<>'ready'",consume); self.assertIn("ship_resource_movement",consume)
   reload=c.execute("SELECT pg_get_functiondef('senc_apply_weapon_reload()'::regprocedure)").fetchone()[0]
   self.assertIn("action_row.action_code<>'reload-weapons'",reload); self.assertIn("state.readiness_status<>'spent'",reload)
   self.assertIn("reserve_quantity<state.ammunition_per_attack",reload)
   sand=c.execute("SELECT pg_get_functiondef('senc_spend_fire_sand_system()'::regprocedure)").fetchone()[0]
   self.assertIn("readiness_status='ready'",sand); self.assertIn("senc_fire_sand_ammo_receipt",sand)
if __name__=='__main__': unittest.main()
