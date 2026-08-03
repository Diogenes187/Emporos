import os
import unittest

import psycopg
from psycopg.errors import ForeignKeyViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class IdentityCampaignIntegrationTests(unittest.TestCase):
    def test_legacy_references_create_relational_authority_and_clock(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Relational Campaign','referee-one')
                       RETURNING campaign_id"""
                ).fetchone()[0]
                actor_id = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Controlled Actor','player-one')
                       RETURNING actor_id""",
                    (campaign_id,),
                ).fetchone()[0]

                clock = connection.execute(
                    """SELECT day_number,second_of_day,concurrency_version
                       FROM camp_clock WHERE campaign_id=%s""",
                    (campaign_id,),
                ).fetchone()
                self.assertEqual(clock, (0, 0, 1))
                self.assertEqual(
                    connection.execute(
                        """SELECT count(*) FROM camp_installed_package
                           WHERE campaign_id=%s
                             AND installation_status='active'""",
                        (campaign_id,),
                    ).fetchone()[0],
                    1,
                )
                memberships = connection.execute(
                    """SELECT account.account_reference,role.role_code
                       FROM iam_campaign_membership membership
                       JOIN iam_account account
                         ON account.account_id=membership.account_id
                       JOIN iam_role role ON role.role_id=membership.role_id
                       WHERE membership.campaign_id=%s
                         AND membership.membership_status='active'
                       ORDER BY account.account_reference,role.role_code""",
                    (campaign_id,),
                ).fetchall()
                self.assertEqual(
                    memberships,
                    [("player-one", "player"),
                     ("referee-one", "referee")],
                )
                controller = connection.execute(
                    """SELECT controller.actor_id,
                              account.account_reference,
                              controller.authority_level
                       FROM iam_character_controller controller
                       JOIN iam_campaign_membership membership
                         ON membership.campaign_membership_id=
                            controller.campaign_membership_id
                       JOIN iam_account account
                         ON account.account_id=membership.account_id
                       WHERE controller.actor_id=%s
                         AND controller.controller_status='active'""",
                    (actor_id,),
                ).fetchone()
                self.assertEqual(
                    controller, (actor_id, "player-one", "owner"))

    def test_reference_changes_end_old_relational_authority(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Authority Change','referee-old')
                       RETURNING campaign_id"""
                ).fetchone()[0]
                actor_id = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'Changing Actor','player-old')
                       RETURNING actor_id""",
                    (campaign_id,),
                ).fetchone()[0]
                connection.execute(
                    """UPDATE camp_campaign SET owner_reference='referee-new'
                       WHERE campaign_id=%s""",
                    (campaign_id,),
                )
                connection.execute(
                    """UPDATE actor_actor SET controller_reference='player-new'
                       WHERE actor_id=%s""",
                    (actor_id,),
                )

                controllers = connection.execute(
                    """SELECT account.account_reference,
                              controller.controller_status
                       FROM iam_character_controller controller
                       JOIN iam_campaign_membership membership
                         ON membership.campaign_membership_id=
                            controller.campaign_membership_id
                       JOIN iam_account account
                         ON account.account_id=membership.account_id
                       WHERE controller.actor_id=%s
                       ORDER BY account.account_reference""",
                    (actor_id,),
                ).fetchall()
                self.assertEqual(
                    controllers,
                    [("player-new", "active"), ("player-old", "ended")],
                )
                referee_memberships = connection.execute(
                    """SELECT account.account_reference,
                              membership.membership_status
                       FROM iam_campaign_membership membership
                       JOIN iam_account account
                         ON account.account_id=membership.account_id
                       JOIN iam_role role ON role.role_id=membership.role_id
                       WHERE membership.campaign_id=%s
                         AND role.role_code='referee'
                       ORDER BY account.account_reference""",
                    (campaign_id,),
                ).fetchall()
                self.assertEqual(
                    referee_memberships,
                    [("referee-new", "active"), ("referee-old", "ended")],
                )

    def test_controller_cannot_cross_campaign_boundary(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                first = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('First Campaign','first-referee')
                       RETURNING campaign_id"""
                ).fetchone()[0]
                second = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Second Campaign','second-referee')
                       RETURNING campaign_id"""
                ).fetchone()[0]
                actor_id = connection.execute(
                    """INSERT INTO actor_actor
                       (campaign_id,name,controller_reference)
                       VALUES (%s,'First Actor','first-player')
                       RETURNING actor_id""",
                    (first,),
                ).fetchone()[0]
                second_membership = connection.execute(
                    """SELECT membership.campaign_membership_id
                       FROM iam_campaign_membership membership
                       JOIN iam_role role ON role.role_id=membership.role_id
                       WHERE membership.campaign_id=%s
                         AND role.role_code='referee'""",
                    (second,),
                ).fetchone()[0]
                with self.assertRaises(ForeignKeyViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO iam_character_controller
                               (campaign_id,actor_id,campaign_membership_id,
                                authority_level)
                               VALUES (%s,%s,%s,'viewer')""",
                            (second, actor_id, second_membership),
                        )


if __name__ == "__main__":
    unittest.main()
