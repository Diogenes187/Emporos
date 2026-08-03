"""Import paired-source Free Action mechanics for CE-COMBAT-019."""

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
    session.headers["User-Agent"] = "BaseCepheus free-actions importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "do not even qualify as a minor action",
        "shouting a warning",
        "pushing a button",
        "checking your watch",
        "as many of these free actions as he likes in a turn",
        "the referee may require him to spend a minor or even a significant action",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Free Action sources omit: {phrase}")

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
            connection, package, "combat.free-actions", "Free Actions",
            "combat", "Turn-scoped negligible actions with referee escalation."
        )
        payload = {
            "performed_during_actor_turn": True,
            "below_minor_action_threshold": True,
            "unbounded_by_default": True,
            "examples": ["shout_warning", "push_button", "check_watch"],
            "multiple_may_require_referee_escalation": True,
            "escalation_costs": ["minor", "significant"],
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Other Actions > Free Actions",
                "personal-free-actions", "Free Actions", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.free-actions", payload)
            add_provenance(
                connection, rule, package, locator, candidate, review,
                "direct" if side == "ogn" else "corroborating",
                side == "ogn")
        connection.execute(
            """INSERT INTO rule_personal_free_action
               VALUES (%s,true,true,true,true,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 performed_during_actor_turn=true,
                 below_minor_action_threshold=true,
                 unbounded_by_default=true,
                 multiple_may_require_referee_escalation=true,
                 escalation_may_cost_minor_action=true,
                 escalation_may_cost_significant_action=true""", (rule,))
        connection.execute(
            "DELETE FROM rule_personal_free_action_example "
            "WHERE free_action_rule_id=%s", (rule,))
        for order, code in enumerate(
            ("shout_warning", "push_button", "check_watch"), 1
        ):
            connection.execute(
                """INSERT INTO rule_personal_free_action_example
                   VALUES (%s,%s,%s)""", (rule, code, order))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published paired-source Free Action mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
