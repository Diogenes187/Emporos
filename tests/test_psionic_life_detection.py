import os
import unittest

import psycopg
from psycopg.errors import RaiseException

from engine.psionics import (
    LifeDetectionObservation,
    activate_psionic_power_command,
    set_telepathic_shield_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PsionicLifeDetectionTests(unittest.TestCase):
    def _actors(self, connection):
        campaign = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Life Detection','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actors = []
        for name, controller in (
            ("Detector", "player"),
            ("Known Contact", "referee"),
            ("Shielded Telepath", "referee"),
        ):
            actors.append(connection.execute(
                """INSERT INTO actor_actor
                   (campaign_id,name,controller_reference)
                   VALUES (%s,%s,%s) RETURNING actor_id,public_id""",
                (campaign, name, controller),
            ).fetchone())
        detector_id, detector_public = actors[0]
        for code, value in (
            ("characteristic.psionic-strength", 10),
            ("characteristic.endurance", 8),
        ):
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,%s,%s FROM rule_rule WHERE rule_code=%s""",
                (detector_id, value, value, code),
            )
        telepathy_skill = connection.execute(
            """SELECT rule_id FROM rule_rule
               WHERE rule_code='skill.psionic-telepathy'"""
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
               VALUES (%s,%s,2),(%s,%s,1)""",
            (detector_id, telepathy_skill, actors[2][0], telepathy_skill),
        )
        set_telepathic_shield_command(
            connection,
            initiator_reference="player",
            idempotency_key="lower-life-detection-shield",
            actor_public_id=str(detector_public),
            shield_raised=False,
        )
        return tuple(str(row[1]) for row in actors)

    def test_mechanics_and_normalized_detected_minds(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                detector, known, _ = self._actors(connection)
                result = activate_psionic_power_command(
                    connection,
                    initiator_reference="player",
                    idempotency_key="life-detection",
                    actor_public_id=detector,
                    power_rule_code="psionics.power.life-detection",
                    range_rule_code="psionics.range.short",
                    life_detection_area_reference="sealed cargo bay",
                    life_detection_referee_summary=(
                        "Two significant minds are present."
                    ),
                    life_detection_observations=(
                        LifeDetectionObservation(
                            "human", "behind the portside partition", known,
                            True, "The detector knows this contact personally",
                        ),
                        LifeDetectionObservation(
                            "animal", "inside the forward cargo cage",
                        ),
                    ),
                    random_source=FixedRandom((4, 4, 3)),
                )
                header = connection.execute(
                    """SELECT effect_snapshot,timing_rounds_snapshot,
                              search_area_reference,detected_mind_count
                       FROM cmd_psi_life_detection_receipt receipt
                       JOIN cmd_command command
                         ON command.command_id=activation_command_id
                       WHERE command.public_id=%s""",
                    (result.command_public_id,),
                ).fetchone()
                minds = connection.execute(
                    """SELECT general_mind_type,approximate_location,
                              recognized_known_individual,recognition_basis
                       FROM cmd_psi_life_detection_mind mind
                       JOIN cmd_command command
                         ON command.command_id=mind.activation_command_id
                       WHERE command.public_id=%s ORDER BY mind_order""",
                    (result.command_public_id,),
                ).fetchall()
                self.assertEqual(
                    header, (7, 3, "sealed cargo bay", 2))
                self.assertEqual(minds, [
                    (
                        "human", "behind the portside partition", True,
                        "The detector knows this contact personally",
                    ),
                    ("animal", "inside the forward cargo cage", False, None),
                ])
                connection.execute("SET CONSTRAINTS ALL IMMEDIATE")
                with self.assertRaises(RaiseException):
                    with connection.transaction():
                        connection.execute(
                            "DELETE FROM cmd_psi_life_detection_mind")

    def test_shielded_telepath_cannot_be_recorded_as_detected(self):
        with psycopg.connect(DSN) as connection:
            with connection.transaction(force_rollback=True):
                detector, _, shielded = self._actors(connection)
                with self.assertRaisesRegex(
                    ValueError, "Shielded minds are undetectable"
                ):
                    activate_psionic_power_command(
                        connection,
                        initiator_reference="player",
                        idempotency_key="detect-shielded",
                        actor_public_id=detector,
                        power_rule_code="psionics.power.life-detection",
                        range_rule_code="psionics.range.short",
                        life_detection_area_reference="briefing room",
                        life_detection_referee_summary="One mind.",
                        life_detection_observations=(
                            LifeDetectionObservation(
                                "human", "at the table", shielded),
                        ),
                        random_source=FixedRandom((6, 6, 2)),
                    )


if __name__ == "__main__":
    unittest.main()
