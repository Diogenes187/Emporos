import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.armor_runtime import (
    apply_personal_armor_usage_command,
    equip_personal_armor_command,
    unequip_personal_armor_command,
)
from engine.commands import resolve_personal_attack_command


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalArmorRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.connection = psycopg.connect(DSN)
        self.campaign = self.connection.execute(
            "INSERT INTO camp_campaign(name) VALUES ('Armor Runtime') "
            "RETURNING campaign_id").fetchone()[0]
        self.actor_id, self.actor_public = self.connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Tester','player')
               RETURNING actor_id,public_id""", (self.campaign,)).fetchone()
        for code in ("characteristic.strength",
                     "characteristic.dexterity"):
            rule = self.connection.execute(
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (code,)).fetchone()[0]
            self.connection.execute(
                "INSERT INTO actor_characteristic VALUES (%s,%s,8,8)",
                (self.actor_id, rule))
        self.items = {}
        for code in ("ablat", "reflec", "battle-dress", "vacc-suit"):
            self.items[code] = self._item(code)

    def tearDown(self):
        self.connection.rollback()
        self.connection.close()

    def _item(self, code):
        rule = self.connection.execute(
            "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
            (f"equipment.armor.{code}",)).fetchone()[0]
        item_id, public = self.connection.execute(
            """INSERT INTO inv_item_instance(campaign_id,item_rule_id)
               VALUES (%s,%s) RETURNING item_instance_id,public_id""",
            (self.campaign, rule)).fetchone()
        self.connection.execute(
            """INSERT INTO inv_item_owner
               (item_instance_id,campaign_id,actor_id)
               VALUES (%s,%s,%s)""",
            (item_id, self.campaign, self.actor_id))
        return item_id, str(public)

    def test_layering_usage_and_replay_are_transactional(self):
        ablat = equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-ablat",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["ablat"][1], layer_order=1)
        reflec = equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-reflec",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["reflec"][1], layer_order=1)
        self.assertEqual(ablat.layers, ((self.items["ablat"][1], 1),))
        self.assertEqual(reflec.layers, (
            (self.items["reflec"][1], 1),
            (self.items["ablat"][1], 2),
        ))
        usage = apply_personal_armor_usage_command(
            self.connection, initiator_reference="player",
            idempotency_key="ablat-hit",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["ablat"][1], laser_hits=2)
        replay = apply_personal_armor_usage_command(
            self.connection, initiator_reference="player",
            idempotency_key="ablat-hit",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["ablat"][1], laser_hits=99)
        self.assertEqual((usage.laser_rating_before,
                          usage.laser_rating_after), (8, 6))
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.laser_rating_after, 6)
        removed = unequip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="remove-reflec",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["reflec"][1])
        self.assertEqual(removed.layers, ((self.items["ablat"][1], 1),))

    def test_laser_attack_resolves_layers_outside_in_and_degrades_ablat(self):
        equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-ablat-for-attack",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["ablat"][1], layer_order=1)
        equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-reflec-for-attack",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["reflec"][1], layer_order=1)
        result = resolve_personal_attack_command(
            self.connection,initiator_reference="player",
            idempotency_key="layered-laser-attack",
            item_rule_code="equipment.weapon.laser-pistol",
            attack_profile_code="pistol",range_rule_code="combat.range.short",
            armor_rule_code="combat.armor.unarmored",skill_modifier=0,
            characteristic_modifier=0,target_actor_public_id=str(self.actor_public),
            use_equipped_armor=True,random_source=FixedRandom((6,6,3,3,3,3)))
        self.assertEqual(result.receipt.armor_rating,22)
        self.assertEqual(result.receipt.penetrating_damage,0)
        layers=self.connection.execute(
            """SELECT layer_order,applicable_armor_rating,damage_before,damage_after
               FROM cmd_attack_armor_layer_receipt layer
               JOIN cmd_command command USING(command_id)
               WHERE command.public_id=%s ORDER BY layer_order""",
            (result.command_public_id,)).fetchall()
        self.assertEqual(layers,[(1,14,16,2),(2,8,2,0)])
        ablat_rating=self.connection.execute(
            """SELECT current_laser_armor_rating FROM inv_armor_instance_state
               WHERE item_instance_id=%s""",(self.items["ablat"][0],)).fetchone()[0]
        self.assertEqual(ablat_rating,7)

    def test_life_support_and_battle_dress_effective_values(self):
        equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-vacc",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["vacc-suit"][1], layer_order=1)
        usage = apply_personal_armor_usage_command(
            self.connection, initiator_reference="player",
            idempotency_key="use-air",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["vacc-suit"][1],
            life_support_seconds_used=3600)
        self.assertEqual((usage.life_support_before,
                          usage.life_support_after), (21600, 18000))
        unequip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="remove-vacc",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["vacc-suit"][1])
        equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-dress",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["battle-dress"][1], layer_order=1)
        values = self.connection.execute(
            """SELECT damage_tracking_value,armor_modifier,effective_value
               FROM actor_effective_armor_characteristic
               WHERE actor_id=%s ORDER BY characteristic_rule_id""",
            (self.actor_id,)).fetchall()
        self.assertEqual(values, [(8, 4, 12), (8, 4, 12)])

    def test_illegal_layers_and_direct_history_mutation_are_rejected(self):
        equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-ablat",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["ablat"][1], layer_order=1)
        with self.assertRaisesRegex(ValueError, "exactly one Reflec"):
            equip_personal_armor_command(
                self.connection, initiator_reference="player",
                idempotency_key="equip-vacc",
                actor_public_id=str(self.actor_public),
                item_public_id=self.items["vacc-suit"][1], layer_order=2)
        receipt = self.connection.execute(
            "SELECT command_id FROM cmd_personal_armor_equip_receipt LIMIT 1"
        ).fetchone()[0]
        with self.assertRaises(RaiseException):
            with self.connection.transaction():
                self.connection.execute(
                    """UPDATE cmd_personal_armor_equip_receipt
                       SET layer_count_before=1 WHERE command_id=%s""",
                    (receipt,))

    def test_direct_state_and_ownership_bypasses_are_rejected(self):
        equip_personal_armor_command(
            self.connection, initiator_reference="player",
            idempotency_key="equip-ablat",
            actor_public_id=str(self.actor_public),
            item_public_id=self.items["ablat"][1], layer_order=1)
        with self.assertRaises(RaiseException):
            with self.connection.transaction():
                self.connection.execute(
                    """UPDATE inv_item_owner SET actor_id=NULL
                       WHERE item_instance_id=%s""",
                    (self.items["ablat"][0],))
        with self.assertRaises(RaiseException):
            with self.connection.transaction():
                self.connection.execute(
                    """UPDATE inv_armor_instance_state
                       SET current_laser_armor_rating=7,
                           concurrency_version=2
                       WHERE item_instance_id=%s""",
                    (self.items["ablat"][0],))
                self.connection.execute("SET CONSTRAINTS ALL IMMEDIATE")


if __name__ == "__main__":
    unittest.main()
