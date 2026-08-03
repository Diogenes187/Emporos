"""Reconcile Book 1 ranged RoF and ammunition listings for CE-EQUIP-030."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import ROOT, fetch, normalize
from import_ranged_weapons import AMMUNITION, EQUIPMENT_URL, WEAPONS

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"


def fire_values(text):
    values = [int(value) for value in text.split("/")]
    return tuple((values+[None,None])[:3])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = normalize(SOURCE.read_text())
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus ranged reconciliation/1.0"
    _, soup = fetch(session, EQUIPMENT_URL)
    website = normalize(soup.get_text(" "))
    for phrase in (
        "submachinegun | 5 | cr500 | 2500g | 0/4",
        "gauss rifle | 12 | cr1500 | 3500g | 1/4/10",
        "snub pistol | 8 | cr10 | 30g | 6/15",
    ):
        if any(normalize(phrase) not in text for text in (github,website)):
            raise ValueError(f"Paired ranged sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        for slug,_,_,_,_,rof,*_ in WEAPONS:
            rule = connection.execute(
                """SELECT rule_id FROM rule_rule WHERE rule_code=%s""",
                (f"equipment.weapon.{slug}",)).fetchone()[0]
            connection.execute(
                """INSERT INTO rule_book1_ranged_weapon_fire_profile
                   VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule,*fire_values(rof)))
        for slug,variant,capacity,*_ in AMMUNITION:
            rule = connection.execute(
                """SELECT rule_id FROM rule_rule WHERE rule_code=%s""",
                (f"equipment.ammunition.{slug}.{variant}",)).fetchone()[0]
            connection.execute(
                """INSERT INTO rule_book1_ranged_ammunition_listing
                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule,slug,capacity))
    print("reconciled 18 ranged fire profiles and 19 ammunition variants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
