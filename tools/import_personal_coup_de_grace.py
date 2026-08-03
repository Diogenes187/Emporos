"""Import paired-source Coup de Grace mechanics for CE-COMBAT-017."""

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
    session.headers["User-Agent"] = "BaseCepheus coup-de-grace importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "melee weapon to deliver a coup de grace",
        "helpless opponent that is within close range",
        "ranged weapon to do so",
        "provided they are adjacent to the target",
        "attack automatically hit",
        "opponent dies",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Coup de Grace sources omit: {phrase}")

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
            connection, package, "combat.coup-de-grace", "Coup de Grace",
            "combat", "Automatically kill a helpless opponent with a weapon."
        )
        payload = {
            "helpless_target_required": True,
            "melee_maximum_range_code": "close-quarters",
            "ranged_requires_adjacency": True,
            "attack_roll_required": False,
            "automatic_hit": True,
            "target_dies": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Significant Actions > Coup de Grace",
                "personal-coup-de-grace", "Coup de Grace", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.coup-de-grace", payload)
            add_provenance(
                connection, rule, package, locator, candidate, review,
                "direct" if side == "ogn" else "corroborating",
                side == "ogn")
        connection.execute(
            """INSERT INTO rule_personal_coup_de_grace
               VALUES (%s,true,true,'close-quarters',true,true,false,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 helpless_target_required=true,melee_weapon_permitted=true,
                 melee_maximum_range_code='close-quarters',
                 ranged_weapon_permitted=true,ranged_requires_adjacency=true,
                 attack_roll_required=false,automatic_hit=true,target_dies=true""",
            (rule,),
        )
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],),
        )
    print("published paired-source Coup de Grace mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
