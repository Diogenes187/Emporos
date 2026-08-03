"""Import paired-source Drawing and Reloading weapon-ready mechanics."""

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
    session.headers["User-Agent"] = "BaseCepheus weapon-ready importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "depends on its size and ease of use",
        "listed in the description of each weapon",
        "most weapons take one minor action to draw",
        "some weapons are especially fast or slow",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired weapon-ready sources omit: {phrase}")
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
            connection, package, "combat.weapon-readying", "Weapon Readying",
            "combat", "Published draw-time default and explicit source gap.")
        payload = {
            "default_minor_actions": 1,
            "time_depends_on_size_and_ease": True,
            "weapon_description_governs_specific_time": True,
            "especially_fast_or_slow_exceptions_exist": True,
            "source_specific_profiles_absent": True,
            "agreed_interpretation": "default_one_unless_explicit_or_referee_override",
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Minor Actions > Drawing and Reloading",
                "personal-weapon-readying", "Drawing and Reloading", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.weapon-readying", payload)
            add_provenance(connection, rule, package, locator, candidate, review,
                "direct" if side == "ogn" else "corroborating", side == "ogn")
        connection.execute("""INSERT INTO rule_personal_weapon_readying
            VALUES (%s,1,true,true,true,true,true)
            ON CONFLICT (rule_id) DO UPDATE SET default_minor_actions=1,
              time_depends_on_size_and_ease=true,
              weapon_description_governs_specific_time=true,
              especially_fast_or_slow_exceptions_exist=true,
              source_specific_profiles_absent=true,
              referee_override_requires_reason=true""", (rule,))
        connection.execute("DELETE FROM inv_weapon_ready_profile")
        connection.execute("""INSERT INTO rule_interpretation
            (rule_id,interpretation_type,rationale,decision_register_entry)
            VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-021')
            ON CONFLICT DO NOTHING""",
            (rule, "Use the published one-minor-action default where the "
                   "promised weapon-specific ready time is absent; preserve "
                   "explicit and referee-reasoned override lanes."))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published paired-source weapon-ready mechanics and CE-COMBAT-021")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
