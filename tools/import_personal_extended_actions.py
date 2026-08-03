"""Import paired-source Extended Action mechanics for CE-COMBAT-018."""

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
URL = (
    "https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
    "cepheus-engine-personal-combat/"
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
    session.headers["User-Agent"] = "BaseCepheus extended-actions importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "make a timing roll for the task",
        "six second combat rounds",
        "cannot do anything else",
        "can abandon their action at any time",
        "must make an 8+ roll using the skill in question",
        "negative dm equal to the amount of damage",
        "this round's work does not count",
        "failure by six or more",
        "ruins the task",
        "must start again",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Extended Action sources omit: {phrase}")

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
            connection, package, "combat.extended-actions",
            "Extended Actions", "combat",
            "Timing-derived exclusive combat work with damage interruption."
        )
        payload = {
            "timing_roll_required": True,
            "combat_round_seconds": 6,
            "exclusive_activity": True,
            "may_abandon_any_time": True,
            "interruption_target_number": 8,
            "interruption_damage_dm": "negative_post_armor_damage",
            "failed_check_loses_current_round": True,
            "exceptional_failure_maximum_effect": -6,
            "exceptional_failure_ruins_task": True,
            "ruined_task_restarts_from_beginning": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Other Actions > Extended Actions",
                "personal-extended-actions", "Extended Actions", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.extended-actions", payload)
            add_provenance(
                connection, rule, package, locator, candidate, review,
                "direct" if side == "ogn" else "corroborating",
                side == "ogn")
        connection.execute(
            """INSERT INTO rule_personal_extended_action
               VALUES (%s,true,true,6,true,true,true,8,true,true,true,-6,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 timing_roll_required=true,
                 timing_result_determines_required_rounds=true,
                 combat_round_seconds=6,exclusive_activity=true,
                 may_abandon_any_time=true,
                 hit_requires_interruption_check=true,
                 interruption_target_number=8,
                 interruption_uses_task_skill=true,
                 post_armor_damage_is_negative_dm=true,
                 failed_check_loses_current_round=true,
                 exceptional_failure_maximum_effect=-6,
                 exceptional_failure_ruins_task=true,
                 ruined_task_restarts_from_beginning=true""",
            (rule,),
        )
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],),
        )
    print("published paired-source Extended Action mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
