"""Prepare an Emporos database during a production release."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import psycopg


ROOT = Path(__file__).resolve().parents[1]


def run(*arguments: str) -> None:
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main() -> int:
    dsn = (
        os.environ.get("EMPOROS_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    )
    if not dsn:
        raise SystemExit("EMPOROS_DATABASE_URL or DATABASE_URL is required")
    os.environ["EMPOROS_DATABASE_URL"] = dsn
    os.environ["BASE_CEPHEUS_DATABASE_URL"] = dsn
    with psycopg.connect(dsn) as connection:
        # Managed PostgreSQL services may install their own relations in public.
        # Only Emporos's migration ledger proves this is an existing game DB.
        initialized = connection.execute(
            "SELECT to_regclass('public.sys_schema_migration') IS NOT NULL"
        ).fetchone()[0]
    if initialized:
        run("tools/migrate.py")
        run("tools/verify_database.py")
    else:
        run("tools/bootstrap_database.py", "--dsn", dsn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
