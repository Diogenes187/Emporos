import os
import unittest
import psycopg

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1VehicleCapabilityTests(unittest.TestCase):
    def test_cargo_orbit_and_atmosphere_boundaries_are_exact(self):
        with psycopg.connect(DSN) as connection:
            cargo = connection.execute(
                """SELECT profile.profile_code,capability.cargo_capacity_kg
                   FROM rule_book1_vehicle_capability capability
                   JOIN rule_book1_vehicle_profile profile
                     ON profile.rule_id=capability.vehicle_profile_rule_id
                   WHERE capability.cargo_capacity_kg IS NOT NULL
                   ORDER BY profile.profile_code"""
            ).fetchall()
            orbit = connection.execute(
                """SELECT profile.profile_code,
                          capability.orbit_duration_basis,
                          capability.vacc_suit_required_at_orbit_altitude
                   FROM rule_book1_vehicle_capability capability
                   JOIN rule_book1_vehicle_profile profile
                     ON profile.rule_id=capability.vehicle_profile_rule_id
                   WHERE capability.orbit_duration_basis IS NOT NULL
                   ORDER BY profile.profile_code"""
            ).fetchall()
        self.assertEqual(len(cargo), 9)
        self.assertIn(("steamship", 50000), cargo)
        self.assertIn(("twin-jet-aircraft", 5000), cargo)
        self.assertEqual(orbit, [
            ("air-raft", "world-size-hours", True),
            ("g-carrier", "world-size-hours", False),
            ("grav-floater", "world-size-hours", False),
            ("speeder", "one-hour", False),
        ])

    def test_atv_grav_belt_and_gcarrier_rules_are_typed(self):
        with psycopg.connect(DSN) as connection:
            atv = connection.execute(
                """SELECT capability.pressurized,
                          capability.floats_on_calm_water,
                          capability.built_in_sensors,
                          capability.built_in_communications,
                          capability.unarmed_turret_hardpoint
                   FROM rule_book1_vehicle_capability capability
                   JOIN rule_book1_vehicle_profile profile
                     ON profile.rule_id=capability.vehicle_profile_rule_id
                   WHERE profile.profile_code='atv'"""
            ).fetchone()
            batteries = connection.execute(
                """SELECT minimum_tech_level,duration_seconds
                   FROM rule_book1_grav_belt_battery
                   ORDER BY minimum_tech_level"""
            ).fetchall()
            gcarrier = connection.execute(
                """SELECT capability.serious_firepower_rules,
                          capability.weapon_radiation_leak
                   FROM rule_book1_vehicle_capability capability
                   JOIN rule_book1_vehicle_profile profile
                     ON profile.rule_id=capability.vehicle_profile_rule_id
                   WHERE profile.profile_code='g-carrier'"""
            ).fetchone()
        self.assertEqual(atv, (True, True, True, True, True))
        self.assertEqual(batteries, [(12, 14400), (15, 43200)])
        self.assertEqual(gcarrier, (True, False))

    def test_afv_lasers_use_canonical_energy_rifle(self):
        with psycopg.connect(DSN) as connection:
            row = connection.execute(
                """SELECT skill.rule_code,laser.damage_dice_count,
                          laser.damage_die_sides,laser.range_profile_code,
                          laser.minimum_lasers_per_attack,
                          laser.maximum_lasers_per_attack,
                          laser.single_attack_action
                   FROM rule_book1_afv_laser_fire laser
                   JOIN rule_rule skill
                     ON skill.rule_id=laser.attack_skill_rule_id"""
            ).fetchone()
        self.assertEqual(
            row, ("skill.energy-rifle",4,6,"ranged-rifle",1,3,True))


if __name__ == "__main__":
    unittest.main()
