"""Import paired-source ground-force attacks against starship-scale targets."""
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
    session.headers["User-Agent"] = "BaseCepheus scale combat importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "dm +4 bonus to hit",
        "divide its damage by 50",
        "multiple weapons to all target the starship simultaneously",
        "every additional ground weapon beyond the first",
        "add half its damage dice",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired scale-combat sources omit: {phrase}")
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
            connection, package, "combat.ground-force-starship-scale",
            "Ground Force Weaponry against Starship-scale Targets", "combat",
            "Ground weapon attack bonus, cumulative dice, scale conversion, "
            "armor, and Hull damage.")
        payload = {
            "attack_dm": 4,
            "damage_divisor": 50,
            "additional_weapon_dice": "one-half",
            "additional_dice_rounding": "aggregate-then-floor",
            "converted_damage_rounding": "floor",
            "successful_attacks_only": True,
            "primary_weapon": "controller-designated-successful-hit",
            "armor_order": "after-scale-conversion",
            "minimum_damage": False,
            "damage_target": "hull",
        }
        heading = (
            "Personal Combat > Ground Force Weaponry against "
            "Starship-scale Targets"
        )
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading", heading,
                "ground-force-starship-scale",
                "Ground Force Weaponry against Starship-scale Targets", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.ground-force-starship-scale", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_ground_force_starship_attack
               VALUES (%s,4,50,'floor',true,false,'hull')
               ON CONFLICT (rule_id) DO NOTHING""", (rule_id,))
        connection.execute(
            """INSERT INTO rule_ground_force_starship_volley_contribution
               VALUES (%s,1,1,1,2,true,'floor',true,true,true)
               ON CONFLICT (rule_id) DO NOTHING""", (rule_id,))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-016')
               ON CONFLICT DO NOTHING""",
            (rule_id, "Raymond approved aggregate-then-floor half dice, floor "
             "after division by 50, successful attacks only, a designated "
             "successful primary weapon, post-conversion armor, direct Hull "
             "damage, and no cross-scale minimum damage."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published ground-force starship-scale rules and CE-COMBAT-016")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
