"""Import paired-source Survival Equipment catalogue for CE-EQUIP-022."""
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
ITEMS = (
    ("cold-weather-clothing", "Cold Weather Clothing", 1, 200, 2000),
    ("filter-mask", "Filter Mask", 3, 10, None),
    ("swimming-equipment", "Swimming Equipment", 3, 200, 1000),
    ("combination-mask", "Combination Mask", 5, 150, None),
    ("oxygen-tanks", "Oxygen Tanks", 5, 500, 5000),
    ("respirator", "Respirator", 5, 100, None),
    ("underwater-air-tanks", "Underwater Air Tanks", 5, 800, 5000),
    ("artificial-gill", "Artificial Gill", 8, 4000, 4000),
    ("environment-suit", "Environment Suit", 8, 500, None),
    ("rescue-bubble", "Rescue Bubble", 9, 600, 3000),
    ("thruster-pack", "Thruster Pack", 9, 2000, 5000),
    ("portable-generator", "Portable Generator", 10, 500000, 15000),
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
    session.headers["User-Agent"] = "BaseCepheus survival equipment/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "cold weather clothing | 1 | cr200 | 2",
        "filter mask | 3 | cr10",
        "combination mask | 5 | cr150",
        "oxygen tanks | 5 | cr500 | 5",
        "artificial gill | 8 | cr4,000 | 4",
        "environment suit | 8 | cr500",
        "rescue bubble | 9 | cr600 | 3",
        "portable generator | 10 | cr500,000 | 15",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(
                f"Paired Survival Equipment sources omit: {phrase}")
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
            connection, package, "equipment.personal-survival-equipment",
            "Survival Equipment", "equipment",
            "Personal Survival Equipment catalogue.")
        rules = [catalogue]
        for code, name, tech, cost, mass in ITEMS:
            rule = publish_rule(
                connection, package, f"equipment.survival.{code}", name,
                "equipment", f"{name} survival equipment.")
            connection.execute(
                """INSERT INTO inv_item_definition VALUES
                   (%s,'equipment',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tech, cost, mass))
            connection.execute(
                """INSERT INTO inv_personal_survival_equipment_definition
                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule, code, mass is None))
            rules.append(rule)
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                rule_code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact,
                    "heading" if order == 0 else "table_row",
                    "Equipment > Survival Equipment",
                    rule_code, rule_code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_survival_equipment", rule_code,
                    {"rule_code": rule_code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 12 survival equipment items and CE-EQUIP-022")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
