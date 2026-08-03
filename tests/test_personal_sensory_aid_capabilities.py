import os
import unittest

import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalSensoryAidCapabilityTests(unittest.TestCase):
    def test_operating_durations_and_vision_boundaries_are_typed(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT aid.sensory_aid_code,
                          capability.operating_duration_seconds,
                          capability.duration_is_approximate,
                          capability.requires_non_total_darkness,
                          capability.detects_heat_emitting_sources,
                          capability.viewing_distance_is_unquantified
                   FROM rule_personal_sensory_aid_capability capability
                   JOIN inv_personal_sensory_aid_definition aid
                     ON aid.item_rule_id=capability.sensory_aid_rule_id
                   ORDER BY aid.sensory_aid_code"""
            ).fetchall()
        self.assertEqual(len(rows), 7)
        self.assertIn(
            ("electric-torch", 21600, True, False, False, False), rows)
        self.assertIn(
            ("cold-light-lantern", 259200, False, False, False, False), rows)
        self.assertIn(
            ("light-intensifier-goggles", None, None, True, False, False),
            rows)
        self.assertIn(
            ("binoculars", None, None, False, False, True), rows)

    def test_illumination_geometry_is_exact(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT aid.sensory_aid_code,mode.mode_code,
                          mode.minimum_tech_level,mode.clear_radius_metres,
                          mode.shadow_radius_metres,mode.beam_length_metres,
                          mode.beam_end_radius_metres,
                          mode.later_tech_level_is_unquantified
                   FROM rule_personal_sensory_aid_illumination_mode mode
                   JOIN inv_personal_sensory_aid_definition aid
                     ON aid.item_rule_id=mode.sensory_aid_rule_id
                   ORDER BY aid.sensory_aid_code,mode.mode_code"""
            ).fetchall()
        self.assertEqual(len(rows), 8)
        self.assertIn(
            ("oil-lamp", "radial", 2, 4.5, 9, None, None, False), rows)
        self.assertIn(
            ("electric-torch", "tight-beam", None, None, None, 36, 1, True),
            rows)
        self.assertIn(
            ("cold-light-lantern", "area", 6, 10, None, None, None, False),
            rows)

    def test_binocular_upgrades_preserve_separate_published_profiles(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT minimum_tech_level,cost_credits,image_capture,
                          light_intensification,
                          portable_radiation_imaging_system,
                          spectrum_low_code,spectrum_high_code
                   FROM rule_personal_binocular_upgrade
                   ORDER BY minimum_tech_level"""
            ).fetchall()
        self.assertEqual(rows, [
            (8, 750, True, True, False, None, None),
            (12, 3500, False, False, True, "infrared", "gamma-rays"),
        ])


if __name__ == "__main__":
    unittest.main()
