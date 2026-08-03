"""Import paired-source common ranged weapons and ammunition."""

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

PROFILES = {
    "extended-reach": ("Extended Reach", "skill.piercing-weapons",
                       ["difficult", "average", None, None, None, None, None]),
    "pistol": ("Pistol", "skill.slug-pistol",
               ["difficult", "average", "average", "difficult",
                "very-difficult", None, None]),
    "rifle": ("Rifle", "skill.slug-rifle",
              ["very-difficult", "difficult", "average", "average",
               "average", "difficult", "very-difficult"]),
    "shotgun": ("Shotgun", "skill.shotgun",
                ["difficult", "average", "difficult", "difficult",
                 "very-difficult", None, None]),
    "assault-weapon": ("Assault Weapon", "skill.slug-rifle",
                       ["difficult", "average", "average", "average",
                        "difficult", "very-difficult", "formidable"]),
    "rocket": ("Rocket", "skill.heavy-weapons",
               ["very-difficult", "difficult", "difficult", "average",
                "average", "difficult", "very-difficult"]),
}

WEAPONS = (
    ("bow", "Bow", 1, 60, 1000, "1", "assault-weapon", 2, "piercing", True, 6, "skill.archery"),
    ("crossbow", "Crossbow", 2, 75, 3000, "1", "rifle", 2, "piercing", True, 6, "skill.archery"),
    ("revolver", "Revolver", 4, 150, 900, "1", "pistol", 2, "piercing", True, 6, "skill.slug-pistol"),
    ("auto-pistol", "Auto Pistol", 5, 200, 750, "1", "pistol", 2, "piercing", True, 6, "skill.slug-pistol"),
    ("carbine", "Carbine", 5, 200, 3000, "1", "shotgun", 2, "piercing", True, 6, "skill.slug-rifle"),
    ("rifle", "Rifle", 5, 200, 4000, "1", "rifle", 3, "piercing", True, 6, "skill.slug-rifle"),
    ("shotgun", "Shotgun", 5, 1500, 3750, "1", "shotgun", 4, "piercing", True, 7, "skill.shotgun"),
    ("submachinegun", "Submachinegun", 5, 500, 2500, "0/4", "assault-weapon", 2, "piercing", True, 4, "skill.slug-pistol"),
    ("auto-rifle", "Auto Rifle", 6, 1000, 5000, "1/4", "rifle", 3, "piercing", True, 6, "skill.slug-rifle"),
    ("assault-rifle", "Assault Rifle", 7, 300, 3000, "1/4", "rifle", 3, "piercing", True, 4, "skill.slug-rifle"),
    ("body-pistol", "Body Pistol", 7, 500, 250, "1", "pistol", 2, "piercing", True, 1, "skill.slug-pistol"),
    ("laser-carbine", "Laser Carbine", 8, 2500, 5000, "1", "pistol", 4, "energy", False, 2, "skill.energy-rifle"),
    ("snub-pistol", "Snub Pistol", 8, 150, 250, "1", "pistol", 2, "piercing", False, 6, "skill.slug-pistol"),
    ("accelerator-rifle", "Accelerator Rifle", 9, 900, 2500, "1/3", "rifle", 3, "piercing", False, 6, "skill.slug-rifle"),
    ("laser-rifle", "Laser Rifle", 9, 3500, 6000, "1", "rifle", 5, "energy", False, 2, "skill.energy-rifle"),
    ("advanced-combat-rifle", "Advanced Combat Rifle", 10, 1000, 3500, "1/4", "rifle", 3, "piercing", True, 6, "skill.slug-rifle"),
    ("gauss-rifle", "Gauss Rifle", 12, 1500, 3500, "1/4/10", "rifle", 4, "piercing", False, 6, "skill.slug-rifle"),
    ("laser-pistol", "Laser Pistol", 12, 1000, 1200, "1", "pistol", 4, "energy", False, 2, "skill.energy-pistol"),
)

