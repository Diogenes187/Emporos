"""Import the paired-source Cepheus Engine core task-resolution vocabulary."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, stage_candidate, upsert_artifact,
    upsert_locator,
)

INTRO = ROOT / "sources" / "cepheus-srd" / "src" / "introduction.md"
URL = "https://cepheus-srd.opengamingnetwork.com/"
DIFFICULTIES = [
    ("simple", "Simple", 6), ("easy", "Easy", 4),
    ("routine", "Routine", 2), ("average", "Average", 0),
    ("difficult", "Difficult", -2),
    ("very-difficult", "Very Difficult", -4),
    ("formidable", "Formidable", -6),
]
EFFECTS = [
    ("exceptional-failure", "Exceptional Failure", None, -6, False),
    ("failure", "Failure", -5, -1, False),
    ("success", "Success", 0, 5, True),
    ("exceptional-success", "Exceptional Success", 6, None, True),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")

    github = INTRO.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus task importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    required = [
        "roll two six sided dice", "equals or exceeds 8",
        *[f"{name} {dm:+d}" if dm else f"{name} 0"
          for _, name, dm in DIFFICULTIES],
        "exceptional failure", "exceptional success",
    ]
    for phrase in required:
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired sources disagree or omit: {phrase}")

    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """
            SELECT content_package_id FROM sys_content_package
            WHERE package_code='cepheus-engine' AND package_version='9.1-draft'
        """, ())
        works = {
            "github": get_id(connection,
                "SELECT source_work_id FROM src_work WHERE work_code=%s",
                ("cepheus-engine.github-v9.1",)),
            "ogn": get_id(connection,
                "SELECT source_work_id FROM src_work WHERE work_code=%s",
                ("cepheus-engine.ogn",)),
        }
        inputs = {"github": (github, "src/introduction.md", "repository_file",
                             GITHUB_COMMIT, "text/markdown"),
                  "ogn": (website, URL, "web_page", None, "text/html")}
        artifacts = {}
        for key, (data, uri, kind, revision, media) in inputs.items():
            artifact = upsert_artifact(
                connection, works[key], kind, uri, revision, data, media)
            artifacts[key] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))

        def sourced_rule(code, name, category, description, payload, anchor):
            rule = publish_rule(
                connection, package, code, name, category, description)
            for order, key in enumerate(("github", "ogn")):
                artifact, batch = artifacts[key]
                locator = upsert_locator(
                    connection, works[key], artifact, "table_row",
                    "Introduction > Die Rolls > Difficulty and Effect",
                    anchor, name, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, category,
                    code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if key == "github" else "corroborating",
                    key == "github")
            return rule

        core = sourced_rule(
            "task.core-check", "Core Check", "task",
            "Roll 2D6, add relevant modifiers, and succeed on 8 or higher.",
            {"dice_count": 2, "die_sides": 6, "target": 8,
             "natural_min_auto_failure": False,
             "natural_max_auto_success": False}, "core-task-resolution")
        connection.execute("""INSERT INTO rule_check_system
            (rule_id,dice_count,die_sides,target_number,
             natural_min_auto_failure,natural_max_auto_success)
            VALUES (%s,2,6,8,false,false)
            ON CONFLICT (rule_id) DO UPDATE SET dice_count=2,die_sides=6,
            target_number=8,natural_min_auto_failure=false,
            natural_max_auto_success=false""", (core,))

        for order, (code, name, dm) in enumerate(DIFFICULTIES, 1):
            rule = sourced_rule(
                f"difficulty.{code}", name, "difficulty",
                f"{name} difficulty applies DM {dm:+d}.",
                {"modifier": dm, "display_order": order,
                 "is_default": code == "average"}, f"difficulty-{code}")
            connection.execute("""INSERT INTO rule_difficulty
                (rule_id,modifier,display_order,is_default) VALUES (%s,%s,%s,%s)
                ON CONFLICT (rule_id) DO UPDATE SET modifier=EXCLUDED.modifier,
                display_order=EXCLUDED.display_order,
                is_default=EXCLUDED.is_default""",
                (rule, dm, order, code == "average"))

        for order, (code, name, low, high, successful) in enumerate(EFFECTS, 1):
            rule = sourced_rule(
                f"effect.{code}", name, "task", name,
                {"minimum": low, "maximum": high, "successful": successful},
                f"effect-{code}")
            connection.execute("""INSERT INTO rule_effect_band
                (rule_id,minimum_effect,maximum_effect,outcome_code,
                 successful,display_order) VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (rule_id) DO UPDATE SET
                minimum_effect=EXCLUDED.minimum_effect,
                maximum_effect=EXCLUDED.maximum_effect,
                outcome_code=EXCLUDED.outcome_code,
                successful=EXCLUDED.successful,
                display_order=EXCLUDED.display_order""",
                (rule, low, high, code.replace("-", "_"), successful, order))

        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 1 core check, 7 difficulties, and 4 effect bands")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
