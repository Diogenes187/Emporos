"""Import paired-source starship meeting rules and category table."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book3/starship-encounters.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-starship-encounters/")
CATEGORIES = [
    (2, "alien_vessel", "Alien Vessel"),
    (3, "derelict", "Derelict"),
    (4, "space_habitat", "Space Habitat"),
    (5, "astrogation", "Astrogation"),
    (6, "space_junk", "Space Junk"),
    (7, "merchant_vessel", "Merchant Vessel"),
    (8, "personal_vessel", "Personal Vessel"),
    (9, "hostile_vessel", "Hostile Vessel"),
    (10, "military_vessel", "Military Vessel"),
    (11, "spacecraft", "Spacecraft"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus starship importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "roll 1d6 on a 6 a space encounter occurs",
        "begin at very long range",
        "near a planet at medium range",
        "one range category closer",
        "dm+4 on detection efforts",
        "12 referee's choice",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired starship sources disagree or omit: {phrase}")

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
            ("github", github, "src/book3/starship-encounters.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))

        def source_rule(code, name, description, payload, heading, anchor):
            rule = publish_rule(
                connection, package, code, name, "encounter", description)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row",
                    heading, anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "encounter", code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        encounter_type = source_rule(
            "encounter.type.starship", "Starship Encounter",
            "A meeting or event in interplanetary space.",
            {"encounter_type": "starship", "display_order": 8},
            "Starship Encounters", "encounter-type-starship")
        connection.execute("""INSERT INTO rule_encounter_type
            (rule_id,encounter_type_code,display_order)
            VALUES (%s,'starship',8) ON CONFLICT (rule_id) DO UPDATE SET
            encounter_type_code='starship',display_order=8""", (encounter_type,))
        system = source_rule(
            "encounter.starship-system", "Starship Encounter System",
            "Occurrence, type, initial meeting range, and detection adjustment.",
            {"occurrence": "6 on 1D6", "type": "2D6", "subtype": "1D6",
             "deep_space_range": "very_long",
             "near_planet_range": "medium",
             "failed_comms_one_closer": True,
             "active_transponder_dm": 4},
            "Starship Encounters", "starship-encounter-system")
        connection.execute("""INSERT INTO rule_starship_encounter_system
            VALUES (%s,1,6,6,true,true,2,6,1,6,'very_long','medium',
                    true,4,true,true,true)
            ON CONFLICT (rule_id) DO UPDATE SET
            occurrence_dice_count=1,occurrence_die_sides=6,
            occurrence_target=6,check_on_region_entry=true,
            check_on_region_exit=true,type_dice_count=2,type_die_sides=6,
            subtype_dice_count=1,subtype_die_sides=6,
            deep_space_initial_range='very_long',
            near_planet_initial_range='medium',
            failed_comms_moves_one_category_closer=true,
            active_transponder_detection_modifier=4,
            referee_may_choose_type=true,
            referee_may_override_nonsensical_result=true,
            special_encounter_range_override=true""", (system,))

        category_ids = {}
        for roll, code, name in CATEGORIES:
            rule = source_rule(
                f"encounter.starship-category.{code.replace('_', '-')}",
                name, name, {"category": code, "roll": roll},
                "Starship Encounters > Starship Encounter Table",
                f"starship-category-{code}")
            category_ids[roll] = rule
            connection.execute("""INSERT INTO rule_starship_encounter_category
                (rule_id,category_code) VALUES (%s,%s)
                ON CONFLICT (rule_id) DO UPDATE SET
                category_code=EXCLUDED.category_code""", (rule, code))
        connection.execute("DELETE FROM src_starship_encounter_roll_provenance")
        connection.execute("DELETE FROM rule_starship_encounter_roll")
        for roll in range(2, 13):
            category = category_ids.get(roll)
            connection.execute("""INSERT INTO rule_starship_encounter_roll
                (roll_total,category_rule_id,referee_choice)
                VALUES (%s,%s,%s)""", (roll, category, roll == 12))
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row",
                    "Starship Encounters > Starship Encounter Table",
                    f"starship-roll-{roll}", f"Starship encounter roll {roll}", roll)
                payload = {"roll": roll, "category_rule_id": category,
                           "referee_choice": roll == 12}
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "starship_encounter_roll", str(roll), payload)
                connection.execute("""INSERT INTO
                    src_starship_encounter_roll_provenance
                    VALUES (%s,%s,%s,%s,%s,%s)""",
                    (roll, locator, candidate, review,
                     "direct" if side == "github" else "corroborating",
                     side == "github"))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published starship encounter system and 2D6 category table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
