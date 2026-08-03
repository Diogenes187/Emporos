"""Import paired Book 1 vehicle capabilities for CE-EQUIP-026."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import ROOT, fetch, get_id, normalize

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-equipment/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_text()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus Book 1 vehicle capabilities/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "one, two or three may be fired at the same target",
        "taking a number of hours equal to the world's size code",
        "passengers at that altitude must wear vacc suits",
        "capable of floating on calm water",
        "only usable on words with a thin atmosphere or thicker",
        "battery can operate for a maximum of four hours",
        "at tl 15, the battery can operate for 12 hours",
        "options cannot be added to the grav belt",
        "does not leak radiation with each shot",
        "this vehicle only takes an hour to reach orbit",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(
                f"Paired Book 1 vehicle sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        profiles = dict(connection.execute(
            """SELECT profile_code,rule_id
               FROM rule_book1_vehicle_profile""").fetchall())
        cargo = {
            "biplane":100, "destroyer":40000, "helicopter":500,
            "hovercraft":3000, "motor-boat":10000, "steamship":50000,
            "speeder":100, "submersible":30000,
            "twin-jet-aircraft":5000,
        }
        for code, rule in profiles.items():
            orbit = (
                "one-hour" if code=="speeder"
                else "world-size-hours" if code in (
                    "air-raft","g-carrier","grav-floater") else None)
            connection.execute(
                """INSERT INTO rule_book1_vehicle_capability VALUES
                   (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (rule,cargo.get(code),orbit,code=="air-raft",
                 code=="atv",code=="atv",code=="atv",code=="atv",
                 code=="atv","thin" if code=="hovercraft" else None,
                 14400 if code=="grav-belt" else None,
                 code=="grav-belt",code=="g-carrier",
                 False if code=="g-carrier" else None,
                 code=="air-raft"))
        belt = profiles["grav-belt"]
        connection.execute(
            """INSERT INTO rule_book1_grav_belt_battery VALUES
               (%s,12,14400),(%s,15,43200) ON CONFLICT DO NOTHING""",
            (belt,belt))
        energy = get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code='skill.energy-rifle'",
            ())
        connection.execute(
            """INSERT INTO rule_book1_afv_laser_fire
               VALUES (%s,%s,4,6,'ranged-rifle',1,3,true)
               ON CONFLICT DO NOTHING""", (profiles["afv"],energy))
    print("published 16 Book 1 vehicle capabilities and weapon exceptions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
