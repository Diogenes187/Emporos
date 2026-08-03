"""Import paired-source Read Surface Thoughts mechanics for CE-PSI-010."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import ROOT, fetch, normalize


URL = (
    "https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
    "cepheus-engine-psionics/"
)
SOURCE = ROOT / "sources/cepheus-srd/src/book1/psionics.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus Surface Thoughts mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "only active, current thoughts are read",
        "if himself not a telepath unaware",
        "cannot be read due to the presence of their natural shields",
        "unless they willingly lower their shielding",
        "effect of the check determines the clarity",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(
                f"Paired Read Surface Thoughts sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_read_surface_thoughts
               SELECT power_rule_id,true,true,true,true,true,true
                 FROM psi_power WHERE power_code='read-surface-thoughts'"""
        )
    print("published paired-source Read Surface Thoughts mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
