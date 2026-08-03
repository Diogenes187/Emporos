import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalDeviceCatalogueTests(unittest.TestCase):
    def test_catalogue_is_exact_and_omitted_mass_stays_null(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT device.device_code,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams,
                          device.catalogue_mass_is_unquantified
                   FROM inv_personal_device_definition device
                   JOIN inv_item_definition item
                     ON item.rule_id=device.item_rule_id
                   ORDER BY item.minimum_tech_level,device.device_code"""
            ).fetchall()
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0], ("magnetic-compass", 3, 10, None, True))
        self.assertIn(
            ("hand-computer-fixed", 11, 1000, 500, False), rows)
        self.assertEqual(rows[-1],
                         ("neural-activity-sensor", 15, 35000, 10000, False))

    def test_fixed_hand_computer_does_not_replace_scalable_family(self):
        with psycopg.connect(DSN) as connection:
            fixed = connection.execute(
                """SELECT count(*) FROM inv_personal_device_definition
                   WHERE device_code='hand-computer-fixed'""").fetchone()[0]
            scalable = connection.execute(
                """SELECT count(*) FROM inv_personal_computer_definition
                   WHERE computer_kind='hand-computer'""").fetchone()[0]
        self.assertEqual((fixed, scalable), (1, 8))


if __name__ == "__main__":
    unittest.main()
