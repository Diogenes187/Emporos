"""Reconcile Assault across OGN, GitHub, and the complete Traveller SRD."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import ROOT, fetch, normalize


URL = (
    "https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
    "cepheus-engine-psionics/"
)
TRAVELLER_URL = "https://www.traveller-srd.com/core-rules/psionics/"
SOURCE = ROOT / "sources/cepheus-srd/src/book1/psionics.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus Assault reconciliation/1.0"
    _, soup = fetch(session, URL)
    _, traveller_soup = fetch(session, TRAVELLER_URL)
    github = normalize(SOURCE.read_text())
    website = normalize(soup.get_text(" "))
    complete = normalize(traveller_soup.get_text(" "))
    shared = (
        "rendered unconscious immediately",
        "2d6 + effect damage",
        "psionic strength (if the victim has it), then intelligence, then endurance",
        "intelligence returns at the rate of one point per day",
    )
    for phrase in shared:
        if (
            normalize(phrase) not in github
            or normalize(phrase) not in website
            or normalize(phrase) not in complete
        ):
            raise ValueError(f"Assault sources disagree on: {phrase}")
    website_only = (
        "shielded mind is assaulted",
        "opposed telepathy checks",
        "1-6 seconds",
        "formidable (-6)",
        "costs 8+range",
    )
    for phrase in website_only:
        if normalize(phrase) not in complete:
            raise ValueError(f"Complete Assault source omits: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """UPDATE psi_power
               SET difficulty_rule_id=(
                     SELECT rule_id FROM rule_rule
                     WHERE rule_code='difficulty.formidable'
                   ),
                   timing_dice_count=1,timing_die_sides=6,
                   timing_unit='seconds',base_cost=8,
                   adds_range_cost=true,requires_check=true,
                   mechanics_complete=true
               WHERE power_code='assault'"""
        )
        connection.execute(
            """INSERT INTO rule_psi_assault
               SELECT power_rule_id,true,2,6,true,true,true,true,true,true,1,
                      true,true
               FROM psi_power WHERE power_code='assault'"""
        )
    print("published website-first Assault mechanics reconciliation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
