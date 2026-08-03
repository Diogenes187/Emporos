import os
import unittest
import psycopg

DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")

@unittest.skipUnless(DSN,"BASE_CEPHEUS_DATABASE_URL is required")
class Book1GrenadeTests(unittest.TestCase):
 def test_catalogue_delivery_and_paired_provenance(self):
  with psycopg.connect(DSN) as connection:
   counts=connection.execute("""SELECT
    (SELECT count(*) FROM rule_book1_grenade),
    (SELECT count(*) FROM rule_book1_grenade_delivery_mode),
    (SELECT count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id)
      WHERE r.rule_code LIKE 'equipment.grenade.%')""").fetchone()
   rows=connection.execute("""SELECT grenade_code,minimum_tech_level,
    case_cost_credits,grenades_per_case,mass_grams_per_grenade,
    illegal_at_law_level FROM rule_book1_grenade ORDER BY grenade_code""").fetchall()
  self.assertEqual(counts,(4,8,8))
  self.assertEqual(rows,[("aerosol",9,90,6,500,1),("frag",6,180,6,500,1),
                         ("smoke",6,90,6,500,1),("stun",9,180,6,500,1)])

 def test_frag_smoke_aerosol_and_stun_are_exact(self):
  with psycopg.connect(DSN) as connection:
   frag=connection.execute("""SELECT maximum_distance_metres,damage_dice_count
    FROM rule_book1_frag_grenade_damage_band ORDER BY maximum_distance_metres""").fetchall()
   fields=connection.execute("""SELECT g.grenade_code,f.radius_metres,
    f.duration_dice_count,f.duration_die_sides,f.duration_multiplier_rounds,
    f.attack_modifier,f.laser_attack_modifier,f.laser_damage_reduction,
    f.blocks_normal_vision,f.blocks_laser_communications
    FROM rule_book1_grenade_field_effect f JOIN rule_book1_grenade g
      ON g.rule_id=f.grenade_rule_id ORDER BY g.grenade_code""").fetchall()
   stun=connection.execute("""SELECT radius_metres,stun_damage_dice_count,
    check_modifier_equals_post_armor_damage,failed_check_causes_unconsciousness,
    successful_check_ignores_stun_damage,inflicts_normal_damage
    FROM rule_book1_stun_grenade_effect""").fetchone()
  self.assertEqual(frag,[(3,5),(6,3),(9,1)])
  self.assertEqual(fields,[("aerosol",6,1,6,3,None,None,10,False,True),
                           ("smoke",6,1,6,3,-2,-4,None,True,False)])
  self.assertEqual(stun,(6,3,True,True,True,False))

if __name__=="__main__": unittest.main()
