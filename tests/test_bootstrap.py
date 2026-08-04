from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import psycopg

from tools import bootstrap_database


class BootstrapStructureTests(unittest.TestCase):
    def test_schema_probe_is_limited_to_emporos_markers(self) -> None:
        class Connection:
            sql = ""

            def execute(self, sql: str):
                self.sql = sql
                return [("sys_content_package",)]

        connection = Connection()
        self.assertEqual(
            bootstrap_database.public_relations(connection),
            ["sys_content_package"],
        )
        self.assertIn("c.relname IN", connection.sql)
        self.assertNotIn("flyway_schema_history", connection.sql)

    def test_importer_dependency_boundaries_are_ordered(self) -> None:
        targets = [
            target
            for target, _ in bootstrap_database.BOOTSTRAP_PHASES
            if target is not None
        ]
        self.assertEqual(
            targets,
            [8, 15, 16, 19, 21, 36, 38, 41, 44, 187, 188, 189, 190, 191, 192,
             193, 197, 198, 201, 203, 206, 209, 211, 214, 218, 221, 223, 227,
             228, 233, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244,
             245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257,
             258, 259, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271,
             272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284,
             285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297,
             298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310,
             311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322,
             323, 324, 325, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335,
             336, 337, 338, 339, 340, 341, 342, 343, 344, 345, 346, 347,
             348, 349, 350, 351, 352, 353, 354, 355, 356, 357, 358, 359,
             360, 361, 362, 363, 364, 365, 366, 367, 368, 369, 370, 371, 372,
             373, 374, 375, 376, 377, 378, 379, 380, 381, 382, 383, 384],
        )
        self.assertIsNone(bootstrap_database.BOOTSTRAP_PHASES[-1][0])

        importers = [
            importer
            for _, phase_importers in bootstrap_database.BOOTSTRAP_PHASES
            for importer in phase_importers
        ]
        self.assertEqual(len(importers), 105)
        self.assertEqual(len(importers), len(set(importers)))

    def test_project_tool_uses_environment_dsn_not_command_line(self) -> None:
        env = {"BASE_CEPHEUS_DATABASE_URL": "secret-dsn"}
        with patch("subprocess.run") as run:
            bootstrap_database.run_project_tool(
                "migrate.py", env, "--target", "8"
            )
        command = run.call_args.args[0]
        self.assertNotIn("secret-dsn", command)
        self.assertEqual(command[-2:], ["--target", "8"])
        self.assertEqual(run.call_args.kwargs["env"], env)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class BootstrapDatabaseGuardTests(unittest.TestCase):
    def test_live_database_is_detected_as_nonempty(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            relations = bootstrap_database.public_relations(connection)
        self.assertIn("sys_schema_migration", relations)


if __name__ == "__main__":
    unittest.main()
