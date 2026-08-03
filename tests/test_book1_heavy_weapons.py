import os,unittest
import psycopg
DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")
@unittest.skipUnless(DSN,"BASE_CEPHEUS_DATABASE_URL is required")
class Book1HeavyWeaponTests(unittest.TestCase):
 def test_catalogues_and_provenance(self):
  with psycopg.connect(DSN) as c:
   counts=c.execute("""SELECT
    (SELECT count(*) FROM rule_book1_heavy_weapon),
    (SELECT count(*) FROM rule_book1_heavy_weapon_fire_profile),
    (SELECT count(*) FROM rule_book1_heavy_ammunition),
    (SELECT count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id)
      WHERE r.rule_code LIKE 'equipment.heavy-weapon.%'
         OR r.rule_code LIKE 'equipment.heavy-ammunition.%')""").fetchone()
   launchers=c.execute("""SELECT weapon_code,damage_basis,damage_dice_count
    FROM rule_book1_heavy_weapon WHERE weapon_code LIKE '%launcher'
    ORDER BY weapon_code""").fetchall()
  self.assertEqual(counts,(5,5,5,20))
  self.assertEqual(launchers,[("grenade-launcher","selected-grenade",None),
   ("ram-grenade-launcher","selected-grenade",None),
   ("rocket-launcher","fixed-dice",4)])
 def test_exact_direct_fire_and_ammunition(self):
  with psycopg.connect(DSN) as c:
   weapons=c.execute("""SELECT weapon_code,minimum_tech_level,cost_credits,
    mass_grams,damage_dice_count,has_recoil,illegal_at_law_level
    FROM rule_book1_heavy_weapon WHERE weapon_code IN ('pgmp','fgmp')
    ORDER BY weapon_code""").fetchall()
   ammo=c.execute("""SELECT ammunition_code,cost_credits,mass_grams,capacity_rounds
    FROM rule_book1_heavy_ammunition ORDER BY ammunition_code""").fetchall()
  self.assertEqual(weapons,[("fgmp",14,100000,12000,16,True,2),
                            ("pgmp",12,20000,10000,10,True,2)])
  self.assertEqual(ammo,[("fgmp",65000,9000,40),("grenade-launcher",180,500,6),
   ("pgmp",2500,6000,40),("ram-grenade-launcher",180,500,6),
   ("rocket-launcher",300,1000,1)])
if __name__=="__main__":unittest.main()
