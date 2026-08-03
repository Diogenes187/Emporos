"""Import paired-source robot/drone options for CE-EQUIP-018."""
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
    session.headers["User-Agent"] = "BaseCepheus robot options/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "armor can be increased by 5",
        "increases the drone or robot's cost by 25%",
        "increasing the cost of the device by +50%",
        "at the cost of cr10,000 + the cost of the weapon",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired robot-option sources omit: {phrase}")
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
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        definitions = (
            ("armor", "Robot/Drone Armor", 5, 2500, None, None, False),
            ("integral-system", "Integral System", None, None,
             5000, None, True),
            ("integral-weapon", "Integral Weapon", None, None,
             None, 10000, True),
        )
        for order, definition in enumerate(definitions, 1):
            code, name, armor, robot_bp, item_bp, fixed, selected = definition
            rule_code = f"equipment.robot-drone-option.{code}"
            rule = publish_rule(
                connection, package, rule_code, name, "equipment",
                f"{name} construction option.")
            connection.execute(
                """INSERT INTO rule_personal_robot_drone_option
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (rule, code, armor, robot_bp, item_bp, fixed, selected))
            payload = {
                "option_code": code, "armor_increase": armor,
                "robot_cost_basis_points": robot_bp,
                "selected_item_cost_basis_points": item_bp,
                "fixed_surcharge_credits": fixed,
            }
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    "Equipment > Robots and Drones > Robot and Drone Options",
                    rule_code, rule_code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "robot_drone_option", rule_code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 3 robot and drone construction options")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
