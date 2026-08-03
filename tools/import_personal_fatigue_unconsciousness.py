"""Import paired-source Fatigue, Unconsciousness, and CE-COMBAT-012."""
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
    session.headers["User-Agent"] = "BaseCepheus fatigue importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    phrases = (
        "a fatigued character suffers a -2 dm to all checks",
        "3 - the character's endurance dm hours",
        "while already fatigued they fall unconscious",
        "endurance check after every minute of unconsciousness",
        "+1 dm on the check for every check previously failed",
    )
    for phrase in phrases:
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired condition sources omit: {phrase}")
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
        definitions = (
            ("combat.fatigue", "Fatigue", "Fatigue", {
                "check_modifier": -2, "rest_base_hours": 3,
                "rest_uses_endurance_modifier": True,
                "repeated_fatigue_causes_unconsciousness": True,
            }),
            ("combat.unconsciousness", "Unconsciousness", "Unconsciousness", {
                "recovery_interval_minutes": 1,
                "prior_failure_modifier": 1,
                "recovery_difficulty": "difficulty.average",
                "waking_clears_fatigue": False,
            }),
        )
        rule_ids = {}
        for code, name, heading, payload in definitions:
            rule_id = publish_rule(
                connection, package, code, name, "combat",
                f"Personal combat {name.lower()} procedure.")
            rule_ids[code] = rule_id
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    f"Personal Combat > Damage > {heading}",
                    f"personal-{heading.lower()}", heading, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, "combat",
                    code, payload)
                add_provenance(
                    connection, rule_id, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute(
            """INSERT INTO rule_personal_fatigue
               VALUES (%s,-2,3,true,true)
               ON CONFLICT (rule_id) DO NOTHING""",
            (rule_ids["combat.fatigue"],))
        average = get_id(connection, "SELECT rule_id FROM rule_rule "
            "WHERE rule_code='difficulty.average'", ())
        connection.execute(
            """INSERT INTO rule_personal_unconsciousness
               VALUES (%s,1,%s,1,false)
               ON CONFLICT (rule_id) DO NOTHING""",
            (rule_ids["combat.unconsciousness"], average))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-012')
               ON CONFLICT DO NOTHING""",
            (rule_ids["combat.unconsciousness"],
             "Raymond approved Average 8+ recovery, elapsed-minute attempts, "
             "cumulative prior-failure DM, fatigue retained on waking, and "
             "non-negative frozen rest duration."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Fatigue, Unconsciousness, and CE-COMBAT-012")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
