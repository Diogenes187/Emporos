"""Import paired-source Personal Combat Grappling and CE-COMBAT-010."""
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
    session.headers["User-Agent"] = "BaseCepheus grappling importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "attacker must move to personal range", "continue the grapple",
        "disarm his opponent", "drag his opponent up to three meters",
        "inflict damage equal to 2 + the effect", "knock his opponent prone",
        "throw his opponent up to three meters for 1d6 damage",
        "throwing an opponent always ends the grapple",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Grappling sources omit: {phrase}")
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
            connection, package, "combat.grappling", "Grappling", "combat",
            "Opposed Natural Weapons checks at Personal range produce one "
            "of seven winner-selected grapple outcomes.")
        payload = {
            "skill": "skill.natural-weapons",
            "range": "combat.range.personal", "action_cost": 1,
            "damage_base": 2, "disarm_take_minimum_effect": 6,
            "maximum_displacement_metres": 3, "throw_damage": "1D6",
            "ties_have_no_winner": True, "armor_applies": False,
            "options": [
                "continue", "disarm", "drag", "escape", "damage",
                "knock_prone", "throw",
            ],
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Grappling", "personal-grappling",
                "Grappling", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.grappling", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        skill = get_id(connection, "SELECT rule_id FROM rule_rule "
            "WHERE rule_code='skill.natural-weapons'", ())
        personal_range = get_id(connection, "SELECT rule_id FROM rule_rule "
            "WHERE rule_code='combat.range.personal'", ())
        connection.execute(
            """INSERT INTO rule_personal_grapple
               VALUES (%s,%s,%s,1,2,6,3,1,6,true,false)
               ON CONFLICT (rule_id) DO NOTHING""",
            (rule_id, skill, personal_range))
        options = (
            ("continue", 1, True, False, False, False),
            ("disarm", 2, True, False, False, False),
            ("drag", 3, True, False, True, False),
            ("escape", 4, False, False, False, False),
            ("damage", 5, True, False, False, True),
            ("knock_prone", 6, True, False, False, False),
            ("throw", 7, False, True, True, True),
        )
        for option in options:
            connection.execute(
                """INSERT INTO rule_personal_grapple_option
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                option)
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-010')
               ON CONFLICT DO NOTHING""",
            (rule_id, "Opposed totals, ties, winning-margin Effect, action "
             "cost, exclusive current state, armor exclusion, and relational "
             "outcome state follow the approved implementation boundary."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Grappling and CE-COMBAT-010")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
