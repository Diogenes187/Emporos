import os
import unittest

import psycopg
from psycopg.errors import CheckViolation

from tests import test_space_combat_dodge


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class ShipCombatArmorStateTests(unittest.TestCase):
    def test_armor_is_campaign_state_bounded_by_class(self):
        helper=test_space_combat_dodge.SpaceCombatDodgeTests()
        helper.setUp()
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _,_,ships,_,_,_,_,_=helper.fixture(connection)
                ship_id=ships[0]
                maximum=connection.execute(
                    "SELECT armor_current FROM ship_ship WHERE ship_id=%s",(ship_id,)
                ).fetchone()[0]
                connection.execute(
                    "UPDATE ship_ship SET armor_current=greatest(0,armor_current-1) WHERE ship_id=%s",
                    (ship_id,),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT armor_current FROM ship_ship WHERE ship_id=%s",(ship_id,)
                    ).fetchone()[0],
                    max(0,maximum-1),
                )
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE ship_ship SET armor_current=%s WHERE ship_id=%s",
                            (maximum+1,ship_id),
                        )


if __name__ == "__main__": unittest.main()
