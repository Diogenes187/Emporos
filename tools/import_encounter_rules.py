"""Import paired-source social encounter and attitude rules."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book3/social-encounters.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-social-encounters/")
TYPES = ["routine", "legal", "patron", "random", "rumor", "scenario"]
ATTITUDES = [
    ("hostile", "Hostile", "Will take risks to oppose you"),
    ("unfriendly", "Unfriendly", "Wishes you ill"),
    ("indifferent", "Indifferent", "Doesn't care either way"),
    ("friendly", "Friendly", "Wishes you well"),
    ("helpful", "Helpful", "Will take risks to aid you"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus encounter importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    required = [
        "routine legal patron random rumor and scenario",
        "hostile will take risks to oppose you",
        "helpful will take risks to aid you",
        "difficult -2 social standing based check",
        "players get to choose their characters attitudes",
    ]
    for phrase in required:
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired social sources disagree or omit: {phrase}")

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
            ("github", github, "src/book3/social-encounters.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))

        def source_rule(code, name, description, payload, heading, anchor):
            rule = publish_rule(
                connection, package, code, name, "encounter", description)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row", heading,
                    anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "encounter", code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        for order, code in enumerate(TYPES, 1):
            name = f"{code.title()} Encounter"
            rule = source_rule(
                f"encounter.type.{code}", name,
                f"Source-defined {code} social encounter.",
                {"encounter_type": code, "display_order": order},
                "Social Encounters > Encounter Types", f"encounter-type-{code}")
            connection.execute("""INSERT INTO rule_encounter_type
                (rule_id,encounter_type_code,display_order)
                VALUES (%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                encounter_type_code=EXCLUDED.encounter_type_code,
                display_order=EXCLUDED.display_order""", (rule, code, order))

        for order, (code, name, meaning) in enumerate(ATTITUDES, 1):
            rule = source_rule(
                f"encounter.attitude.{code}", name, meaning,
                {"attitude": code, "meaning": meaning, "source_order": order},
                "Social Encounters > Influencing Attitudes",
                f"attitude-{code}")
            connection.execute("""INSERT INTO rule_attitude
                (rule_id,attitude_code,source_order,meaning)
                VALUES (%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                attitude_code=EXCLUDED.attitude_code,
                source_order=EXCLUDED.source_order,
                meaning=EXCLUDED.meaning""", (rule, code, order, meaning))

        influence = source_rule(
            "encounter.attitude-influence", "Influence Attitude", "Influence",
            {"difficulty": "difficult", "success_shift": 1,
             "exceptional_success_shift": 2, "failure_shift": 0,
             "exceptional_failure_shift": -1,
             "usual_attempts_per_scene": 1,
             "can_force_player_character": False},
            "Social Encounters > Influencing Attitudes", "influence-attitude")
        difficult = get_id(connection, """SELECT r.rule_id FROM rule_rule r
            WHERE r.rule_code='difficulty.difficult'""", ())
        connection.execute("""INSERT INTO rule_attitude_influence_system
            (rule_id,difficulty_rule_id,success_shift,
             exceptional_success_shift,failure_shift,
             exceptional_failure_shift,usual_attempts_per_scene,
             can_force_player_character)
            VALUES (%s,%s,1,2,0,-1,1,false)
            ON CONFLICT (rule_id) DO UPDATE SET
            difficulty_rule_id=EXCLUDED.difficulty_rule_id,
            success_shift=1,exceptional_success_shift=2,failure_shift=0,
            exceptional_failure_shift=-1,usual_attempts_per_scene=1,
            can_force_player_character=false""", (influence, difficult))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 6 encounter types, 5 attitudes, and influence rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
