"""Import paired-source Extreme Range Firing and CE-COMBAT-007."""

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
    session.headers["User-Agent"] = "BaseCepheus extreme-range importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "additional dm of -2", "at least three levels of skill",
        "must be stationary", "some kind of rest",
        "vehicles must be stationary", "half damage (round up)",
        "combined with aiming for the kill",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Extreme Range sources omit: {phrase}")
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
            connection, package, "combat.extreme-range-firing",
            "Extreme Range Firing", "combat",
            "Distant-capable weapons may fire beyond ordinary range at DM-2 "
            "when a skilled, stationary firer uses a rest and has line of sight.")
        payload = {
            "base_range": "combat.range.distant",
            "additional_attack_modifier": -2,
            "minimum_skill_level": 3,
            "requires_line_of_sight": True,
            "requires_stationary_firer": True,
            "requires_firing_rest": True,
            "vehicle_requires_stationary": True,
            "energy_damage_divisor": 2,
            "energy_damage_rounding": "up",
            "permits_kill_aim": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Extreme Range Firing",
                "personal-extreme-range-firing", "Extreme Range Firing", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.extreme-range-firing", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        distant = get_id(
            connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code='combat.range.distant'",
            ())
        connection.execute(
            """INSERT INTO rule_personal_extreme_range
               VALUES (%s,%s,-2,3,true,true,true,true,2,'up',true)
               ON CONFLICT (rule_id) DO NOTHING""",
            (rule_id, distant),
        )
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-007')
               ON CONFLICT DO NOTHING""",
            (rule_id, "The referee authorizes the source-undefined boundary; "
             "rest, line of sight, skill, movement, and any vehicle platform "
             "are frozen relational declaration facts."),
        )
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],),
        )
    print("published Extreme Range Firing and CE-COMBAT-007")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
