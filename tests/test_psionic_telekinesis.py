import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import activate_psionic_power_command


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicTelekinesisTests(unittest.TestCase):
    def _actors_and_item(self, connection):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Telekinesis','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor, actor_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Mover','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        for code, value in (
            ("characteristic.psionic-strength", 15),
            ("characteristic.endurance", 8),
            ("characteristic.dexterity", 8),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (actor, value, value, code),
            )
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,4 FROM rule_rule
               WHERE rule_code='skill.psionic-telekinesis'""",
            (actor,),
        )
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,2 FROM rule_rule
               WHERE rule_code='skill.athletics'""",
            (actor,),
        )
        target_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Target','referee') RETURNING public_id""",
            (campaign,),
        ).fetchone()[0]
        creature_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Thrown Creature','referee') RETURNING public_id""",
            (campaign,),
        ).fetchone()[0]
        item_rule = connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,'equipment.psi-test-weight',
                      'Test Weight','equipment','approved'
                 FROM sys_content_package
                WHERE package_code='cepheus-engine'
                ORDER BY content_package_id LIMIT 1 RETURNING rule_id"""
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO inv_item_definition
               VALUES (%s,'equipment',0,1,500)""",
            (item_rule,),
        )
        item_public = connection.execute(
            """INSERT INTO inv_item_instance(campaign_id,item_rule_id)
               VALUES (%s,%s) RETURNING public_id""",
            (campaign, item_rule),
        ).fetchone()[0]
        return (
            str(actor_public), str(item_public), str(target_public),
            str(creature_public),
        )

    def test_system_and_six_mass_profiles_are_exact(self):
        with psycopg.connect(DSN) as connection:
            system = connection.execute(
                """SELECT physical_manipulation_equivalent,
                          physical_danger_feedback,pain_feedback,
                          limited_manipulation_sensory_awareness,
                          effect_determines_duration_rounds,
                          throwing_uses_greater_distance,
                          effect_added_to_throw_damage,
                          creature_and_target_take_equal_damage
                   FROM rule_psi_telekinesis_system"""
            ).fetchone()
            profiles = connection.execute(
                """SELECT profile.maximum_mass_grams,
                          profile.throwing_damage_dice_count,
                          profile.throwing_damage_die_sides,
                          profile.throwing_damage_flat,
                          profile.can_inflict_throwing_damage
                   FROM rule_psi_telekinesis_mass_profile profile
                   ORDER BY profile.maximum_mass_grams"""
            ).fetchall()
        self.assertEqual(
            system,
            (True, False, False, True, True, True, True, True),
        )
        self.assertEqual(profiles, [
            (10, None, None, None, False),
            (100, None, None, None, False),
            (1000, None, None, 1, True),
            (10000, 1, 6, None, True),
            (100000, 2, 6, None, True),
            (1000000, 8, 6, None, True),
        ])

    def test_item_manipulation_is_mass_validated_and_immutable(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor_public, item_public, _, _ = self._actors_and_item(
                    connection)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="telekinesis-lift",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.lift-1kg",
                    range_rule_code="psionics.range.personal",
                    telekinetic_item_public_id=item_public,
                    telekinetic_duration_rounds=4,
                    random_source=FixedRandom((6, 6, 3)),
                )
                receipt = connection.execute(
                    """SELECT target_kind,mass_grams_snapshot,
                              maximum_mass_grams_snapshot,duration_rounds
                       FROM cmd_psi_telekinetic_manipulation_receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, ("item", 500, 1000, 4))
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """DELETE FROM
                               cmd_psi_telekinetic_manipulation_receipt"""
                        )

    def test_item_throw_uses_greater_distance_and_throw_effect(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor_public, item_public, target_public, _ = (
                    self._actors_and_item(connection))
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="telekinesis-item-throw",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.lift-1kg",
                    range_rule_code="psionics.range.personal",
                    telekinetic_item_public_id=item_public,
                    telekinetic_duration_rounds=2,
                    telekinetic_throw_target_actor_public_id=target_public,
                    telekinetic_psion_to_target_metres=1,
                    telekinetic_object_origin_to_target_metres=2,
                    telekinetic_throw_range_rule_code="combat.range.close",
                    random_source=FixedRandom((6, 6, 3, 4, 5)),
                )
                receipt = connection.execute(
                    """SELECT selected_distance_metres,skill_modifier,
                              attack_total,attack_effect,hit,rolled_damage,
                              effect_damage,raw_damage,thrown_creature_damage
                       FROM cmd_psi_telekinetic_throw_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=receipt.activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(
                    receipt, (2, 2, 11, 3, True, 1, 3, 4, None))

    def test_creature_throw_mirrors_raw_damage(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor_public, _, target_public, creature_public = (
                    self._actors_and_item(connection))
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="telekinesis-creature-throw",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.lift-100kg",
                    range_rule_code="psionics.range.personal",
                    telekinetic_creature_public_id=creature_public,
                    telekinetic_creature_mass_grams=70000,
                    telekinetic_duration_rounds=3,
                    telekinetic_throw_target_actor_public_id=target_public,
                    telekinetic_psion_to_target_metres=1,
                    telekinetic_object_origin_to_target_metres=2,
                    telekinetic_throw_range_rule_code="combat.range.close",
                    random_source=FixedRandom((6, 6, 2, 6, 6, 4, 5)),
                )
                receipt = connection.execute(
                    """SELECT damage_dice_count,rolled_damage,effect_damage,
                              raw_damage,thrown_creature_damage
                       FROM cmd_psi_telekinetic_throw_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=receipt.activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(receipt, (2, 9, 6, 15, 15))


if __name__ == "__main__":
    unittest.main()
