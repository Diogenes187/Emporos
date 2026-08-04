from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from app.database import CampaignReader


class DatabaseStatusTests(unittest.TestCase):
    def test_status_reads_the_migration_ledger_version(self) -> None:
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = {"version": 574}
        context = MagicMock()
        context.__enter__.return_value = connection

        with patch("app.database.psycopg.connect", return_value=context):
            status = CampaignReader("postgresql://test").status()

        self.assertEqual(
            status,
            {"configured": True, "connected": True, "schema_version": 574},
        )
        self.assertIn("max(version)", connection.execute.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
