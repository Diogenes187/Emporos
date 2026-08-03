from __future__ import annotations

import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation

from engine.encounters import (
    add_encounter_participant_command,
    create_encounter_command,
    transition_encounter_mode_command,
)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class EncounterAggregateStateTests(unittest.TestCase):
    def fixture(self, connection):
        campaign, campaign_public = connection.execute(
            """INSERT INTO camp_campaign(name,owner_reference)
               VALUES ('Aggregate Encounter','referee')
               RETURNING campaign_id,public_id"""
        ).fetchone()
        actors = []
        for name, controller in (
            ("Player", "player"),
            ("Opponent", "referee"),
        ):
            actors.append(
                connection.execute(
                    """INSERT INTO actor_actor (
                           campaign_id,name,controller_reference
                       )
                       VALUES (%s,%s,%s)
                       RETURNING actor_id,public_id""",
                    (campaign, name, controller),
                ).fetchone()
            )
        encounter = create_encounter_command(
            connection,
            initiator_reference="referee",
            idempotency_key="aggregate-create",
            campaign_public_id=str(campaign_public),
            encounter_type_code="routine",
        )
        for index, (actor, role, side) in enumerate(
            (
                (actors[0], "player_character", "party"),
                (actors[1], "non_player_character", "opposition"),
            )
        ):
            add_encounter_participant_command(
                connection,
                initiator_reference="referee",
                idempotency_key=f"aggregate-add-{index}",
                encounter_public_id=encounter.encounter_public_id,
                actor_public_id=str(actor[1]),
                participant_role=role,
                side_code=side,
            )
        encounter_id = connection.execute(
            """SELECT encounter_id
               FROM enc_encounter WHERE public_id=%s""",
            (encounter.encounter_public_id,),
        ).fetchone()[0]
        return campaign, encounter, encounter_id, actors

    def test_campaign_sides_objectives_intentions_and_outcome(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign, encounter, encounter_id, actors = (
                    self.fixture(connection)
                )
                other_campaign = connection.execute(
                    """INSERT INTO camp_campaign(name,owner_reference)
                       VALUES ('Other Campaign','other')
                       RETURNING campaign_id"""
                ).fetchone()[0]
                other_actor = connection.execute(
                    """INSERT INTO actor_actor (
                           campaign_id,name,controller_reference
                       )
                       VALUES (%s,'Outsider','other')
                       RETURNING actor_id""",
                    (other_campaign,),
                ).fetchone()[0]
                with self.assertRaises(ForeignKeyViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO enc_participant (
                                   encounter_id,campaign_id,actor_id,
                                   participant_role,side_code
                               )
                               VALUES (
                                   %s,%s,%s,'other','party'
                               )""",
                            (
                                encounter_id, campaign,
                                other_actor,
                            ),
                        )

                objectives = []
                for order, values in enumerate(
                    (
                        (
                            "party", "defeat", "side",
                            None, "opposition",
                        ),
                        (
                            "opposition", "escape", "none",
                            None, None,
                        ),
                    ),
                    1,
                ):
                    objectives.append(
                        connection.execute(
                            """INSERT INTO enc_objective (
                                   encounter_id,campaign_id,
                                   objective_order,owner_kind,
                                   owner_side_code,objective_kind,
                                   target_kind,target_actor_id,
                                   target_side_code
                               )
                               VALUES (
                                   %s,%s,%s,'side',%s,%s,%s,%s,%s
                               )
                               RETURNING encounter_objective_id""",
                            (
                                encounter_id, campaign, order,
                                *values,
                            ),
                        ).fetchone()[0]
                    )
                connection.execute(
                    """INSERT INTO enc_participant_intention (
                           encounter_id,campaign_id,actor_id,
                           intention_order,intention_kind,
                           target_kind,target_side_code
                       )
                       VALUES
                           (%s,%s,%s,1,'attack','side','opposition'),
                           (%s,%s,%s,1,'flee','none',NULL)""",
                    (
                        encounter_id, campaign, actors[0][0],
                        encounter_id, campaign, actors[1][0],
                    ),
                )
                resolution = connection.execute(
                    """INSERT INTO enc_resolution (
                           encounter_id,campaign_id,outcome_kind,
                           winning_side_code,resolution_summary
                       )
                       VALUES (
                           %s,%s,'decisive','party',
                           'The opposition withdraws.'
                       )
                       RETURNING encounter_resolution_id""",
                    (encounter_id, campaign),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO enc_objective_result (
                           encounter_resolution_id,encounter_id,
                           campaign_id,encounter_objective_id,
                           result_status
                       )
                       VALUES (%s,%s,%s,%s,'achieved')""",
                    (
                        resolution, encounter_id,
                        campaign, objectives[0],
                    ),
                )
                with self.assertRaisesRegex(
                    CheckViolation,
                    "objective results do not reconcile",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE enc_resolution
                               SET finalized=true,
                                   resolved_at=clock_timestamp()
                               WHERE encounter_resolution_id=%s""",
                            (resolution,),
                        )
                connection.execute(
                    """INSERT INTO enc_objective_result (
                           encounter_resolution_id,encounter_id,
                           campaign_id,encounter_objective_id,
                           result_status
                       )
                       VALUES (%s,%s,%s,%s,'failed')""",
                    (
                        resolution, encounter_id,
                        campaign, objectives[1],
                    ),
                )
                connection.execute(
                    """UPDATE enc_resolution
                       SET finalized=true,
                           resolved_at=clock_timestamp()
                       WHERE encounter_resolution_id=%s""",
                    (resolution,),
                )
                summary = connection.execute(
                    """SELECT encounter_status,side_count,
                              participant_count,
                              active_objective_count,
                              current_intention_count,
                              outcome_kind,winning_side_code,
                              outcome_finalized
                       FROM enc_current_summary
                       WHERE encounter_id=%s""",
                    (encounter_id,),
                ).fetchone()
                self.assertEqual(
                    summary,
                    (
                        "resolved", 2, 2, 0, 0,
                        "decisive", "party", True,
                    ),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE enc_objective_result
                               SET result_status='abandoned'
                               WHERE encounter_resolution_id=%s
                                 AND encounter_objective_id=%s""",
                            (resolution, objectives[1]),
                        )

    def test_general_resolution_completes_personal_combat(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign, encounter, encounter_id, _ = (
                    self.fixture(connection)
                )
                transition_encounter_mode_command(
                    connection,
                    initiator_reference="referee",
                    idempotency_key="aggregate-combat-transition",
                    encounter_public_id=encounter.encounter_public_id,
                    to_mode="personal_combat",
                    reason="Negotiations fail.",
                )
                connection.execute(
                    """INSERT INTO enc_personal_combat(encounter_id)
                       VALUES (%s)""",
                    (encounter_id,),
                )
                resolution = connection.execute(
                    """INSERT INTO enc_resolution (
                           encounter_id,campaign_id,outcome_kind
                       )
                       VALUES (%s,%s,'negotiated')
                       RETURNING encounter_resolution_id""",
                    (encounter_id, campaign),
                ).fetchone()[0]
                connection.execute(
                    """UPDATE enc_resolution
                       SET finalized=true,
                           resolved_at=clock_timestamp()
                       WHERE encounter_resolution_id=%s""",
                    (resolution,),
                )
                self.assertEqual(
                    connection.execute(
                        """SELECT combat_status,completed_at IS NOT NULL
                           FROM enc_personal_combat
                           WHERE encounter_id=%s""",
                        (encounter_id,),
                    ).fetchone(),
                    ("completed", True),
                )


if __name__ == "__main__":
    unittest.main()
