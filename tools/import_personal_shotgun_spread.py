"""Import paired-source Shotgun Spread and agreed corrections."""

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
    session.headers["User-Agent"] = "BaseCepheus shotgun-spread importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "shotgun loaded specifically with flechette rounds",
        "medium or long range", "damage reduced to 2d6",
        "dm+1 bonus to hit", "friend or foe",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Shotgun Spread sources omit: {phrase}")
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
        spread = publish_rule(
            connection, package, "combat.shotgun-spread", "Shotgun Spread",
            "combat", "Flechette-shell spread against a declared target group.")
        payload = {
            "attack_modifier": 1, "damage_dice": 2,
            "ranges": ["medium", "long"],
            "affects_personal_range_bystanders": True,
            "shared_attack_roll": True, "shared_damage_roll": True,
            "armor_resolved_individually": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Special Considerations > Shotgun Spread",
                "personal-shotgun-spread", "Shotgun Spread", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.shotgun-spread", payload)
            add_provenance(
                connection, spread, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        medium, long_range = connection.execute(
            """SELECT
                 (SELECT rule_id FROM rule_rule
                   WHERE rule_code='combat.range.medium'),
                 (SELECT rule_id FROM rule_rule
                   WHERE rule_code='combat.range.long')"""
        ).fetchone()
        connection.execute(
            """INSERT INTO rule_personal_shotgun_spread
               VALUES (%s,1,2,%s,%s,true,true,true,true)
               ON CONFLICT (rule_id) DO NOTHING""",
            (spread, medium, long_range))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-002')
               ON CONFLICT DO NOTHING""",
            (spread, "Correct frag shell to flechette shell; share attack and "
             "damage rolls across the group; resolve armor individually."))
        shotgun, standard = connection.execute(
            """SELECT weapon.item_rule_id,ammunition.ammunition_rule_id
               FROM inv_weapon_definition weapon
               JOIN rule_rule weapon_rule ON weapon_rule.rule_id=weapon.item_rule_id
               JOIN inv_ammunition_definition ammunition
                 ON ammunition.weapon_rule_id=weapon.item_rule_id
               WHERE weapon_rule.rule_code='equipment.weapon.shotgun'
                 AND ammunition.ammunition_code='standard'"""
        ).fetchone()
        ammo_rule = publish_rule(
            connection, package,
            "equipment.ammunition.shotgun.flechette-shell",
            "Shotgun Flechette Shells", "equipment",
            "Shotgun magazine explicitly loaded with flechette shells.")
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Special Considerations > Shotgun Spread",
                "personal-shotgun-flechette-shell",
                "Shotgun Flechette Shells", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "equipment",
                "equipment.ammunition.shotgun.flechette-shell",
                {"weapon": "shotgun", "payload": "flechette-shell"})
            add_provenance(
                connection, ammo_rule, package, locator, candidate, review,
                "interpretation", side == "github")
        connection.execute(
            """INSERT INTO inv_ammunition_definition
               SELECT %s,weapon_rule_id,'flechette-shell',capacity_rounds,
                      minimum_tech_level,cost_credits,mass_grams,
                      reload_procedure,reload_units
               FROM inv_ammunition_definition WHERE ammunition_rule_id=%s
               ON CONFLICT (ammunition_rule_id) DO NOTHING""",
            (ammo_rule, standard))
        connection.execute(
            """INSERT INTO inv_weapon_shotgun_spread_capability VALUES (%s,%s)
               ON CONFLICT DO NOTHING""", (shotgun, ammo_rule))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Shotgun Spread, flechette shells, and adjudication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
