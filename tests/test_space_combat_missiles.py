import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatMissileTests(unittest.TestCase):
 def test_launch_rules_and_runtime_are_relational(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT range_band_code,turns_to_impact FROM rule_space_combat_missile_range WHERE launch_available ORDER BY range_band_code").fetchall(),[('distant',2),('long',1),('medium',1),('short',1),('very_long',2)])
   self.assertEqual(c.execute("SELECT impact_target_number FROM rule_space_combat_missile_launch_effect ORDER BY display_order").fetchall(),[(11,),(10,),(8,),(7,),(6,)])
   self.assertEqual(c.execute("SELECT thrust,endurance_turns,smart_fixed_target,smart_repeats_after_miss,reactions_wait_until_arrival FROM rule_space_combat_missile_behavior").fetchone(),(10,4,8,True,True))
   self.assertEqual(c.execute("SELECT count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='combat.space.missile-flight'").fetchone()[0],2)
   definition=c.execute("SELECT pg_get_functiondef('senc_validate_missile_launch_receipt()'::regprocedure)").fetchone()[0]
   self.assertIn("band.effect_range @> attack.effect",definition); self.assertIn("weapon.ammunition_per_attack",definition)
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_missile_impact_attempt','senc_missile_impact_roll','senc_missile_impact_final_receipt')").fetchone()[0],3)
   final=c.execute("SELECT pg_get_functiondef('senc_finalize_missile_impact()'::regprocedure)").fetchone()[0]
   self.assertIn("attempt.smart_missiles",final); self.assertIn("attempt.endurance_expires_after_round",final)
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_missile_arrival_receipt','senc_missile_arrival_close_receipt')").fetchone()[0],2)
   reaction=c.execute("SELECT pg_get_functiondef('senc_validate_reaction_budget()'::regprocedure)").fetchone()[0]
   self.assertIn('triggering_missile_arrival_id',reaction)
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_missile_damage_attempt','senc_missile_damage_die','senc_missile_damage_final_receipt','senc_missile_damage_location_group_roll','senc_missile_damage_location_hit_receipt','senc_nuclear_missile_radiation_hit_receipt')").fetchone()[0],6)
   damage=c.execute("SELECT pg_get_functiondef('senc_validate_missile_damage_final()'::regprocedure)").fetchone()[0]
   self.assertIn('greatest(0,total-a.armor_snapshot)',damage)
   apply_hit=c.execute("SELECT pg_get_functiondef('senc_apply_next_missile_location_hit(bigint,smallint)'::regprocedure)").fetchone()[0]
   self.assertIn('senc_ship_system_damage_state',apply_hit)
   radiation=c.execute("SELECT pg_get_functiondef('senc_validate_nuclear_missile_radiation()'::regprocedure)").fetchone()[0]
   self.assertIn('NEW.armor_dm<>-a.armor_snapshot',radiation)
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_missile_crew_hit_receipt','senc_missile_crew_population','senc_missile_crew_population_receipt','senc_missile_crew_target','senc_missile_crew_target_receipt','senc_missile_crew_consequence_die','senc_missile_crew_consequence_receipt','senc_missile_crew_application_receipt')").fetchone()[0],8)
   application=c.execute("SELECT pg_get_functiondef('senc_apply_missile_crew_consequence()'::regprocedure)").fetchone()[0]
   self.assertIn('health_damage_instance',application); self.assertIn('actor_radiation_state',application)
if __name__=='__main__': unittest.main()
