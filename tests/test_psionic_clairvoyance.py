import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import activate_psionic_power_command
from test_psionics import FixedRandom


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicClairvoyanceTests(unittest.TestCase):
    def _actor_and_location(self, connection):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Clairvoyance','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor, actor_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Seer','player') RETURNING actor_id,public_id""",
            (campaign,),
        ).fetchone()
        for code, maximum in (
            ("characteristic.psionic-strength", 10),
            ("characteristic.endurance", 8),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (actor, maximum, maximum, code),
            )
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               SELECT %s,rule_id,5 FROM rule_rule
               WHERE rule_code='skill.psionic-clairvoyance'""",
            (actor,),
        )
        type_id = connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,'location.type.clairvoyance-test',
                      'Clairvoyance Test','world','approved'
                 FROM sys_content_package
                WHERE package_code='cepheus-engine'
                ORDER BY content_package_id LIMIT 1 RETURNING rule_id"""
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO rule_location_type VALUES
               (%s,'clairvoyance-test',true,true)""",
            (type_id,),
        )
        location_public = connection.execute(
            """INSERT INTO loc_location
               (campaign_id,location_type_rule_id,name)
               VALUES (%s,%s,'Sealed room') RETURNING public_id""",
            (campaign, type_id),
        ).fetchone()[0]
        return str(actor_public), str(location_public)

    def test_four_power_mechanics_are_exact(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT power.power_code,mechanic.sensory_vision,
                          mechanic.sensory_hearing,mechanic.snapshot_only,
                          mechanic.effect_controls_detail,
                          mechanic.effect_controls_duration_rounds,
                          mechanic.undetectable_by_others,
                          mechanic.targets_location
                   FROM rule_psi_clairvoyance_power mechanic
                   JOIN psi_power power
                     ON power.power_rule_id=mechanic.power_rule_id
                   ORDER BY power.display_order"""
            ).fetchall()
        self.assertEqual(rows, [
            ("sense", False, False, True, False, False, True, True),
            ("clairvoyance", True, False, False, True, True, True, True),
            ("clairaudience", False, True, False, True, True, True, True),
            ("clairsentience", True, True, False, True, True, True, True),
        ])

    def test_remote_viewing_records_location_effect_and_referee_evidence(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                actor_public, location_public = self._actor_and_location(
                    connection)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="clairvoyance-observe",
                    actor_public_id=actor_public,
                    power_rule_code="psionics.power.clairsentience",
                    range_rule_code="psionics.range.short",
                    target_location_public_id=location_public,
                    clairvoyant_observation=(
                        "Two guards speak beside a sealed hatch."
                    ),
                    clairvoyant_maintained_rounds=3,
                    random_source=FixedRandom((6, 6, 4)),
                )
                receipt = connection.execute(
                    """SELECT effect_snapshot,timing_rounds_snapshot,
                              sensory_vision,sensory_hearing,snapshot_only,
                              maintained_rounds,referee_observation
                       FROM cmd_psi_clairvoyant_observation_receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                self.assertEqual(
                    receipt,
                    (8, 4, True, True, False, 3,
                     "Two guards speak beside a sealed hatch."),
                )
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_psi_clairvoyant_observation_receipt"
                        )


if __name__ == "__main__":
    unittest.main()
