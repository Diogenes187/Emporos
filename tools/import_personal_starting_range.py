"""Import paired-source personal-combat Starting Range mechanics."""

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
    session.headers["User-Agent"] = "BaseCepheus starting-range importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "the referee must decide the starting range",
        "starting range is usually short",
        "outdoor encounters is usually medium",
        "long or even very long range would not be inappropriate",
        "total darkness reduces starting range to short or less",
        "partial darkness restricts starting range to medium or less",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Starting Range sources omit: {phrase}")
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
        rule = publish_rule(
            connection, package, "combat.starting-range", "Starting Range",
            "combat", "Referee-selected opening geometry with visibility caps.")
        payload = {
            "tight_quarters_default": "short", "outdoors_default": "medium",
            "open_area_options": ["long", "very-long"],
            "total_darkness_maximum": "short",
            "partial_darkness_maximum": "medium",
            "referee_decides": True,
        }
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            locator = upsert_locator(
                connection, works[side], artifact, "heading",
                "Personal Combat > Range > Starting Range",
                "personal-starting-range", "Starting Range", 0)
            candidate, review = stage_candidate(
                connection, batch, artifact, locator, "combat",
                "combat.starting-range", payload)
            add_provenance(connection, rule, package, locator, candidate, review,
                "direct" if side == "ogn" else "corroborating", side == "ogn")
        ids = dict(connection.execute(
            """SELECT rule_code,rule_id FROM rule_rule
               WHERE rule_code=ANY(%s)""", (list((
                "combat.range.short","combat.range.medium",
                "combat.range.long","combat.range.very-long")),)).fetchall())
        connection.execute("DELETE FROM rule_personal_starting_range_option")
        connection.execute("DELETE FROM rule_personal_starting_range_context")
        connection.execute("DELETE FROM rule_personal_starting_range_light_cap")
        connection.execute("""INSERT INTO rule_personal_starting_range_context
            VALUES ('tight_quarters',1,%s,false),('outdoors',2,%s,false),
                   ('open_area',3,NULL,true)""",
            (ids["combat.range.short"], ids["combat.range.medium"]))
        connection.execute("""INSERT INTO rule_personal_starting_range_option
            VALUES ('tight_quarters',%s,1),('outdoors',%s,1),
                   ('open_area',%s,1),('open_area',%s,2)""",
            (ids["combat.range.short"], ids["combat.range.medium"],
             ids["combat.range.long"], ids["combat.range.very-long"]))
        connection.execute("""INSERT INTO rule_personal_starting_range_light_cap
            VALUES ('normal',NULL),('partial_darkness',%s),
                   ('total_darkness',%s)""",
            (ids["combat.range.medium"], ids["combat.range.short"]))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published paired-source Starting Range mechanics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
