"""Import paired-source suppression-fire rules and immunities."""

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
IMMUNITIES = (
    ("vehicle-enclosed", "Vehicles or Fully Enclosed Occupants"),
    ("zealot", "Zealots"),
    ("mechanical-android", "Mechanical or Android Targets"),
    ("full-battle-dress", "Full Battle Dress"),
    ("suicidal", "Suicidal Targets"),
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
    session.headers["User-Agent"] = "BaseCepheus suppression-fire importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "double the normal amount of ammunition",
        "initiative penalty equal to the effect",
        "current and following combat round",
        "highest effect takes precedence",
        "target must be allowed to take one action",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired suppression-fire sources omit: {phrase}")

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

        def sourced(code, name, payload, anchor):
            rule = publish_rule(
                connection, package, code, name, "combat",
                "Published suppression-fire procedure.")
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    "Personal Combat > Special Considerations > Suppression Fire",
                    anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, "combat", code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        procedure = sourced(
            "combat.suppression-fire", "Suppression Fire",
            {"attack_modifier": -2, "ammunition_multiplier": 2,
             "check_modifier": -1, "duration_rounds": 1,
             "initiative_penalty_uses_effect": True,
             "highest_effect_only": True,
             "requires_intervening_action": True},
            "personal-suppression-fire")
        connection.execute(
            """INSERT INTO rule_personal_suppression_fire
               VALUES (%s,-2,2,-1,1,true,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 attack_modifier=-2,ammunition_multiplier=2,
                 check_modifier=-1,duration_rounds=1,
                 initiative_penalty_uses_effect=true,
                 highest_effect_only=true,requires_intervening_action=true""",
            (procedure,))
        for code, name in IMMUNITIES:
            rule = sourced(
                f"combat.suppression-immunity.{code}", name,
                {"immunity_code": code}, f"personal-suppression-{code}")
            connection.execute(
                """INSERT INTO rule_personal_suppression_immunity
                   VALUES (%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                   immunity_code=EXCLUDED.immunity_code""", (rule, code))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published suppression-fire rules and immunities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
