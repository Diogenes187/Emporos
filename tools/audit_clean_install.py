"""Prove the supported installer can build Emporos from an empty database.

The audit creates a uniquely named temporary database beside the configured
Emporos database, runs the production preparation command against it, verifies
core relational catalogues, and always removes only that temporary database.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "emporos_clean_install_audit_"


def configured_dsn() -> str:
    dsn = (
        os.environ.get("EMPOROS_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    )
    if not dsn:
        raise SystemExit("An Emporos PostgreSQL database URL is required")
    return dsn


def main() -> int:
    source = conninfo_to_dict(configured_dsn())
    database_name = PREFIX + uuid.uuid4().hex[:12]
    admin_dsn = make_conninfo(**{**source, "dbname": "postgres"})
    audit_dsn = make_conninfo(**{**source, "dbname": database_name})
    print(f"creating temporary database {database_name}")
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name)))
    try:
        environment = os.environ.copy()
        environment["EMPOROS_DATABASE_URL"] = audit_dsn
        environment["BASE_CEPHEUS_DATABASE_URL"] = audit_dsn
        subprocess.run(
            [sys.executable, "-B", "tools/deploy_database.py"],
            cwd=ROOT,
            env=environment,
            check=True,
        )
        with psycopg.connect(audit_dsn) as connection:
            version = connection.execute(
                "SELECT max(version) FROM sys_schema_migration"
            ).fetchone()[0]
            complete = connection.execute(
                "SELECT EXISTS(SELECT 1 FROM sys_database_bootstrap_completion "
                "WHERE singleton)"
            ).fetchone()[0]
            rules = connection.execute("SELECT count(*) FROM rule_rule").fetchone()[0]
            careers = connection.execute("SELECT count(*) FROM rule_career").fetchone()[0]
            attack_profiles = connection.execute(
                "SELECT count(*) FROM combat_attack_profile"
            ).fetchone()[0]
        if version != 592 or not complete:
            raise RuntimeError(
                f"clean install incomplete: schema={version}, marker={complete}"
            )
        if min(rules, careers, attack_profiles) < 1:
            raise RuntimeError(
                "clean install is missing a core relational rules catalogue"
            )
        print(
            "clean install verified: "
            f"schema={version}, rules={rules}, careers={careers}, "
            f"attack_profiles={attack_profiles}"
        )
    finally:
        if not database_name.startswith(PREFIX):
            raise RuntimeError("refusing to remove an unexpected database name")
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname=%s AND pid<>pg_backend_pid()",
                (database_name,),
            )
            admin.execute(
                sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
            )
        print(f"removed temporary database {database_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
