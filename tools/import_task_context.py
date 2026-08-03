"""Import Cepheus task time, adjustment, and Law Level rules."""

import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, SKILL_URL, add_provenance, fetch, get_id,
    import_batch, normalize, publish_rule, sha256, stage_candidate,
    upsert_artifact, upsert_locator,
)

SOURCE = ROOT / "sources" / "cepheus-srd" / "src" / "book1" / "skills.md"
TIMES = [
    ("seconds", "1D6 Seconds", "second", 1, "One second"),
    ("rounds", "1D6 Rounds", "round", 6,
     "One personal combat round (6 seconds)"),
    ("minutes", "1D6 Minutes", "minute", 60,
     "One minute (60 seconds, or 10 personal combat rounds)"),
    ("kiloseconds", "1D6 Kiloseconds", "kilosecond", 1000,
     "One kilosecond (~16.67 minutes, or one space combat turn)"),
    ("hours", "1D6 Hours", "hour", 3600, "One hour (60 minutes)"),
    ("days", "1D6 Days", "day", 86400, "One day (24 hours)"),
    ("weeks", "1D6 Weeks", "week", 604800, "One week (7 days)"),
    ("months", "1D6 Months", "month", None,
     "One common month (30-31 days)"),
    ("quarters", "1D6 Quarters", "quarter", None,
     "One quarter (3 common months)"),
]
ADJUSTMENTS = [
    ("faster", "Faster Task", -1, 2, False),
    ("slower", "Slower Task", 1, 2, False),
    ("extra-action", "Extra Simultaneous Action", -2, None, True),
]
LAW = [(0, 0, "routine"), (1, 3, "average"), (4, 6, "difficult"),
       (7, 9, "very-difficult"), (10, None, "formidable")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus task-context importer/1.0"
    website, soup = fetch(session, SKILL_URL)
    texts = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in ["going faster or slower", "1d6 kiloseconds",
                   "for every extra thing", "base difficulty by law level"]:
        if any(normalize(phrase) not in text for text in texts):
            raise ValueError(f"Paired sources disagree or omit: {phrase}")

    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        work_codes = {"github": "cepheus-engine.github-v9.1",
                      "ogn": "cepheus-engine.ogn"}
        artifacts = {}
        for key, work_code in work_codes.items():
            work = get_id(connection,
                "SELECT source_work_id FROM src_work WHERE work_code=%s",
                (work_code,))
            data, uri, kind, revision, media = (
                (github, "src/book1/skills.md", "repository_file",
                 GITHUB_COMMIT, "text/markdown") if key == "github"
                else (website, SKILL_URL, "web_page", None, "text/html"))
            artifact = upsert_artifact(
                connection, work, kind, uri, revision, data, media)
            artifacts[key] = (work, artifact, import_batch(
                connection, package, artifact, sha256(data)))

        def source_rule(code, name, description, payload, heading, anchor):
            rule = publish_rule(
                connection, package, code, name, "task", description)
            for order, key in enumerate(("github", "ogn")):
                work, artifact, batch = artifacts[key]
                locator = upsert_locator(
                    connection, work, artifact, "table_row", heading,
                    anchor, name, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, "task", code, payload)
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if key == "github" else "corroborating",
                    key == "github")
            return rule

        for order, (code, name, unit, seconds, description) in enumerate(TIMES, 1):
            rule = source_rule(
                f"time-frame.{code}", name, description,
                {"unit": unit, "seconds": seconds}, "Skills > Going Faster or Slower",
                f"time-frame-{code}")
            connection.execute("""INSERT INTO rule_time_frame
                (rule_id,dice_count,die_sides,increment_unit,
                 exact_increment_seconds,source_description,display_order)
                VALUES (%s,1,6,%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
                increment_unit=EXCLUDED.increment_unit,
                exact_increment_seconds=EXCLUDED.exact_increment_seconds,
                source_description=EXCLUDED.source_description,
                display_order=EXCLUDED.display_order""",
                (rule, unit, seconds, description, order))

        for code, name, modifier, maximum, all_checks in ADJUSTMENTS:
            rule = source_rule(
                f"task-adjustment.{code}", name, name,
                {"modifier_per_step": modifier, "maximum_steps": maximum},
                "Skills > Task Resolution", f"task-adjustment-{code}")
            connection.execute("""INSERT INTO rule_task_adjustment
                (rule_id,adjustment_kind,modifier_per_step,maximum_steps,
                 applies_to_all_checks) VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT (rule_id) DO UPDATE SET
                modifier_per_step=EXCLUDED.modifier_per_step,
                maximum_steps=EXCLUDED.maximum_steps,
                applies_to_all_checks=EXCLUDED.applies_to_all_checks""",
                (rule, code.replace("-", "_"), modifier, maximum, all_checks))

        connection.execute("DELETE FROM src_law_level_difficulty_provenance")
        connection.execute("DELETE FROM rule_law_level_difficulty")
        for order, (low, high, difficulty) in enumerate(LAW, 1):
            difficulty_id = get_id(connection, """SELECT d.rule_id
                FROM rule_difficulty d JOIN rule_rule r ON r.rule_id=d.rule_id
                WHERE r.rule_code=%s""", (f"difficulty.{difficulty}",))
            row_id = connection.execute("""INSERT INTO rule_law_level_difficulty
                (minimum_law_level,maximum_law_level,difficulty_rule_id,
                 display_order) VALUES (%s,%s,%s,%s)
                RETURNING law_level_difficulty_id""",
                (low, high, difficulty_id, order)).fetchone()[0]
            for source_order, key in enumerate(("github", "ogn")):
                work, artifact, batch = artifacts[key]
                locator = upsert_locator(
                    connection, work, artifact, "table_row",
                    "Skills > Local Law Level", f"law-level-{low}",
                    f"Law Level {low}{'+' if high is None else f'-{high}'}",
                    source_order)
                payload = {"minimum": low, "maximum": high,
                           "difficulty": difficulty}
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "law_level_difficulty", f"{low}:{high}", payload)
                connection.execute("""INSERT INTO
                    src_law_level_difficulty_provenance
                    (law_level_difficulty_id,source_locator_id,
                     import_candidate_id,source_review_id,provenance_class,
                     is_primary_citation) VALUES (%s,%s,%s,%s,%s,%s)""",
                    (row_id, locator, candidate, review,
                     "direct" if key == "github" else "corroborating",
                     key == "github"))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[2] for value in artifacts.values()],))
    print("published 9 time frames, 3 task adjustments, and 5 Law Level mappings")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
