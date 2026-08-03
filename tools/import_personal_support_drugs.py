"""Import paired-source support drug mechanics for CE-EQUIP-011."""
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
    session.headers["User-Agent"] = "BaseCepheus support drugs importer/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "slowing his metabolic rate down to a ratio of 60 to 1",
        "subjective day for the user is actually two months",
        "require the medic skill", "positive dm towards resisting",
        "wrong drug is administered", "poison with a damage of 1d6",
        "medical facility where life-support and cryo-technology",
        "around thirty times normal",
        "month of healing in a single day",
        "guaranteed not to make things worse",
        "check as if he had",
        "one dose must be taken each month",
        "immediate roll on the aging table",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired support-drug sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        drugs = dict(connection.execute(
            """SELECT drug_code,item_rule_id
               FROM inv_personal_drug_definition""").fetchall())
        medic = get_id(connection, """SELECT rule_id FROM rule_rule
            WHERE rule_code='skill.medicine'""", ())
        difficult = get_id(connection, """SELECT difficulty.rule_id
            FROM rule_difficulty difficulty JOIN rule_rule rule USING(rule_id)
            WHERE rule.name='Difficult'""", ())
        connection.execute(
            """INSERT INTO rule_personal_fast_drug
               VALUES (%s,60,1,2,true,true) ON CONFLICT DO NOTHING""",
            (drugs["fast"],))
        connection.execute(
            """INSERT INTO rule_personal_medicinal_drug
               VALUES (%s,%s,true,true,true,%s,1,6)
               ON CONFLICT DO NOTHING""",
            (drugs["medicinal"], medic, difficult))
        connection.execute(
            """INSERT INTO rule_personal_medicinal_slow_drug
               VALUES (%s,true,true,true,30,true,1,1)
               ON CONFLICT DO NOTHING""", (drugs["medicinal-slow"],))
        connection.execute(
            """INSERT INTO rule_personal_panacea
               VALUES (%s,true,true,0,'infection-or-disease')
               ON CONFLICT DO NOTHING""", (drugs["panacea"],))
        connection.execute(
            """INSERT INTO rule_personal_anagathic_dosing
               VALUES (%s,1,'calendar-month',true,true)
               ON CONFLICT DO NOTHING""", (drugs["anagathic"],))
    print("published support drug mechanics for 5 drugs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
