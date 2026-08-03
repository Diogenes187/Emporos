import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.combat_runtime import (
    aim_personal_attack_command, begin_personal_turn_command,
    declare_personal_attack_command,
)
from engine.commands import resolve_personal_attack_command
from tests import test_combat_runtime as combat_tests


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "requires the project PostgreSQL database")
class PersonalWeaponAssistanceTests(unittest.TestCase):
    def _setup(self, connection):
        encounter, actors = combat_tests.PersonalCombatRuntimeIntegrationTests()._initialized_combat(
            connection)
        actor_id, campaign_id = connection.execute(
            "SELECT actor_id,campaign_id FROM actor_actor WHERE public_id=%s",
            (actors[0],),
        ).fetchone()
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,1 FROM rule_rule
               WHERE rule_code='skill.slug-pistol'""", (actor_id,))
        connection.execute(
            """INSERT INTO actor_weapon_state
               (actor_id,weapon_rule_id,ready,rounds_loaded,
                loaded_ammunition_rule_id)
               SELECT %s,weapon.rule_id,true,15,ammunition.rule_id
               FROM rule_rule weapon CROSS JOIN rule_rule ammunition
               WHERE weapon.rule_code='equipment.weapon.auto-pistol'
                 AND ammunition.rule_code=
                     'equipment.ammunition.auto-pistol.standard'""", (actor_id,))
        container_id = connection.execute(
            "INSERT INTO inv_container(campaign_id,name) VALUES (%s,'Holster') "
            "RETURNING container_id", (campaign_id,)).fetchone()[0]
        connection.execute(
            "INSERT INTO inv_actor_container VALUES (%s,%s,%s)",
            (container_id, campaign_id, actor_id))
        weapon_id, weapon_public = connection.execute(
            """INSERT INTO inv_item_instance
               (campaign_id,item_rule_id,instance_name)
               SELECT %s,rule_id,'Assisted auto-pistol' FROM rule_rule
               WHERE rule_code='equipment.weapon.auto-pistol'
               RETURNING item_instance_id,public_id""", (campaign_id,)).fetchone()
        connection.execute(
            "INSERT INTO inv_container_item VALUES (%s,%s,%s,DEFAULT,NULL)",
            (weapon_id, campaign_id, container_id))
        for code in ("laser-sights", "intelligent-weapon"):
            option_rule, cost, mass = connection.execute(
                """SELECT option.rule_id,option.canonical_cost_credits,
                          option.listed_mass_grams
                   FROM rule_book1_ranged_weapon_option option
                   WHERE option.option_code=%s""", (code,)).fetchone()
            option_item = connection.execute(
                """INSERT INTO inv_item_instance
                   (campaign_id,item_rule_id,instance_name)
                   VALUES (%s,%s,%s) RETURNING item_instance_id""",
                (campaign_id, option_rule, code)).fetchone()[0]
            connection.execute(
                """INSERT INTO cmd_book1_ranged_weapon_option_receipt
                   (idempotency_key,campaign_id,weapon_item_instance_id,
                    option_item_instance_id,option_rule_id,
                    installed_cost_credits,installed_mass_grams)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (f"assist-{campaign_id}-{code}", campaign_id, weapon_id,
                 option_item, option_rule, cost, mass))
        return encounter, actors, str(weapon_public)

    def _declare(self, connection, encounter, actors, weapon_public, **kwargs):
        return declare_personal_attack_command(
            connection, initiator_reference="player",
            idempotency_key=kwargs.pop("idempotency_key", "assist-declare"),
            encounter_public_id=encounter,
            attacker_actor_public_id=actors[0],
            target_actor_public_id=actors[1],
            item_rule_code="equipment.weapon.auto-pistol",
            attack_profile_code="pistol",
            range_rule_code="combat.range.short",
            weapon_item_instance_public_id=weapon_public,
            **kwargs,
        )

    def test_installed_assistance_is_frozen_and_applied(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors, weapon = self._setup(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="assist-begin",
                    encounter_public_id=encounter, actor_public_id=actors[0])
                aim_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="assist-aim",
                    encounter_public_id=encounter, actor_public_id=actors[0],
                    target_actor_public_id=actors[1])
                declared = self._declare(connection, encounter, actors, weapon)
                assistance = connection.execute(
                    """SELECT laser_sight_modifier,intelligent_weapon_modifier,
                              intelligent_weapon_suppressed
                       FROM enc_personal_attack_weapon_assistance assistance
                       JOIN enc_personal_attack attack USING(personal_attack_id)
                       WHERE attack.public_id=%s""",
                    (declared.personal_attack_public_id,)).fetchone()
                self.assertEqual(assistance, (1, 1, False))
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="assist-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=combat_tests.FixedRandom((3, 3, 3, 3)))
                self.assertEqual(resolved.receipt.circumstance_modifiers.count(1), 3)
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE enc_personal_attack_weapon_assistance
                               SET intelligent_weapon_modifier=0
                               WHERE personal_attack_id=(SELECT personal_attack_id
                                 FROM enc_personal_attack WHERE public_id=%s)""",
                            (declared.personal_attack_public_id,))

    def test_referee_reason_can_suppress_intelligent_weapon(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                encounter, actors, weapon = self._setup(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="suppress-begin",
                    encounter_public_id=encounter, actor_public_id=actors[0])
                declared = self._declare(
                    connection, encounter, actors, weapon,
                    idempotency_key="suppress-declare",
                    intelligent_weapon_suppressed=True,
                    intelligent_weapon_suppression_referee_reference="referee",
                    intelligent_weapon_suppression_reason=(
                        "Targeting conditions exceed program tolerance."))
                row = connection.execute(
                    """SELECT laser_sight_modifier,intelligent_weapon_modifier,
                              suppression_referee_reference,suppression_reason
                       FROM enc_personal_attack_weapon_assistance assistance
                       JOIN enc_personal_attack attack USING(personal_attack_id)
                       WHERE attack.public_id=%s""",
                    (declared.personal_attack_public_id,)).fetchone()
                self.assertEqual(row[:3], (0, 0, "referee"))
                self.assertIn("tolerance", row[3])


if __name__ == "__main__":
    unittest.main()
