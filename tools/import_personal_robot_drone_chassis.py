"""Import paired-source robot and drone chassis for CE-EQUIP-016."""
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
CHASSIS = (
    ("cargo-robot", "Cargo Robot", "robot", 11, 75000,
     30, 9, 2, 2, 3, 5, 0, 8),
    ("repair-robot", "Repair Robot", "robot", 11, 10000,
     6, 7, 1, 1, 5, 6, 0, None),
    ("personal-drone", "Personal Drone", "drone", 11, 2000,
     2, 7, 1, 1, None, None, None, None),
    ("probe-drone", "Probe Drone", "drone", 11, 15000,
     3, 7, 3, 3, None, None, None, 5),
    ("autodoc", "Autodoc", "robot", 12, 40000,
     6, 15, 1, 1, 9, 12, 0, None),
    ("combat-drone", "Combat Drone", "drone", 12, 90000,
     12, 10, 4, 4, None, None, None, 9),
    ("servitor", "Servitor", "robot", 13, 120000,
     7, 9, 2, 2, 9, 12, 7, None),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus robot chassis/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "cargo robot (tl 11)", "strength 30", "price cr75,000",
        "repair robot (tl 11)", "personal drone (tl 11)",
        "probe drone (tl 11)", "operating range of five hundred kilometers",
        "autodoc (tl 12)", "combat drone (tl 12)",
        "cr90,000, plus the cost of the weapon", "servitor (tl 13)",
        "cargo drones can be constructed as low as technology level 9",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired robot chassis sources omit: {phrase}")
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
        catalogue = publish_rule(
            connection, package, "equipment.personal-robot-drone-chassis",
            "Personal Robot and Drone Chassis", "equipment",
            "Published personal robot and drone chassis profiles.")
        rules = [catalogue]
        for values in CHASSIS:
            code, name, kind, tech, cost, strength, dexterity, hull, structure, intelligence, education, social, armor = values
            rule_code = ("equipment.probe-drone" if code == "probe-drone"
                         else f"equipment.robot-drone.{code}")
            rule = publish_rule(
                connection, package, rule_code, name, "equipment",
                f"{name} complete chassis.")
            connection.execute(
                """INSERT INTO inv_item_definition
                   (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
                   VALUES (%s,'equipment',%s,%s,NULL)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits""",
                (rule, tech, cost))
            connection.execute(
                """INSERT INTO inv_personal_robot_drone_chassis VALUES
                   (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                    %s,%s) ON CONFLICT DO NOTHING""",
                (rule, code, kind, strength, dexterity, hull, structure,
                 intelligence, education, social, armor,
                 code == "combat-drone",
                 9 if code == "cargo-robot" else None,
                 code == "cargo-robot"))
            rules.append(rule)
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    "Equipment > Robots and Drones", code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "robot_drone_chassis", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 7 personal robot and drone chassis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
