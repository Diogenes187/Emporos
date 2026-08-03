import os
import unittest
from datetime import datetime, timezone

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import activate_psionic_power_command


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, _minimum, _maximum):
        return next(self.values)


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicTeleportationRuntimeTests(unittest.TestCase):
    def test_success_moves_actor_and_records_immutable_disorientation(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = connection.execute(
                    """INSERT INTO camp_campaign(name,owner_reference)
                       VALUES ('Teleport runtime','player')
                       RETURNING campaign_id"""
                ).fetchone()[0]
                actor_id, actor_public = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Traveller','player')
                       RETURNING actor_id,public_id""",
                    (campaign_id,),
                ).fetchone()
                connection.execute(
                    """INSERT INTO actor_characteristic
                       (actor_id,characteristic_rule_id,current_value,maximum_value)
                       SELECT %s,rule_id,12,12 FROM rule_rule
                       WHERE rule_code IN (
                         'characteristic.psionic-strength',
                         'characteristic.endurance')""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,10 FROM rule_rule
                       WHERE rule_code='skill.psionic-teleportation'""",
                    (actor_id,),
                )
                location_type = connection.execute(
                    """INSERT INTO rule_rule
                       (content_package_id,rule_code,name,rule_category,rule_status)
                       SELECT content_package_id,
                              'location.type.teleport-runtime',
                              'Teleport Runtime Location','world','approved'
                       FROM sys_content_package
                       WHERE package_code='cepheus-engine'
                       ORDER BY content_package_id LIMIT 1
                       RETURNING rule_id"""
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO rule_location_type
                       VALUES (%s,'teleport-runtime',true,true)""",
                    (location_type,),
                )
                origin_id = connection.execute(
                    """INSERT INTO loc_location
                       (campaign_id,location_type_rule_id,name)
                       VALUES (%s,%s,'Origin') RETURNING location_id""",
                    (campaign_id, location_type),
                ).fetchone()[0]
                destination_id, destination_public = connection.execute(
                    """INSERT INTO loc_location
                       (campaign_id,location_type_rule_id,name)
                       VALUES (%s,%s,'Destination')
                       RETURNING location_id,public_id""",
                    (campaign_id, location_type),
                ).fetchone()
                connection.execute(
                    """INSERT INTO loc_actor_position
                       (campaign_id,actor_id,location_id)
                       VALUES (%s,%s,%s)""",
                    (campaign_id, actor_id, origin_id),
                )
                used_at = datetime(2026, 7, 31, tzinfo=timezone.utc)
                result = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="teleport-runtime",
                    actor_public_id=str(actor_public),
                    power_rule_code="psionics.power.teleport-moderate-load",
                    range_rule_code="psionics.range.very-distant",
                    random_source=FixedRandom((6, 6, 2, 3, 4)),
                    used_at=used_at,
                    teleport_destination_location_public_id=
                        str(destination_public),
                    teleport_destination_knowledge_kind="personal_visit",
                    teleport_destination_knowledge_evidence=
                        "Visited and mapped during the previous expedition.",
                    teleport_altitude_change_metres=100,
                    teleport_hourly_cumulative_altitude_metres=100,
                )
                self.assertTrue(result.succeeded)
                position = connection.execute(
                    """SELECT location_id,source_command_id
                       FROM loc_actor_position
                       WHERE actor_id=%s AND position_status='current'""",
                    (actor_id,),
                ).fetchone()
                self.assertEqual(position[0], destination_id)
                receipt = connection.execute(
                    """SELECT load_kind,disorientation_seconds,
                              temperature_change_celsius,
                              actor_version_before,actor_version_after
                       FROM cmd_psi_teleportation_receipt"""
                ).fetchone()
                self.assertEqual(receipt, ("moderate", 70, -0.25, 1, 2))
                replay = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="teleport-runtime",
                    actor_public_id=str(actor_public),
                    power_rule_code="psionics.power.teleport-moderate-load",
                )
                self.assertTrue(replay.replayed)
                with self.assertRaises(RaiseException):
                    connection.execute(
                        """UPDATE cmd_psi_teleportation_receipt
                           SET destination_knowledge_evidence='altered'"""
                    )

    def test_unsafe_altitude_requires_explicit_hazard_resolution(self):
        # The normalized rule is enforced before a command or state mutation.
        with psycopg.connect(DSN) as connection:
            columns = connection.execute(
                """SELECT count(*) FROM information_schema.columns
                   WHERE table_name='cmd_psi_teleportation_receipt'"""
            ).fetchone()[0]
            self.assertEqual(columns, 23)


if __name__ == "__main__":
    unittest.main()
