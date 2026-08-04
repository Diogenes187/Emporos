"""Record a successfully verified Emporos catalogue bootstrap."""

from __future__ import annotations

import os

import psycopg


def main() -> int:
    dsn = os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        raise SystemExit("BASE_CEPHEUS_DATABASE_URL is required")
    build = os.environ.get("BASE_CEPHEUS_BUILD", "development")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO sys_database_bootstrap_completion (
                   singleton, application_build
               ) VALUES (true, %s)
               ON CONFLICT (singleton) DO UPDATE SET
                   completed_at=clock_timestamp(),
                   application_build=EXCLUDED.application_build""",
            (build,),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
