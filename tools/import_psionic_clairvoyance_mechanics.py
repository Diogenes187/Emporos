"""Import paired-source Clairvoyance mechanics for CE-PSI-004."""

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
ROWS = (
    ("sense", False, False, True, False, False),
    ("clairvoyance", True, False, False, True, True),
    ("clairaudience", False, True, False, True, True),
    ("clairsentience", True, True, False, True, True),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus Clairvoyance mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (
        normalize(SOURCE.read_text()),
        normalize(soup.get_text(" ")),
    )
    for phrase in (
        "clairvoyant activity cannot be sensed by others",
        "sense will determine if a room is occupied or empty",
        "the effect of the check determines the level of accuracy and clarity",
        "allows the psion to observe as if he was there in person",
        "detail perceived and the duration in rounds",
        "allows hearing instead of seeing",
        "capable of both seeing and hearing",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Clairvoyance sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        power_ids = dict(connection.execute(
            """SELECT power_code,power_rule_id FROM psi_power
               WHERE power_code IN (
                 'sense','clairvoyance','clairaudience','clairsentience')"""
        ).fetchall())
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO rule_psi_clairvoyance_power
                   VALUES (%s,%s,%s,%s,true,true,%s,%s,true,true)""",
                [
                    (power_ids[code], vision, hearing, snapshot, detail, duration)
                    for code, vision, hearing, snapshot, detail, duration in ROWS
                ],
            )
    print("published paired-source Clairvoyance mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
