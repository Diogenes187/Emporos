"""Import paired-source Shelters catalogue and capabilities for CE-EQUIP-021."""
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
SHELTERS = (
    ("tarpaulin", "Tarpaulin", 1, 10, 2000),
    ("tent", "Tent", 2, 200, 3000),
    ("pre-fabricated-cabin", "Pre-Fabricated Cabin", 6, 10000, 4000000),
    ("basic-life-support-supplies", "Basic Life Support Supplies",
     7, 100, 2000),
    ("pressure-tent", "Pressure Tent", 7, 2000, 25000),
    ("advanced-base", "Advanced Base", 8, 50000, 6000000),
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
    session.headers["User-Agent"] = "BaseCepheus shelters/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "tarpaulin | 1 | cr10 | 2",
        "pre-fabricated cabin | 6 | cr10,000 | 4,000",
        "basic life support supplies | 7 | cr100 | 2",
        "advanced base | 8 | cr50,000 | 6,000",
        "requires 12 man-hours to erect or dismantle",
        "life-support for six people for 7 days",
        "support one person for one day",
        "there is no airlock",
        "measures 4 meters long by 2 meters wide",
        "temperatures down to 0",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Shelters sources omit: {phrase}")
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
            connection, package, "equipment.personal-shelters",
            "Shelters", "equipment", "Personal Shelters catalogue.")
        rules = [catalogue]
        shelter_ids = {}
        for code, name, tech, cost, mass in SHELTERS:
            rule = publish_rule(
                connection, package, f"equipment.shelter.{code}", name,
                "equipment", f"{name} shelter equipment.")
            connection.execute(
                """INSERT INTO inv_item_definition VALUES
                   (%s,'equipment',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tech, cost, mass))
            connection.execute(
                """INSERT INTO inv_personal_shelter_definition
                   VALUES (%s,%s) ON CONFLICT DO NOTHING""", (rule, code))
            shelter_ids[code] = rule
            rules.append(rule)
        capabilities = (
            ("tarpaulin",None,"not-applicable",True,False,"not-stated",
             "not-stated",None,None,None,None,None,None,None,4,2),
            ("tent",2,"unpressurized",True,True,"light-to-moderate",
             "down-to-celsius",0,None,None,None,None,None,None,None,None),
            ("pre-fabricated-cabin",6,"unpressurized",True,True,
             "light-to-severe","down-to-celsius",-10,8,8,None,None,
             None,None,None,None),
            ("basic-life-support-supplies",None,"not-applicable",False,False,
             "not-stated","not-stated",None,None,None,None,1,
             None,None,None,None),
            ("pressure-tent",2,"pressurized-standard",True,True,"up-to-strong",
             "not-stated",None,None,None,None,None,False,True,None,None),
            ("advanced-base",6,"pressurized-standard",True,False,
             "below-hurricane","all-but-most-extreme",None,12,12,42,None,
             None,None,None,None),
        )
        for row in capabilities:
            code, *values = row
            connection.execute(
                """INSERT INTO rule_personal_shelter_capability
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (shelter_ids[code], *values))
        for code in ("pre-fabricated-cabin", "advanced-base"):
            connection.execute(
                """INSERT INTO rule_personal_modular_shelter_geometry
                   VALUES (%s,16,1.5,1.5,2,true)
                   ON CONFLICT DO NOTHING""", (shelter_ids[code],))
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                rule_code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact,
                    "heading" if order == 0 else "table_row",
                    "Equipment > Shelters", rule_code, rule_code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_shelter", rule_code, {"rule_code": rule_code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 6 shelters, capabilities, and modular geometry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
