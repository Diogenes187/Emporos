"""Import paired-source Firing into Combat and CE-COMBAT-009."""
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
    session.headers["User-Agent"] = "BaseCepheus firing-into-combat importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "firing into combat", "personal range to another combatant",
        "attack suffers a", "if the attack misses", "on a 4+",
        "nearest other combatant",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(
                f"Paired Firing into Combat sources omit: {phrase}")
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
            connection, package, "combat.firing-into-combat",
            "Firing into Combat", "combat",
            "Shooting at a target beside another combatant suffers DM-2; "
            "a miss redirects to the nearest other combatant on 1D6 4+.")
        payload = {
            "attack_modifier": -2, "scatter_die_sides": 6,
            "scatter_hit_minimum": 4, "nearest_only": True,
            "permits_friendly_targets": True,
            "redirected_uses_original_effect": True,
            "redirected_excludes_kill_aim": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Firing into Combat",
                "personal-firing-into-combat", "Firing into Combat", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.firing-into-combat", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_firing_into_combat
               VALUES (%s,-2,6,4,true,true,true,true)
               ON CONFLICT (rule_id) DO NOTHING""", (rule_id,))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-009')
               ON CONFLICT DO NOTHING""",
            (rule_id, "The referee freezes relational Personal-range "
             "proximity tiers. Friend and foe are eligible; nearest-tier ties "
             "are random. Redirected damage retains the original negative "
             "Effect but excludes kill-aim damage."),
        )
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],),
        )
    print("published Firing into Combat and CE-COMBAT-009")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
