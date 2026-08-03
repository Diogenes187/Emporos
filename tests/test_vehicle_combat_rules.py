from __future__ import annotations

import os
import unittest
from decimal import Decimal

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleCombatRuleTests(unittest.TestCase):
    def test_vehicle_turn_and_occupant_rules_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            procedure = connection.execute(
                """SELECT moves_on_driver_initiative,
                          facing_must_be_tracked,
                          normal_control_action_kind,
                          complex_control_action_kind,
                          vehicle_target_attack_dm
                   FROM rule_vehicle_personal_combat"""
            ).fetchone()
            self.assertEqual(
                procedure,
                (True, True, "minor", "significant", 1),
            )

            protection = connection.execute(
                """SELECT protection_code,cover_kind,
                          cover_fraction,
                          firing_occupants_per_arc,
                          occupants_may_attack_any_direction
                   FROM rule_vehicle_occupant_protection
                   ORDER BY protection_code"""
            ).fetchall()
            self.assertEqual(
                protection,
                [
                    (
                        "closed-civilian",
                        "soft",
                        Decimal("0.5"),
                        2,
                        False,
                    ),
                    (
                        "closed-military",
                        "hard",
                        Decimal("1"),
                        1,
                        False,
                    ),
                    ("open", "none", Decimal("0"), None, True),
                ],
            )

    def test_published_weapon_arcs_are_numeric(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            arcs = connection.execute(
                """SELECT arc_code,arc_degrees,
                          unrestricted_direction
                   FROM rule_vehicle_weapon_arc
                   ORDER BY arc_code"""
            ).fetchall()
            self.assertEqual(
                arcs,
                [
                    ("front-fixed", 90, False),
                    ("turret", 360, True),
                ],
            )

    def test_collision_formula_preserves_occupant_distinctions(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            collision = connection.execute(
                """SELECT speed_increment_kph,
                          damage_dice_per_increment,
                          damage_die_sides,increment_rounding,
                          struck_target_takes_full_damage,
                          solid_target_damages_ramming_vehicle,
                          unsecured_occupant_damage_fraction,
                          unsecured_throw_metres_per_increment,
                          secured_occupant_damage_fraction,
                          secured_occupants_are_thrown
                   FROM rule_vehicle_collision"""
            ).fetchone()
            self.assertEqual(
                collision,
                (
                    10, 1, 6, "ceiling", True, True,
                    Decimal("1"), Decimal("3"),
                    Decimal("0.25"), False,
                ),
            )

    def test_all_driver_actions_are_relational(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            actions = connection.execute(
                """SELECT action_code,action_kind,
                          check_requirement,
                          collision_on_success,
                          affected_by_dodge,
                          affected_by_evasive_action
                   FROM rule_vehicle_combat_action
                   ORDER BY action_code"""
            ).fetchall()
            self.assertEqual(
                actions,
                [
                    (
                        "evasive","significant","vehicle-skill",
                        False,False,False,
                    ),
                    (
                        "maneuver","significant","none",
                        False,False,False,
                    ),
                    (
                        "ram","significant","vehicle-skill",
                        True,True,True,
                    ),
                    (
                        "stunt","significant","vehicle-control",
                        False,False,False,
                    ),
                    (
                        "weave","significant","vehicle-skill",
                        False,False,False,
                    ),
                ],
            )

    def test_evasion_stunt_and_weave_formulas_are_typed(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            evasive = connection.execute(
                """SELECT incoming_attack_dm_uses_negative_effect,
                          outgoing_attack_dm_uses_negative_effect,
                          applies_to_vehicle_attacks,
                          applies_to_occupant_attacks,
                          duration_basis
                   FROM rule_vehicle_evasive_action"""
            ).fetchone()
            self.assertEqual(
                evasive,
                (
                    True,True,True,True,
                    "until-next-driver-action",
                ),
            )
            stunt = connection.execute(
                """SELECT additional_fire_arcs,
                          additional_fire_arc_duration_rounds,
                          maximum_maneuver_equivalents,
                          may_start_task_chain
                   FROM rule_vehicle_stunt_action"""
            ).fetchone()
            self.assertEqual(stunt, (1, 1, 3, True))
            weave = connection.execute(
                """SELECT minimum_weave_number,
                          speed_kph_per_maximum_weave_number,
                          maximum_rounding,
                          check_dm_per_weave_number,
                          failure_causes_collision,
                          pursuer_must_match_weave_number,
                          pursuer_may_break_off
                   FROM rule_vehicle_weave_action"""
            ).fetchone()
            self.assertEqual(
                weave,
                (1, 20, "ceiling", -1, True, True, True),
            )

    def test_vehicle_combat_rules_have_paired_provenance(self) -> None:
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
                   WHERE rule.rule_code LIKE
                         'vehicle.combat.%'"""
            ).fetchone()
            self.assertEqual(counts, (18, 9, 9))


if __name__ == "__main__":
    unittest.main()
