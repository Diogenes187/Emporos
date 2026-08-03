import os
import unittest

import psycopg

from engine.ground_starship_runtime import (
    finalize_ground_starship_volley_command,
    resolve_ground_starship_volley_attacks_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class GroundStarshipRuntimeTests(unittest.TestCase):
    def test_successful_battery_volley_consumes_ammo_and_damages_hull(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = connection.execute(
                    """INSERT INTO camp_campaign(name,owner_reference)
                       VALUES ('Pulse Cannon Test','player')
                       RETURNING campaign_id""").fetchone()[0]
                actor_id = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Battery Commander','player')
                       RETURNING actor_id""", (campaign_id,)).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_characteristic
                       (actor_id,characteristic_rule_id,
                        maximum_value,current_value)
                       SELECT %s,rule_id,7,7 FROM rule_rule
                       WHERE rule_code='characteristic.dexterity'""",
                    (actor_id,))
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,0 FROM rule_rule
                       WHERE rule_code='skill.heavy-weapons'""", (actor_id,))
                location_rule = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,
                        rule_category,rule_status)
                       SELECT content_package_id,
                              'location.type.pulse-site',
                              'Pulse Site','world','approved'
                       FROM sys_content_package
                       WHERE package_code='cepheus-engine'
                       RETURNING rule_id""").fetchone()[0]
                connection.execute(
                    """INSERT INTO rule_location_type
                       VALUES (%s,'pulse-site',true,true)""",
                    (location_rule,))
                location_id = connection.execute(
                    """INSERT INTO loc_location
                       (campaign_id,location_type_rule_id,name)
                       VALUES (%s,%s,'Pulse Battery Site')
                       RETURNING location_id""",
                    (campaign_id, location_rule)).fetchone()[0]
                item_rule = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,
                        rule_category,rule_status)
                       SELECT content_package_id,'item.ship.pulse-target',
                              'Pulse Target Hull','equipment','approved'
                       FROM sys_content_package
                       WHERE package_code='cepheus-engine'
                       RETURNING rule_id""").fetchone()[0]
                connection.execute(
                    """INSERT INTO inv_item_definition
                       (rule_id,item_kind,minimum_tech_level,
                        cost_credits,mass_grams)
                       VALUES (%s,'equipment',9,1000000,NULL)""",
                    (item_rule,))
                item_id = connection.execute(
                    """INSERT INTO inv_item_instance
                       (campaign_id,item_rule_id,instance_name)
                       VALUES (%s,%s,'Target Hull')
                       RETURNING item_instance_id""",
                    (campaign_id, item_rule)).fetchone()[0]
                class_rule = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,
                        rule_category,rule_status)
                       SELECT content_package_id,'ship.class.pulse-target',
                              'Pulse Target Class','ship','approved'
                       FROM sys_content_package
                       WHERE package_code='cepheus-engine'
                       RETURNING rule_id""").fetchone()[0]
                connection.execute(
                    """INSERT INTO ship_class
                       (ship_class_rule_id,class_code,hull_tons,hull_points,
                        structure_points,minimum_tech_level,
                        construction_cost_minor)
                       VALUES (%s,'pulse-target',200,10,4,9,50000000)""",
                    (class_rule,))
                connection.execute(
                    """INSERT INTO ship_class_characteristic
                       VALUES (%s,'armor',1)""", (class_rule,))
                ship_public = connection.execute(
                    """INSERT INTO ship_ship
                       (campaign_id,ship_class_rule_id,
                        inventory_item_instance_id,name,
                        hull_current,structure_current)
                       VALUES (%s,%s,%s,'ISS Target',10,4)
                       RETURNING public_id""",
                    (campaign_id, class_rule, item_id)).fetchone()[0]
                battery_public = connection.execute(
                    """INSERT INTO gf_ground_weapon_battery
                       (campaign_id,battery_reference,location_id,
                        operator_actor_id,weapon_rule_id,
                        governing_skill_rule_id,
                        operational_weapon_count,ammunition_remaining)
                       SELECT %s,'Pulse Cannon Battery',%s,%s,
                              weapon.weapon_rule_id,skill.rule_id,4,10
                       FROM rule_vehicle_weapon_definition weapon
                       JOIN rule_rule weapon_rule
                         ON weapon_rule.rule_id=weapon.weapon_rule_id
                       JOIN rule_rule skill
                         ON skill.rule_code='skill.heavy-weapons'
                       WHERE weapon_rule.rule_code=
                             'vehicle.weapon.artillery-gun-tl-17'
                       RETURNING public_id""",
                    (campaign_id, location_id, actor_id)).fetchone()[0]
                volley = resolve_ground_starship_volley_attacks_command(
                    connection, initiator_reference="player",
                    idempotency_key="pulse-volley-attacks",
                    target_ship_public_id=str(ship_public),
                    target_range_code="medium",
                    batteries=((str(battery_public), 4),),
                    random_source=FixedRandom((6,) * 8),
                )
                self.assertEqual(volley.successful_attack_count, 4)
                self.assertEqual(volley.volley_status, "awaiting_primary")
                final = finalize_ground_starship_volley_command(
                    connection, initiator_reference="player",
                    idempotency_key="pulse-volley-final",
                    volley_command_public_id=volley.command_public_id,
                    primary_attack_order=1,
                    random_source=FixedRandom((6,) * 42),
                )
                self.assertEqual(final.combined_damage_dice, 42)
                self.assertEqual(final.personal_scale_damage, 252)
                self.assertEqual(final.converted_damage, 5)
                self.assertEqual(final.armor_rating, 1)
                self.assertEqual(final.hull_damage, 4)
                self.assertEqual((final.hull_before, final.hull_after), (10, 6))
                state = connection.execute(
                    """SELECT battery.ammunition_remaining,ship.hull_current,
                              count(damage.ship_damage_id)
                       FROM gf_ground_weapon_battery battery
                       CROSS JOIN ship_ship ship
                       LEFT JOIN ship_damage damage
                         ON damage.ship_id=ship.ship_id
                       WHERE battery.public_id=%s AND ship.public_id=%s
                       GROUP BY battery.ammunition_remaining,
                                ship.hull_current""",
                    (battery_public, ship_public)).fetchone()
                self.assertEqual(state, (6, 6, 1))
                replay = finalize_ground_starship_volley_command(
                    connection, initiator_reference="player",
                    idempotency_key="pulse-volley-final",
                    volley_command_public_id=volley.command_public_id,
                    primary_attack_order=1,
                )
                self.assertTrue(replay.replayed)
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "Ground-starship volley history is immutable",
                ):
                    connection.execute(
                        """UPDATE cmd_ground_starship_volley_final_receipt
                           SET armor_rating=0""")


if __name__ == "__main__":
    unittest.main()
