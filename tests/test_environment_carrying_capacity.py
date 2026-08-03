import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, RaiseException


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class CarryingCapacityTests(unittest.TestCase):
    def test_load_bands_gravity_state_and_arithmetic_adjudication(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            self.assertEqual(
                connection.execute(
                    """SELECT load_band_code,strength_multiplier,physical_check_dm,movement_percent,
                              fixed_movement_millimeters,other_actions_allowed
                       FROM rule_carrying_load_band ORDER BY display_order"""
                ).fetchall(),
                [
                    ("light", 2, 0, 100, None, True),
                    ("medium", 4, -1, 75, None, True),
                    ("heavy", 6, -2, 75, None, True),
                    ("maximum", 12, None, None, 1500, False),
                ],
            )
            self.assertEqual(
                connection.execute(
                    """SELECT issue_status,published_value,calculated_value,engine_disposition
                       FROM src_issue WHERE issue_code='environment.carrying.maximum-load-example'"""
                ).fetchone(),
                ("resolved", "94 kg", "84 kg", "preserve_rule"),
            )
            self.assertEqual(
                connection.execute(
                    "SELECT strength_multiplier,movement_percent,favorable_capacity_multiplier,adverse_default_multiplier FROM rule_push_drag_capacity"
                ).fetchone(),
                (30, 50, 2.0, 0.5),
            )
            with connection.transaction(force_rollback=True):
                campaign = connection.execute(
                    "INSERT INTO camp_campaign(name) VALUES('Encumbrance test') RETURNING campaign_id"
                ).fetchone()[0]
                actor = connection.execute(
                    """INSERT INTO actor_actor(campaign_id,name,controller_reference)
                       VALUES(%s,'Porter','test') RETURNING actor_id""",
                    (campaign,),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value)
                       SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.strength'""",
                    (actor,),
                )
                receipt = connection.execute(
                    """INSERT INTO actor_encumbrance_receipt(actor_id,campaign_id,state_version_before,state_version_after,
                       strength_snapshot,carried_mass_grams,gravity_milligee,light_limit_grams,medium_limit_grams,
                       heavy_limit_grams,maximum_limit_grams,load_band_code,physical_check_dm,movement_percent,
                       fixed_movement_millimeters,other_actions_allowed)
                       VALUES(%s,%s,0,1,7,28000,1000,14000,28000,42000,84000,
                              'medium',-1,75,NULL,true) RETURNING actor_encumbrance_receipt_id""",
                    (actor, campaign),
                ).fetchone()[0]
                self.assertEqual(
                    connection.execute(
                        "SELECT load_band_code,physical_check_dm,movement_percent,concurrency_version FROM actor_encumbrance_state WHERE actor_id=%s",
                        (actor,),
                    ).fetchone(),
                    ("medium", -1, 75, 1),
                )
                with self.assertRaisesRegex(RaiseException, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM actor_encumbrance_receipt WHERE actor_encumbrance_receipt_id=%s", (receipt,)
                        )
                with self.assertRaisesRegex(CheckViolation, "require an immutable receipt"):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE actor_encumbrance_state SET carried_mass_grams=0 WHERE actor_id=%s", (actor,)
                        )


if __name__ == "__main__":
    unittest.main()
