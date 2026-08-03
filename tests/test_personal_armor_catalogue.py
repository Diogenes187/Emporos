import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, UniqueViolation


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalArmorCatalogueTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_catalogue_rule_is_typed(self) -> None:
        with self.connect() as connection:
            row = connection.execute(
                """SELECT ordinary_simultaneous_armor_limit,
                          source_noted_layering_exceptions,
                          layered_damage_resolution,
                          exceptional_effect_minimum_damage,
                          exceptional_effect_threshold
                   FROM rule_personal_armor_catalogue"""
            ).fetchone()
        self.assertEqual(row, (1, True, "outside-in", 1, 6))

    def test_all_nine_profiles_match_the_governing_table(self) -> None:
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT rule.rule_code,item.minimum_tech_level,
                          armor.general_armor_rating,
                          armor.laser_armor_rating,item.cost_credits,
                          item.mass_grams,skill.rule_code,
                          armor.catalogue_display_order,
                          armor.laser_rating_explicit
                   FROM inv_armor_definition armor
                   JOIN inv_item_definition item
                     ON item.rule_id=armor.item_rule_id
                   JOIN rule_rule rule ON rule.rule_id=item.rule_id
                   LEFT JOIN rule_rule skill
                     ON skill.rule_id=armor.required_skill_rule_id
                   WHERE armor.catalogue_display_order IS NOT NULL
                   ORDER BY armor.catalogue_display_order"""
            ).fetchall()
        self.assertEqual(rows, [
            ("equipment.armor.ablat", 9, 3, 8, 75, 2000, None, 1, True),
            ("equipment.armor.battle-dress", 13, 18, None, 200000, 60000,
             "skill.battle-dress", 2, False),
            ("equipment.armor.cloth", 6, 9, None, 250, 2000, None, 3, False),
            ("equipment.armor.combat-armor", 11, 11, None, 20000, 18000,
             "skill.zero-g", 4, False),
            ("equipment.armor.hostile-environment-vacc-suit", 12, 8, None,
             18000, 40000, "skill.zero-g", 5, False),
            ("equipment.armor.jack", 1, 3, None, 50, 1000, None, 6, False),
            ("equipment.armor.mesh", 7, 5, None, 150, 2000, None, 7, False),
            ("equipment.armor.reflec", 10, 0, 14, 1500, 1000, None, 8, True),
            ("equipment.armor.vacc-suit", 9, 6, None, 9000, 8000,
             "skill.zero-g", 9, False),
        ])

    def test_profiles_have_paired_provenance_and_explicit_conflicts(self) -> None:
        with self.connect() as connection:
            provenance = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE provenance.is_primary_citation),
                          count(DISTINCT provenance.rule_id)
                   FROM src_record_provenance provenance
                   JOIN src_import_candidate candidate
                     USING (import_candidate_id)
                   JOIN rule_rule rule USING (rule_id)
                   WHERE candidate.candidate_type=
                         'personal_armor_catalogue'
                     AND (rule.rule_code=
                          'equipment.personal-armor-catalogue'
                       OR rule.rule_code LIKE 'equipment.armor.%')"""
            ).fetchone()
            issues = connection.execute(
                """SELECT issue_code,published_value,calculated_value,
                          issue_status,engine_disposition,
                          count(locator.source_locator_id)
                   FROM src_issue issue
                   JOIN src_issue_locator locator USING (source_issue_id)
                   WHERE issue.domain_code='equipment.armor'
                   GROUP BY issue.source_issue_id
                   ORDER BY issue.issue_code"""
            ).fetchall()
        self.assertEqual(provenance, (20, 10, 10))
        self.assertEqual(issues, [
            ("equipment.armor.cloth-tech-level", "table TL 6",
             "description TL 7", "accepted_as_published",
             "preserve_published", 4),
            ("equipment.armor.hev-suit-tech-level", "table TL 12",
             "description TL 8", "accepted_as_published",
             "preserve_published", 4),
            ("equipment.armor.vacc-suit-tech-level", "table TL 9",
             "description TL 8", "accepted_as_published",
             "preserve_published", 4),
        ])

    def test_catalogue_order_and_explicit_laser_rating_are_invariants(
        self,
    ) -> None:
        with self.connect() as connection:
            armor_id = connection.execute(
                """SELECT item_rule_id FROM inv_armor_definition
                   WHERE catalogue_display_order=1"""
            ).fetchone()[0]
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE inv_armor_definition
                           SET laser_armor_rating=NULL
                           WHERE item_rule_id=%s""", (armor_id,))
            with self.assertRaises(UniqueViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE inv_armor_definition
                           SET catalogue_display_order=2
                           WHERE item_rule_id=%s""", (armor_id,))


if __name__ == "__main__":
    unittest.main()
