from __future__ import annotations

import os
import unittest

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class SpeciesProvenanceTests(unittest.TestCase):
    def test_all_species_rules_have_paired_source_provenance(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT rule.rule_code,
                          count(DISTINCT work.work_code),
                          count(*) FILTER (
                            WHERE provenance.is_primary_citation)
                     FROM rule_rule rule
                     JOIN src_record_provenance provenance USING(rule_id)
                     JOIN src_locator locator USING(source_locator_id)
                     JOIN src_work work USING(source_work_id)
                    WHERE rule.rule_category IN ('species','species_trait')
                    GROUP BY rule.rule_id,rule.rule_code
                    ORDER BY rule.rule_code"""
            ).fetchall()
        self.assertEqual(len(rows), 39)
        self.assertTrue(all(row[1:] == (2, 1) for row in rows))

    def test_natural_weapon_uses_the_published_trait_citation(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            rows = connection.execute(
                """SELECT work.work_code,locator.anchor,
                          provenance.provenance_class,
                          provenance.is_primary_citation
                     FROM rule_rule rule
                     JOIN src_record_provenance provenance USING(rule_id)
                     JOIN src_locator locator USING(source_locator_id)
                     JOIN src_work work USING(source_work_id)
                    WHERE rule.rule_code=
                      'equipment.weapon.species-natural-weapon'
                    ORDER BY work.work_code"""
            ).fetchall()
        self.assertEqual(
            rows,
            [
                (
                    "cepheus-engine.github-v9.1",
                    "species-trait-descriptions",
                    "corroborating",
                    False,
                ),
                (
                    "cepheus-engine.ogn",
                    "species-trait-descriptions",
                    "direct",
                    True,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
