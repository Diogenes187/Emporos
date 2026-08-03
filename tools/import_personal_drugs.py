"""Import paired-source personal drugs for CE-EQUIP-009."""
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
DRUGS = (
    ("medicinal", "Medicinal Drugs", 5, None),
    ("anti-radiation", "Anti-Radiation Drugs", 8, 1000),
    ("panacea", "Panaceas", 8, 200),
    ("stim", "Stim Drugs", 8, 50),
    ("combat", "Combat Drug", 10, 1000),
    ("fast", "Fast Drug", 10, 200),
    ("metabolic-accelerator", "Metabolic Accelerator", 10, 500),
    ("medicinal-slow", "Medicinal Slow Drug", 11, 500),
    ("anagathic", "Anagathics", 11, 2000),
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
    session.headers["User-Agent"] = "BaseCepheus drugs importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "medicinal drugs | 5 | cr5+",
        "anti-radiation drugs | 8 | cr1,000",
        "combat drug | 10 | cr1,000",
        "medicinal slow drug | 11 | cr500",
        "anagathics | 11 | cr2,000",
        "range in cost from cr5 to 1d6",
        "synthetic anagathics become possible at tl 15",
        "comparable effects at all technology levels",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired drug sources omit: {phrase}")
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
            connection, package, "equipment.personal-drugs",
            "Personal Drugs", "equipment", "Personal drug catalogue.")
        rules = [catalogue]
        for code, name, tech, cost in DRUGS:
            rule = publish_rule(
                connection, package, f"equipment.drug.{code}", name,
                "equipment", f"{name} dose.")
            connection.execute(
                """INSERT INTO inv_item_definition
                   (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
                   VALUES (%s,'equipment',%s,%s,NULL)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=NULL""", (rule, tech, cost))
            if cost is None:
                values = ("minimum-plus-variable", 5, None, 1, 6, 1000)
            else:
                values = ("fixed", cost, cost, None, None, None)
            connection.execute(
                """INSERT INTO inv_personal_drug_definition
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,true)
                   ON CONFLICT DO NOTHING""",
                (rule, code, tech, *values))
            rules.append(rule)
        anagathic = get_id(
            connection, """SELECT item_rule_id
                FROM inv_personal_drug_definition
                WHERE drug_code='anagathic'""", ())
        connection.execute(
            """INSERT INTO rule_anagathic_availability
               VALUES (%s,11,15,true,true) ON CONFLICT DO NOTHING""",
            (anagathic,))
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact,
                    "heading" if order == 0 else "table_row",
                    "Equipment > Drugs", code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_drug", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 9 personal drugs and CE-EQUIP-009")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
