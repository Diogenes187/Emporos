"""Import paired-source Probe mechanics for CE-PSI-012."""

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
    session.headers["User-Agent"] = "BaseCepheus Probe mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "innermost thoughts",
        "divulge specific information",
        "deliberate untruths",
        "cannot be used against a shielded mind",
        "effect of the check determines the clarity",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Probe sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_probe
               SELECT power_rule_id,mode,true,true,true,true,true,true
               FROM psi_power
               CROSS JOIN (VALUES
                 ('probe-deliberate','deliberate'),
                 ('probe-rapid','rapid')
               ) AS expected(power_code,mode)
               WHERE psi_power.power_code=expected.power_code"""
        )
    print("published paired-source deliberate and rapid Probe mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
