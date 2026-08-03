"""Import paired-source Telempathy mechanics for CE-PSI-009."""

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
    session.headers["User-Agent"] = "BaseCepheus Telempathy mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "the communication of emotions and basic feelings",
        "although not necessarily in the manner desired",
        "allows the emotions and feelings of others to be read",
        "effect of the check determines the strength",
        "telepaths will always recognize",
        "others will not",
        "shielded individuals are immune to telempathy",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Telempathy sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_telempathy
               SELECT power_rule_id,true,true,true,true,true,true,true
                 FROM psi_power WHERE power_code='telempathy'"""
        )
    print("published paired-source Telempathy mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
