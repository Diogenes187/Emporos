import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalShelterTests(unittest.TestCase):
    def test_catalogue_and_paired_provenance_are_exact(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT shelter.shelter_code,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams
                   FROM inv_personal_shelter_definition shelter
                   JOIN inv_item_definition item
                     ON item.rule_id=shelter.item_rule_id
                   ORDER BY item.minimum_tech_level,shelter.shelter_code"""
            ).fetchall()
            provenance = connection.execute(
                """SELECT count(*),count(*) FILTER (WHERE is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.personal-shelters'
                      OR rule.rule_code LIKE 'equipment.shelter.%'"""
            ).fetchone()
        self.assertEqual(rows, [
            ("tarpaulin", 1, 10, 2000),
            ("tent", 2, 200, 3000),
            ("pre-fabricated-cabin", 6, 10000, 4000000),
            ("basic-life-support-supplies", 7, 100, 2000),
            ("pressure-tent", 7, 2000, 25000),
            ("advanced-base", 8, 50000, 6000000),
        ])
        self.assertEqual(provenance, (14, 7, 7))

    def test_pressure_weather_temperature_and_life_support_are_typed(self):
        with psycopg.connect(DSN) as connection:
            rows = {
                row[0]: row[1:]
                for row in connection.execute(
                """SELECT shelter.shelter_code,
                          capability.person_capacity,
                          capability.pressurization_code,
                          capability.wind_resistance_code,
                          capability.temperature_protection_code,
                          capability.minimum_temperature_celsius,
                          capability.included_life_support_person_days,
                          capability.supplied_life_support_person_days,
                          capability.has_airlock,
                          capability.depressurize_to_enter_or_leave
                   FROM rule_personal_shelter_capability capability
                   JOIN inv_personal_shelter_definition shelter
                     ON shelter.item_rule_id=capability.shelter_rule_id"""
                ).fetchall()
            }
        self.assertEqual(
            tuple(rows["advanced-base"]),
            (6, "pressurized-standard", "below-hurricane",
             "all-but-most-extreme", None, 42, None, None, None))
        self.assertEqual(
            tuple(rows["pressure-tent"]),
            (2, "pressurized-standard", "up-to-strong", "not-stated",
             None, None, None, False, True))
        self.assertEqual(
            tuple(rows["basic-life-support-supplies"]),
            (None, "not-applicable", "not-stated", "not-stated",
             None, None, 1, None, None))

    def test_modular_geometry_and_tarpaulin_dimensions_are_exact(self):
        with psycopg.connect(DSN) as connection:
            modules = connection.execute(
                """SELECT shelter.shelter_code,geometry.module_count,
                          geometry.module_width_metres,
                          geometry.module_length_metres,
                          geometry.module_height_metres
                   FROM rule_personal_modular_shelter_geometry geometry
                   JOIN inv_personal_shelter_definition shelter
                     ON shelter.item_rule_id=geometry.shelter_rule_id
                   ORDER BY shelter.shelter_code"""
            ).fetchall()
            tarp = connection.execute(
                """SELECT capability.length_metres,capability.width_metres
                   FROM rule_personal_shelter_capability capability
                   JOIN inv_personal_shelter_definition shelter
                     ON shelter.item_rule_id=capability.shelter_rule_id
                   WHERE shelter.shelter_code='tarpaulin'"""
            ).fetchone()
        self.assertEqual(modules, [
            ("advanced-base", 16, 1.5, 1.5, 2),
            ("pre-fabricated-cabin", 16, 1.5, 1.5, 2),
        ])
        self.assertEqual(tarp, (4, 2))


if __name__ == "__main__":
    unittest.main()
