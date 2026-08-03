"""Import paired-source Explosions and the agreed relational ruling."""

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
    session.headers["User-Agent"] = "BaseCepheus explosions importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "explosives affect an area", "usual initiative cost",
        "reduce the damage by 1d6", "half if he dives for cover",
        "ends up prone", "loses his next significant action",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Explosions sources omit: {phrase}")
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
            connection, package, "combat.explosions", "Explosions", "combat",
            "Area damage permits a usual-cost dodge for 1D6 reduction or a "
            "dive for half damage, prone, and loss of the next significant action.")
        payload = {
            "shared_damage_roll": True,
            "dodge_reduction_dice": 1,
            "dive_divisor": 2,
            "dive_rounding": "down",
            "reduction_before_armor": True,
            "dive_ends_prone": True,
            "dive_loses_significant_actions": 1,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Explosions", "personal-explosions",
                "Explosions", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.explosions", payload)
            add_provenance(
                connection, rule_id, package, locator, candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_explosion
               VALUES (%s,true,1,2,'down',true,true,1)
               ON CONFLICT (rule_id) DO NOTHING""",
            (rule_id,),
        )
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-006')
               ON CONFLICT DO NOTHING""",
            (rule_id, "Freeze the referee-declared affected roster, roll damage "
             "once, resolve each target's independent reaction before armor, "
             "then apply armor separately."),
        )
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],),
        )
    print("published Explosions and CE-COMBAT-006")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
