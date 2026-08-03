"""Import paired-source miscellaneous combat actions for CE-COMBAT-024."""

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
    session.headers["User-Agent"] = "BaseCepheus miscellaneous-actions importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "the referee may permit a character to perform a skill check or other action as a minor action",
        "does not require the character's full attention or complex physical actions",
        "requires the character's full attention, concentration, complicated physical actions",
        "time interval of 1-6 seconds",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired miscellaneous-action sources omit: {phrase}")
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
            ("github", github, "src/book1/personal-combat.md", "repository_file",
             GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(connection, works[side], kind, uri,
                                       revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        rows = (
            ("minor", "Minor Miscellaneous Action", False, False, None, None,
             "Personal Combat > Minor Actions > Miscellaneous"),
            ("significant", "Significant Miscellaneous Action", True, True, 1, 6,
             "Personal Combat > Significant Actions > Miscellaneous"),
        )
        batch_ids = [value[1] for value in artifacts.values()]
        for tier, name, attention, complex_action, minimum, maximum, heading in rows:
            code = f"combat.miscellaneous-action.{tier}"
            rule = publish_rule(connection, package, code, name, "combat",
                                f"Referee-authorized {tier} combat action.")
            payload = {"action_tier": tier, "action_cost": 1,
                       "referee_permission_required": True,
                       "permits_skill_check": True, "permits_other_action": True,
                       "requires_full_attention": attention,
                       "permits_complex_physical_action": complex_action,
                       "minimum_seconds": minimum, "maximum_seconds": maximum}
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading", heading,
                    f"personal-miscellaneous-{tier}", name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, "combat", code, payload)
                add_provenance(connection, rule, package, locator, candidate, review,
                               "direct" if side == "ogn" else "corroborating",
                               side == "ogn")
            connection.execute(
                """INSERT INTO rule_personal_miscellaneous_action
                   VALUES (%s,%s,1,true,true,true,%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET action_tier=EXCLUDED.action_tier,
                     action_cost=1,referee_permission_required=true,
                     permits_skill_check=true,permits_other_action=true,
                     requires_full_attention=EXCLUDED.requires_full_attention,
                     permits_complex_physical_action=EXCLUDED.permits_complex_physical_action,
                     minimum_seconds=EXCLUDED.minimum_seconds,
                     maximum_seconds=EXCLUDED.maximum_seconds""",
                (rule, tier, attention, complex_action, minimum, maximum))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""", (batch_ids,))
    print("published paired-source miscellaneous combat actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
