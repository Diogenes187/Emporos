from __future__ import annotations

import os
import unittest

import psycopg

from tools.generate_source_coverage_report import DEFAULT_OUTPUT, build_report


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class SourceCoverageReportTests(unittest.TestCase):
    def test_committed_report_matches_relational_source_state(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            report = build_report(connection)
        self.assertEqual(DEFAULT_OUTPUT.read_text(encoding="utf-8"), report)

    def test_report_keeps_coverage_and_open_questions_distinct(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            report = build_report(connection)
        self.assertIn("- Normalized rules: 1087", report)
        self.assertIn("- Covered by paired sources: 1062", report)
        self.assertIn("- Partial — explicit source gap: 25", report)
        self.assertIn("- Partial — not individually linked: 0", report)
        self.assertIn("- Latest schema migration: 0577", report)
        self.assertIn("- Open source questions: 0", report)
        self.assertNotIn("```json", report)


if __name__ == "__main__":
    unittest.main()
