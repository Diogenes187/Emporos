import os
import unittest

import psycopg
from psycopg.errors import CheckViolation

from tests import test_space_combat_dodge


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class SpaceCombatSystemDamageStateTests(unittest.TestCase):
    def test_state_is_campaign_scoped_and_installation_bounded(self):
        helper=test_space_combat_dodge.SpaceCombatDodgeTests()
        helper.setUp()
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign,_,ships,_,_,_,_,_=helper.fixture(connection)
                class_id=connection.execute(
                    "SELECT ship_class_rule_id FROM ship_ship WHERE ship_id=%s",(ships[0],)
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO ship_class_weapon_mount(ship_class_rule_id,mount_code,mount_identifier,mount_count) VALUES(%s,'single-turret','damage-state',1)",
                    (class_id,),
                )
                connection.execute(
                    "INSERT INTO senc_ship_system_damage_state(ship_id,campaign_id,system_code,hit_count,system_status,attack_dm) VALUES(%s,%s,'turret',1,'damaged',-2)",
                    (ships[0],campaign),
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT hit_count,system_status,attack_dm FROM senc_ship_system_damage_state WHERE ship_id=%s AND system_code='turret'",
                        (ships[0],),
                    ).fetchone(),
                    (1,'damaged',-2),
                )
                with self.assertRaises(CheckViolation):
                    with connection.transaction():
                        connection.execute(
                            "INSERT INTO senc_ship_system_damage_state(ship_id,campaign_id,system_code,system_instance,hit_count,system_status) VALUES(%s,%s,'turret',2,1,'damaged')",
                            (ships[0],campaign),
                        )


if __name__ == "__main__": unittest.main()
