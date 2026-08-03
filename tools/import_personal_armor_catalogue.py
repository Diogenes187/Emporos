"""Import paired-source personal armor catalogue and CE-EQUIP-001."""
import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-equipment/")

ARMOR = (
    ("ablat", "Ablat", 9, 3, 8, 75, 2000, None),
    ("battle-dress", "Battle Dress", 13, 18, None, 200000, 60000,
     "skill.battle-dress"),
    ("cloth", "Cloth", 6, 9, None, 250, 2000, None),
    ("combat-armor", "Combat Armor", 11, 11, None, 20000, 18000,
     "skill.zero-g"),
    ("hostile-environment-vacc-suit", "Hostile Env Vacc Suit", 12, 8, None,
     18000, 40000, "skill.zero-g"),
    ("jack", "Jack", 1, 3, None, 50, 1000, None),
    ("mesh", "Mesh", 7, 5, None, 150, 2000, None),
    ("reflec", "Reflec", 10, 0, 14, 1500, 1000, None),
    ("vacc-suit", "Vacc Suit", 9, 6, None, 9000, 8000, "skill.zero-g"),
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
    session.headers["User-Agent"] = "BaseCepheus armor importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "resolve damage from the outside in",
        "only one type of armor can be worn at a time",
        "ablat", "battle dress", "hostile env vacc suit", "reflec",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired armor sources omit: {phrase}")
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
            ("github", github, "src/book1/equipment.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        catalogue_rule = publish_rule(
            connection, package, "equipment.personal-armor-catalogue",
            "Common Personal Armor", "equipment",
            "Typed personal armor profiles and baseline layering rules.")
        locators = {}
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Equipment > Armor", "personal-armor",
                "Common Personal Armor", 0)
            locators[side] = locator
            candidate, review = stage_candidate(
                connection, batch, artifact, locator,
                "personal_armor_catalogue",
                "equipment.personal-armor-catalogue",
                {"entry_count": 9, "ordinary_layer_limit": 1,
                 "layer_resolution": "outside-in"})
            add_provenance(
                connection, catalogue_rule, package, locator,
                candidate, review,
                "direct" if side == "github" else "corroborating",
                side == "github")
        connection.execute(
            """INSERT INTO rule_personal_armor_catalogue
               VALUES (%s,1,true,'outside-in',1,6)
               ON CONFLICT (rule_id) DO NOTHING""", (catalogue_rule,))
        armor_locators = {}
        for order, (
            code, name, tech, general, laser, cost, mass, skill_code
        ) in enumerate(ARMOR, 1):
            rule_id = publish_rule(
                connection, package, f"equipment.armor.{code}",
                name, "equipment", f"{name} personal armor.")
            connection.execute(
                """INSERT INTO inv_item_definition
                   (rule_id,item_kind,minimum_tech_level,
                    cost_credits,mass_grams)
                   VALUES (%s,'armor',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     item_kind=EXCLUDED.item_kind,
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule_id, tech, cost, mass))
            skill_id = None if skill_code is None else get_id(
                connection, "SELECT rule_id FROM rule_rule "
                "WHERE rule_code=%s", (skill_code,))
            connection.execute(
                """INSERT INTO inv_armor_definition
                   (item_rule_id,general_armor_rating,laser_armor_rating,
                    required_skill_rule_id,catalogue_display_order,
                    laser_rating_explicit)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (item_rule_id) DO UPDATE SET
                     general_armor_rating=EXCLUDED.general_armor_rating,
                     laser_armor_rating=EXCLUDED.laser_armor_rating,
                     required_skill_rule_id=EXCLUDED.required_skill_rule_id,
                     catalogue_display_order=EXCLUDED.catalogue_display_order,
                     laser_rating_explicit=EXCLUDED.laser_rating_explicit""",
                (rule_id, general, laser, skill_id, order, laser is not None))
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row",
                    "Equipment > Armor", f"armor-{code}", name, order)
                armor_locators[(code, side, "table")] = locator
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_armor_catalogue",
                    f"equipment.armor.{code}",
                    {"tl": tech, "general_ar": general, "laser_ar": laser,
                     "cost_credits": cost, "mass_grams": mass,
                     "required_skill": skill_code})
                add_provenance(
                    connection, rule_id, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
                armor_locators[(code, side, "description")] = upsert_locator(
                    connection, works[side], artifact, "heading",
                    f"Equipment > Armor > {name}",
                    f"armor-{code}-description", name, order)
        for code, subject, table_tl, prose_tl in (
            ("cloth-tech-level", "cloth", 6, 7),
            ("hev-suit-tech-level", "hostile-environment-vacc-suit", 12, 8),
            ("vacc-suit-tech-level", "vacc-suit", 9, 8),
        ):
            connection.execute(
                """INSERT INTO src_issue
                   (issue_code,domain_code,issue_type,review_priority,
                    issue_status,subject_code,title,problem_statement,
                    published_value,calculated_value,reviewer_question,
                    requested_evidence,engine_disposition,
                    resolved_at,resolution_summary)
                   VALUES (%s,'equipment.armor','tech_level_conflict','medium',
                     'accepted_as_published',%s,%s,%s,%s,%s,%s,%s,
                     'preserve_published',clock_timestamp(),%s)
                   ON CONFLICT (issue_code) DO NOTHING""",
                (f"equipment.armor.{code}", subject,
                 f"{subject} table and description Tech Levels conflict",
                 "The structured armor table and armor description print "
                 "different minimum Tech Levels.",
                 f"table TL {table_tl}", f"description TL {prose_tl}",
                 "Which printed Tech Level should govern the catalogue?",
                 "Publisher errata or a corrected authorized printing.",
                 "Raymond approved the structured armor table as governing."))
            issue_id = get_id(
                connection, "SELECT source_issue_id FROM src_issue "
                "WHERE issue_code=%s", (f"equipment.armor.{code}",))
            for side, location_kind, role in (
                ("github", "table", "primary"),
                ("ogn", "table", "corroborating"),
                ("github", "description", "conflicting"),
                ("ogn", "description", "conflicting"),
            ):
                connection.execute(
                    """INSERT INTO src_issue_locator
                       VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (issue_id, armor_locators[
                        (subject, side, location_kind)
                    ], role))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-EQUIP-001')
               ON CONFLICT DO NOTHING""",
            (catalogue_rule, "Raymond approved table Tech Levels as governing "
             "for Cloth, HEV Suit, and Vacc Suit; prose conflicts remain "
             "explicit accepted source issues."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 9 personal armors and CE-EQUIP-001")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
