"""Import paired-source robot and drone framework for CE-EQUIP-015."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
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
    session.headers["User-Agent"] = "BaseCepheus robot framework/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "robot has an intellect program running",
        "drones are remote-controlled by a character",
        "operate in combat like characters but take damage as if they were vehicles",
        "hull and structure characteristics instead of an endurance characteristic",
        "endurance dm of 0", "drones have neither",
        "operator can use his own social standing score",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired robot framework sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        works = {
            "github": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.github-v9.1'", ()),
            "ogn": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.ogn'", ()),
        }
        artifacts = {}
        for side, data, uri, kind, revision, media in (
            ("github", github, "src/book1/equipment.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html")):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        rule = publish_rule(
            connection, package, "equipment.robot-drone-framework",
            "Robot and Drone Framework", "equipment",
            "Shared personal robot and drone operation rules.")
        payload = {
            "combat_like_character": True, "damage_like_vehicle": True,
            "uses_hull_structure": True, "endurance_dm": 0,
            "drone_control_skill": "skill.comms",
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Equipment > Robots and Drones", "robots-and-drones",
                "Robots and Drones", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator,
                "robot_drone_framework", "equipment.robot-drone-framework",
                payload)
            add_provenance(
                connection, rule, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        comms = get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code='skill.comms'", ())
        connection.execute(
            """INSERT INTO rule_personal_robot_drone_framework
               VALUES (%s,%s,true,true,true,0) ON CONFLICT DO NOTHING""",
            (rule, comms))
        connection.execute(
            """INSERT INTO rule_personal_robot_drone_kind VALUES
               (%s,'robot',true,false,true,'usually-zero-with-exceptions'),
               (%s,'drone',false,true,false,'operator-score-for-social-use')
               ON CONFLICT DO NOTHING""", (rule, rule))
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published robot and drone framework with 2 kind rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
