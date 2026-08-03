"""Import paired-source animal encounter and reaction rules."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book3/planetary-wilderness-encounters.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-planetary-wilderness-encounters/")
SUBTYPES = [
    ("chaser", "Chaser", "carnivore",
     ("attack", "outnumbers_characters", None, None, False),
     ("flee", "roll_at_most", 5, None, False)),
    ("killer", "Killer", "carnivore",
     ("attack", "roll_at_least", 6, None, False),
     ("flee", "roll_at_most", 3, None, False)),
    ("pouncer", "Pouncer", "carnivore",
     ("attack", "has_surprise", None, None, False),
     ("flee", "is_surprised", None, None, False)),
    ("siren", "Siren", "carnivore",
     ("attack", "has_surprise", None, None, False),
     ("flee", "roll_at_most", 4, None, False)),
    ("trapper", "Trapper", "carnivore",
     ("attack", "has_surprise", None, None, False),
     ("flee", "roll_at_most", 5, None, False)),
    ("filter", "Filter", "herbivore",
     ("attack", "roll_at_least", 10, None, True),
     ("flee", "roll_at_most", 5, None, False)),
    ("grazer", "Grazer", "herbivore",
     ("attack", "roll_at_least", 8, None, False),
     ("flee", "roll_at_most", 6, None, False)),
    ("intermittent", "Intermittent", "herbivore",
     ("attack", "roll_at_least", 10, None, False),
     ("flee", "roll_at_most", 4, None, False)),
    ("eater", "Eater", "omnivore",
     ("attack", "roll_at_least", 5, None, False),
     ("flee", "roll_at_most", 4, None, False)),
    ("gatherer", "Gatherer", "omnivore",
     ("attack", "roll_at_least", 9, None, False),
     ("flee", "roll_at_most", 7, None, False)),
    ("hunter", "Hunter", "omnivore",
     ("attack", "size_dependent_roll", 6, 10, False),
     ("flee", "roll_at_most", 5, None, False)),
    ("carrion-eater", "Carrion-eater", "scavenger",
     ("attack", "roll_at_least", 11, None, False),
     ("flee", "roll_at_most", 7, None, False)),
    ("hijacker", "Hijacker", "scavenger",
     ("attack", "roll_at_least", 7, None, False),
     ("flee", "roll_at_most", 6, None, False)),
    ("intimidator", "Intimidator", "scavenger",
     ("attack", "roll_at_least", 8, None, False),
     ("flee", "roll_at_most", 7, None, False)),
    ("reducer", "Reducer", "scavenger",
     ("attack", "roll_at_least", 10, None, False),
     ("flee", "roll_at_most", 7, None, False)),
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
    session.headers["User-Agent"] = "BaseCepheus animal importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "one third chance 5+ on 1d6",
        "animal reactions by subtype",
        "if the chasers outnumber the characters they attack",
        "if the hunter is bigger than at least one character",
        "neither attack nor flee then the animal stands still",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired animal sources disagree or omit: {phrase}")

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
            ("github", github, "src/book3/planetary-wilderness-encounters.md",
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

        animal_type = source_rule(
            "encounter.type.animal", "Animal Encounter", "Animal encounter.",
            {"encounter_type": "animal", "display_order": 7},
            "Planetary Wilderness Encounters", "encounter-type-animal")
        connection.execute("""INSERT INTO rule_encounter_type
            (rule_id,encounter_type_code,display_order) VALUES (%s,'animal',7)
            ON CONFLICT (rule_id) DO UPDATE SET
            encounter_type_code='animal',display_order=7""", (animal_type,))
        system = source_rule(
            "encounter.animal-system", "Animal Encounter System",
            "Check while travelling and halted; 5+ on 1D6; react on 2D6.",
            {"occurrence": "5+ on 1D6", "reaction": "2D6",
             "stand_when_no_outcome": True,
             "reroll_when_provoked_again": True},
            "Planetary Wilderness Encounters > Using the Encounter Tables",
            "animal-encounter-system")
        connection.execute("""INSERT INTO rule_animal_encounter_system
            VALUES (%s,1,6,5,1,1,2,6,true,true)
            ON CONFLICT (rule_id) DO UPDATE SET
            occurrence_dice_count=1,occurrence_die_sides=6,
            occurrence_target=5,checks_while_travelling=1,
            checks_while_halted=1,reaction_dice_count=2,
            reaction_die_sides=6,stand_when_no_outcome=true,
            reroll_when_provoked_again=true""", (system,))

        connection.execute("DELETE FROM src_animal_reaction_condition_provenance")
        connection.execute("DELETE FROM rule_animal_reaction_condition")
        for order, (code, name, animal_group, *conditions) in enumerate(SUBTYPES, 1):
            rule = source_rule(
                f"encounter.animal-subtype.{code}", name,
                f"{animal_group.title()} subtype reaction procedure.",
                {"subtype": code, "animal_type": animal_group},
                "Planetary Wilderness Encounters > Animal Reactions",
                f"animal-subtype-{code}")
            connection.execute("""INSERT INTO rule_animal_subtype
                (rule_id,subtype_code,animal_type,display_order)
                VALUES (%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                subtype_code=EXCLUDED.subtype_code,
                animal_type=EXCLUDED.animal_type,
                display_order=EXCLUDED.display_order""",
                (rule, code, animal_group, order))
            for condition_order, condition in enumerate(conditions, 1):
                outcome, kind, threshold, alternate, possible = condition
                condition_id = connection.execute(
                    """INSERT INTO rule_animal_reaction_condition
                       (subtype_rule_id,outcome,condition_kind,threshold,
                        alternate_threshold,requires_outnumbers,
                        requires_has_surprise,requires_is_surprised,
                        requires_bigger_than_character,
                        requires_outcome_possible,source_order)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       RETURNING animal_reaction_condition_id""",
                    (rule, outcome, kind, threshold, alternate,
                     kind == "outnumbers_characters", kind == "has_surprise",
                     kind == "is_surprised",
                     True if kind == "size_dependent_roll" else None,
                     possible, condition_order),
                ).fetchone()[0]
                for side in ("github", "ogn"):
                    artifact, batch = artifacts[side]
                    anchor = f"{code}-{outcome}"
                    locator = upsert_locator(
                        connection, works[side], artifact, "table_row",
                        "Planetary Wilderness Encounters > Animal Reactions",
                        anchor, anchor, condition_order)
                    payload = {"subtype": code, "outcome": outcome,
                               "kind": kind, "threshold": threshold,
                               "alternate_threshold": alternate,
                               "requires_outcome_possible": possible}
                    candidate, review = stage_candidate(
                        connection, batch, artifact, locator,
                        "animal_reaction_condition", anchor, payload)
                    connection.execute("""INSERT INTO
                        src_animal_reaction_condition_provenance
                        VALUES (%s,%s,%s,%s,%s,%s)""",
                        (condition_id, locator, candidate, review,
                         "direct" if side == "github" else "corroborating",
                         side == "github"))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published animal encounter system, 15 subtypes, and 30 reactions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
