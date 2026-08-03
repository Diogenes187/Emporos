import os,unittest
import psycopg

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatDamageTableTests(unittest.TestCase):
 def test_adjudicated_continuous_bands_and_locations(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   rows=c.execute("SELECT lower(damage_range),upper(damage_range),single_hit_groups,double_hit_groups,triple_hit_groups FROM rule_space_combat_damage_band WHERE damage_range @> 12 OR damage_range @> 13 OR damage_range @> 16 OR damage_range @> 17 OR damage_range @> 24 OR damage_range @> 25 ORDER BY display_order").fetchall()
   self.assertEqual(rows,[(9,13,0,1,0),(13,17,3,0,0),(17,21,2,1,0),(21,25,0,2,0),(25,29,0,0,1)])
   self.assertEqual(c.execute('SELECT count(*) FROM rule_space_combat_damage_band').fetchone()[0],12)
   self.assertEqual(c.execute('SELECT count(*) FROM rule_space_combat_hit_location').fetchone()[0],11)
   self.assertEqual(c.execute("SELECT external_vessel_location,internal_vessel_location,small_craft_location FROM rule_space_combat_hit_location WHERE roll_total=7").fetchone(),('armor','crew','armor'))
   self.assertEqual(c.execute("SELECT decision_register_entry FROM rule_interpretation i JOIN rule_rule r USING(rule_id) WHERE r.rule_code='combat.space.damage-bands'").fetchone()[0],'CE-SC-006')

if __name__=='__main__': unittest.main()
