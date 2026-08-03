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
class VehicleDamageApplicationTests(unittest.TestCase):
    def test_finalized_hits_apply_staged_system_and_hull_damage(
        self,
    ) -> None:
        helper = encounter_helpers.VehicleEncounterStateTests()
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture = helper.fixture(connection, "grav-tank")
                target_rule = helper.rule(
                    connection,
                    "item.vehicle.damage-target",
                    "Vehicle Damage Target Item",
                    "equipment",
                )
                connection.execute(
                    """INSERT INTO inv_item_definition (
                           rule_id,item_kind,minimum_tech_level,
                           cost_credits
                       )
                       VALUES (%s,'equipment',9,100000)""",
                    (target_rule,),
                )
                target_item = connection.execute(
                    """INSERT INTO inv_item_instance (
                           campaign_id,item_rule_id,instance_name
                       )
                       VALUES (%s,%s,'Damage Target')
                       RETURNING item_instance_id""",
                    (fixture["campaign"], target_rule),
                ).fetchone()[0]
                vehicle_class = connection.execute(
                    """SELECT vehicle_class_rule_id,armor_rating,
                              hull_points,structure_points
                       FROM vehicle_class
                       WHERE class_code='grav-tank'"""
                ).fetchone()
                target_instance = connection.execute(
                    """INSERT INTO vehicle_vehicle (
                           campaign_id,vehicle_class_rule_id,
                           inventory_item_instance_id,name,
                           hull_current,structure_current
                       )
                       VALUES (%s,%s,%s,'Damage Target',%s,%s)
                       RETURNING vehicle_id""",
                    (
                        fixture["campaign"], vehicle_class[0],
                        target_item, vehicle_class[2],
                        vehicle_class[3],
                    ),
                ).fetchone()[0]
                target_force = connection.execute(
                    """INSERT INTO venc_force (
                           vehicle_engagement_id,campaign_id,
                           side_code,force_name
                       )
                       VALUES (%s,%s,'red','Red Force')
                       RETURNING vehicle_force_id""",
                    (fixture["engagement"], fixture["campaign"]),
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
                        fixture["engagement"], fixture["campaign"],
                        target_force, target_instance,
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
                       WHERE mount.vehicle_class_rule_id=%s
                       ORDER BY mount.mount_sequence,weapon.slot_order
                       LIMIT 1""",
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
                           8,8,8,0,true,21,0,21,%s,12,
                           'damage-10-12'
                       )
                       RETURNING vehicle_attack_id""",
                    (
                        fixture["turn"], fixture["round"],
                        fixture["engagement"], fixture["campaign"],
                        fixture["vehicle"], target_vehicle,
                        armament[0], armament[1], armament[2],
                        armament[3], difficulty, vehicle_class[1],
                    ),
                ).fetchone()[0]
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
                sensor = connection.execute(
                    """INSERT INTO vehicle_system_state (
                           vehicle_id,campaign_id,location_code,
                           system_identifier
                       )
                       VALUES (%s,%s,'sensors','primary-sensors')
                       RETURNING vehicle_system_state_id""",
                    (target_instance, fixture["campaign"]),
                ).fetchone()[0]
                application = connection.execute(
                    """INSERT INTO venc_damage_application (
                           vehicle_attack_id,vehicle_engagement_id,
                           campaign_id,target_vehicle_id,
                           target_vehicle_instance_id,
                           armor_before,hull_before,structure_before,
                           armor_after,hull_after,structure_after,
                           lifecycle_before,lifecycle_after
                       )
                       VALUES (
                           %s,%s,%s,%s,%s,%s,%s,%s,
                           %s,%s,%s,'active','disabled'
                       )
                       RETURNING vehicle_damage_application_id""",
                    (
                        attack, fixture["engagement"],
                        fixture["campaign"], target_vehicle,
                        target_instance, vehicle_class[1],
                        vehicle_class[2], vehicle_class[3],
                        vehicle_class[1], vehicle_class[2] - 1,
                        vehicle_class[3],
                    ),
                ).fetchone()[0]
                hit_rows = [
                    (
                        1, 1, 1, 1, "vehicle-external", 3, 1,
                        "sensors", "direct", "vehicle-external",
                        "sensors", sensor, sensor, vehicle_class[1],
                        vehicle_class[2], vehicle_class[3],
                        vehicle_class[1], vehicle_class[2],
                        vehicle_class[3], 0, 1, "degraded",
                    ),
                    (
                        2, 1, 2, 1, "vehicle-external", 11, 1,
                        "sensors", "direct", "vehicle-external",
                        "sensors", sensor, sensor, vehicle_class[1],
                        vehicle_class[2], vehicle_class[3],
                        vehicle_class[1], vehicle_class[2],
                        vehicle_class[3], 1, 2, "blinded",
                    ),
                    (
                        3, 1, 3, 1, "vehicle-external", 11, 1,
                        "sensors", "overflow", "vehicle-external",
                        "hull", None, sensor, vehicle_class[1],
                        vehicle_class[2], vehicle_class[3],
                        vehicle_class[1], vehicle_class[2] - 1,
                        vehicle_class[3], None, None, None,
                    ),
                ]
                insert_hit = """INSERT INTO venc_damage_location_hit (
                    vehicle_damage_application_id,hit_order,
                    packet_order,packet_instance,hit_within_packet,
                    rolled_context,roll_total,rolled_option_order,
                    rolled_location_code,resolution_kind,
                    resolved_context,location_code,
                    vehicle_system_state_id,
                    rolled_vehicle_system_state_id,
                    armor_before,hull_before,structure_before,
                    armor_after,hull_after,structure_after,
                    system_hits_before,system_hits_after,
                    system_status_after
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )"""
                for row in hit_rows[:2]:
                    connection.execute(insert_hit, (application, *row))
                with self.assertRaisesRegex(
                    CheckViolation, "hit plan does not reconcile",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE venc_damage_application
                               SET finalized=true,
                                   applied_at=clock_timestamp()
                               WHERE vehicle_damage_application_id=%s""",
                            (application,),
                        )
                connection.execute(
                    insert_hit, (application, *hit_rows[2])
                )
                connection.execute(
                    """UPDATE venc_damage_application
                       SET finalized=true,
                           applied_at=clock_timestamp()
                       WHERE vehicle_damage_application_id=%s""",
                    (application,),
                )

                current = connection.execute(
                    """SELECT armor_current,hull_current,
                              structure_current,lifecycle_status,
                              damaged_systems,system_hits
                       FROM vehicle_current_damage_state
                       WHERE vehicle_id=%s""",
                    (target_instance,),
                ).fetchone()
                self.assertEqual(
                    current,
                    (
                        vehicle_class[1], vehicle_class[2] - 1,
                        vehicle_class[3], "disabled", 1, 2,
                    ),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT current_hits,system_status
                           FROM vehicle_system_state
                           WHERE vehicle_system_state_id=%s""",
                        (sensor,),
                    ).fetchone(),
                    (2, "blinded"),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """DELETE FROM venc_damage_location_hit
                               WHERE vehicle_damage_application_id=%s
                                 AND hit_order=3""",
                            (application,),
                        )


if __name__ == "__main__":
    unittest.main()
