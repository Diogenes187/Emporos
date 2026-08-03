"""Import paired-source Send Thoughts mechanics for CE-PSI-011."""

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
    session.headers["User-Agent"] = "BaseCepheus Send Thoughts mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "ability to send thoughts to others",
        "need not themselves be telepathic",
        "telepathic individuals are normally open",
        "may close their shields against them",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Send Thoughts sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_send_thoughts
               SELECT power_rule_id,true,true,true,true,true,false
                 FROM psi_power WHERE power_code='send-thoughts'"""
        )
    print("published paired-source Send Thoughts mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
