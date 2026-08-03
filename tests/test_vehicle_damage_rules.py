from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleDamageRuleTests(unittest.TestCase):
    def test_damage_bands_preserve_hit_packets(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            bands = connection.execute(
                """SELECT band.damage_band_code,
                          band.minimum_damage,
                          band.maximum_damage,
                          coalesce(sum(
                              packet.location_hit_count*
                              packet.packet_quantity
                          ),0)
                   FROM rule_vehicle_damage_band band
                   LEFT JOIN rule_vehicle_damage_band_packet packet
                     USING (damage_band_code)
                   GROUP BY band.damage_band_code,
                            band.minimum_damage,
                            band.maximum_damage,
                            band.display_order
                   ORDER BY band.display_order"""
            ).fetchall()
            self.assertEqual(len(bands), 12)
            self.assertEqual(bands[0], ("none", None, 0, 0))
            self.assertEqual(
                bands[-1],
                ("damage-31-33", 31, 33, 6),
            )
            packets = connection.execute(
                """SELECT location_hit_count,packet_quantity
                   FROM rule_vehicle_damage_band_packet
                   WHERE damage_band_code='damage-28-30'
                   ORDER BY packet_order"""
            ).fetchall()
            self.assertEqual(packets, [(3, 1), (2, 1), (1, 1)])
            excess = connection.execute(
                """SELECT damage_increment,location_hit_count,
                          cumulative_with_other_increments
                   FROM rule_vehicle_excess_damage_packet
                   ORDER BY damage_increment"""
            ).fetchall()
            self.assertEqual(excess, [(3, 1, True), (6, 2, True)])

    def test_all_three_hit_location_matrices_are_exact(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT
                    (SELECT count(*)
                       FROM rule_vehicle_hit_location),
                    (SELECT count(*)
                       FROM rule_vehicle_hit_location_roll),
                    (SELECT count(*)
                       FROM rule_vehicle_hit_location_roll_option)"""
            ).fetchone()
            self.assertEqual(counts, (12, 33, 35))
            roll_seven = connection.execute(
                """SELECT roll.target_context,option.location_code
                   FROM rule_vehicle_hit_location_roll roll
                   JOIN rule_vehicle_hit_location_roll_option option
                     USING (target_context,roll_total)
                   WHERE roll.roll_total=7
                   ORDER BY roll.target_context"""
            ).fetchall()
            self.assertEqual(
                roll_seven,
                [
                    ("robot-drone", "armor"),
                    ("vehicle-external", "armor"),
                    ("vehicle-internal", "passengers"),
                ],
            )
            robot_five = connection.execute(
                """SELECT roll.selection_mode,option.location_code
                   FROM rule_vehicle_hit_location_roll roll
                   JOIN rule_vehicle_hit_location_roll_option option
                     USING (target_context,roll_total)
                   WHERE roll.target_context='robot-drone'
                     AND roll.roll_total=5
                   ORDER BY option.option_order"""
            ).fetchall()
            self.assertEqual(
                robot_five,
                [
                    ("random-eligible", "weapon"),
                    ("random-eligible", "limb"),
                ],
            )

    def test_system_damage_stages_are_numeric(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            drive = connection.execute(
                """SELECT hit_number,system_status,
                          movement_reduction_fraction,
                          control_check_dm
                   FROM rule_vehicle_system_hit_stage
                   WHERE location_code='drive'
                   ORDER BY hit_number"""
            ).fetchall()
            self.assertEqual(
                drive,
                [
                    (1, "degraded", Decimal("0.10"), -1),
                    (2, "degraded", Decimal("0.25"), -2),
                    (3, "disabled", None, None),
                ],
            )
            power_plant = connection.execute(
                """SELECT hit_number,system_status,
                          actions_lost_rounds,
                          movement_reduction_fraction,
                          collateral_hull_dice_count,
                          collateral_hull_die_sides
                   FROM rule_vehicle_system_hit_stage
                   WHERE location_code='power-plant'
                   ORDER BY hit_number"""
            ).fetchall()
            self.assertEqual(
                power_plant,
                [
                    (1, "actions-lost", 1, None, None, None),
                    (
                        2,"degraded",None,
                        Decimal("0.50"),None,None,
                    ),
                    (3, "destroyed", None, None, 1, 6),
                ],
            )

    def test_hit_overflow_rules_are_explicit(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            overflow = connection.execute(
                """SELECT target_context,location_code,
                          overflow_condition,overflow_kind,
                          overflow_location_code
                   FROM rule_vehicle_location_overflow
                   ORDER BY target_context,location_code"""
            ).fetchall()
            self.assertEqual(len(overflow), 10)
            self.assertIn(
                (
                    "vehicle-external","hull",
                    "integrity-exhausted",
                    "same-roll-internal",None,
                ),
                overflow,
            )
            self.assertIn(
                (
                    "any","computer",
                    "after-final-stage","location","structure",
                ),
                overflow,
            )

    def test_destruction_and_explosion_zones_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            destruction = connection.execute(
                """SELECT destroyed_at_structure,
                          explodes_below_structure,
                          closed_occupants_may_evade_explosion,
                          open_occupants_may_evade_explosion
                   FROM rule_vehicle_destruction"""
            ).fetchone()
            self.assertEqual(destruction, (0, 0, False, True))
            zones = connection.execute(
                """SELECT maximum_radius_metres,
                          damage_dice_count,damage_die_sides,
                          includes_occupants
                   FROM rule_vehicle_explosion_zone
                   ORDER BY maximum_radius_metres"""
            ).fetchall()
            self.assertEqual(
                zones,
                [
                    (Decimal("6"), 4, 6, True),
                    (Decimal("12"), 2, 6, True),
                ],
            )

    def test_repair_time_cost_and_material_rules_are_typed(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            repairs = connection.execute(
                """SELECT repair.repair_category,
                          repair.skill_requirement,
                          skill.rule_code,
                          difficulty_rule.rule_code,
                          repair.time_dice_count,
                          repair.time_die_sides,
                          repair.time_multiplier_hours,
                          repair.time_basis,
                          repair.spare_part_hits_consumed,
                          repair.workshop_required,
                          repair.base_vehicle_cost_fraction_per_point
                   FROM rule_vehicle_repair_category repair
                   LEFT JOIN rule_rule skill
                     ON skill.rule_id=repair.fixed_skill_rule_id
                   LEFT JOIN rule_rule difficulty_rule
                     ON difficulty_rule.rule_id=
                        repair.difficulty_rule_id
                   ORDER BY repair.repair_category"""
            ).fetchall()
            self.assertEqual(
                repairs,
                [
                    (
                        "hull","fixed","skill.mechanics",None,
                        1,6,1,"per-repair",1,False,None,
                    ),
                    (
                        "structure","none",None,None,
                        1,6,10,"per-damage-point",None,True,
                        Decimal("0.20"),
                    ),
                    (
                        "system","appropriate",None,
                        "difficulty.average",1,6,1,
                        "per-repair",1,False,None,
                    ),
                ],
            )
            states = connection.execute(
                """SELECT system_damage_state,may_be_jury_rigged,
                          may_use_spare_parts,workshop_required,
                          specialist_materials_required,
                          repair_cost_dice_count,
                          repair_cost_die_sides,
                          repair_cost_fraction_per_die_point
                   FROM rule_vehicle_system_repair_state
                   ORDER BY system_damage_state"""
            ).fetchall()
            self.assertEqual(
                states,
                [
                    (
                        "damaged",True,True,False,False,
                        None,None,None,
                    ),
                    (
                        "destroyed",False,False,True,True,
                        2,6,Decimal("0.10"),
                    ),
                ],
            )

    def test_damage_and_repair_rules_have_paired_provenance(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (
                              WHERE provenance.is_primary_citation
                          ),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code LIKE 'vehicle.damage.%'
                      OR rule.rule_code LIKE 'vehicle.repair.%'"""
            ).fetchone()
            self.assertEqual(counts, (10, 5, 5))


if __name__ == "__main__":
    unittest.main()
