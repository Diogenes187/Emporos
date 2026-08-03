"""Import paired-source burst-fire rules and weapon eligibility."""

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

BURSTS = (
    (3, 1, 0, 1),
    (4, 1, 1, 0),
    (10, 2, 2, 0),
    (20, 3, 3, 0),
    (100, 4, 4, 0),
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
    session.headers["User-Agent"] = "BaseCepheus burst-fire importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "increasing the chances of scoring a hit",
        "precise grouped burst",
        "3 round burst +1 +1 point of damage",
        "100 round burst +4 +4d6 damage",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired burst-fire sources omit: {phrase}")

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

        def source_rule(code, name, description, payload, anchor):
            rule = publish_rule(
                connection, package, code, name, "combat", description)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    "Personal Combat > Special Considerations > Burst Fire",
                    anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "combat", code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        burst_ids = {}
        for rounds, attack_dm, extra_dice, extra_flat in BURSTS:
            code = f"combat.burst-size.{rounds}"
            rule_id = source_rule(
                code, f"{rounds}-Round Burst",
                f"Published {rounds}-round burst-fire benefits.",
                {"rounds_consumed": rounds, "attack_modifier": attack_dm,
                 "extra_damage_dice": extra_dice,
                 "extra_damage_flat": extra_flat},
                f"personal-burst-{rounds}")
            burst_ids[rounds] = rule_id
            connection.execute(
                """INSERT INTO rule_personal_burst_size
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     rounds_consumed=EXCLUDED.rounds_consumed,
                     attack_modifier=EXCLUDED.attack_modifier,
                     extra_damage_dice=EXCLUDED.extra_damage_dice,
                     extra_damage_flat=EXCLUDED.extra_damage_flat""",
                (rule_id, rounds, attack_dm, extra_dice, extra_flat))

        for code, name, accuracy, damage in (
            ("spray", "Spray Burst", True, False),
            ("grouped", "Grouped Burst", False, True),
        ):
            rule_id = source_rule(
                f"combat.burst-option.{code}", name,
                f"Apply the burst to {'accuracy' if accuracy else 'damage'}.",
                {"option_code": code, "applies_attack_modifier": accuracy,
                 "applies_extra_damage": damage},
                f"personal-burst-option-{code}")
            connection.execute(
                """INSERT INTO rule_personal_burst_option
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     option_code=EXCLUDED.option_code,
                     applies_attack_modifier=EXCLUDED.applies_attack_modifier,
                     applies_extra_damage=EXCLUDED.applies_extra_damage""",
                (rule_id, code, accuracy, damage))

        connection.execute("DELETE FROM inv_weapon_burst_capability")
        for weapon_id, rate_text in connection.execute(
            """SELECT item_rule_id,rate_of_fire_text
               FROM inv_weapon_definition
               WHERE rate_of_fire_text IS NOT NULL"""
        ):
            supported = {int(value) for value in rate_text.split("/")}
            for rounds in supported.intersection(burst_ids):
                connection.execute(
                    """INSERT INTO inv_weapon_burst_capability
                       VALUES (%s,%s)""",
                    (weapon_id, burst_ids[rounds]))

        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published burst-fire rules and weapon eligibility")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
