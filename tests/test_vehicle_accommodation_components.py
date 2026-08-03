from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg
from psycopg.errors import CheckViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleAccommodationComponentTests(unittest.TestCase):
    def test_accommodations_are_role_and_capacity_aware(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT accommodation.accommodation_code,
                          accommodation.duration_code,
                          component.unit_spaces,
                          component.unit_cost_minor,
                          accommodation.maximum_occupants,
                          accommodation.crew_capacity,
                          accommodation.additional_person_capacity,
                          accommodation.comfortable_occupants,
                          accommodation.cramped_occupants,
                          accommodation.military_only,
                          accommodation.hibernation_berth,
                          accommodation.includes_fresher
                   FROM rule_vehicle_accommodation accommodation
                   JOIN vehicle_component_definition component
                     USING (component_rule_id)
                   ORDER BY accommodation.accommodation_code"""
            ).fetchall()
            self.assertEqual(len(rows), 12)
            self.assertIn(
                (
                    "control-cabin-standard", "long", 72, 20000,
                    3, 2, 1, None, None, False, False, False,
                ),
                rows,
            )
            self.assertIn(
                (
                    "stateroom-standard", "long", 48, 500000,
                    2, 0, 2, 1, 2, False, False, True,
                ),
                rows,
            )
            self.assertIn(
                (
                    "seat-cramped", "short", 4, 2000,
                    3, 0, 3, None, 3, False, False, False,
                ),
                rows,
            )

    def test_life_support_and_sailing_crew_formulas_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            life_support = connection.execute(
                """SELECT life.life_support_code,
                          component.minimum_tech_level,
                          life.supported_people_per_unit,
                          life.spaces_per_unit,
                          life.price_per_space_minor,
                          component.unit_cost_minor,
                          life.duration_days
                   FROM rule_vehicle_life_support life
                   JOIN vehicle_component_definition component
                     USING (component_rule_id)
                   ORDER BY life.life_support_code"""
            ).fetchall()
            self.assertEqual(
                life_support,
                [
                    ("basic", 4, 20, 3, 3500, 10500, 10),
                    ("extended", 7, 5, 3, 17500, 52500, 90),
                ],
            )
            inclusions = connection.execute(
                """SELECT condition_code,life.life_support_code,
                          included_spaces,included_cost_minor
                   FROM rule_vehicle_life_support_inclusion inclusion
                   JOIN rule_vehicle_life_support life
                     USING (component_rule_id)
                   ORDER BY condition_code"""
            ).fetchall()
            self.assertEqual(
                inclusions,
                [
                    (
                        "hostile-environmental-protection",
                        "basic", 3, 0,
                    ),
                    ("submersible", "basic", 3, 0),
                ],
            )
            sailing = connection.execute(
                """SELECT tech_level_subtrahend,
                          minimum_crew_per_tonnage_group,
                          displacement_tons_per_group,
                          small_vessel_maximum_tons,
                          small_vessel_crew_multiplier
                   FROM rule_vehicle_sailing_crew_formula
                   WHERE formula_code='standard'"""
            ).fetchone()
            self.assertEqual(
                sailing,
                (10, 1, 4, 2, Decimal("0.5")),
            )

    def test_additional_component_catalogue_preserves_exact_values(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            count = connection.execute(
                """SELECT count(*)
                   FROM vehicle_component_definition
                   WHERE component_code LIKE 'additional.%'"""
            ).fetchone()[0]
            self.assertEqual(count, 35)
            selected = connection.execute(
                """SELECT component_code,minimum_tech_level,
                          unit_spaces,unit_cost_minor,
                          space_basis,cost_basis,
                          capacity_kind,capacity_per_unit,
                          calculation_status
                   FROM vehicle_component_definition
                   WHERE component_code IN (
                       'additional.wet-bar',
                       'additional.folding-wings-rotors',
                       'additional.emergency-low-berth',
                       'additional.holding-tank'
                   )
                   ORDER BY component_code"""
            ).fetchall()
            self.assertEqual(
                selected,
                [
                    (
                        "additional.emergency-low-berth", 12, 12,
                        100000, "fixed", "fixed", "person", 4,
                        "adjudicated",
                    ),
                    (
                        "additional.folding-wings-rotors", 3, 0,
                        0, "included", "per_chassis_space",
                        None, None, "adjudicated",
                    ),
                    (
                        "additional.holding-tank", 8, 1, 1500,
                        "fixed", "per_space", "liquid_gas_space",
                        1, "formula",
                    ),
                    (
                        "additional.wet-bar", 2, Decimal("1.5"),
                        2000, "fixed", "fixed", None, None,
                        "adjudicated",
                    ),
                ],
            )

    def test_component_formulas_are_numeric_not_prose(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            formulas = connection.execute(
                """SELECT component.component_code,
                          formula.quantity_basis,
                          formula.base_spaces,
                          formula.spaces_per_increment,
                          formula.basis_units_per_increment,
                          formula.increment_rounding,
                          formula.base_cost_minor,
                          formula.cost_per_basis_unit_minor,
                          formula.cost_per_allocated_space_minor,
                          formula.cost_per_increment_minor
                   FROM rule_vehicle_component_formula formula
                   JOIN vehicle_component_definition component
                     USING (component_rule_id)
                   ORDER BY component.component_code"""
            ).fetchall()
            self.assertEqual(len(formulas), 9)
            self.assertIn(
                (
                    "additional.floats-pontoons", "chassis_spaces",
                    0, 1, 12, "ceiling", 0, 0, 0, 250,
                ),
                formulas,
            )
            self.assertIn(
                (
                    "additional.galley-full", "people_served",
                    18, 3, 10, "ceiling", 2000, 500, 0, 0,
                ),
                formulas,
            )
            self.assertIn(
                (
                    "additional.refueling-station", "vessel_tons",
                    12, 1, 50, "ceiling", 0, 0, 15000, 0,
                ),
                formulas,
            )

    def test_trailers_mobility_and_manipulators_are_relational(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            trailers = connection.execute(
                """SELECT model.displacement_tons,
                          model.capacity_spaces,model.price_minor
                   FROM rule_vehicle_cargo_trailer_model model
                   ORDER BY model.displacement_tons"""
            ).fetchall()
            self.assertEqual(
                trailers,
                [
                    (Decimal("0.25"), 3, 1450),
                    (Decimal("0.5"), 6, 1700),
                    (Decimal("1"), 12, 2200),
                    (Decimal("2"), 24, 3200),
                    (Decimal("4"), 48, 5700),
                    (Decimal("8"), 96, 12000),
                ],
            )
            trailer_rule = connection.execute(
                """SELECT agility_dm,small_vehicle_maximum_tons,
                          small_vehicle_additional_agility_dm,
                          towing_speed_rounding_kph,
                          towing_speed_formula_code
                   FROM rule_vehicle_cargo_trailer_rule"""
            ).fetchone()
            self.assertEqual(
                trailer_rule,
                (
                    -1, 2, -1, 10,
                    "base-speed-times-chassis-space-ratio",
                ),
            )
            mobility = connection.execute(
                """SELECT component.component_code,
                          effect.base_speed_multiplier,
                          effect.agility_dm,
                          effect.stored_size_multiplier,effect.removable
                   FROM rule_vehicle_mobility_component effect
                   JOIN vehicle_component_definition component
                     USING (component_rule_id)
                   ORDER BY component.component_code"""
            ).fetchall()
            self.assertEqual(
                mobility,
                [
                    (
                        "additional.floats-pontoons",
                        Decimal("0.9"), -1, None, True,
                    ),
                    (
                        "additional.folding-wings-rotors",
                        None, None, Decimal("0.75"), False,
                    ),
                ],
            )
            manipulator = connection.execute(
                """SELECT arm.base_strength,arm.base_dexterity,
                          arm.price_per_added_attribute_point_minor,
                          count(limit_row.*)
                   FROM rule_vehicle_manipulator_arm arm
                   JOIN rule_vehicle_manipulator_limit limit_row
                     USING (component_rule_id)
                   GROUP BY arm.component_rule_id"""
            ).fetchone()
            self.assertEqual(manipulator, (2, 1, 5000, 4))

    def test_facility_capabilities_and_progressions_are_typed(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*) FROM rule_vehicle_crane),
                    (SELECT count(*) FROM rule_vehicle_galley),
                    (SELECT count(*) FROM rule_vehicle_refueling_rate),
                    (SELECT count(*) FROM rule_vehicle_sampler_bonus),
                    (SELECT count(*)
                       FROM rule_vehicle_research_lab_bonus),
                    (SELECT count(*)
                       FROM rule_vehicle_research_lab_discipline),
                    (SELECT count(*)
                       FROM rule_vehicle_liquid_cannon_purpose),
                    (SELECT count(*)
                       FROM rule_vehicle_holding_tank_content)"""
            ).fetchone()
            self.assertEqual(counts, (3, 2, 2, 4, 3, 6, 3, 2))
            emergency = connection.execute(
                """SELECT survival_capacity,
                          passenger_transport_permitted,
                          locator.heading_path
                   FROM rule_vehicle_emergency_low_berth berth
                   JOIN src_locator locator
                     ON locator.source_locator_id=
                        berth.capacity_source_locator_id"""
            ).fetchone()
            self.assertEqual(
                emergency,
                (
                    4, False,
                    "Ship Design and Construction > Ship Crew > "
                    "Accommodation",
                ),
            )

    def test_provenance_errata_and_legacy_check_are_complete(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM vehicle_component_definition),
                    (SELECT count(*)
                       FROM src_record_provenance provenance
                       JOIN rule_rule rule USING (rule_id)
                      WHERE rule.rule_code LIKE 'vehicle.component.%'),
                    (SELECT count(*)
                       FROM src_open_issue_report
                      WHERE domain_code='vehicle.catalogue'),
                    (SELECT count(*)
                       FROM src_issue_comparison_check comparison
                       JOIN src_issue issue USING (source_issue_id)
                      WHERE issue.issue_code LIKE 'vehicle.%')"""
            ).fetchone()
            self.assertEqual(counts, (77, 156, 0, 30))
            issues = connection.execute(
                """SELECT issue_code,review_priority,
                          published_value,calculated_value,
                          engine_disposition
                   FROM src_issue
                   WHERE issue_code LIKE 'vehicle.components.%'
                   ORDER BY issue_code"""
            ).fetchall()
            self.assertEqual(
                issues,
                [
                    (
                        "vehicle.components.emergency-low-berth-capacity",
                        "medium", "Vehicle capacity unspecified",
                        "Four-person survival capacity", "preserve_rule",
                    ),
                    (
                        "vehicle.components.folding-wings-summary-omission",
                        "medium", "No summary-table row",
                        "Prose rule retained", "preserve_rule",
                    ),
                    (
                        "vehicle.components.wet-bar-table",
                        "high", 'Table: 1 Space; "5 Cr2,000"',
                        "Prose: 1.5 Spaces; Cr2,000", "preserve_rule",
                    ),
                ],
            )

    def test_research_lab_bonus_constraint_is_enforced(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE rule_vehicle_research_lab_bonus
                           SET skill_dm=4
                           WHERE skill_dm=3"""
                    )


if __name__ == "__main__":
    unittest.main()
