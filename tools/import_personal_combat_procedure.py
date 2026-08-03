"""Import paired-source personal combat procedure and action economy."""

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
    session.headers["User-Agent"] = "BaseCepheus combat procedure importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    required = [
        "each combat round lasts around six seconds",
        "automatic 12 on their initiative roll",
        "minor action and a significant action",
        "three minor actions",
        "each reaction lowers initiative by 2",
        "applies a -1 dm to all skill checks",
        "can only react once to each attack",
        "can only react to attacks that he is aware of",
        "the attacker declares his target",
        "the foe may choose to react",
        "at the start of each combat round",
        "+2 bonus to his initiative",
        "all his actions receive a -1 dm",
        "he may act at any later point during the round",
        "even interrupting another's actions",
        "his initiative is set to the count on which he acted",
        "spends a minor action aiming at a target",
        "gets a +1 dm to his next attack",
        "maximum aiming dm of +6",
        "change to any one of the three stances",
        "crouching or prone targets can claim cover one step higher",
        "a prone character cannot make melee attacks or dodge",
        "character moves up to six meters",
        "difficult terrain",
        "crouching also halves movement",
        "-1 for every 10 full meters of target movement",
        "bonus of +2 to his damage",
        "maximum bonus obtainable from aiming for the kill is +6",
    ]
    for phrase in required:
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired combat sources disagree or omit: {phrase}")

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

        def source_rule(code, name, description, payload, heading, anchor):
            rule = publish_rule(
                connection, package, code, name, "combat", description)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    heading, anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "combat", code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule

        procedure = source_rule(
            "combat.personal-procedure", "Personal Combat Procedure",
            "Awareness, initiative, six-second rounds, and ordering.",
            {"round_seconds": 6, "initiative": "2D6 + Dexterity DM",
             "aware_unopposed_base": 12, "descending": True,
             "tie_breaker": "characteristic.dexterity",
             "exact_tie_simultaneous": True,
             "rerolled_each_round": False},
            "Personal Combat > Initiative and Combat Round",
            "personal-combat-procedure")
        dexterity = get_id(
            connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
            ("characteristic.dexterity",))
        connection.execute("""INSERT INTO rule_personal_combat_procedure
            VALUES (%s,6,2,6,12,true,%s,true,false)
            ON CONFLICT (rule_id) DO UPDATE SET
            round_seconds=6,initiative_dice_count=2,initiative_die_sides=6,
            aware_unopposed_base=12,initiative_descending=true,
            tie_break_characteristic_rule_id=EXCLUDED.tie_break_characteristic_rule_id,
            exact_tie_simultaneous=true,initiative_rerolled_each_round=false""",
            (procedure, dexterity))

        economy = source_rule(
            "combat.personal-action-economy", "Personal Action Economy",
            "One significant and one minor action, or three minor actions.",
            {"significant": 1, "minor_with_significant": 1,
             "minor_without_significant": 3,
             "minor_from_significant": 2,
             "free_unbounded": True, "reactions_unbounded": True},
            "Personal Combat > Combat Round and Actions",
            "personal-action-economy")
        connection.execute("""INSERT INTO rule_personal_action_economy
            VALUES (%s,1,1,3,2,true,true)
            ON CONFLICT (rule_id) DO UPDATE SET
            significant_actions=1,minor_actions_with_significant=1,
            minor_actions_without_significant=3,
            minor_actions_from_significant=2,
            free_actions_unbounded_by_default=true,
            reactions_unbounded_by_default=true""", (economy,))

        reactions = source_rule(
            "combat.personal-reactions", "Personal Combat Reactions",
            "Cumulative dodge and parry reactions.",
            {"initiative_cost": -2, "check_modifier": -1,
             "maximum_per_round": None, "maximum_per_attack": 1,
             "requires_awareness": True, "dodge_attack_modifier": -1,
             "dodge_with_cover_attack_modifier": -2,
             "parry_uses_negative_melee_skill": True},
            "Personal Combat > Reactions", "personal-reactions")
        connection.execute("""INSERT INTO rule_personal_reaction_system
            (rule_id,initiative_cost_per_reaction,check_modifier_per_reaction,
             cumulative,maximum_per_round,maximum_per_attack,
             requires_awareness,dodge_attack_modifier,
             dodge_with_cover_attack_modifier,
             parry_uses_negative_melee_skill)
            VALUES (%s,-2,-1,true,NULL,1,true,-1,-2,true)
            ON CONFLICT (rule_id) DO UPDATE SET
            initiative_cost_per_reaction=-2,check_modifier_per_reaction=-1,
            cumulative=true,maximum_per_round=NULL,maximum_per_attack=1,
            requires_awareness=true,dodge_attack_modifier=-1,
            dodge_with_cover_attack_modifier=-2,
            parry_uses_negative_melee_skill=true""", (reactions,))
        attack_sequence = source_rule(
            "combat.personal-attack-sequence", "Personal Attack Sequence",
            "Declare target, allow reaction, make the attack check, then deal damage.",
            {"consumes_significant_action": True,
             "target_declared_before_reaction": True,
             "reaction_before_attack_check": True,
             "damage_after_successful_check": True},
            "Personal Combat > Significant Actions > Attack",
            "personal-attack-sequence")
        connection.execute(
            """INSERT INTO rule_personal_attack_sequence
               VALUES (%s,true,true,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 consumes_significant_action=true,
                 target_declared_before_reaction=true,
                 reaction_before_attack_check=true,
                 damage_after_successful_check=true""", (attack_sequence,))
        hasten = source_rule(
            "combat.personal-hasten", "Hasten Personal Action",
            "At round start, hasten once for Initiative +2 and DM-1 to actions.",
            {"initiative_modifier": 2, "check_modifier": -1,
             "maximum_per_round": 1, "current_round_only": True,
             "declared_at_round_start": True},
            "Personal Combat > Dynamic Initiative",
            "personal-hasten")
        connection.execute(
            """INSERT INTO rule_personal_hasten
               VALUES (%s,2,-1,1,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 initiative_modifier=2,check_modifier=-1,
                 maximum_per_round=1,lasts_current_round_only=true,
                 declared_at_round_start=true""", (hasten,))
        delay = source_rule(
            "combat.personal-delay", "Delay Personal Action",
            "Yield a turn, act later or interrupt, and adopt that Initiative count.",
            {"may_act_later_in_round": True, "may_interrupt_action": True,
             "initiative_becomes_action_count": True,
             "may_forfeit_for_first_next_round": True,
             "next_round_above_current_first": 1},
            "Personal Combat > Other Actions > Delay",
            "personal-delay")
        connection.execute(
            """INSERT INTO rule_personal_delay
               VALUES (%s,true,true,true,true,1)
               ON CONFLICT (rule_id) DO UPDATE SET
                 may_act_later_in_round=true,may_interrupt_action=true,
                 initiative_becomes_action_count=true,
                 may_forfeit_for_first_next_round=true,
                 next_round_initiative_above_current_first=1""", (delay,))
        aim = source_rule(
            "combat.personal-aim", "Aim Personal Attack",
            "Spend minor actions for DM+1 each on the next attack, maximum DM+6.",
            {"minor_actions_per_step": 1, "modifier_per_step": 1,
             "maximum_modifier": 6, "requires_same_target": True,
             "lost_on_other_action": True},
            "Personal Combat > Minor Actions > Aiming",
            "personal-aim")
        connection.execute(
            """INSERT INTO rule_personal_aim
               VALUES (%s,1,1,6,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 minor_actions_per_step=1,modifier_per_step=1,
                 maximum_modifier=6,requires_same_target=true,
                 lost_on_other_action=true""", (aim,))
        stances = (
            ("standing", "Standing", 1, 0, True, True, 0, 0),
            ("crouched", "Crouched", 2, 1, True, True, 0, 0),
            ("prone", "Prone", 3, 1, False, False, 2, -2),
        )
        for code, name, order, cover_step, dodge, melee, personal, distant in stances:
            rule = source_rule(
                f"combat.stance.{code}", f"{name} Stance",
                f"Source-defined {name.lower()} personal-combat stance.",
                {"cover_step_bonus": cover_step, "may_dodge": dodge,
                 "may_make_melee_attack": melee,
                 "ranged_dm_personal": personal,
                 "ranged_dm_medium_or_greater": distant},
                "Personal Combat > Special Considerations > Stance",
                f"personal-stance-{code}")
            connection.execute(
                """INSERT INTO rule_personal_stance
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     stance_code=EXCLUDED.stance_code,
                     display_order=EXCLUDED.display_order,
                     cover_step_bonus=EXCLUDED.cover_step_bonus,
                     may_dodge=EXCLUDED.may_dodge,
                     may_make_melee_attack=EXCLUDED.may_make_melee_attack,
                     ranged_dm_personal=EXCLUDED.ranged_dm_personal,
                     ranged_dm_medium_or_greater=
                        EXCLUDED.ranged_dm_medium_or_greater""",
                (rule, code, order, cover_step, dodge, melee, personal, distant))
        covers = (
            ("one_quarter", "One-Quarter Cover", 1, 0),
            ("one_half", "One-Half Cover", 2, -1),
            ("three_quarters", "Three-Quarters Cover", 3, -2),
            ("full", "Full Cover", 4, -4),
        )
        for code, name, order, modifier in covers:
            rule = source_rule(
                f"combat.cover.{code}", name,
                f"Source-defined {name.lower()} attack modifier.",
                {"display_order": order, "attack_modifier": modifier},
                "Personal Combat > Special Considerations > Cover",
                f"personal-cover-{code}")
            connection.execute(
                """INSERT INTO rule_personal_cover VALUES (%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     cover_code=EXCLUDED.cover_code,
                     display_order=EXCLUDED.display_order,
                     attack_modifier=EXCLUDED.attack_modifier""",
                (rule, code, order, modifier))
        movement = source_rule(
            "combat.personal-movement", "Personal Combat Movement",
            "A minor action moves six metres; difficult terrain and crouching halve it.",
            {"minor_actions": 1, "normal_metres": 6,
             "difficult_terrain_divisor": 2, "crouched_divisor": 2,
             "target_modifier_metres": 10,
             "target_modifier_per_increment": -1},
            "Personal Combat > Minor Actions > Movement",
            "personal-movement")
        connection.execute(
            """INSERT INTO rule_personal_movement
               VALUES (%s,1,6,2,2,10,-1)
               ON CONFLICT (rule_id) DO UPDATE SET
                 minor_actions_per_move=1,normal_metres=6,
                 difficult_terrain_divisor=2,crouched_divisor=2,
                 target_modifier_metres=10,
                 target_modifier_per_increment=-1""", (movement,))
        kill_aim = source_rule(
            "combat.personal-kill-aim", "Aim for the Kill",
            "Spend minor actions for +2 damage each, maximum +6.",
            {"minor_actions": 1, "damage_per_step": 2,
             "maximum_damage": 6, "forbids_dodge": True,
             "forbids_movement": True,
             "lost_when_hit_or_distracted": True},
            "Personal Combat > Minor Actions > Aiming for the Kill",
            "personal-kill-aim")
        connection.execute(
            """INSERT INTO rule_personal_kill_aim
               VALUES (%s,1,2,6,true,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 minor_actions_per_step=1,damage_per_step=2,
                 maximum_damage=6,forbids_dodge=true,
                 forbids_movement=true,
                 lost_when_hit_or_distracted=true""", (kill_aim,))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published personal combat procedure, action economy, and reactions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
