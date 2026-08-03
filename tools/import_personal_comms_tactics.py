"""Import paired-source Battlefield Comms, Tactics, and Leadership."""

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

METHODS = (
    ("direct", "Direct Communication", False, False, False, False, False),
    ("hardlink", "Hardlinked Communication", False, False, False, False, False),
    ("radio", "Radio Communication", True, True, False, False, False),
    ("laser", "Laser Communication", False, True, True, False, False),
    ("maser", "Maser Communication", False, True, True, True, False),
    ("meson", "Meson Communication", False, False, False, True, True),
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
    session.headers["User-Agent"] = "BaseCepheus battlefield-comms importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "battlefield comms", "hardlink", "radio", "laser", "maser", "meson",
        "tactics", "leadership", "initiative",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Battlefield Comms sources omit: {phrase}")
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

        def sourced_rule(code, name, domain, summary, heading, payload):
            rule_id = publish_rule(
                connection, package, code, name, domain, summary)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading", heading,
                    code.replace(".", "-"), name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, domain, code, payload)
                add_provenance(
                    connection, rule_id, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule_id

        for code, name, jammed, blocked, los, smoke, moving in METHODS:
            rule_id = sourced_rule(
                f"combat.communication.{code}", name, "combat",
                f"Battlefield communication by {code}.",
                "Personal Combat > Battlefield Comms",
                {"method": code, "can_be_jammed": jammed,
                 "can_be_blocked": blocked, "requires_line_of_sight": los,
                 "penetrates_smoke_aerosols": smoke,
                 "forbidden_while_moving": moving})
            connection.execute(
                """INSERT INTO rule_personal_communication_method
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO NOTHING""",
                (rule_id, code, jammed, blocked, los, smoke, moving))
        for code, skill_code, whole_unit, action in (
            ("tactics", "skill.tactics", True, False),
            ("leadership", "skill.leadership", False, True),
        ):
            rule_id = sourced_rule(
                f"combat.initiative-support.{code}", code.title(), "combat",
                f"{code.title()} check increases initiative by Effect.",
                f"Personal Combat > {code.title()}",
                {"support": code, "skill": skill_code,
                 "affects_whole_unit": whole_unit,
                 "consumes_significant_action": action,
                 "requires_communication": True, "bonus_uses_effect": True})
            skill_id = get_id(
                connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (skill_code,))
            connection.execute(
                """INSERT INTO rule_personal_initiative_support
                   VALUES (%s,%s,%s,%s,%s,true,true)
                   ON CONFLICT (rule_id) DO NOTHING""",
                (rule_id, code, skill_id, whole_unit, action))
            connection.execute(
                """INSERT INTO rule_interpretation
                   (rule_id,interpretation_type,rationale,
                    decision_register_entry)
                   VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-003')
                   ON CONFLICT DO NOTHING""",
                (rule_id, "Encounter sides are units; benefits require an "
                 "active commander-to-member communication link."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Battlefield Comms, Tactics, and Leadership")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
