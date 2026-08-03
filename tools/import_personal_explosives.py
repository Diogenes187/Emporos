"""Import paired-source personal explosives for CE-EQUIP-012."""
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
EXPLOSIVES = (
    ("plastic", "Plastic", 6, 200, 3, 1, 2, False, False),
    ("pocket-nuke", "Pocket Nuke", 12, 20000, 2, 20, 15, False, True),
    ("tdx", "TDX", 12, 1000, 4, 1, 4, True, False),
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
    session.headers["User-Agent"] = "BaseCepheus explosives importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "skill check multiplies the damage with a minimum of",
        "damage for an effect of 0 or 1",
        "not legally available on any world with a law level of 1 or greater",
        "plastic | 6 | 3d6 | 2d6 meters | 200",
        "pocket nuke | 12 | 2d6 x 20 | 15d6 meters | 20,000",
        "tdx | 12 | 4d6 | 4d6 meters | 1,000",
        "too large to fit into a grenade launcher",
        "explodes only along the horizontal axis",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired explosive sources omit: {phrase}")
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
        catalogue = publish_rule(
            connection, package, "equipment.personal-explosives",
            "Personal Explosives", "equipment", "Personal explosive catalogue.")
        rules = [catalogue]
        for code, name, tech, cost, dice, multiplier, radius, axis, too_large in EXPLOSIVES:
            rule = publish_rule(
                connection, package, f"equipment.explosive.{code}", name,
                "equipment", f"{name} explosive.")
            connection.execute(
                """INSERT INTO inv_item_definition
                   (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
                   VALUES (%s,'weapon',%s,%s,NULL)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,mass_grams=NULL""",
                (rule, tech, cost))
            connection.execute(
                """INSERT INTO inv_personal_explosive_definition
                   VALUES (%s,%s,%s,6,%s,%s,6,'metre',true,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (rule, code, dice, multiplier, radius, axis, too_large))
            rules.append(rule)
        demolitions = get_id(connection, """SELECT rule_id FROM rule_rule
            WHERE rule_code='skill.demolitions'""", ())
        connection.execute(
            """INSERT INTO rule_personal_explosive_use
               VALUES (%s,%s,1,1,true,true,1) ON CONFLICT DO NOTHING""",
            (catalogue, demolitions))
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact,
                    "heading" if order == 0 else "table_row",
                    "Equipment > Explosives", code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_explosive", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 3 personal explosives and CE-EQUIP-012")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
