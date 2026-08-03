"""Import paired-source personal software mechanics for CE-EQUIP-008."""
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
    session.headers["User-Agent"] = "BaseCepheus software mechanics importer/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "searched with a computer check or using an agent",
        "without an interface is a formidable",
        "only have language skills",
        "bonus equal to their rating",
        "required for using expert programs",
        "skill at the program's rating -1",
        "only intelligence and education-based checks",
        "expert program grants a +1 dm",
        "computer skill equal to their rating",
        "number of skills simultaneously equal to its rating",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired software mechanics omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        family = dict(connection.execute(
            """SELECT software_code,rule_id
               FROM rule_personal_software_family""").fetchall())
        difficulty = dict(connection.execute(
            """SELECT lower(replace(rule.name,' ','-')),difficulty.rule_id
               FROM rule_difficulty difficulty
               JOIN rule_rule rule USING (rule_id)""").fetchall())
        computer_skill = get_id(
            connection, """SELECT rule_id FROM rule_rule
                WHERE rule_code='skill.computer'""", ())
        connection.execute(
            """INSERT INTO rule_personal_database_mechanic
               VALUES (%s,%s,true) ON CONFLICT DO NOTHING""",
            (family["database"], computer_skill))
        connection.execute(
            """INSERT INTO rule_personal_interface_mechanic
               VALUES (%s,%s,true) ON CONFLICT DO NOTHING""",
            (family["interface"], difficulty["formidable"]))
        for rating, code in enumerate(
            ("average","difficult","very-difficult","formidable")
        ):
            connection.execute(
                """INSERT INTO rule_personal_security_difficulty
                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                (family["security"], rating, difficulty[code]))
        connection.execute(
            """INSERT INTO rule_personal_translator_mechanic
               VALUES (%s,true,true,1,true) ON CONFLICT DO NOTHING""",
            (family["translator"],))
        connection.execute(
            """INSERT INTO rule_personal_intrusion_mechanic
               VALUES (%s,true,true) ON CONFLICT DO NOTHING""",
            (family["intrusion"],))
        for row in (
            (1, "low-autonomous", True, True, False, False, False),
            (2, "high-autonomous", True, True, True, True, False),
            (3, "true-ai", True, True, True, True, True),
        ):
            connection.execute(
                """INSERT INTO rule_personal_intelligent_interface_capability
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (family["intelligent-interface"], *row))
        connection.execute(
            """INSERT INTO rule_personal_expert_mechanic
               VALUES (%s,%s,-1,1) ON CONFLICT DO NOTHING""",
            (family["expert"], family["intelligent-interface"]))
        for code in (
            "characteristic.intelligence", "characteristic.education"
        ):
            characteristic = get_id(
                connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (code,))
            connection.execute(
                """INSERT INTO rule_personal_expert_allowed_characteristic
                   VALUES (%s,%s) ON CONFLICT DO NOTHING""",
                (family["expert"], characteristic))
        connection.execute(
            """INSERT INTO rule_personal_agent_mechanic
               VALUES (%s,%s,true,true,%s,%s) ON CONFLICT DO NOTHING""",
            (family["agent"], computer_skill, family["expert"],
             family["intellect"]))
        connection.execute(
            """INSERT INTO rule_personal_intellect_mechanic
               VALUES (%s,true,true,true) ON CONFLICT DO NOTHING""",
            (family["intellect"],))
    print("published relational mechanics for 8 software families")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
