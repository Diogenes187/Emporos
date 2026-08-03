"""Import combat-facing drug mechanics and timing issues for CE-EQUIP-010."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, fetch, get_id, import_batch, normalize, sha256,
    upsert_artifact, upsert_locator,
)

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
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus combat drugs importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "within ten minutes", "absorb up to 100 rads per dose",
        "once per day", "permanent endurance damage of 1d6 per dose",
        "adds +4 to his initiative", "dodge once each round",
        "reduces all damage suffered by two points",
        "twenty seconds (four rounds)", "adds +8 to his initiative",
        "dodge up to twice each round", "45 seconds (eight rounds)",
        "suffers 2d6 points of damage", "removes fatigue",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired combat-drug sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        drugs = dict(connection.execute(
            """SELECT drug_code,item_rule_id
               FROM inv_personal_drug_definition""").fetchall())
        connection.execute(
            """INSERT INTO rule_personal_combat_drug_effect VALUES
               (%s,4,1,false,2,20,4,true,600,true,
                'fatigued',0,NULL),
               (%s,8,2,false,0,45,8,true,600,true,
                'damage-and-exhausted',2,6)
               ON CONFLICT DO NOTHING""",
            (drugs["combat"], drugs["metabolic-accelerator"]))
        connection.execute(
            """INSERT INTO rule_personal_antiradiation_drug
               VALUES (%s,true,600,100,1,1,6,true,true)
               ON CONFLICT DO NOTHING""", (drugs["anti-radiation"],))
        connection.execute(
            """INSERT INTO rule_personal_stim_drug
               VALUES (%s,true,true,true) ON CONFLICT DO NOTHING""",
            (drugs["stim"],))

        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        works = {
            "github": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.github-v9.1'", ()),
            "ogn": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.ogn'", ()),
        }
        locators = {}
        for side, data, uri, kind, revision, media in (
            ("github", github, "src/book1/equipment.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            batch = import_batch(
                connection, package, artifact, sha256(data))
            for order, code in enumerate(("combat","metabolic-accelerator")):
                locators[(side, code)] = upsert_locator(
                    connection, works[side], artifact, "heading",
                    "Equipment > Drugs", f"{code}-timing",
                    code, order)
            connection.execute("""UPDATE src_import_batch
                SET batch_status='published',
                    completed_at=COALESCE(completed_at,clock_timestamp())
                WHERE import_batch_id=%s""", (batch,))
        for code, seconds, rounds, difference in (
            ("combat", 20, 4, 4),
            ("metabolic-accelerator", 45, 8, 3),
        ):
            issue_code = f"equipment.drug.{code}-activation-timing"
            connection.execute(
                """INSERT INTO src_issue
                   (issue_code,domain_code,issue_type,review_priority,
                    subject_code,title,problem_statement,published_value,
                    calculated_value,difference_value,value_unit,
                    reviewer_question,requested_evidence,engine_disposition)
                   VALUES (%s,'equipment.drug','arithmetic_conflict','low',
                    %s,%s,%s,%s,%s,%s,'seconds',%s,%s,'preserve_published')
                   ON CONFLICT DO NOTHING""",
                (issue_code, code, f"{code} activation timing differs",
                 "Printed seconds and rounds are unequal at six seconds/round.",
                 f"{seconds} seconds; {rounds} rounds",
                 f"{rounds*6} seconds from canonical rounds", difference,
                 "Which printed timing should govern runtime activation?",
                 "Publisher errata or edition commentary."))
            issue = get_id(
                connection, "SELECT source_issue_id FROM src_issue "
                "WHERE issue_code=%s", (issue_code,))
            for side, role in (("github","primary"),("ogn","corroborating")):
                connection.execute(
                    """INSERT INTO src_issue_locator VALUES (%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    (issue, locators[(side, code)], role))
    print("published combat drug mechanics and 2 timing issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
