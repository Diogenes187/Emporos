"""Import paired-source Sensory Aids catalogue for CE-EQUIP-019."""
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
AIDS = (
    ("torch", "Torch", 1, 1, 250),
    ("lamp-oil", "Lamp Oil", 2, 2, None),
    ("oil-lamp", "Oil Lamp", 2, 10, 500),
    ("binoculars", "Binoculars", 3, 75, 1000),
    ("electric-torch", "Electric Torch", 5, 10, 500),
    ("cold-light-lantern", "Cold Light Lantern", 6, 20, 250),
    ("infrared-goggles", "Infrared Goggles", 6, 500, None),
    ("light-intensifier-goggles", "Light Intensifier Goggles", 7, 500, None),
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
    session.headers["User-Agent"] = "BaseCepheus sensory aids/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "torch | 1 | cr1 | 0.25",
        "lamp oil | 2 | cr2",
        "binoculars | 3 | cr75 | 1",
        "cold light lantern | 6 | cr20 | 0.25",
        "infrared goggles | 6 | cr500",
        "light intensifier goggles | 7 | cr500",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Sensory Aids sources omit: {phrase}")
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
            connection, package, "equipment.personal-sensory-aids",
            "Sensory Aids", "equipment", "Sensory Aids catalogue.")
        rules = [catalogue]
        for code, name, tech, cost, mass in AIDS:
            rule = publish_rule(
                connection, package, f"equipment.sensory-aid.{code}", name,
                "equipment", f"{name} sensory aid.")
            connection.execute(
                """INSERT INTO inv_item_definition VALUES
                   (%s,'equipment',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tech, cost, mass))
            connection.execute(
                """INSERT INTO inv_personal_sensory_aid_definition
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
                    "Equipment > Sensory Aids", rule_code, rule_code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_sensory_aid", rule_code,
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
    print("published 8 sensory aids and CE-EQUIP-019")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
