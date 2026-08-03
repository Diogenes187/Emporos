"""Import paired-source Panic Fire and the agreed tier interpretation."""

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
    session.headers["User-Agent"] = "BaseCepheus panic-fire importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "small arms slug thrower", "uses all remaining rounds",
        "burst fire rules for damage", "dm -2 penalty to hit",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Panic Fire sources omit: {phrase}")

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
        rule = publish_rule(
            connection, package, "combat.panic-fire", "Panic Fire", "combat",
            "Consume all remaining slug-thrower rounds for burst damage.")
        payload = {
            "attack_modifier": -2, "consumes_all_remaining": True,
            "damage_only_burst_fire": True,
            "tier_selection_code": "greatest-not-exceeding",
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Special Considerations > Panic Fire",
                "personal-panic-fire", "Panic Fire", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.panic-fire", payload)
            add_provenance(
                connection, rule, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_panic_fire
               VALUES (%s,-2,true,true,'greatest-not-exceeding')
               ON CONFLICT (rule_id) DO UPDATE SET attack_modifier=-2,
                 consumes_all_remaining=true,damage_only_burst_fire=true,
                 tier_selection_code='greatest-not-exceeding'""", (rule,))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,%s)
               ON CONFLICT DO NOTHING""",
            (rule,
             "For intermediate ammunition counts, consume every round and use "
             "the greatest published Burst Fire damage tier not exceeding it.",
             "CE-COMBAT-001"))
        connection.execute("DELETE FROM inv_weapon_panic_fire_capability")
        connection.execute(
            """INSERT INTO inv_weapon_panic_fire_capability
               SELECT DISTINCT mode.item_rule_id,
                      split_part(skill.rule_code,'.',2)
               FROM inv_weapon_attack_mode mode
               JOIN rule_rule skill
                 ON skill.rule_id=mode.required_skill_rule_id
               WHERE skill.rule_code IN (
                   'skill.slug-pistol','skill.slug-rifle'
               )""")
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Panic Fire rules, eligibility, and interpretation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
