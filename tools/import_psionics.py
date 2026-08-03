"""Import the paired-source Cepheus Engine psionics catalogue."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book1/psionics.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-psionics/")

TALENTS = (
    ("awareness", "Awareness", 1, True),
    ("clairvoyance", "Clairvoyance", 3, False),
    ("telekinesis", "Telekinesis", 2, False),
    ("telepathy", "Telepathy", 4, False),
    ("teleportation", "Teleportation", 0, False),
)

# code, name, talent, difficulty, timing unit, cost, per point, range,
# throwing dice, throwing flat, complete
POWERS = (
    ("suspended-animation", "Suspended Animation", "awareness", "average", "minutes", 3, False, False, None, None, True),
    ("enhanced-strength", "Psionically Enhanced Strength", "awareness", "average", "seconds", 1, True, False, None, None, True),
    ("enhanced-endurance", "Psionically Enhanced Endurance", "awareness", "average", "seconds", 1, True, False, None, None, True),
    ("regeneration", "Regeneration", "awareness", "very-difficult", "rounds", 1, True, False, None, None, True),
    ("sense", "Sense", "clairvoyance", "routine", "rounds", 1, False, True, None, None, True),
    ("clairvoyance", "Clairvoyance", "clairvoyance", "average", "rounds", 2, False, True, None, None, True),
    ("clairaudience", "Clairaudience", "clairvoyance", "average", "rounds", 2, False, True, None, None, True),
    ("clairsentience", "Clairsentience", "clairvoyance", "difficult", "rounds", 3, False, True, None, None, True),
    ("lift-10g", "Telekinetically Lift 10 Grams", "telekinesis", "easy", "seconds", 2, False, True, None, None, True),
    ("lift-100g", "Telekinetically Lift 100 Grams", "telekinesis", "routine", "seconds", 3, False, True, None, None, True),
    ("lift-1kg", "Telekinetically Lift 1 kg", "telekinesis", "average", "seconds", 5, False, True, None, 1, True),
    ("lift-10kg", "Telekinetically Lift 10 kg", "telekinesis", "difficult", "seconds", 7, False, True, 1, None, True),
    ("lift-100kg", "Telekinetically Lift 100 kg", "telekinesis", "very-difficult", "seconds", 9, False, True, 2, None, True),
    ("lift-1000kg", "Telekinetically Lift 1000 kg", "telekinesis", "formidable", "seconds", 10, False, True, 8, None, True),
    ("life-detection", "Life Detection", "telepathy", "easy", "rounds", 1, False, True, None, None, True),
    ("telempathy", "Telempathy", "telepathy", "routine", "rounds", 1, False, True, None, None, True),
    ("read-surface-thoughts", "Read Surface Thoughts", "telepathy", "average", "rounds", 2, False, True, None, None, True),
    ("send-thoughts", "Send Thoughts", "telepathy", "difficult", "rounds", 2, False, True, None, None, True),
    ("probe-deliberate", "Probe (Deliberate)", "telepathy", "very-difficult", "minutes", 4, False, True, None, None, True),
    ("probe-rapid", "Probe (Rapid)", "telepathy", "formidable", "seconds", 8, False, True, None, None, True),
    ("shield", "Shield", "telepathy", None, None, None, False, False, None, None, True),
    # The prose specifies damage but omits check difficulty, timing, and cost.
    ("assault", "Assault", "telepathy", None, None, None, False, False, None, None, False),
    ("teleport-unclothed", "Teleport Self, Unclothed", "teleportation", "average", "seconds", 0, False, True, None, None, True),
    ("teleport-light-load", "Teleport Self, Light Load", "teleportation", "difficult", "seconds", 2, False, True, None, None, True),
    ("teleport-moderate-load", "Teleport Self, Moderate Load", "teleportation", "very-difficult", "seconds", 3, False, True, None, None, True),
    ("teleport-heavy-load", "Teleport Self, Heavy Load", "teleportation", "very-difficult", "seconds", 4, False, True, None, None, True),
)

RANGES = (
    ("personal", "Personal", 0, 1.5, (0, 0, 0, 1)),
    ("close", "Close", 1.5, 3, (0, 2, 1, 1)),
    ("short", "Short", 3, 12, (1, 4, 1, 2)),
    ("medium", "Medium", 12, 50, (1, 5, 2, 2)),
    ("long", "Long", 51, 250, (2, 7, 2, 3)),
    ("very-long", "Very Long", 251, 500, (2, 9, 3, 3)),
    ("distant", "Distant", 501, 5000, (3, None, 3, 4)),
    ("very-distant", "Very Distant", 5000, 500000, (3, None, 4, 4)),
    ("regional", "Regional", 50000, 500000, (4, None, 4, 5)),
    ("continental", "Continental", 500000, 5000000, (4, None, 5, 5)),
)

TARGET_KINDS = {
    "suspended-animation": "self",
    "enhanced-strength": "self",
    "enhanced-endurance": "self",
    "regeneration": "self",
    "sense": "location",
    "clairvoyance": "location",
    "clairaudience": "location",
    "clairsentience": "location",
    "lift-10g": "object_or_creature",
    "lift-100g": "object_or_creature",
    "lift-1kg": "object_or_creature",
    "lift-10kg": "object_or_creature",
    "lift-100kg": "object_or_creature",
    "lift-1000kg": "object_or_creature",
    "life-detection": "area",
    "telempathy": "actor",
    "read-surface-thoughts": "actor",
    "send-thoughts": "actor",
    "probe-deliberate": "actor",
    "probe-rapid": "actor",
    "shield": "passive",
    "assault": "actor",
    "teleport-unclothed": "self",
    "teleport-light-load": "self",
    "teleport-moderate-load": "self",
    "teleport-heavy-load": "self",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus psionics importer/1.0"
    github_raw = SOURCE.read_bytes()
    ogn_raw, soup = fetch(session, URL)
    paired = (
        normalize(github_raw.decode()),
        normalize(soup.get_text(" ")),
    )
    for phrase in (
        "awareness",
        "clairvoyance",
        "telekinesis",
        "telepathy",
        "teleportation",
        "expended psionic strength points are recovered at the rate of one point per hour",
        "using a talent in combat is a significant action",
        "telekinetically lift 1000 kg formidable",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired psionics sources omit: {phrase}")

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
        for side, raw, uri, kind, revision, media in (
            ("github", github_raw, "src/book1/psionics.md", "repository_file",
             GITHUB_COMMIT, "text/markdown"),
            ("ogn", ogn_raw, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, raw, media)
            artifacts[side] = (
                artifact, import_batch(connection, package, artifact, sha256(raw)))

        def source_rule(code, name, payload, heading, anchor, category="psionics"):
            rule = publish_rule(
                connection, package, code, name, category, name)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
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

        system_rule = source_rule(
            "psionics.system", "Psionic Talent System",
            {"failed_cost": 1, "recovery_delay_hours": 3,
             "recovery_per_hour": 1, "combat_action": "significant"},
            "Psionics > Using a Psionic Talent", "using-a-psionic-talent")
        psi_characteristic = get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code="
            "'characteristic.psionic-strength'", ())
        endurance = get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code="
            "'characteristic.endurance'", ())
        connection.execute(
            """INSERT INTO psi_system VALUES (%s,%s,1,3,1,'significant',false,%s)
               ON CONFLICT (rule_id) DO UPDATE SET
                 characteristic_rule_id=EXCLUDED.characteristic_rule_id""",
            (system_rule, psi_characteristic, endurance))

        talent_ids = {}
        for order, (code, name, learning_dm, self_only) in enumerate(TALENTS, 1):
            skill_rule = source_rule(
                f"skill.psionic-{code}", name, {"permits_untrained": False},
                "Psionics > Psionic Talents", code, "skill")
            connection.execute(
                """INSERT INTO rule_skill VALUES (%s,false,false,NULL)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     permits_untrained=false,untrained_modifier=NULL""",
                (skill_rule,))
            talent_rule = source_rule(
                f"psionics.talent.{code}", name,
                {"learning_modifier": learning_dm, "self_only": self_only},
                "Psionics > Psionic Training", code)
            talent_ids[code] = talent_rule
            connection.execute(
                """INSERT INTO psi_talent VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (talent_rule_id) DO UPDATE SET
                     skill_rule_id=EXCLUDED.skill_rule_id,
                     learning_modifier=EXCLUDED.learning_modifier,
                     display_order=EXCLUDED.display_order,
                     self_only=EXCLUDED.self_only""",
                (talent_rule, skill_rule, learning_dm, order, self_only))

        for order, row in enumerate(POWERS, 1):
            (code, name, talent, difficulty, unit, cost, per_point,
             adds_range, damage_dice, damage_flat, complete) = row
            power_rule = source_rule(
                f"psionics.power.{code}", name,
                {"talent": talent, "difficulty": difficulty, "timing": unit,
                 "base_cost": cost, "cost_per_point": per_point,
                 "adds_range_cost": adds_range,
                 "mechanics_complete": complete},
                f"Psionics > {talent.title()}", code)
            difficulty_id = None if difficulty is None else get_id(
                connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (f"difficulty.{difficulty}",))
            connection.execute(
                """INSERT INTO psi_power
                   (power_rule_id,talent_rule_id,power_code,difficulty_rule_id,
                    timing_dice_count,timing_die_sides,timing_unit,base_cost,
                    cost_per_point,adds_range_cost,requires_check,
                    mechanics_complete,throwing_damage_dice,
                    throwing_damage_flat,display_order)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (power_rule_id) DO UPDATE SET
                     difficulty_rule_id=EXCLUDED.difficulty_rule_id,
                     mechanics_complete=EXCLUDED.mechanics_complete""",
                (power_rule, talent_ids[talent], code, difficulty_id,
                 1 if unit else None, 6 if unit else None, unit, cost,
                 per_point, adds_range, code != "shield", complete,
                 damage_dice, damage_flat, order))
            connection.execute(
                """INSERT INTO psi_power_targeting VALUES (%s,%s)
                   ON CONFLICT (power_rule_id) DO UPDATE SET
                     target_kind=EXCLUDED.target_kind""",
                (power_rule, TARGET_KINDS[code]))

        ranged_talents = ("clairvoyance", "telekinesis", "telepathy",
                          "teleportation")
        for order, (code, name, minimum, maximum, costs) in enumerate(RANGES, 1):
            range_rule = source_rule(
                f"psionics.range.{code}", name,
                {"minimum_metres": minimum, "maximum_metres": maximum},
                "Psionics > Range", code)
            connection.execute(
                """INSERT INTO psi_range_band VALUES (%s,%s,%s,%s)
                   ON CONFLICT (range_band_rule_id) DO UPDATE SET
                     minimum_metres=EXCLUDED.minimum_metres,
                     maximum_metres=EXCLUDED.maximum_metres,
                     display_order=EXCLUDED.display_order""",
                (range_rule, minimum, maximum, order))
            for talent, cost in zip(ranged_talents, costs):
                connection.execute(
                    """INSERT INTO psi_talent_range_cost VALUES (%s,%s,%s,%s)
                       ON CONFLICT (talent_rule_id,range_band_rule_id)
                       DO UPDATE SET
                         psionic_strength_cost=EXCLUDED.psionic_strength_cost,
                         permitted=EXCLUDED.permitted""",
                    (talent_ids[talent], range_rule, cost, cost is not None))
                for side in ("github", "ogn"):
                    artifact, batch = artifacts[side]
                    anchor = f"{talent}-{code}"
                    locator = upsert_locator(
                        connection, works[side], artifact, "table_row",
                        "Psionics > Psionic Range Costs", anchor, anchor, 0)
                    candidate, review = stage_candidate(
                        connection, batch, artifact, locator,
                        "psionic_range_cost", anchor,
                        {"talent": talent, "range": code, "cost": cost})
                    connection.execute(
                        """INSERT INTO src_psi_talent_range_cost_provenance
                           VALUES (%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (talent_ids[talent], range_rule, locator, candidate,
                         review, "direct" if side == "github"
                         else "corroborating", side == "github"))
        connection.commit()
    print("published 5 psionic talents, 26 powers, and 10 range bands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
