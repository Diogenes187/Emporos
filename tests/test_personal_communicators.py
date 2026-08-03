import os
import unittest

import psycopg
from psycopg.errors import CheckViolation


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalCommunicatorTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_catalogue_profiles_are_exact(self):
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT rule.rule_code,item.minimum_tech_level,
                          item.cost_credits,item.mass_grams,
                          communicator.channel_count,
                          communicator.nominal_range_meters,
                          communicator.range_kind,
                          communicator.minimum_operating_world_tech_level,
                          communicator.private_channel,
                          communicator.secure_channel,
                          communicator.network_access_fee_required
                   FROM inv_communicator_definition communicator
                   JOIN inv_item_definition item
                     ON item.rule_id=communicator.item_rule_id
                   JOIN rule_rule rule ON rule.rule_id=item.rule_id
                   ORDER BY rule.rule_code"""
            ).fetchall()
        self.assertEqual(rows, [
            ("equipment.communicator.long-range", 6, 500, 15000, 10,
             500000, "fixed", None, False, False, False),
            ("equipment.communicator.medium-range", 5, 200, 10000, 5,
             30000, "fixed", None, False, False, False),
            ("equipment.communicator.personal", 8, 250, 300, 1,
             None, "satellite-network", 8, True, False, True),
            ("equipment.communicator.short-range", 5, 100, 5000, 3,
             10000, "fixed", None, False, False, False),
        ])

    def test_tl_profiles_capabilities_and_environment_are_relational(self):
        with self.connect() as connection:
            profiles = connection.execute(
                """SELECT rule.rule_code,profile.minimum_tech_level,
                          profile.mass_grams,profile.form_factor
                   FROM inv_communicator_tech_profile profile
                   JOIN rule_rule rule ON rule.rule_id=profile.item_rule_id
                   ORDER BY rule.rule_code,profile.minimum_tech_level"""
            ).fetchall()
            capabilities = connection.execute(
                """SELECT rule.rule_code,capability.capability_code
                   FROM rule_communicator_contact_capability capability
                   JOIN rule_rule rule ON rule.rule_id=capability.item_rule_id
                   ORDER BY rule.rule_code"""
            ).fetchall()
            environments = connection.execute(
                """SELECT environment_code,effect_kind
                   FROM rule_communicator_environment_effect
                   ORDER BY environment_code"""
            ).fetchall()
        self.assertEqual(profiles, [
            ("equipment.communicator.long-range", 6, 15000, "backpack"),
            ("equipment.communicator.long-range", 7, 1500, "belt-or-sling"),
            ("equipment.communicator.medium-range", 5, 10000,
             "belt-or-sling"),
            ("equipment.communicator.medium-range", 7, 500, "belt-or-sling"),
            ("equipment.communicator.personal", 8, 300, "handheld"),
            ("equipment.communicator.short-range", 5, 5000, "belt"),
            ("equipment.communicator.short-range", 7, 300, "handheld"),
        ])
        self.assertEqual(capabilities, [
            ("equipment.communicator.long-range", "orbital-ship-contact"),
            ("equipment.communicator.medium-range", "official-radio-channels"),
            ("equipment.communicator.personal",
             "worldwide-satellite-addressing"),
        ])
        self.assertEqual(environments, [
            ("underground", "unquantified-range-reduction"),
            ("underwater", "unquantified-range-reduction"),
        ])

    def test_usage_and_paired_provenance_are_complete(self):
        with self.connect() as connection:
            usage = connection.execute(
                """SELECT routine_use_requires_check,rule.rule_code
                   FROM rule_personal_communicator_usage usage
                   JOIN rule_rule rule
                     ON rule.rule_id=usage.exceptional_use_skill_rule_id"""
            ).fetchone()
            provenance = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE provenance.is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code='equipment.personal-communicators'
                      OR rule.rule_code LIKE
                         'equipment.communicator.%'"""
            ).fetchone()
        self.assertEqual(usage, (False, "skill.comms"))
        self.assertEqual(provenance, (10, 5, 5))

    def test_satellite_range_requires_world_tl_and_no_fixed_range(self):
        with self.connect() as connection:
            personal = connection.execute(
                """SELECT item_rule_id FROM inv_communicator_definition
                   WHERE range_kind='satellite-network'"""
            ).fetchone()[0]
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE inv_communicator_definition
                           SET nominal_range_meters=1
                           WHERE item_rule_id=%s""", (personal,))


if __name__ == "__main__":
    unittest.main()
