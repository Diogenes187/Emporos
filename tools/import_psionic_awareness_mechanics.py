"""Import paired-source Awareness power mechanics for CE-PSI-002."""

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
    session.headers["User-Agent"] = "BaseCepheus Awareness mechanics/1.0"
    _, soup = fetch(session, URL)
    paired = (
        normalize(SOURCE.read_text()),
        normalize(soup.get_text(" ")),
    )
    for phrase in (
        "such a state continues for 7 days without need for food or water",
        "provided external stimulus is given to awaken the sleeper",
        "may the number of strength points gained exceed the character's current level in awareness",
        "strength may not be increased beyond the character's racial maximum",
        "remains at that peak for ten minutes",
        "declines at the rate of 1 strength point per minute",
        "it cannot be used as a 'quick heal'",
        "exchanging one psionic strength point to regenerate one characteristic point",
        "it may not be used again until all expended psionic strength is recovered",
        "regeneration may not be used to counteract aging",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Awareness sources omit: {phrase}")

    with psycopg.connect(dsn) as connection:
        powers = dict(connection.execute(
            """SELECT power_code,power_rule_id FROM psi_power
               WHERE power_code IN (
                 'suspended-animation','enhanced-strength',
                 'enhanced-endurance','regeneration'
               )"""
        ).fetchall())
        characteristics = dict(connection.execute(
            """SELECT rule_code,rule_id FROM rule_rule WHERE rule_code IN (
                 'characteristic.strength','characteristic.dexterity',
                 'characteristic.endurance'
               )"""
        ).fetchall())
        connection.execute(
            """INSERT INTO rule_psi_suspended_animation
               VALUES (%s,7,false,false,'minimal',true,false,true)""",
            (powers["suspended-animation"],),
        )
        for power_code, characteristic_code in (
            ("enhanced-strength", "characteristic.strength"),
            ("enhanced-endurance", "characteristic.endurance"),
        ):
            connection.execute(
                """INSERT INTO rule_psi_characteristic_enhancement
                   VALUES (%s,%s,1,true,true,10,1,1,true,false,true)""",
                (powers[power_code], characteristics[characteristic_code]),
            )
        regeneration = powers["regeneration"]
        connection.execute(
            """INSERT INTO rule_psi_regeneration
               VALUES (%s,1,NULL,true,true,true,false,true)""",
            (regeneration,),
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO rule_psi_regeneration_characteristic
                   VALUES (%s,%s)""",
                [
                    (regeneration, characteristics[code])
                    for code in (
                        "characteristic.strength",
                        "characteristic.dexterity",
                        "characteristic.endurance",
                    )
                ],
            )
    print("published paired-source Awareness power mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
