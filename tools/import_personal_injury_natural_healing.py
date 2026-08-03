"""Import paired-source Injury, Natural Healing, and CE-COMBAT-013."""
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
    session.headers["User-Agent"] = "BaseCepheus injury importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "lost at least one point from all three",
        "1.5 meters per combat round",
        "lose their minor action",
        "1d6 + endurance dm per day of full rest",
        "1 + endurance dm per day",
        "equal to his endurance dm per day of rest",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired injury sources omit: {phrase}")
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
            connection, package, "combat.natural-healing",
            "Injury and Natural Healing", "combat",
            "Derived injury state and signed daily physical recovery.")
        payload = {
            "wounded_full_rest": "1D6+Endurance DM",
            "wounded_active": "1+Endurance DM",
            "seriously_wounded_rest": "Endurance DM",
            "serious_movement_limit_metres": 1.5,
            "serious_minor_action_loss": 1,
            "signed_results": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Injury and Recovery > Natural Healing",
                "personal-natural-healing", "Natural Healing", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.natural-healing", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_natural_healing
               VALUES (%s,1,6,true,1,true,true,1.5,1)
               ON CONFLICT (rule_id) DO NOTHING""", (rule_id,))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-013')
               ON CONFLICT DO NOTHING""",
            (rule_id, "Raymond approved signed natural-healing results, "
             "controller-selected degradation allocation, derived injury "
             "status, and one receipt per actor and campaign day."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Injury, Natural Healing, and CE-COMBAT-013")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
