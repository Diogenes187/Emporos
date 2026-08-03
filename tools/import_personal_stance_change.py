"""Import paired-source Changing Stance mechanics for CE-COMBAT-023."""

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
    session.headers["User-Agent"] = "BaseCepheus stance-change importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "change to any one of the three stances",
        "prone, crouched or standing",
        "as a minor action",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Changing Stance sources omit: {phrase}")

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
            connection, package, "combat.stance-change", "Changing Stance",
            "combat", "Spend one minor action to adopt a different stance.")
        payload = {
            "minor_action_cost": 1,
            "available_stances": ["prone", "crouched", "standing"],
            "may_choose_any_stance": True,
            "must_change_stance": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Minor Actions > Changing Stance",
                "personal-changing-stance", "Changing Stance", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.stance-change", payload)
            add_provenance(
                connection, rule, package, locator, candidate, review,
                "direct" if side == "ogn" else "corroborating",
                side == "ogn")
        connection.execute(
            """INSERT INTO rule_personal_stance_change VALUES (%s,1,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 minor_action_cost=1,may_choose_any_stance=true,
                 must_change_stance=true""", (rule,))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published paired-source Changing Stance mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
