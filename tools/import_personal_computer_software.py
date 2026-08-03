"""Import paired-source personal computer software for CE-EQUIP-007."""
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

FAMILIES = (
    ("database", False, None, None, False),
    ("interface", True, 0, 0, False),
    ("security", True, 0, 3, False),
    ("translator", True, 0, 1, False),
    ("intrusion", True, 1, 4, False),
    ("intelligent-interface", True, 1, 3, False),
    ("expert", True, 1, 3, False),
    ("agent", True, 0, 3, False),
    ("intellect", True, 1, 3, True),
)
PROFILES = {
    "database": ((None, False, 7, "range", 10, 10000),),
    "interface": ((0, False, 7, "included", 0, 0),),
    "security": (
        (0, False, 7, "included", 0, 0),
        (1, False, 9, "fixed", 200, 200),
        (2, False, 11, "fixed", 1000, 1000),
        (3, False, 12, "fixed", 20000, 20000)),
    "translator": (
        (0, False, 9, "fixed", 50, 50),
        (1, False, 10, "fixed", 500, 500)),
    "intrusion": (
        (1, False, 10, "fixed", 1000, 1000),
        (2, False, 11, "fixed", 10000, 10000),
        (3, False, 13, "fixed", 100000, 100000),
        (4, False, 15, "unavailable", None, None)),
    "intelligent-interface": (
        (1, False, 11, "fixed", 100, 100),
        (2, False, 13, "fixed", 1000, 1000),
        (3, False, 17, "fixed", 10000, 10000)),
    "expert": (
        (1, False, 11, "fixed", 1000, 1000),
        (2, False, 12, "fixed", 10000, 10000),
        (3, False, 13, "fixed", 100000, 100000)),
    "agent": (
        (0, False, 11, "fixed", 500, 500),
        (1, False, 12, "fixed", 2000, 2000),
        (2, False, 13, "fixed", 100000, 100000),
        (3, False, 14, "fixed", 250000, 250000)),
    "intellect": (
        (1, False, 12, "fixed", 2000, 2000),
        (2, False, 13, "fixed", 50000, 50000),
        (3, True, 14, "not-stated", None, None)),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus software importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "high-rating software at a lower rating",
        "programs above rating/1 cannot be copied easily",
        "cr10 to cr10,000",
        "intrusion | 1 | 10 | cr1,000",
        "4 | 15 | n/a",
        "intellect | 1 | 12 | cr2,000",
        "3+ | 14",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired software sources omit: {phrase}")
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
        catalogue = publish_rule(
            connection, package, "equipment.personal-computer-software",
            "Personal Computer Software", "equipment",
            "Personal computer software catalogue.")
        connection.execute(
            """INSERT INTO rule_personal_software_catalogue
               VALUES (%s,true,true,1,true) ON CONFLICT DO NOTHING""",
            (catalogue,))
        rules = [catalogue]
        for code, ranked, minimum, maximum, open_ended in FAMILIES:
            rule = publish_rule(
                connection, package, f"software.personal.{code}",
                code.replace("-", " ").title(), "equipment",
                f"{code.replace('-', ' ').title()} software.")
            connection.execute(
                """INSERT INTO rule_personal_software_family
                   VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule, code, ranked, minimum, maximum, open_ended))
            for order, profile in enumerate(PROFILES[code], 1):
                connection.execute(
                    """INSERT INTO rule_personal_software_profile
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""", (rule, order, *profile))
            rules.append(rule)
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            for order, rule in enumerate(rules):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection, works[side], artifact,
                    "heading" if order == 0 else "table_row",
                    "Equipment > Computers > Computer Software",
                    code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_computer_software", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 9 software families, 25 profiles, and CE-EQUIP-007")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
