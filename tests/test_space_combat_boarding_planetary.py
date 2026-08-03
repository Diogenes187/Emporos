import os,unittest
import psycopg
@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class BoardingPlanetaryTests(unittest.TestCase):
 def test_rules_runtime_and_provenance_are_relational(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   self.assertEqual(c.execute("SELECT exceptional_effect_minimum,success_next_check_dm,success_internal_single_hits,exceptional_internal_damage_dice,control_delay_turns,requires_docked_range FROM rule_space_combat_abstract_boarding").fetchone(),(6,2,1,2,1,True))
   self.assertEqual(c.execute("SELECT count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code IN('combat.space.abstract-boarding','combat.space.planetary-maneuvers')").fetchone()[0],4)
   self.assertEqual(c.execute("SELECT maneuver_code,success_state,failure_state FROM rule_space_combat_planetary_maneuver ORDER BY maneuver_code").fetchall(),[('atmospheric-entry','atmosphere','orbit'),('orbital-insertion','orbit','decaying-orbit')])
   self.assertEqual(c.execute("SELECT modifier_code,modifier,automatic_success FROM rule_space_combat_atmospheric_entry_modifier ORDER BY display_order").fetchall(),[('size-large',-2,False),('size-small',2,False),('atmosphere-trace-or-none',None,True),('atmosphere-thin',2,False),('atmosphere-low',-2,False),('atmosphere-dense',-2,False),('atmosphere-ellipsoid',2,False)])
   self.assertEqual(c.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_boarding_operation','senc_boarding_round_receipt','senc_boarding_internal_damage_die','senc_boarding_internal_damage_receipt','senc_boarding_reaction_denial','senc_boarding_damage_location_group_roll','senc_boarding_damage_location_hit_receipt','senc_vessel_planetary_state','senc_planetary_maneuver_receipt')").fetchone()[0],9)
   self.assertIn('decaying-orbit',c.execute("SELECT pg_get_functiondef('senc_validate_planetary_maneuver()'::regprocedure)").fetchone()[0])
   self.assertIn('internal_vessel_location',c.execute("SELECT pg_get_functiondef('senc_apply_next_boarding_location_hit(bigint)'::regprocedure)").fetchone()[0])
if __name__=='__main__': unittest.main()