AMMUNITION = (
    ("bow", "standard", 1, 1, 1, 25, "unspecified", None),
    ("crossbow", "standard", 1, 2, 2, 20, "minor_actions", 6),
    ("revolver", "standard", 6, 4, 5, 100, "full_rounds", 2),
    ("auto-pistol", "standard", 15, 5, 10, 250, "minor_actions", 1),
    ("body-pistol", "standard", 6, 7, 20, 50, "minor_actions", 1),
    ("snub-pistol", "six-round", 6, 8, 10, 30, "unspecified", None),
    ("snub-pistol", "fifteen-round", 15, 8, 10, 30, "unspecified", None),
    ("shotgun", "standard", 10, 5, 10, 750, "full_rounds", 2),
    ("rifle", "standard", 10, 5, 20, 500, "minor_actions", 1),
    ("carbine", "standard", 20, 5, 10, 125, "minor_actions", 1),
    ("auto-rifle", "standard", 20, 6, 20, 500, "unspecified", None),
    ("assault-rifle", "standard", 30, 7, 20, 330, "unspecified", None),
    ("accelerator-rifle", "standard", 15, 9, 25, 500, "unspecified", None),
    ("advanced-combat-rifle", "standard", 20, 10, 15, 500, "unspecified", None),
    ("gauss-rifle", "standard", 40, 12, 30, 400, "unspecified", None),
    ("submachinegun", "standard", 30, 5, 20, 500, "full_rounds", 1),
    ("laser-pistol", "power-pack", 25, 12, 100, 500, "unspecified", None),
    ("laser-carbine", "power-pack", 50, 8, 200, 3000, "recharge_hours", 8),
    ("laser-rifle", "power-pack", 100, 9, 300, 4000, "recharge_hours", 8),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus ranged importer/1.0"
    raw = {
        "github_equipment": EQUIPMENT.read_bytes(),
        "github_combat": COMBAT.read_bytes(),
    }
    raw["ogn_equipment"], equipment_soup = fetch(session, EQUIPMENT_URL)
    raw["ogn_combat"], combat_soup = fetch(session, COMBAT_URL)
    paired = {
        "equipment": (normalize(raw["github_equipment"].decode()),
                      normalize(equipment_soup.get_text(" "))),
        "combat": (normalize(raw["github_combat"].decode()),
                   normalize(combat_soup.get_text(" "))),
    }
    for domain, phrase in (
        ("equipment", "gauss rifle 12 cr1500 3500g 1 4 10"),
        ("equipment", "auto pistol 5 cr10 250g 15"),
        ("combat", "pistol difficult average average difficult very difficult"),
        ("combat", "assault weapon difficult average average average difficult"),
    ):
        if any(normalize(phrase) not in text for text in paired[domain]):
            raise ValueError(f"Paired {domain} sources omit: {phrase}")

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
        specs = {
            "github_equipment": ("github", "src/book1/equipment.md",
                                 "repository_file", GITHUB_COMMIT, "text/markdown"),
            "github_combat": ("github", "src/book1/personal-combat.md",
                              "repository_file", GITHUB_COMMIT, "text/markdown"),
            "ogn_equipment": ("ogn", EQUIPMENT_URL, "web_page", None, "text/html"),
            "ogn_combat": ("ogn", COMBAT_URL, "web_page", None, "text/html"),
        }
        for key, (side, uri, kind, revision, media) in specs.items():
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, raw[key], media)
            artifacts[key] = (artifact, import_batch(
                connection, package, artifact, sha256(raw[key])))

        def source_rule(code, name, category, payload, domain, heading, anchor):
            rule = publish_rule(
                connection, package, code, name, category, name)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[f"{side}_{domain}"]
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row",
                    heading, anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, category, code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        ranges = dict(connection.execute(
            """SELECT replace(r.rule_code,'combat.range.',''),r.rule_id
               FROM combat_range_band b JOIN rule_rule r ON r.rule_id=b.rule_id"""
        ).fetchall())
        for profile, (name, default_skill, difficulties) in PROFILES.items():
            rule = source_rule(
                f"combat.attack-profile.{profile}", name, "combat",
                {"required_skill": default_skill}, "combat",
                "Personal Combat > Range > Attack Difficulties", profile)
            skill = get_id(connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (default_skill,))
            connection.execute(
                """INSERT INTO combat_attack_profile
                   (attack_profile_code,name,required_skill_rule_id,rule_id)
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (attack_profile_code) DO UPDATE SET
                     name=EXCLUDED.name,
                     required_skill_rule_id=EXCLUDED.required_skill_rule_id,
                     rule_id=EXCLUDED.rule_id""", (profile, name, skill, rule))
            for (range_code, range_id), difficulty in zip(
                    sorted(ranges.items(), key=lambda item: connection.execute(
                        "SELECT display_order FROM combat_range_band WHERE rule_id=%s",
                        (item[1],)).fetchone()[0]), difficulties):
                difficulty_id = None
                if difficulty:
                    difficulty_id = get_id(
                        connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                        (f"difficulty.{difficulty}",))
                connection.execute(
                    """INSERT INTO combat_attack_profile_difficulty
                       VALUES (%s,%s,%s,%s)
                       ON CONFLICT (attack_profile_code,range_band_rule_id)
                       DO UPDATE SET difficulty_rule_id=EXCLUDED.difficulty_rule_id,
                                     permitted=EXCLUDED.permitted""",
                    (profile, range_id, difficulty_id, difficulty is not None))
                for side in ("github", "ogn"):
                    artifact, batch = artifacts[f"{side}_combat"]
                    anchor = f"{profile}-{range_code}"
                    locator = upsert_locator(
                        connection, works[side], artifact, "table_row",
                        "Personal Combat > Range > Attack Difficulties",
                        anchor, anchor, 0)
                    candidate, review = stage_candidate(
                        connection, batch, artifact, locator,
                        "attack_profile_difficulty", anchor,
                        {"profile": profile, "range": range_code,
                         "difficulty": difficulty})
                    connection.execute(
                        """INSERT INTO src_attack_profile_difficulty_provenance
                           VALUES (%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (profile, range_id, locator, candidate, review,
                         "direct" if side == "github" else "corroborating",
                         side == "github"))

        weapon_ids = {}
        for (slug, name, tl, cost, mass, rof, profile, dice, damage_type,
             recoil, law, skill_code) in WEAPONS:
            rule = source_rule(
                f"equipment.weapon.{slug}", name, "equipment",
                {"tl": tl, "cost": cost, "mass_grams": mass, "rof": rof,
                 "profile": profile, "damage": f"{dice}D6",
                 "damage_type": damage_type, "recoil": recoil,
                 "law_level": law}, "equipment",
                "Equipment > Common Personal Ranged Weapons", slug)
            weapon_ids[slug] = rule
            connection.execute(
                """INSERT INTO inv_item_definition
                   VALUES (%s,'weapon',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     item_kind='weapon',minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tl, cost, mass))
            connection.execute(
                """INSERT INTO inv_weapon_definition
                   (item_rule_id,damage_dice_count,damage_die_sides,
                    illegal_at_law_level,rate_of_fire_text,has_recoil)
                   VALUES (%s,%s,6,%s,%s,%s)
                   ON CONFLICT (item_rule_id) DO UPDATE SET
                     damage_dice_count=EXCLUDED.damage_dice_count,
                     damage_die_sides=6,
                     illegal_at_law_level=EXCLUDED.illegal_at_law_level,
                     rate_of_fire_text=EXCLUDED.rate_of_fire_text,
                     has_recoil=EXCLUDED.has_recoil""",
                (rule, dice, law, rof, recoil))
            connection.execute(
                """INSERT INTO inv_weapon_damage_type VALUES (%s,%s)
                   ON CONFLICT DO NOTHING""", (rule, damage_type))
            skill = get_id(connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (skill_code,))
            connection.execute(
                """INSERT INTO inv_weapon_attack_mode
                   (item_rule_id,attack_profile_code,display_order,
                    required_skill_rule_id)
                   VALUES (%s,%s,1,%s)
                   ON CONFLICT (item_rule_id,attack_profile_code) DO UPDATE SET
                     required_skill_rule_id=EXCLUDED.required_skill_rule_id""",
                (rule, profile, skill))
            for side in ("github", "ogn"):
                artifact, batch = artifacts[f"{side}_equipment"]
                anchor = f"{slug}-{profile}"
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row",
                    "Equipment > Common Personal Ranged Weapons",
                    anchor, anchor, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "weapon_attack_mode", anchor,
                    {"item": slug, "profile": profile,
                     "required_skill": skill_code})
                connection.execute(
                    """INSERT INTO src_weapon_attack_mode_provenance
                       VALUES (%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    (rule, profile, locator, candidate, review,
                     "direct" if side == "github" else "corroborating",
                     side == "github"))

        for slug, variant, capacity, tl, cost, mass, procedure, units in AMMUNITION:
            name = f"{dict((row[0], row[1]) for row in WEAPONS)[slug]} Ammunition"
            if variant != "standard":
                name += f" ({variant.replace('-', ' ').title()})"
            rule = source_rule(
                f"equipment.ammunition.{slug}.{variant}", name, "equipment",
                {"weapon": slug, "capacity": capacity, "tl": tl, "cost": cost,
                 "mass_grams": mass, "reload_procedure": procedure,
                 "reload_units": units}, "equipment",
                "Equipment > Common Ranged Ammunition", f"{slug}-{variant}")
            connection.execute(
                """INSERT INTO inv_ammunition_definition
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (ammunition_rule_id) DO UPDATE SET
                     weapon_rule_id=EXCLUDED.weapon_rule_id,
                     ammunition_code=EXCLUDED.ammunition_code,
                     capacity_rounds=EXCLUDED.capacity_rounds,
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams,
                     reload_procedure=EXCLUDED.reload_procedure,
                     reload_units=EXCLUDED.reload_units""",
                (rule, weapon_ids[slug], variant, capacity, tl, cost, mass,
                 procedure, units))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
               completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 18 ranged weapons, 19 ammunition variants, and 6 profiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
