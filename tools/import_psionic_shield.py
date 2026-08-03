"""Import paired-source Telepathic Shield mechanics for CE-PSI-015."""

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
    session.headers["User-Agent"] = "BaseCepheus Shield mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "all telepathically able characters learn",
        "automatically in force at all times",
        "requires no psionic strength point expenditure",
        "cannot use any telepathic powers",
        "shield can be lowered",
        "free action in combat",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Shield sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_shield
               SELECT power_rule_id,true,true,true,0,true,true,true,'free'
               FROM psi_power WHERE power_code='shield'"""
        )
    print("published paired-source Telepathic Shield mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
