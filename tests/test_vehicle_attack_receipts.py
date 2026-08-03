from __future__ import annotations

import os
import unittest

import psycopg
from psycopg.errors import CheckViolation

from tests import test_vehicle_encounter_state as encounter_helpers


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleAttackReceiptTests(unittest.TestCase):
    def test_mounted_attack_receipt_reconciles_and_freezes(
        self,
    ) -> None:
        helper = encounter_helpers.VehicleEncounterStateTests()
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture = helper.fixture(connection, "grav-tank")
                target_item_rule = helper.rule(
                    connection,
                    "item.vehicle.attack-target",
                    "Vehicle Attack Target Item",
                    "equipment",
                )
                connection.execute(
                    """INSERT INTO inv_item_definition (
                           rule_id,item_kind,minimum_tech_level,
                           cost_credits
                       )
                       VALUES (%s,'equipment',9,100000)""",
                    (target_item_rule,),
                )
                target_item = connection.execute(
                    """INSERT INTO inv_item_instance (
                           campaign_id,item_rule_id,instance_name
                       )
                       VALUES (%s,%s,'Target Grav Tank')
                       RETURNING item_instance_id""",
                    (fixture["campaign"], target_item_rule),
                ).fetchone()[0]
                vehicle_class = connection.execute(
                    """SELECT vehicle_class_rule_id,hull_points,
                              structure_points,armor_rating
                       FROM vehicle_class
                       WHERE class_code='grav-tank'"""
                ).fetchone()
                target_instance = connection.execute(
                    """INSERT INTO vehicle_vehicle (
                           campaign_id,vehicle_class_rule_id,
                           inventory_item_instance_id,name,
                           hull_current,structure_current
                       )
                       VALUES (%s,%s,%s,'Target Tank',%s,%s)
                       RETURNING vehicle_id""",
                    (
                        fixture["campaign"], vehicle_class[0],
                        target_item, vehicle_class[1],
                        vehicle_class[2],
                    ),
                ).fetchone()[0]
                target_force = connection.execute(
                    """INSERT INTO venc_force (
                           vehicle_engagement_id,campaign_id,
                           side_code,force_name
                       )
                       VALUES (%s,%s,'red','Red Force')
                       RETURNING vehicle_force_id""",
                    (
                        fixture["engagement"],
                        fixture["campaign"],
                    ),
                ).fetchone()[0]
                target_vehicle = connection.execute(
                    """INSERT INTO venc_vehicle (
                           vehicle_engagement_id,campaign_id,
                           vehicle_force_id,vehicle_id,
                           initiative_current,joined_round
                       )
                       VALUES (%s,%s,%s,%s,7,1)
                       RETURNING venc_vehicle_id""",
                    (
                        fixture["engagement"],
                        fixture["campaign"], target_force,
                        target_instance,
                    ),
                ).fetchone()[0]
                armament = connection.execute(
                    """SELECT mount.class_armament_mount_id,
                              weapon.slot_order,
                              weapon.weapon_rule_id,
                              definition.range_profile_code
                       FROM vehicle_class_armament_mount mount
                       JOIN vehicle_class_armament_weapon weapon
                         USING (class_armament_mount_id)
                       JOIN rule_vehicle_weapon_definition definition
                         ON definition.weapon_rule_id=
                            weapon.weapon_rule_id
                       WHERE mount.vehicle_class_rule_id=%s""",
                    (vehicle_class[0],),
                ).fetchone()
                difficulty = connection.execute(
                    """SELECT difficulty_rule_id
                       FROM rule_vehicle_weapon_range_difficulty
                       WHERE range_profile_code=%s
                         AND target_range_code='medium'""",
                    (armament[3],),
                ).fetchone()[0]
                attack = connection.execute(
                    """INSERT INTO venc_attack (
                           vehicle_crew_turn_id,
                           vehicle_combat_round_id,
                           vehicle_engagement_id,campaign_id,
                           attacker_vehicle_id,target_vehicle_id,
                           class_armament_mount_id,
                           weapon_slot_order,weapon_rule_id,
                           fire_arc_code,range_profile_code,
                           target_range_code,difficulty_rule_id,
                           attack_roll,attack_total,target_number,
                           effect,hit,rolled_damage,effect_damage,
                           raw_damage,armor_rating_used,
                           penetrating_damage,damage_band_code
                       )
                       VALUES (
                           %s,%s,%s,%s,%s,%s,%s,%s,%s,
                           'turret',%s,'medium',%s,
                           7,9,8,1,true,20,1,21,%s,12,
                           'damage-10-12'
                       )
                       RETURNING vehicle_attack_id""",
                    (
                        fixture["turn"], fixture["round"],
                        fixture["engagement"],
                        fixture["campaign"], fixture["vehicle"],
                        target_vehicle, armament[0], armament[1],
                        armament[2], armament[3], difficulty,
                        vehicle_class[3],
                    ),
                ).fetchone()[0]
                modifiers = [
                    (1, "skill", 2, "actor"),
                    (2, "range-difficulty", 0, "range-matrix"),
                    (3, "vehicle-size", 1, "vehicle"),
                    (4, "target-evasion", -1, "action-resolution"),
                ]
                for modifier in modifiers:
                    connection.execute(
                        """INSERT INTO venc_attack_modifier (
                               vehicle_attack_id,modifier_order,
                               modifier_code,modifier_value,
                               source_kind
                           )
                           VALUES (%s,%s,%s,%s,%s)""",
                        (attack, *modifier),
                    )
                with self.assertRaisesRegex(
                    CheckViolation, "does not reconcile",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE venc_attack
                               SET finalized=true,
                                   finalized_at=clock_timestamp()
                               WHERE vehicle_attack_id=%s""",
                            (attack,),
                        )

                connection.execute(
                    """INSERT INTO venc_attack_damage_packet (
                           vehicle_attack_id,packet_order,
                           location_hit_count,packet_quantity
                       )
                       VALUES (%s,1,1,3)""",
                    (attack,),
                )
                connection.execute(
                    """UPDATE venc_attack
                       SET finalized=true,
                           finalized_at=clock_timestamp()
                       WHERE vehicle_attack_id=%s""",
                    (attack,),
                )
                total = connection.execute(
                    """SELECT modifier_total,attack_total,effect,
                              penetrating_damage,
                              damage_band_code,location_hits,
                              finalized
                       FROM venc_attack_receipt_total
                       WHERE vehicle_attack_id=%s""",
                    (attack,),
                ).fetchone()
                self.assertEqual(
                    total,
                    (2, 9, 1, 12, "damage-10-12", 3, True),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE venc_attack_modifier
                               SET modifier_value=3
                               WHERE vehicle_attack_id=%s
                                 AND modifier_code='skill'""",
                            (attack,),
                        )


if __name__ == "__main__":
    unittest.main()
