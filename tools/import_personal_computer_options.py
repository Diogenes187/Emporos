"""Import paired-source personal computer options for CE-EQUIP-006."""
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus computer options importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "data display/recorder (tl 13)",
        "dd/rs can display data from any system",
        "data wafer (tl 10)",
        "rating of 1 or 2 higher for that program only",
        "costs 25% more per added rating",
        "does not count against that total",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired computer-option sources omit: {phrase}")
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
        rules = []

        def option(code, name, tech, cost, kind, flags):
            rule = publish_rule(connection, package, code, name, "equipment",
                                f"{name} computer option.")
            connection.execute(
                """INSERT INTO inv_item_definition
                   (rule_id,item_kind,minimum_tech_level,cost_credits,mass_grams)
                   VALUES (%s,'equipment',%s,%s,NULL)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""", (rule, tech, cost))
            connection.execute(
                """INSERT INTO inv_personal_computer_option_definition
                   VALUES (%s,%s,true,%s,%s,%s,%s)
                   ON CONFLICT (item_rule_id) DO NOTHING""",
                (rule, kind, *flags))
            rules.append(rule)

        option("equipment.computer-option.data-display-recorder",
               "Data Display/Recorder", 13, 5000,
               "data-display-recorder", (True, True, True, False))
        option("equipment.computer-option.data-wafer", "Data Wafer", 10, 5,
               "data-wafer", (False, False, False, True))
        specialization = publish_rule(
            connection, package, "equipment.computer-option.specialized",
            "Specialized Computer", "equipment",
            "Computer specialization for one program.")
        connection.execute(
            """INSERT INTO rule_personal_computer_specialization
               VALUES (%s,1,2,2500,true,0) ON CONFLICT DO NOTHING""",
            (specialization,))
        rules.append(specialization)
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules, 1):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    "Equipment > Computers > Computer Options",
                    code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_computer_option", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 3 personal computer options and CE-EQUIP-006")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
