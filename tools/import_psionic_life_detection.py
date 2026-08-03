"""Import paired-source Life Detection mechanics for CE-PSI-008."""

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
    session.headers["User-Agent"] = "BaseCepheus Life Detection mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "sense the presence of other minds",
        "the number of minds present",
        "the general type of minds",
        "their approximate location",
        "distinguish intelligent beings from bacteria or unimportant animals",
        "shielded minds are undetectable",
        "he or she will be recognized",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Life Detection sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_life_detection
               SELECT power_rule_id,true,true,true,true,true,true,true
                 FROM psi_power WHERE power_code='life-detection'"""
        )
    print("published paired-source Life Detection mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
