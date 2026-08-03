import os,unittest
import psycopg
DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")
@unittest.skipUnless(DSN,"BASE_CEPHEUS_DATABASE_URL is required")
class HeavyCapabilityTests(unittest.TestCase):
 def test_five_capabilities_are_exact(self):
  with psycopg.connect(DSN) as c:
   rows=c.execute("""SELECT w.weapon_code,x.minimum_strength,
    x.attack_modifier_per_strength_shortfall,x.reload_minor_actions,
    x.handheld_grenades_interchangeable,x.has_gravity_suspension
    FROM rule_book1_heavy_weapon_capability x JOIN rule_book1_heavy_weapon w
    ON w.rule_id=x.weapon_rule_id ORDER BY w.weapon_code""").fetchall()
  self.assertEqual(rows,[("fgmp",9,None,None,None,True),
   ("grenade-launcher",None,None,None,False,False),
   ("pgmp",12,-1,None,None,False),
   ("ram-grenade-launcher",None,None,2,False,False),
   ("rocket-launcher",None,None,3,None,False)])
 def test_fgmp_and_rocket_boundaries(self):
  with psycopg.connect(DSN) as c:
   fgmp=c.execute("""SELECT radiation_dice_count,radiation_die_sides,
    radiation_multiplier_rads,radiation_affects_unprotected,
    radiation_radius_is_unquantified FROM rule_book1_heavy_weapon_capability x
    JOIN rule_book1_heavy_weapon w ON w.rule_id=x.weapon_rule_id
    WHERE w.weapon_code='fgmp'""").fetchone()
   rocket=c.execute("""SELECT backblast_distance_metres,backblast_damage_dice,
    vehicle_mount_removes_backblast FROM rule_book1_heavy_weapon_capability x
    JOIN rule_book1_heavy_weapon w ON w.rule_id=x.weapon_rule_id
    WHERE w.weapon_code='rocket-launcher'""").fetchone()
   impact=c.execute("""SELECT effect_added_to_damage,blast_radius_metres,
    miss_detonation_die_sides,miss_detonation_minimum_roll,
    miss_detonation_distance_base_metres,
    miss_detonation_distance_effect_coefficient,miss_direction_random,
    failed_detonation_leaves_battlefield FROM rule_book1_rocket_impact""").fetchone()
  self.assertEqual(fgmp,(2,6,20,True,True))
  self.assertEqual(rocket,(1.5,3,True))
  self.assertEqual(impact,(False,6,6,4,6,-1,True,True))
if __name__=="__main__":unittest.main()
