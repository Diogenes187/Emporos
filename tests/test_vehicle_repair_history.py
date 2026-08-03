from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.errors import CheckViolation

from tests import test_vehicle_encounter_state as encounter_helpers


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleRepairHistoryTests(unittest.TestCase):
    def fixture(self, connection):
        helper = encounter_helpers.VehicleEncounterStateTests()
        fixture = helper.fixture(connection, "grav-tank")
        vehicle_class = connection.execute(
            """SELECT armor_rating,hull_points,structure_points,
                      construction_cost_minor
               FROM vehicle_class
               WHERE class_code='grav-tank'"""
        ).fetchone()
        return fixture, vehicle_class

    def repair_rule(self, connection, category):
        return connection.execute(
            """SELECT repair_rule_id
               FROM rule_vehicle_repair_category
               WHERE repair_category=%s""",
            (category,),
        ).fetchone()[0]

    def skill_rule(self, connection, code):
        return connection.execute(
            """SELECT rule_id FROM rule_rule WHERE rule_code=%s""",
            (code,),
        ).fetchone()[0]

    def test_hull_repair_restores_vehicle_and_freezes_history(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture, vehicle_class = self.fixture(connection)
                connection.execute(
                    """UPDATE vehicle_vehicle
                       SET hull_current=0,lifecycle_status='disabled'
                       WHERE vehicle_id=%s""",
                    (fixture["vehicle_instance"],),
                )
                receipt = connection.execute(
                    """INSERT INTO vehicle_repair_receipt (
                           vehicle_id,campaign_id,repair_rule_id,
                           repair_category,repair_method,
                           repairing_actor_id,skill_rule_id,
                           check_roll,check_total,succeeded,
                           integrity_points_restored,
                           armor_before,hull_before,structure_before,
                           armor_after,hull_after,structure_after,
                           lifecycle_before,lifecycle_after,
                           work_duration_hours,workshop_used,
                           specialist_materials_used,
                           spare_part_hits_consumed
                       )
                       VALUES (
                           %s,%s,%s,'hull','full',%s,%s,
                           7,9,true,1,%s,0,%s,%s,1,%s,
                           'disabled','active',4,false,false,1
                       )
                       RETURNING vehicle_repair_receipt_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                        self.repair_rule(connection, "hull"),
                        fixture["actor"],
                        self.skill_rule(connection, "skill.mechanics"),
                        vehicle_class[0], vehicle_class[2],
                        vehicle_class[0], vehicle_class[2],
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO vehicle_repair_modifier (
                           vehicle_repair_receipt_id,modifier_order,
                           modifier_code,modifier_value
                       )
                       VALUES (%s,1,'skill',2)""",
                    (receipt,),
                )
                connection.execute(
                    """INSERT INTO vehicle_repair_spare_source (
                           vehicle_repair_receipt_id,source_order,
                           source_kind,source_reference,
                           spare_part_hits
                       )
                       VALUES (%s,1,'workshop',
                               'test-workshop-parts',1)""",
                    (receipt,),
                )
                applied_at = datetime(
                    2030, 1, 1, tzinfo=timezone.utc
                )
                with self.assertRaisesRegex(
                    CheckViolation, "duration does not reconcile",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE vehicle_repair_receipt
                               SET finalized=true,applied_at=%s
                               WHERE vehicle_repair_receipt_id=%s""",
                            (applied_at, receipt),
                        )
                connection.execute(
                    """INSERT INTO vehicle_repair_random_die (
                           vehicle_repair_receipt_id,roll_kind,
                           die_order,die_sides,face_value
                       )
                       VALUES (%s,'work-duration',1,6,4)""",
                    (receipt,),
                )
                connection.execute(
                    """UPDATE vehicle_repair_receipt
                       SET finalized=true,applied_at=%s
                       WHERE vehicle_repair_receipt_id=%s""",
                    (applied_at, receipt),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT hull_current,lifecycle_status
                           FROM vehicle_vehicle
                           WHERE vehicle_id=%s""",
                        (fixture["vehicle_instance"],),
                    ).fetchone(),
                    (1, "active"),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE vehicle_repair_modifier
                               SET modifier_value=3
                               WHERE vehicle_repair_receipt_id=%s""",
                            (receipt,),
                        )

    def test_jury_rig_then_full_system_repair(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture, vehicle_class = self.fixture(connection)
                system = connection.execute(
                    """INSERT INTO vehicle_system_state (
                           vehicle_id,campaign_id,location_code,
                           system_identifier,current_hits,
                           system_status
                       )
                       VALUES (
                           %s,%s,'sensors','repair-test-sensors',
                           1,'degraded'
                       )
                       RETURNING vehicle_system_state_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                    ),
                ).fetchone()[0]
                applied_at = datetime(
                    2030, 2, 1, tzinfo=timezone.utc
                )
                restore_until = applied_at + timedelta(hours=5)
                jury_receipt = connection.execute(
                    """INSERT INTO vehicle_repair_receipt (
                           vehicle_id,campaign_id,repair_rule_id,
                           repair_category,repair_method,
                           vehicle_system_state_id,succeeded,
                           system_hits_before,system_hits_after,
                           system_status_before,system_status_after,
                           armor_before,hull_before,structure_before,
                           armor_after,hull_after,structure_after,
                           lifecycle_before,lifecycle_after,
                           temporary_restore_until,
                           workshop_used,specialist_materials_used
                       )
                       VALUES (
                           %s,%s,%s,'system','jury-rig',%s,true,
                           1,1,'degraded','degraded',%s,%s,%s,
                           %s,%s,%s,'active','active',%s,
                           false,false
                       )
                       RETURNING vehicle_repair_receipt_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                        self.repair_rule(connection, "system"),
                        system, vehicle_class[0], vehicle_class[1],
                        vehicle_class[2], vehicle_class[0],
                        vehicle_class[1], vehicle_class[2],
                        restore_until,
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO vehicle_repair_random_die (
                           vehicle_repair_receipt_id,roll_kind,
                           die_order,die_sides,face_value
                       )
                       VALUES (
                           %s,'operating-duration',1,6,5
                       )""",
                    (jury_receipt,),
                )
                connection.execute(
                    """UPDATE vehicle_repair_receipt
                       SET finalized=true,applied_at=%s
                       WHERE vehicle_repair_receipt_id=%s""",
                    (applied_at, jury_receipt),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT damage_status,effective_status,
                                  temporary_restore_until
                           FROM vehicle_system_effective_state
                           WHERE vehicle_system_state_id=%s""",
                        (system,),
                    ).fetchone(),
                    ("degraded", "operational", restore_until),
                )

                difficulty = connection.execute(
                    """SELECT difficulty_rule_id
                       FROM rule_vehicle_repair_category
                       WHERE repair_category='system'"""
                ).fetchone()[0]
                full_receipt = connection.execute(
                    """INSERT INTO vehicle_repair_receipt (
                           vehicle_id,campaign_id,repair_rule_id,
                           repair_category,repair_method,
                           vehicle_system_state_id,
                           repairing_actor_id,skill_rule_id,
                           difficulty_rule_id,check_roll,check_total,
                           target_number,succeeded,
                           system_hits_before,system_hits_after,
                           system_status_before,system_status_after,
                           armor_before,hull_before,structure_before,
                           armor_after,hull_after,structure_after,
                           lifecycle_before,lifecycle_after,
                           work_duration_hours,workshop_used,
                           specialist_materials_used,
                           spare_part_hits_consumed
                       )
                       VALUES (
                           %s,%s,%s,'system','full',%s,%s,%s,
                           %s,6,8,8,true,1,0,'degraded','operational',
                           %s,%s,%s,%s,%s,%s,'active','active',
                           3,false,false,1
                       )
                       RETURNING vehicle_repair_receipt_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                        self.repair_rule(connection, "system"),
                        system, fixture["actor"],
                        self.skill_rule(
                            connection, "skill.electronics"
                        ),
                        difficulty, vehicle_class[0],
                        vehicle_class[1], vehicle_class[2],
                        vehicle_class[0], vehicle_class[1],
                        vehicle_class[2],
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO vehicle_repair_modifier (
                           vehicle_repair_receipt_id,modifier_order,
                           modifier_code,modifier_value
                       )
                       VALUES (%s,1,'skill',2)""",
                    (full_receipt,),
                )
                connection.execute(
                    """INSERT INTO vehicle_repair_random_die (
                           vehicle_repair_receipt_id,roll_kind,
                           die_order,die_sides,face_value
                       )
                       VALUES (%s,'work-duration',1,6,3)""",
                    (full_receipt,),
                )
                connection.execute(
                    """INSERT INTO vehicle_repair_spare_source (
                           vehicle_repair_receipt_id,source_order,
                           source_kind,source_reference,
                           spare_part_hits
                       )
                       VALUES (
                           %s,1,'scrap-yard','test-scrap-yard',1
                       )""",
                    (full_receipt,),
                )
                connection.execute(
                    """UPDATE vehicle_repair_receipt
                       SET finalized=true,applied_at=%s
                       WHERE vehicle_repair_receipt_id=%s""",
                    (
                        applied_at + timedelta(days=1),
                        full_receipt,
                    ),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT current_hits,damage_status,
                                  effective_status,
                                  temporary_restore_until
                           FROM vehicle_system_effective_state
                           WHERE vehicle_system_state_id=%s""",
                        (system,),
                    ).fetchone(),
                    (0, "operational", "operational", None),
                )

    def test_structure_repair_uses_per_point_time_and_cost(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture, vehicle_class = self.fixture(connection)
                connection.execute(
                    """UPDATE vehicle_vehicle
                       SET structure_current=1
                       WHERE vehicle_id=%s""",
                    (fixture["vehicle_instance"],),
                )
                expected_cost = vehicle_class[3] * 0.20
                receipt = connection.execute(
                    """INSERT INTO vehicle_repair_receipt (
                           vehicle_id,campaign_id,repair_rule_id,
                           repair_category,repair_method,succeeded,
                           integrity_points_restored,
                           armor_before,hull_before,structure_before,
                           armor_after,hull_after,structure_after,
                           lifecycle_before,lifecycle_after,
                           work_duration_hours,workshop_used,
                           specialist_materials_used,
                           cost_basis_minor,repair_cost_minor
                       )
                       VALUES (
                           %s,%s,%s,'structure','full',true,1,
                           %s,%s,1,%s,%s,2,'active','active',
                           40,true,true,%s,%s
                       )
                       RETURNING vehicle_repair_receipt_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                        self.repair_rule(connection, "structure"),
                        vehicle_class[0], vehicle_class[1],
                        vehicle_class[0], vehicle_class[1],
                        vehicle_class[3], expected_cost,
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO vehicle_repair_random_die (
                           vehicle_repair_receipt_id,roll_kind,
                           die_order,die_sides,face_value
                       )
                       VALUES (%s,'work-duration',1,6,4)""",
                    (receipt,),
                )
                connection.execute(
                    """UPDATE vehicle_repair_receipt
                       SET finalized=true,
                           applied_at='2030-03-01T00:00:00Z'
                       WHERE vehicle_repair_receipt_id=%s""",
                    (receipt,),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT structure_current,lifecycle_status
                           FROM vehicle_vehicle
                           WHERE vehicle_id=%s""",
                        (fixture["vehicle_instance"],),
                    ).fetchone(),
                    (2, "active"),
                )

    def test_destroyed_system_repair_uses_workshop_cost_dice(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                fixture, vehicle_class = self.fixture(connection)
                system = connection.execute(
                    """INSERT INTO vehicle_system_state (
                           vehicle_id,campaign_id,location_code,
                           system_identifier,current_hits,
                           system_status
                       )
                       VALUES (
                           %s,%s,'weapon','destroyed-test-weapon',
                           2,'destroyed'
                       )
                       RETURNING vehicle_system_state_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                    ),
                ).fetchone()[0]
                difficulty = connection.execute(
                    """SELECT difficulty_rule_id
                       FROM rule_vehicle_repair_category
                       WHERE repair_category='system'"""
                ).fetchone()[0]
                receipt = connection.execute(
                    """INSERT INTO vehicle_repair_receipt (
                           vehicle_id,campaign_id,repair_rule_id,
                           repair_category,repair_method,
                           vehicle_system_state_id,
                           repairing_actor_id,skill_rule_id,
                           difficulty_rule_id,check_roll,check_total,
                           target_number,succeeded,
                           system_hits_before,system_hits_after,
                           system_status_before,system_status_after,
                           armor_before,hull_before,structure_before,
                           armor_after,hull_after,structure_after,
                           lifecycle_before,lifecycle_after,
                           work_duration_hours,workshop_used,
                           specialist_materials_used,
                           cost_basis_minor,repair_cost_minor
                       )
                       VALUES (
                           %s,%s,%s,'system','full',%s,%s,%s,
                           %s,7,8,8,true,2,0,'destroyed','operational',
                           %s,%s,%s,%s,%s,%s,'active','active',
                           2,true,true,10000,7000
                       )
                       RETURNING vehicle_repair_receipt_id""",
                    (
                        fixture["vehicle_instance"],
                        fixture["campaign"],
                        self.repair_rule(connection, "system"),
                        system, fixture["actor"],
                        self.skill_rule(connection, "skill.mechanics"),
                        difficulty, vehicle_class[0],
                        vehicle_class[1], vehicle_class[2],
                        vehicle_class[0], vehicle_class[1],
                        vehicle_class[2],
                    ),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO vehicle_repair_modifier (
                           vehicle_repair_receipt_id,modifier_order,
                           modifier_code,modifier_value
                       )
                       VALUES (%s,1,'skill',1)""",
                    (receipt,),
                )
                connection.execute(
                    """INSERT INTO vehicle_repair_random_die (
                           vehicle_repair_receipt_id,roll_kind,
                           die_order,die_sides,face_value
                       )
                       VALUES
                           (%s,'work-duration',1,6,2),
                           (%s,'repair-cost',1,6,3),
                           (%s,'repair-cost',2,6,4)""",
                    (receipt, receipt, receipt),
                )
                connection.execute(
                    """UPDATE vehicle_repair_receipt
                       SET finalized=true,
                           applied_at='2030-04-01T00:00:00Z'
                       WHERE vehicle_repair_receipt_id=%s""",
                    (receipt,),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT current_hits,system_status
                           FROM vehicle_system_state
                           WHERE vehicle_system_state_id=%s""",
                        (system,),
                    ).fetchone(),
                    (0, "operational"),
                )


if __name__ == "__main__":
    unittest.main()
