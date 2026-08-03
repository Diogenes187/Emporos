"""Import paired-source Telekinesis mechanics for CE-PSI-005."""

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
PROFILES = (
    ("lift-10g", 10, None, None),
    ("lift-100g", 100, None, None),
    ("lift-1kg", 1000, None, 1),
    ("lift-10kg", 10000, 1, None),
    ("lift-100kg", 100000, 2, None),
    ("lift-1000kg", 1000000, 8, None),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus Telekinesis mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (
        normalize(SOURCE.read_text()),
        normalize(soup.get_text(" ")),
    )
    for phrase in (
        "treated as if the person was physically handling the item",
        "physical danger, pain, or other stimuli are not present",
        "effect of the check determines the duration of the telekinesis in rounds",
        "items may be thrown using telekinesis",
        "use the ranged (thrown) category when attacking",
        "using the higher of the distance",
        "add the effect of the attack's skill check to the damage",
        "both the creature and the target take the same damage",
        "telekinetically lift 1000 kg",
        "10+range 8d6",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Telekinesis sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        talent = connection.execute(
            """SELECT talent_rule_id FROM psi_talent
               JOIN rule_rule ON rule_id=talent_rule_id
               WHERE rule_code='psionics.talent.telekinesis'"""
        ).fetchone()[0]
        thrown = connection.execute(
            """SELECT required_skill_rule_id FROM combat_attack_profile
               WHERE attack_profile_code='thrown'"""
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO rule_psi_telekinesis_system
               VALUES (%s,true,false,false,true,true,%s,true,true,true)""",
            (talent, thrown),
        )
        powers = dict(connection.execute(
            """SELECT power_code,power_rule_id FROM psi_power
               WHERE power_code LIKE 'lift-%'"""
        ).fetchall())
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO rule_psi_telekinesis_mass_profile
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                [
                    (powers[code], mass, dice, 6 if dice else None, flat,
                     dice is not None or flat is not None)
                    for code, mass, dice, flat in PROFILES
                ],
            )
    print("published paired-source Telekinesis mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
