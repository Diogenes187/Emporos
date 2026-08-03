import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1VehicleCatalogueTests(unittest.TestCase):
    def test_profiles_link_without_overwriting_vds(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),count(vehicle_class_rule_id),
                          count(*) FILTER (
                              WHERE source_speed_unit_is_unquantified)
                   FROM rule_book1_vehicle_profile"""
            ).fetchone()
            air_raft = connection.execute(
                """SELECT book.minimum_tech_level,book.maximum_speed,
                          book.cost_credits,vds.minimum_tech_level,
                          vds.construction_cost_minor
                   FROM rule_book1_vehicle_profile book
                   JOIN vehicle_class vds
                     ON vds.vehicle_class_rule_id=book.vehicle_class_rule_id
                   WHERE book.profile_code='air-raft'"""
            ).fetchone()
        self.assertEqual(row, (16, 15, 1))
        self.assertEqual(air_raft[0:3], (8, 400, 275000))
        self.assertNotEqual(air_raft[0], air_raft[3])

    def test_occupancy_and_weapons_are_relational(self):
        with psycopg.connect(DSN) as connection:
            occupancy = connection.execute(
                "SELECT count(*) FROM rule_book1_vehicle_occupancy"
            ).fetchone()[0]
            weapons = connection.execute(
                """SELECT profile.profile_code,summary.weapon_code,
                          summary.mount_code,summary.weapon_count
                   FROM rule_book1_vehicle_weapon_summary summary
                   JOIN rule_book1_vehicle_profile profile
                     ON profile.rule_id=summary.vehicle_profile_rule_id
                   WHERE summary.weapon_code<>'none'
                   ORDER BY profile.profile_code"""
            ).fetchall()
        self.assertEqual(occupancy, 32)
        self.assertEqual(weapons, [
            ("afv", "triple-laser", "turret", 3),
            ("g-carrier", "fusion-gun", "turret", 1),
        ])

    def test_paired_provenance_covers_catalogue_and_profiles(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT count(*),count(*) FILTER (WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.book1-vehicles'
                      OR (rule.rule_code LIKE 'vehicle.book1.%'
                          AND rule.rule_code NOT LIKE
                              'vehicle.book1.option.%')"""
            ).fetchone()
        self.assertEqual(row, (34, 17, 17))


if __name__ == "__main__":
    unittest.main()
