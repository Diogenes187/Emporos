"""Import the first paired-source personal-combat equipment slice."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

EQUIPMENT = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
COMBAT = ROOT / "sources/cepheus-srd/src/book1/personal-combat.md"
EQUIPMENT_URL = ("https://cepheus-srd.opengamingnetwork.com/"
                 "cepheus-engine-srd/cepheus-engine-equipment/")
COMBAT_URL = ("https://cepheus-srd.opengamingnetwork.com/"
              "cepheus-engine-srd/cepheus-engine-personal-combat/")
RANGES = [
    ("personal", "Personal", None, 1.5, "Less than 1.5 meters", "0"),
    ("close", "Close", 1.5, 3, "1.5 to 3 meters", "1 to 2 squares"),
    ("short", "Short", 3, 12, "3 to 12 meters", "3 to 8 squares"),
    ("medium", "Medium", 12, 50, "12 to 50 meters", "9 to 34 squares"),
    ("long", "Long", 51, 250, "51 meters to 250 meters", "35 to 166 squares"),
    ("very-long", "Very Long", 251, 500, "251 meters to 500 meters",
     "167 to 334 squares"),
    ("distant", "Distant", 501, None, "501 meters+", "334 squares+"),
]
PROFILE_ROWS = {
    "close-quarters": ["average", "difficult", None, None, None, None, None],
    "thrown": [None, "average", "difficult", "difficult", None, None, None],
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus combat-slice importer/1.0"
    raw = {
        "github_equipment": EQUIPMENT.read_bytes(),
        "github_combat": COMBAT.read_bytes(),
    }
    raw["ogn_equipment"], equipment_soup = fetch(session, EQUIPMENT_URL)
    raw["ogn_combat"], combat_soup = fetch(session, COMBAT_URL)
    pairs = {
        "equipment": (normalize(raw["github_equipment"].decode()),
                      normalize(equipment_soup.get_text(" "))),
        "combat": (normalize(raw["github_combat"].decode()),
                   normalize(combat_soup.get_text(" "))),
    }
    required = {
        "equipment": ["dagger 0 cr10 250g", "jack 1 3 cr50 1kg"],
        "combat": ["personal less than 1 5 meters",
                   "close quarters average difficult",
                   "thrown average difficult difficult"],
    }
    for domain, phrases in required.items():
        for phrase in phrases:
            if any(normalize(phrase) not in text for text in pairs[domain]):
                raise ValueError(f"Paired {domain} sources omit: {phrase}")

    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        work_ids = {
            "github": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.github-v9.1'", ()),
            "ogn": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.ogn'", ()),
        }
        specs = {
            "github_equipment": ("github", "src/book1/equipment.md",
                                 "repository_file", GITHUB_COMMIT, "text/markdown"),
            "github_combat": ("github", "src/book1/personal-combat.md",
                              "repository_file", GITHUB_COMMIT, "text/markdown"),
            "ogn_equipment": ("ogn", EQUIPMENT_URL, "web_page", None, "text/html"),
            "ogn_combat": ("ogn", COMBAT_URL, "web_page", None, "text/html"),
        }
        artifacts = {}
        for key, (side, uri, kind, revision, media) in specs.items():
            artifact = upsert_artifact(
                connection, work_ids[side], kind, uri, revision, raw[key], media)
            artifacts[key] = (work_ids[side], artifact, import_batch(
                connection, package, artifact, sha256(raw[key])))

        def source_rule(code, name, category, description, payload,
                        domain, heading, anchor):
            rule = publish_rule(
                connection, package, code, name, category, description)
            for side in ("github", "ogn"):
                work, artifact, batch = artifacts[f"{side}_{domain}"]
                locator = upsert_locator(
                    connection, work, artifact, "table_row", heading,
                    anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, category, code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        range_ids = {}
        for order, (code, name, low, high, printed, squares) in enumerate(RANGES, 1):
            rule = source_rule(
                f"combat.range.{code}", name, "combat", printed,
                {"minimum_metres": low, "maximum_metres": high,
                 "printed_distance": printed, "printed_squares": squares},
                "combat", "Personal Combat > Range", f"range-{code}")
            range_ids[code] = rule
            connection.execute("""INSERT INTO combat_range_band
                (rule_id,printed_minimum_metres,printed_maximum_metres,
                 printed_distance,printed_squares,display_order)
                VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                printed_minimum_metres=EXCLUDED.printed_minimum_metres,
                printed_maximum_metres=EXCLUDED.printed_maximum_metres,
                printed_distance=EXCLUDED.printed_distance,
                printed_squares=EXCLUDED.printed_squares,
                display_order=EXCLUDED.display_order""",
                (rule, low, high, printed, squares, order))

        profile_specs = [
            ("close-quarters", "Close Quarters", "skill.piercing-weapons"),
            ("thrown", "Thrown", "skill.athletics"),
        ]
        for code, name, skill_code in profile_specs:
            rule = source_rule(
                f"combat.attack-profile.{code}", name, "combat", name,
                {"required_skill": skill_code}, "combat",
                "Personal Combat > Range > Attack Difficulties",
                f"attack-profile-{code}")
            skill = get_id(connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (skill_code,))
            connection.execute("""INSERT INTO combat_attack_profile
                (attack_profile_code,name,required_skill_rule_id,rule_id)
                VALUES (%s,%s,%s,%s) ON CONFLICT (attack_profile_code) DO UPDATE
                SET name=EXCLUDED.name,
                required_skill_rule_id=EXCLUDED.required_skill_rule_id,
                rule_id=EXCLUDED.rule_id""", (code, name, skill, rule))

        connection.execute("DELETE FROM src_attack_profile_difficulty_provenance")
        connection.execute("DELETE FROM combat_attack_profile_difficulty")
        for profile, difficulties in PROFILE_ROWS.items():
            for order, ((range_code, *_), difficulty) in enumerate(
                    zip(RANGES, difficulties), 1):
                difficulty_id = None
                if difficulty:
                    difficulty_id = get_id(connection, """SELECT r.rule_id
                        FROM rule_rule r WHERE r.rule_code=%s""",
                        (f"difficulty.{difficulty}",))
                connection.execute("""INSERT INTO combat_attack_profile_difficulty
                    (attack_profile_code,range_band_rule_id,difficulty_rule_id,
                     permitted) VALUES (%s,%s,%s,%s)""",
                    (profile, range_ids[range_code], difficulty_id,
                     difficulty is not None))
                for side in ("github", "ogn"):
                    work, artifact, batch = artifacts[f"{side}_combat"]
                    anchor = f"{profile}-{range_code}"
                    locator = upsert_locator(connection, work, artifact,
                        "table_row", "Personal Combat > Range > Attack Difficulties",
                        anchor, anchor, order)
                    payload = {"profile": profile, "range": range_code,
                               "difficulty": difficulty}
                    candidate, review = stage_candidate(
                        connection, batch, artifact, locator,
                        "attack_profile_difficulty", anchor, payload)
                    connection.execute("""INSERT INTO
                        src_attack_profile_difficulty_provenance
                        (attack_profile_code,range_band_rule_id,source_locator_id,
                         import_candidate_id,source_review_id,provenance_class,
                         is_primary_citation) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (profile, range_ids[range_code], locator, candidate, review,
                         "direct" if side == "github" else "corroborating",
                         side == "github"))

        dagger = source_rule(
            "equipment.weapon.dagger", "Dagger", "equipment",
            "TL0 Cr10 250g; melee close quarters or ranged thrown; 1D6 piercing; LL5.",
            {"tl": 0, "cost": 10, "mass_grams": 250, "damage": "1D6",
             "damage_type": "piercing", "law_level": 5},
            "equipment", "Equipment > Common Personal Melee Weapons", "dagger")
        jack = source_rule(
            "equipment.armor.jack", "Jack", "equipment",
            "TL1 Cr50 1kg armor with AR3.",
            {"tl": 1, "cost": 50, "mass_grams": 1000, "armor_rating": 3},
            "equipment", "Equipment > Armor", "jack")
        for rule, kind, tl, cost, mass in (
            (dagger, "weapon", 0, 10, 250), (jack, "armor", 1, 50, 1000)):
            connection.execute("""INSERT INTO inv_item_definition
                (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                item_kind=EXCLUDED.item_kind,
                minimum_tech_level=EXCLUDED.minimum_tech_level,
                cost_credits=EXCLUDED.cost_credits,
                mass_grams=EXCLUDED.mass_grams""", (rule, kind, tl, cost, mass))
        connection.execute("""INSERT INTO inv_weapon_definition
            VALUES (%s,1,6,5) ON CONFLICT (item_rule_id) DO UPDATE SET
            damage_dice_count=1,damage_die_sides=6,illegal_at_law_level=5""",
            (dagger,))
        connection.execute("""INSERT INTO inv_weapon_damage_type
            VALUES (%s,'piercing') ON CONFLICT DO NOTHING""", (dagger,))
        connection.execute("""INSERT INTO inv_armor_definition
            (item_rule_id,general_armor_rating) VALUES (%s,3)
            ON CONFLICT (item_rule_id) DO UPDATE SET general_armor_rating=3""",
            (jack,))

        damage_rule = source_rule(
            "combat.personal-damage", "Personal Damage", "combat",
            "Add attack Effect to weapon damage; armor reduces damage; "
            "Effect 6+ inflicts at least one point.",
            {"add_effect": True, "armor_reduces_damage": True,
             "exceptional_effect_threshold": 6,
             "exceptional_minimum_damage": 1,
             "first_characteristic": "characteristic.endurance",
             "overflow_player_choice": True,
             "subsequent_player_choice": True},
            "combat", "Personal Combat > Damage", "personal-damage")
        endurance_id = get_id(
            connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
            ("characteristic.endurance",))
        connection.execute("""INSERT INTO rule_personal_damage_system
            (rule_id,add_attack_effect,armor_reduces_damage,
             exceptional_effect_threshold,exceptional_minimum_damage,
             first_characteristic_rule_id,overflow_player_choice,
             subsequent_player_choice)
            VALUES (%s,true,true,6,1,%s,true,true)
            ON CONFLICT (rule_id) DO UPDATE SET
            add_attack_effect=true,armor_reduces_damage=true,
            exceptional_effect_threshold=6,exceptional_minimum_damage=1,
            first_characteristic_rule_id=EXCLUDED.first_characteristic_rule_id,
            overflow_player_choice=true,subsequent_player_choice=true""",
            (damage_rule, endurance_id))
        outcomes = [
            ("wounded", "Wounded", "physical_characteristics_damaged", 1,
             "at_least"),
            ("seriously-wounded", "Seriously Wounded",
             "physical_characteristics_damaged", 3, "exactly_all"),
            ("unconscious", "Unconscious",
             "physical_characteristics_at_zero", 2, "at_least"),
            ("dead", "Dead", "physical_characteristics_at_zero", 3,
             "exactly_all"),
        ]
        for code, name, metric, threshold, comparison in outcomes:
            rule = source_rule(
                f"health.outcome.{code}", name, "combat", name,
                {"trigger_metric": metric, "threshold": threshold,
                 "comparison": comparison},
                "combat", "Personal Combat > Damage > Characteristic Damage",
                f"health-outcome-{code}")
            connection.execute("""INSERT INTO rule_health_outcome
                (rule_id,outcome_code,trigger_metric,threshold_count,comparison)
                VALUES (%s,%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                outcome_code=EXCLUDED.outcome_code,
                trigger_metric=EXCLUDED.trigger_metric,
                threshold_count=EXCLUDED.threshold_count,
                comparison=EXCLUDED.comparison""",
                (rule, code.replace("-", "_"), metric, threshold, comparison))

        connection.execute("DELETE FROM src_weapon_attack_mode_provenance")
        connection.execute("DELETE FROM inv_weapon_attack_mode")
        for order, profile in enumerate(("close-quarters", "thrown"), 1):
            connection.execute("INSERT INTO inv_weapon_attack_mode VALUES (%s,%s,%s)",
                               (dagger, profile, order))
            for side in ("github", "ogn"):
                work, artifact, batch = artifacts[f"{side}_equipment"]
                anchor = f"dagger-{profile}"
                locator = upsert_locator(connection, work, artifact, "table_row",
                    "Equipment > Common Personal Melee Weapons", anchor, anchor, order)
                candidate, review = stage_candidate(connection, batch, artifact,
                    locator, "weapon_attack_mode", anchor,
                    {"item": "dagger", "profile": profile})
                connection.execute("""INSERT INTO src_weapon_attack_mode_provenance
                    (item_rule_id,attack_profile_code,source_locator_id,
                     import_candidate_id,source_review_id,provenance_class,
                     is_primary_citation) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (dagger, profile, locator, candidate, review,
                     "direct" if side == "github" else "corroborating",
                     side == "github"))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[2] for value in artifacts.values()],))
    print(
        "published 7 ranges, 2 attack profiles, Dagger, Jack, "
        "personal damage, and 4 health outcomes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
