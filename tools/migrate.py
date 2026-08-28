"""Apply Base Cepheus PostgreSQL migrations atomically.

Usage:
    python tools/migrate.py --dsn postgresql://user:pass@host/database

The BASE_CEPHEUS_DATABASE_URL environment variable may be used instead of
--dsn. Migration checksums are recorded in PostgreSQL and may never drift.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

try:
    import psycopg
except ImportError:
    print(
        "psycopg is required. Install the pinned development dependencies with "
        "`python -m pip install -r requirements-dev.txt`.",
        file=sys.stderr,
    )
    raise SystemExit(2)


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIR = ROOT / "db" / "migrations"
MIGRATION_NAME = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.sql$")
LOCK_ID = 1_384_927_441


def normalized_sql_bytes(raw: bytes) -> bytes:
    """Use one checksum on Windows and Unix without weakening SQL checks."""
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def checksum_variants(raw: bytes) -> set[str]:
    normalized = normalized_sql_bytes(raw)
    return {
        hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(normalized).hexdigest(),
        hashlib.sha256(normalized.replace(b"\n", b"\r\n")).hexdigest(),
    }


def migration_files() -> list[tuple[int, str, Path, str]]:
    found: list[tuple[int, str, Path, str]] = []
    for path in sorted(MIGRATION_DIR.glob("*.sql")):
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise ValueError(f"Invalid migration filename: {path.name}")
        raw = path.read_bytes()
        found.append(
            (
                int(match.group("version")),
                match.group("name"),
                path,
                hashlib.sha256(normalized_sql_bytes(raw)).hexdigest(),
            )
        )
    versions = [row[0] for row in found]
    if not versions or versions != list(range(1, len(versions) + 1)):
        raise ValueError(f"Migration versions must be contiguous from 0001: {versions}")
    return found


def applied_migrations(connection: psycopg.Connection) -> dict[int, str]:
    exists = connection.execute(
        "SELECT to_regclass('public.sys_schema_migration') IS NOT NULL"
    ).fetchone()[0]
    if not exists:
        return {}
    rows = connection.execute(
        "SELECT version, checksum_sha256 FROM sys_schema_migration ORDER BY version"
    ).fetchall()
    return dict(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", help="PostgreSQL connection string")
    parser.add_argument(
        "--build",
        default=os.environ.get("BASE_CEPHEUS_BUILD", "development"),
        help="Application build identity recorded with applied migrations",
    )
    parser.add_argument(
        "--target",
        type=int,
        help="Apply migrations only through this inclusive version",
    )
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")

    migrations = migration_files()
    if args.target is not None:
        latest = migrations[-1][0]
        if not 1 <= args.target <= latest:
            parser.error(f"--target must be between 1 and {latest}")
        migrations = [
            migration for migration in migrations
            if migration[0] <= args.target
        ]
    with psycopg.connect(dsn) as connection:
        connection.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_ID,))
        applied = applied_migrations(connection)

        for version, name, path, checksum in migrations:
            recorded = applied.get(version)
            if recorded is not None:
                if recorded not in checksum_variants(path.read_bytes()):
                    raise RuntimeError(
                        f"Applied migration {version:04d} checksum changed: "
                        f"database={recorded}, file={checksum}"
                    )
                print(f"already applied {version:04d}_{name}")
                continue

            later = [applied_version for applied_version in applied if applied_version > version]
            if later:
                raise RuntimeError(
                    f"Cannot apply {version:04d}; later migrations already exist: {later}"
                )

            connection.execute(path.read_text(encoding="utf-8"))
            connection.execute(
                """
                INSERT INTO sys_schema_migration (
                    version, name, checksum_sha256, application_build
                ) VALUES (%s, %s, %s, %s)
                """,
                (version, name, checksum, args.build),
            )
            print(f"applied {version:04d}_{name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

