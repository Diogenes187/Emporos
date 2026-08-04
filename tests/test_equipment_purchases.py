import os
import unittest
import uuid

import psycopg

from engine.campaigns import create_campaign_command
from engine.character_creation import initialize_character_command
from engine.commerce_setup import prepare_trading_command
from engine.equipment_purchases import purchase_personal_equipment_command
from engine.ammunition_purchases import purchase_personal_ammunition_command
from engine.ships import acquire_ship_command


class Fixed:
    def randint(self, low, high):
        return min(3, high)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL"
)
class EquipmentPurchaseTests(unittest.TestCase):
    def test_purchase_posts_ledger_and_creates_owned_custody(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix = str(uuid.uuid4())
                owner = "equipment-purchase-test"
                campaign = create_campaign_command(
                    connection, initiator_reference=owner,
                    idempotency_key="campaign-" + suffix, name="Outfitter"
                )
                actor = initialize_character_command(
                    connection, initiator_reference=owner,
                    idempotency_key="actor-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    character_name="Buyer", random_source=Fixed()
                )
                ship = acquire_ship_command(
                    connection, initiator_reference=owner,
                    idempotency_key="ship-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    owner_actor_public_id=actor.actor_public_id,
                    class_code="merchant-trader", ship_name="Locker"
                )
                prepare_trading_command(
                    connection, initiator_reference=owner,
                    idempotency_key="setup-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    ship_public_id=ship.ship_public_id, opening_balance=200
                )
                key = "blade-" + suffix
                result = purchase_personal_equipment_command(
                    connection, initiator_reference=owner,
                    idempotency_key=key,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    item_rule_code="equipment.weapon.blade"
                )
                replay = purchase_personal_equipment_command(
                    connection, initiator_reference=owner,
                    idempotency_key=key,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    item_rule_code="equipment.weapon.blade"
                )
                self.assertEqual(result.unit_price, 50)
                self.assertEqual(result.balance_after, 150)
                self.assertTrue(replay.replayed)
                state = connection.execute(
                    """SELECT holding.quantity,state.ready,owner.actor_id IS NOT NULL,
                              custody.actor_id IS NOT NULL
                       FROM inv_item_instance item
                       JOIN inv_item_owner owner USING(item_instance_id,campaign_id)
                       JOIN actor_item_holding holding ON holding.item_rule_id=item.item_rule_id
                                                       AND holding.actor_id=owner.actor_id
                       JOIN actor_weapon_state state ON state.actor_id=holding.actor_id
                                                    AND state.weapon_rule_id=holding.item_rule_id
                       JOIN inv_container_item placement USING(item_instance_id,campaign_id)
                       JOIN inv_actor_container custody USING(container_id,campaign_id)
                       WHERE item.public_id=%s""",
                    (result.item_public_id,),
                ).fetchone()
                self.assertEqual(state, (1, False, True, True))
                purchase_personal_equipment_command(
                    connection, initiator_reference=owner,
                    idempotency_key="bow-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    item_rule_code="equipment.weapon.bow"
                )
                ammunition = purchase_personal_ammunition_command(
                    connection, initiator_reference=owner,
                    idempotency_key="arrows-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    ammunition_rule_code="equipment.ammunition.bow.standard",
                    reload_units=2,
                )
                ammunition_replay = purchase_personal_ammunition_command(
                    connection, initiator_reference=owner,
                    idempotency_key="arrows-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    ammunition_rule_code="equipment.ammunition.bow.standard",
                    reload_units=2,
                )
                self.assertEqual(ammunition.total_price, 2)
                self.assertEqual(ammunition.supply_after, 2)
                self.assertEqual(ammunition.balance_after, 88)
                self.assertTrue(ammunition_replay.replayed)

    def test_insufficient_funds_creates_nothing(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                suffix = str(uuid.uuid4())
                owner = "equipment-poor-test"
                campaign = create_campaign_command(
                    connection, initiator_reference=owner,
                    idempotency_key="campaign-" + suffix, name="Poor outfitter"
                )
                actor = initialize_character_command(
                    connection, initiator_reference=owner,
                    idempotency_key="actor-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    character_name="Buyer", random_source=Fixed()
                )
                ship = acquire_ship_command(
                    connection, initiator_reference=owner,
                    idempotency_key="ship-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    owner_actor_public_id=actor.actor_public_id,
                    class_code="merchant-trader", ship_name="Locker"
                )
                prepare_trading_command(
                    connection, initiator_reference=owner,
                    idempotency_key="setup-" + suffix,
                    campaign_public_id=campaign.campaign_public_id,
                    actor_public_id=actor.actor_public_id,
                    ship_public_id=ship.ship_public_id, opening_balance=10
                )
                with self.assertRaisesRegex(ValueError, "Purchase costs"):
                    purchase_personal_equipment_command(
                        connection, initiator_reference=owner,
                        idempotency_key="armor-" + suffix,
                        campaign_public_id=campaign.campaign_public_id,
                        actor_public_id=actor.actor_public_id,
                        item_rule_code="equipment.armor.cloth"
                    )


if __name__ == "__main__":
    unittest.main()
