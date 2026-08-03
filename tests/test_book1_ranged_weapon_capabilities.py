import os
import unittest
import psycopg

DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN,"BASE_CEPHEUS_DATABASE_URL is required")
class Book1RangedCapabilityTests(unittest.TestCase):
    def test_zero_g_power_and_detector_capabilities(self):
        with psycopg.connect(DSN) as c:
            counts=c.execute(
                """SELECT count(*),
                  count(*) FILTER (WHERE designed_for_zero_gravity),
                  count(*) FILTER (WHERE uses_external_power_pack),
                  count(*) FILTER (WHERE evades_most_weapon_detectors)
                  FROM rule_book1_ranged_weapon_capability""").fetchone()
        self.assertEqual(counts,(18,2,3,1))

    def test_crossbow_and_revolver_reload_rules(self):
        with psycopg.connect(DSN) as c:
            crossbow=c.execute(
                """SELECT minimum_tech_level,reload_minor_actions,self_loading
                   FROM rule_book1_crossbow_reload_profile
                   ORDER BY minimum_tech_level""").fetchall()
            revolver=c.execute(
                """SELECT normal_reload_combat_rounds,
                          expedited_reload_combat_rounds,
                          expedited_reload_forfeits_evasion
                   FROM rule_book1_revolver_reload_choice""").fetchone()
        self.assertEqual(crossbow,[(2,6,False),(4,3,False),(9,None,True)])
        self.assertEqual(revolver,(2,1,True))

    def test_mode_switch_and_compatibility_boundaries(self):
        with psycopg.connect(DSN) as c:
            switch=c.execute(
                """SELECT switch_timing,alternate_mode_attack_profile_code,
                          alternate_single_shot_rounds
                   FROM rule_book1_ranged_mode_switch""").fetchone()
            compatibility=c.execute(
                """SELECT ammunition_interchangeable,
                          magazines_interchangeable,count(*)
                   FROM rule_book1_ammunition_compatibility
                   GROUP BY ammunition_interchangeable,
                            magazines_interchangeable
                   ORDER BY ammunition_interchangeable,
                            magazines_interchangeable""").fetchall()
        self.assertEqual(switch,
            ("end-of-round-after-all-firing","rifle",1))
        self.assertEqual(compatibility,[(False,False,1),(True,False,1),
                                        (True,True,1)])


if __name__=="__main__":
    unittest.main()
