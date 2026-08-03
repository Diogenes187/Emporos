import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from tests import test_space_combat_dodge


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatSpecialScalingTests(unittest.TestCase):
    def setUp(self):
        self.helper = test_space_combat_dodge.SpaceCombatDodgeTests()
        self.helper.setUp()

    def task(self, connection, actor_id):
        command_id = connection.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key,command_status,completed_at)
               VALUES('resolve_actor_task','test','personal-scale-pulse','completed',clock_timestamp()) RETURNING command_id"""
        ).fetchone()[0]
        characteristic_id = connection.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.dexterity'"
        ).fetchone()[0]
        skill_id = connection.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'"
        ).fetchone()[0]
        difficulty_id = connection.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'"
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_actor_task_receipt(command_id,actor_id,characteristic_rule_id,skill_rule_id,
               difficulty_rule_id,skill_modifier,characteristic_modifier,difficulty_modifier,circumstance_modifier,
               species_modifier,check_total,target_number,effect,succeeded)
               VALUES(%s,%s,%s,%s,%s,0,0,0,-4,0,9,8,1,true)""",
            (command_id, actor_id, characteristic_id, skill_id, difficulty_id),
        )
        return command_id

    def test_special_profiles_and_personal_scale_damage_are_authoritative(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            profiles = connection.execute(
                """SELECT scaling_weapon_code,damage_dice_count,damage_multiplier,radiation_dice_count
                   FROM rule_space_combat_personal_scale_damage ORDER BY scaling_weapon_code"""
            ).fetchall()
            self.assertEqual(len(profiles), 10)
            self.assertIn(("meson-gun-bay", 5, 50, 4), profiles)
            self.assertIn(("sandcaster", 8, 1, 0), profiles)
            self.assertEqual(
                connection.execute(
                    """SELECT count(*) FROM rule_space_combat_special_weapon special
                       JOIN ship_weapon_definition weapon USING(weapon_rule_id)
                       WHERE weapon.weapon_kind='meson' AND special.force_internal_damage AND special.ignore_armor
                        AND special.additional_radiation_crew_hit"""
                ).fetchone()[0],
                1,
            )
            with connection.transaction(force_rollback=True):
                campaign, engagement, ships, pilots, vessels, round_id, action, _ = self.helper.fixture(connection)
                gunner_assignment = connection.execute(
                    """SELECT turn.crew_assignment_id FROM senc_action action
                       JOIN senc_crew_turn turn USING(crew_turn_id) WHERE action.space_combat_action_id=%s""",
                    (action,),
                ).fetchone()[0]
                gunner_actor = connection.execute(
                    "SELECT actor_id FROM ship_crew_assignment WHERE crew_assignment_id=%s",
                    (gunner_assignment,),
                ).fetchone()[0]
                target_actor = pilots[1][0]
                class_id = connection.execute(
                    "SELECT ship_class_rule_id FROM ship_ship WHERE ship_id=%s", (ships[0],)
                ).fetchone()[0]
                weapon_id = connection.execute(
                    "SELECT weapon_rule_id FROM ship_weapon_definition WHERE weapon_code='pulse-laser'"
                ).fetchone()[0]
                skill_id = connection.execute(
                    "SELECT rule_id FROM rule_rule WHERE rule_code='skill.turret-weapons'"
                ).fetchone()[0]
                connection.execute("INSERT INTO actor_skill VALUES(%s,%s,0)", (gunner_actor, skill_id))
                connection.execute(
                    """INSERT INTO ship_class_weapon(ship_class_rule_id,weapon_rule_id,mount_identifier,quantity,fire_control_tons)
                       VALUES(%s,%s,'personal-scale-test',1,0)""",
                    (class_id, weapon_id),
                )
                task_id = self.task(connection, gunner_actor)
                attack_id = connection.execute(
                    """INSERT INTO senc_personal_scale_attack_receipt(action_id,space_combat_round_id,engagement_id,
                       campaign_id,attacker_vessel_id,gunner_assignment_id,gunner_ship_id,target_actor_id,
                       scaling_weapon_code,weapon_rule_id,task_command_id,task_effect,hit)
                       VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'pulse-laser',%s,%s,1,true)
                       RETURNING personal_scale_attack_receipt_id""",
                    (action, round_id, engagement, campaign, vessels[0], gunner_assignment, ships[0],
                     target_actor, weapon_id, task_id),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO senc_personal_scale_damage_die VALUES(%s,'normal',1,4),(%s,'normal',2,5)",
                    (attack_id, attack_id),
                )
                receipt = connection.execute(
                    """INSERT INTO senc_personal_scale_damage_receipt(personal_scale_attack_receipt_id,target_actor_id,
                       normal_rolled_total,normal_damage,radiation_rolled_total,radiation_rads)
                       VALUES(%s,%s,9,450,0,0) RETURNING damage_instance_id""",
                    (attack_id, target_actor),
                ).fetchone()[0]
                self.assertEqual(
                    connection.execute(
                        "SELECT penetrating_damage FROM health_damage_instance WHERE damage_instance_id=%s", (receipt,)
                    ).fetchone()[0],
                    450,
                )
                with self.assertRaisesRegex(RaiseException, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM senc_personal_scale_damage_receipt WHERE personal_scale_attack_receipt_id=%s",
                            (attack_id,),
                        )


if __name__ == "__main__":
    unittest.main()
