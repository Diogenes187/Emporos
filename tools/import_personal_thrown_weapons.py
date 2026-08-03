"""Import paired-source Thrown Weapons and CE-COMBAT-011."""
import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book1/personal-combat.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-personal-combat/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus thrown-weapons importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "there are two kinds of thrown weapons",
        "use the normal rules for ranged combat",
        "adds the effect of the athletics check to its damage",
        "the second does not",
        "projectile scatters in a random direction",
        "6 + effect",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Thrown Weapons sources omit: {phrase}")
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
            ("github", github, "src/book1/personal-combat.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        rule_id = publish_rule(
            connection, package, "combat.thrown-weapons", "Thrown Weapons",
            "combat", "Thrown impact weapons add Effect; payload weapons "
            "deliver a separate effect and misses scatter.")
        payload = {
            "delivery_types": ["impact", "payload"],
            "impact_adds_effect": True, "payload_adds_effect": False,
            "miss_scatter_formula": "max(0,6+Effect)",
            "direction_die_sides": 360,
            "impact_point_model": "target_reference_plus_polar_offset",
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Thrown Weapons",
                "personal-thrown-weapons", "Thrown Weapons", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.thrown-weapons", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_thrown_weapon
               VALUES (%s,true,false,6,true,0,360)
               ON CONFLICT (rule_id) DO NOTHING""", (rule_id,))
        dagger = get_id(connection, "SELECT rule_id FROM rule_rule "
            "WHERE rule_code='equipment.weapon.dagger'", ())
        connection.execute(
            """INSERT INTO inv_thrown_delivery_capability
               VALUES (%s,'impact','thrown',true)
               ON CONFLICT (item_rule_id) DO NOTHING""", (dagger,))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-011')
               ON CONFLICT DO NOTHING""",
            (rule_id, "The source-undefined random direction uses an auditable "
             "uniform D360. Non-negative source-literal scatter distance and "
             "a polar offset avoid inventing a global encounter coordinate "
             "system; payload resolution remains a distinct command."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Thrown Weapons and CE-COMBAT-011")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
