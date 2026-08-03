"""Import paired-source Teleportation mechanics for CE-PSI-016."""

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
    session.headers["User-Agent"] = "BaseCepheus Teleportation mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(SOURCE.read_text()), normalize(soup.get_text(" ")))
    for phrase in (
        "effectively instantaneous movement",
        "independent items or other individuals may not be moved",
        "must always have a mental image",
        "recorded images are not enough",
        "very distant range or less",
        "20 to 120 seconds",
        "rammed him at its current speed",
        "2.5 degrees celsius",
        "more than 400 meters",
        "more than 600 meters in one hour",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Teleportation sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        connection.execute(
            """INSERT INTO rule_psi_teleportation_system
               SELECT talent.talent_rule_id,true,true,true,true,true,true,
                      true,true,true,true,true,band.range_band_rule_id,
                      400,600,2.5,true
               FROM psi_talent talent
               JOIN rule_rule talent_rule
                 ON talent_rule.rule_id=talent.talent_rule_id
                AND talent_rule.rule_code='psionics.talent.teleportation'
               CROSS JOIN psi_range_band band
               JOIN rule_rule range_rule
                 ON range_rule.rule_id=band.range_band_rule_id
                AND range_rule.rule_code='psionics.range.very-distant'"""
        )
        connection.execute(
            """INSERT INTO rule_psi_teleportation_power
               SELECT power.power_rule_id,expected.load_kind,
                      expected.load_kind<>'unclothed',expected.display_order
               FROM psi_power power
               JOIN (VALUES
                 ('teleport-unclothed','unclothed',1),
                 ('teleport-light-load','light',2),
                 ('teleport-moderate-load','moderate',3),
                 ('teleport-heavy-load','heavy',4)
               ) expected(power_code,load_kind,display_order)
                 ON expected.power_code=power.power_code"""
        )
        connection.execute(
            """INSERT INTO rule_psi_teleportation_disorientation
               SELECT system.talent_rule_id,system.planetary_maximum_range_rule_id,
                      2,6,10
               FROM rule_psi_teleportation_system system"""
        )
    print("published paired-source Teleportation mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
