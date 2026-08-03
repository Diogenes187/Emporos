import os,unittest
import psycopg

@unittest.skipUnless(os.environ.get('BASE_CEPHEUS_DATABASE_URL'),'requires PostgreSQL')
class SpaceCombatAttackRangeTests(unittest.TestCase):
 def test_published_matrix_and_weapon_profiles(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   rows=c.execute("SELECT weapon_profile_code,count(*),count(*) FILTER(WHERE available) FROM rule_space_combat_attack_range GROUP BY weapon_profile_code ORDER BY weapon_profile_code").fetchall()
   self.assertEqual(rows,[('beam-laser',7,7),('fusion-gun',7,7),('meson-gun',7,7),('particle-beam',7,7),('pulse-laser',7,6),('sandcaster',7,3)])
   samples=c.execute("SELECT range.weapon_profile_code,range.range_band_code,difficulty.name,range.available FROM rule_space_combat_attack_range range LEFT JOIN rule_rule difficulty ON difficulty.rule_id=range.difficulty_rule_id WHERE (range.weapon_profile_code,range.range_band_code) IN (('pulse-laser','short'),('pulse-laser','distant'),('meson-gun','adjacent'),('sandcaster','adjacent')) ORDER BY range.weapon_profile_code,range.range_band_code").fetchall()
   self.assertEqual(samples,[('meson-gun','adjacent','Very Difficult',True),('pulse-laser','distant',None,False),('pulse-laser','short','Average',True),('sandcaster','adjacent','Routine',True)])
   self.assertEqual(c.execute('SELECT count(*) FROM rule_space_combat_weapon_profile').fetchone()[0],9)
   self.assertEqual(c.execute("SELECT count(*) FROM rule_space_combat_weapon_profile WHERE weapon_profile_code='missile' AND uses_special_attack_procedure").fetchone()[0],2)

if __name__=='__main__': unittest.main()
