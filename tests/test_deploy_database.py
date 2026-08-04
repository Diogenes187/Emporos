from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from tools import deploy_database


class DeployDatabaseTests(unittest.TestCase):
    def run_main(self, initialized: bool) -> list[tuple[str, ...]]:
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = (initialized,)
        context = MagicMock()
        context.__enter__.return_value = connection
        calls: list[tuple[str, ...]] = []

        with (
            patch.dict("os.environ", {"EMPOROS_DATABASE_URL": "postgresql://test"}),
            patch.object(deploy_database.psycopg, "connect", return_value=context),
            patch.object(deploy_database, "run", side_effect=lambda *args: calls.append(args)),
        ):
            self.assertEqual(deploy_database.main(), 0)

        connection.execute.assert_called_once_with(
            "SELECT to_regclass('public.sys_schema_migration') IS NOT NULL"
        )
        return calls

    def test_provider_relations_do_not_prevent_empty_database_bootstrap(self) -> None:
        self.assertEqual(
            self.run_main(False),
            [("tools/bootstrap_database.py", "--dsn", "postgresql://test")],
        )

    def test_existing_emporos_database_is_migrated_and_verified(self) -> None:
        self.assertEqual(
            self.run_main(True),
            [("tools/migrate.py",), ("tools/verify_database.py",)],
        )


if __name__ == "__main__":
    unittest.main()
