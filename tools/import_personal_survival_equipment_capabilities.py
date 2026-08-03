"""Import paired Survival Equipment capabilities for CE-EQUIP-023."""
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
    session.headers["User-Agent"] = "BaseCepheus survival capabilities/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "dm+2 to all endurance checks",
        "reduce the weight by 1kg for every 5 tl",
        "tainted atmospheres (types 4, 7, and 9)",
        "very thin atmospheres (type 3)",
        "two tanks last 6 hours",
        "refill of proper atmospheric mixture for race cost cr20",
        "two person/hours of life support",
        "zero-g check is required",
        "only be used in microgravity environments",
        "adjacent range",
        "up to one month of use",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(
                f"Paired Survival Equipment sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        items = dict(connection.execute(
            """SELECT survival_equipment_code,item_rule_id
               FROM inv_personal_survival_equipment_definition""").fetchall())
        rows = {
            code: [None] * 23 for code in items
        }
        rows["cold-weather-clothing"][0:4] = [-20, 2, 1000, 5]
        rows["filter-mask"][10:12] = [True, True]
        rows["swimming-equipment"][0] = 5
        rows["combination-mask"][10:12] = [True, True]
        rows["oxygen-tanks"][4:8] = [21600, False, 20, 2]
        rows["oxygen-tanks"][10:13] = [True, True, True]
        rows["underwater-air-tanks"][4:8] = [21600, False, 20, 2]
        rows["artificial-gill"][5] = True
        rows["environment-suit"][13:16] = [True, True, True]
        rows["rescue-bubble"][8:10] = [2, 2]
        rows["rescue-bubble"][16:20] = [True, True, True, True]
        rows["thruster-pack"][21:23] = [True, True]
        rows["portable-generator"][4] = 2592000
        rows["portable-generator"][20] = True
        for code, values in rows.items():
            values[5] = bool(values[5])
            for index in range(10, 23):
                values[index] = bool(values[index])
            connection.execute(
                """INSERT INTO rule_personal_survival_equipment_capability
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                           %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""", (items[code], *values))
        atmosphere_links = {
            "filter-mask": (4, 7, 9),
            "respirator": (3,),
            "combination-mask": (2, 3, 4, 7, 9),
            "artificial-gill": (4, 5, 6, 7, 8, 9),
            "oxygen-tanks": (10,),
        }
        for code, atmospheres in atmosphere_links.items():
            for atmosphere in atmospheres:
                connection.execute(
                    """INSERT INTO rule_personal_survival_equipment_atmosphere
                       VALUES (%s,%s) ON CONFLICT DO NOTHING""",
                    (items[code], atmosphere))
        athletics = get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code='skill.athletics'",
            ())
        zero_g = get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code='skill.zero-g'", ())
        connection.execute(
            """INSERT INTO rule_personal_survival_equipment_skill VALUES
               (%s,%s,1,false),(%s,%s,NULL,true)
               ON CONFLICT DO NOTHING""",
            (items["swimming-equipment"], athletics,
             items["thruster-pack"], zero_g))
    print("published 12 survival capabilities, 16 atmosphere links, 2 skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
