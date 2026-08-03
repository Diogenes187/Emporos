"""Import paired-source Healing and Mental Characteristics."""
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
    session.headers["User-Agent"] = "BaseCepheus mental healing importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "other than psionic strength",
        "intelligence or even their education",
        "each mental characteristic heals at the rate of one point per day",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired mental-healing sources omit: {phrase}")
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
            connection, package, "combat.mental-characteristic-healing",
            "Healing and Mental Characteristics", "combat",
            "Daily Intelligence and Education recovery; Psionic Strength "
            "excluded.")
        payload = {
            "eligible_characteristics": [
                "characteristic.intelligence",
                "characteristic.education",
            ],
            "points_per_characteristic_per_day": 1,
            "excluded_characteristics": [
                "characteristic.psionic-strength",
            ],
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Injury and Recovery > "
                "Healing and Mental Characteristics",
                "personal-mental-characteristic-healing",
                "Healing and Mental Characteristics", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.mental-characteristic-healing", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_mental_healing
               VALUES (%s,1,true) ON CONFLICT (rule_id) DO NOTHING""",
            (rule_id,))
        connection.execute(
            """INSERT INTO rule_personal_mental_healing_characteristic
               SELECT %s,rule_id,1 FROM rule_rule
               WHERE rule_code=ANY(%s)
               ON CONFLICT (characteristic_rule_id) DO NOTHING""",
            (rule_id, [
                "characteristic.intelligence",
                "characteristic.education",
            ]))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-015')
               ON CONFLICT DO NOTHING""",
            (rule_id, "One campaign-day receipt restores one point to each "
             "damaged Intelligence/Education characteristic, capped at its "
             "maximum; Psionic Strength is excluded."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Healing and Mental Characteristics and CE-COMBAT-015")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
