from __future__ import annotations

import os
import unittest

import psycopg


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class VehicleCatalogueCompletenessTests(unittest.TestCase):
    def test_all_published_vehicle_classes_pass_relational_gate(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            total, complete, unresolved = connection.execute(
                """SELECT count(*),
                          count(*) FILTER (
                              WHERE is_relationally_complete
                          ),
                          count(*) FILTER (
                              WHERE reconciliation_status<>
                                    'published_reconciled'
                          )
                   FROM vehicle_class_catalogue_completeness"""
            ).fetchone()
            self.assertEqual((total, complete), (20, 20))
            self.assertEqual(unresolved, 15)

    def test_completeness_keeps_publication_conflicts_visible(
        self,
    ) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            destroyer = connection.execute(
                """SELECT is_relationally_complete,receipt_status,
                          reconciliation_status,
                          retained_variance_count,
                          registered_issue_count
                   FROM vehicle_class_catalogue_completeness
                   WHERE class_code='destroyer-watercraft'"""
            ).fetchone()
            self.assertEqual(
                destroyer,
                (True, "source_gap", "source_gap", 0, 3),
            )


if __name__ == "__main__":
    unittest.main()
