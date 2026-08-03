"""Import paired-source Tools catalogue and mechanics for CE-EQUIP-024."""
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
TOOLS = (
    ("mechanical-toolkit", "Mechanical Toolkit", 4, 1000, 12000),
    ("electronics-toolkit", "Electronics Toolkit", 5, 1000, 12000),
    ("lock-pick-set", "Lock Pick Set", 5, 10, None),
    ("medical-kit", "Medical Kit", 7, 1000, 10000),
    ("forensics-toolkit", "Forensics Toolkit", 8, 1000, 12000),
    ("engineering-toolkit", "Engineering Toolkit", 9, 1000, 12000),
    ("scientific-toolkit", "Scientific Toolkit", 9, 1000, 12000),
    ("surveying-toolkit", "Surveying Toolkit", 9, 1000, 12000),
)
OPERATIONS = {
    "mechanical-toolkit": (("repairs", True, None),
                           ("construction", True, None)),
    "electronics-toolkit": (("electrical-repairs", True, None),
                            ("electrical-installations", True, None)),
    "lock-pick-set": (("ordinary-mechanical-lock-picking", False, None),),
    "medical-kit": (("field-medicine", False, "skill.medicine"),),
    "forensics-toolkit": (("crime-scene-investigation", True, None),
                          ("sample-testing", True, None)),
    "engineering-toolkit": (("equipment-repairs", True, None),
                            ("equipment-installation", True, None)),
    "scientific-toolkit": (("scientific-testing", True, None),
                           ("scientific-analysis", True, None)),
    "surveying-toolkit": (("planetary-survey", True, None),
                          ("mapping", True, None)),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus personal tools/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "mechanical toolkit | 4 | 1,000 | 12",
        "lock pick set | 5 | 10",
        "medical kit | 7 | 1,000 | 10",
        "surveying toolkit | 9 | 1,000 | 12",
        "required for electrical repairs and installations",
        "allows picking of ordinary mechanical locks",
        "illegal on worlds of law level 8+",
        "cost rises to cr100 or more",
        "allowing a medic to practice his art in the field",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Tools sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        works = {side: get_id(connection, """SELECT source_work_id FROM src_work
            WHERE work_code=%s""", (code,)) for side, code in (
                ("github", "cepheus-engine.github-v9.1"),
                ("ogn", "cepheus-engine.ogn"))}
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
        catalogue = publish_rule(
            connection, package, "equipment.personal-tools",
            "Tools", "equipment", "Personal Tools catalogue.")
        rules = [catalogue]
        ids = {}
        for code, name, tech, cost, mass in TOOLS:
            rule = publish_rule(
                connection, package, f"equipment.tool.{code}", name,
                "equipment", f"{name} tool equipment.")
            connection.execute(
                """INSERT INTO inv_item_definition VALUES
                   (%s,'equipment',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tech, cost, mass))
            connection.execute(
                """INSERT INTO inv_personal_tool_definition
                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule, code, mass is None))
            ids[code] = rule
            rules.append(rule)
        for code, operations in OPERATIONS.items():
            for operation, required, skill_code in operations:
                skill = None if skill_code is None else get_id(
                    connection,
                    "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                    (skill_code,))
                connection.execute(
                    """INSERT INTO rule_personal_tool_operation
                       VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (ids[code], operation, required, skill))
        connection.execute(
            """INSERT INTO rule_personal_tool_law_price
               VALUES (%s,8,100,true) ON CONFLICT DO NOTHING""",
            (ids["lock-pick-set"],))
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                rule_code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact,
                    "heading" if order == 0 else "table_row",
                    "Equipment > Tools", rule_code, rule_code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_tool", rule_code, {"rule_code": rule_code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 8 tools, 14 operations, and lock-pick law pricing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
