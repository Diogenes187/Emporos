import os
import unittest
import uuid

import psycopg

from app.auth import (accept_invitation, authenticate, campaign_role,
                      can_access_campaign, create_invitation, create_session,
                      grant_campaign_owner, register, revoke_session,
                      numeric_resources_belong_to_campaign,
                      resources_belong_to_campaign, user_for_session)


class WebAuthenticationTests(unittest.TestCase):
    def test_accounts_sessions_and_invited_campaign_access_are_isolated(self):
        marker = uuid.uuid4().hex
        owner_email = f"owner-{marker}@example.test"
        member_email = f"member-{marker}@example.test"
        campaign_public_id = None
        foreign_campaign_public_id = None
        try:
            owner = register(owner_email, "Owner", "correct horse battery")
            member = register(member_email, "Member", "another correct horse")
            self.assertEqual(authenticate(owner_email, "correct horse battery"), owner)
            self.assertIsNone(authenticate(owner_email, "incorrect password"))

            token = create_session(owner.user_id)
            self.assertEqual(user_for_session(token), owner)
            revoke_session(token)
            self.assertIsNone(user_for_session(token))

            with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
                campaign_public_id = str(connection.execute(
                    "INSERT INTO camp_campaign(name) VALUES(%s) RETURNING public_id",
                    (f"Auth isolation {marker}",),
                ).fetchone()[0])
            grant_campaign_owner(campaign_public_id, owner.user_id)
            self.assertTrue(can_access_campaign(owner.user_id, campaign_public_id))
            self.assertFalse(can_access_campaign(member.user_id, campaign_public_id))
            self.assertEqual(campaign_role(owner.user_id, campaign_public_id), "owner")

            with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
                foreign_campaign_public_id = str(connection.execute(
                    "INSERT INTO camp_campaign(name) VALUES(%s) RETURNING public_id",
                    (f"Foreign isolation {marker}",),
                ).fetchone()[0])
                foreign_actor_id, foreign_actor_public = connection.execute(
                    """INSERT INTO actor_actor(campaign_id,name,controller_reference)
                       SELECT campaign_id,'Foreign Actor','test' FROM camp_campaign
                       WHERE public_id=%s RETURNING actor_id,public_id""",
                    (foreign_campaign_public_id,),
                ).fetchone()
                foreign_actor_public_id = str(foreign_actor_public)
            self.assertTrue(resources_belong_to_campaign(
                foreign_campaign_public_id, {foreign_actor_public_id}
            ))
            self.assertFalse(resources_belong_to_campaign(
                campaign_public_id, {foreign_actor_public_id}
            ))
            self.assertTrue(numeric_resources_belong_to_campaign(
                foreign_campaign_public_id, {"actor_id": {foreign_actor_id}}
            ))
            self.assertFalse(numeric_resources_belong_to_campaign(
                campaign_public_id, {"actor_id": {foreign_actor_id}}
            ))

            invitation = create_invitation(campaign_public_id, owner.user_id, member_email)
            self.assertEqual(accept_invitation(invitation, member), campaign_public_id)
            self.assertTrue(can_access_campaign(member.user_id, campaign_public_id))
            self.assertEqual(campaign_role(member.user_id, campaign_public_id), "member")
        finally:
            with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
                for public_id in (campaign_public_id, foreign_campaign_public_id):
                    if not public_id:
                        continue
                    campaign_id = connection.execute(
                        "SELECT campaign_id FROM camp_campaign WHERE public_id=%s",
                        (public_id,),
                    ).fetchone()[0]
                    connection.execute("DELETE FROM iam_character_controller WHERE campaign_id=%s", (campaign_id,))
                    connection.execute("DELETE FROM actor_actor WHERE campaign_id=%s", (campaign_id,))
                    connection.execute("DELETE FROM iam_campaign_membership WHERE campaign_id=%s", (campaign_id,))
                    connection.execute("DELETE FROM camp_installed_package WHERE campaign_id=%s", (campaign_id,))
                    connection.execute("DELETE FROM camp_clock WHERE campaign_id=%s", (campaign_id,))
                    connection.execute("DELETE FROM camp_campaign WHERE campaign_id=%s", (campaign_id,))
                connection.execute("DELETE FROM auth_user_account WHERE email IN (%s,%s)",
                                   (owner_email, member_email))


if __name__ == "__main__":
    unittest.main()
