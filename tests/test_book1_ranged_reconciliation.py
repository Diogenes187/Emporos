import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1RangedReconciliationTests(unittest.TestCase):
    def test_rate_of_fire_is_relational(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT rule.rule_code,profile.single_shot_rounds,
                          profile.burst_shot_rounds,
                          profile.automatic_fire_rounds
                   FROM rule_book1_ranged_weapon_fire_profile profile
                   JOIN rule_rule rule
                     ON rule.rule_id=profile.weapon_item_rule_id
                   WHERE rule.rule_code IN (
                     'equipment.weapon.submachinegun',
                     'equipment.weapon.gauss-rifle')
                   ORDER BY rule.rule_code"""
            ).fetchall()
            count = connection.execute(
                "SELECT count(*) FROM rule_book1_ranged_weapon_fire_profile"
            ).fetchone()[0]
        self.assertEqual(count,18)
        self.assertEqual(rows, [
            ("equipment.weapon.gauss-rifle",1,4,10),
            ("equipment.weapon.submachinegun",0,4,None),
        ])

    def test_snub_listing_has_two_capacity_variants(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT listing.source_listing_code,
                          listing.capacity_variant_rounds,
                          ammunition.cost_credits,ammunition.mass_grams
                   FROM rule_book1_ranged_ammunition_listing listing
                   JOIN inv_ammunition_definition ammunition
                     USING (ammunition_rule_id)
                   WHERE listing.source_listing_code='snub-pistol'
                   ORDER BY listing.capacity_variant_rounds"""
            ).fetchall()
            counts = connection.execute(
                """SELECT count(*),count(DISTINCT source_listing_code)
                   FROM rule_book1_ranged_ammunition_listing"""
            ).fetchone()
        self.assertEqual(counts,(19,18))
        self.assertEqual(rows,[
            ("snub-pistol",6,10,30),("snub-pistol",15,10,30)])


if __name__ == "__main__":
    unittest.main()
