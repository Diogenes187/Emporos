from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "db" / "migrations"
NAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


class MigrationStructureTests(unittest.TestCase):
    def migration_paths(self) -> list[Path]:
        return sorted(MIGRATIONS.glob("*.sql"))

    def test_versions_are_contiguous_and_names_are_valid(self) -> None:
        paths = self.migration_paths()
        matches = [NAME.fullmatch(path.name) for path in paths]
        self.assertTrue(paths)
        self.assertNotIn(None, matches)
        versions = [int(match.group(1)) for match in matches if match]
        self.assertEqual(versions, list(range(1, len(versions) + 1)))

    def test_files_have_stable_sha256_inputs(self) -> None:
        for path in self.migration_paths():
            raw = path.read_bytes()
            normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            digest = hashlib.sha256(normalized).hexdigest()
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertEqual(
                digest,
                hashlib.sha256(
                    normalized.replace(b"\n", b"\r\n")
                    .replace(b"\r\n", b"\n")
                ).hexdigest(),
            )

    def test_runner_owns_transactions(self) -> None:
        for path in self.migration_paths():
            sql = path.read_text(encoding="utf-8")
            self.assertNotRegex(sql, r"(?im)^\s*(BEGIN|COMMIT)\s*;")

    def test_json_is_confined_to_candidate_staging(self) -> None:
        json_columns: list[tuple[str, str]] = []
        for path in self.migration_paths():
            sql = path.read_text(encoding="utf-8")
            for match in re.finditer(r"(?im)^\s*(\w+)\s+jsonb?\b", sql):
                json_columns.append((path.name, match.group(1)))
        self.assertEqual(
            json_columns,
            [("0002_sources_and_provenance.sql", "staging_value")],
        )

    def test_purchased_books_are_not_referenced_as_artifacts(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8") for path in self.migration_paths()
        )
        self.assertNotIn("CepheusUniversal-SRD2.docx", combined)
        self.assertNotIn("players-book11.pdf", combined)


if __name__ == "__main__":
    unittest.main()
