"""Import paired-source personal computer hardware for CE-EQUIP-005."""
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

STANDARD = (
    (7, 0, 10000, 50, 7200),
    (8, 1, 5000, 100, 28800),
    (9, 1, 5000, 250, None),
    (10, 2, 1000, 350, None),
    (11, 2, 1000, 500, None),
    (12, 3, 500, 1000, None),
    (13, 4, 500, 1500, None),
    (14, 5, 500, 5000, None),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus computer hardware importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "system can run a number of programs up to its rating",
        "storage space is effectively unlimited at tl 9",
        "battery life is two hours at tl 7, eight hours at tl 8",
        "desktops become obsolete during tl 8",
        "computer terminal has model 0, and costs cr200",
        "hand computer costs twice as much as a normal computer",
        "hand computer | 11 | cr1,000 | 0.5",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired computer sources omit: {phrase}")
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
            connection, package, "equipment.personal-computers",
            "Personal Computer Hardware", "equipment",
            "Personal computer capacity, power, storage, and form factors.")
        connection.execute(
            """INSERT INTO rule_personal_computer_catalogue
               VALUES (%s,true,9,0,8) ON CONFLICT DO NOTHING""",
            (catalogue,))
        connection.execute(
            """INSERT INTO rule_personal_computer_form_factor VALUES
               ('laptop',true,0,NULL),('desktop',true,0,8)
               ON CONFLICT DO NOTHING""")
        rules = [catalogue]

        def item(code, name, tech, model, mass, cost, battery, kind, basis,
                 unquantified, network, interface, one_hand):
            rule = publish_rule(
                connection, package, code, name, "equipment",
                f"{name} personal computer hardware.")
            connection.execute(
                """INSERT INTO inv_item_definition
                   (rule_id,item_kind,minimum_tech_level,
                    cost_credits,mass_grams)
                   VALUES (%s,'equipment',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tech, cost, mass))
            connection.execute(
                """INSERT INTO inv_personal_computer_definition
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (item_rule_id) DO NOTHING""",
                (rule, kind, tech, model, battery,
                 ("not-stated" if kind == "terminal" else
                  "effectively-unlimited" if battery is None else "finite"),
                 battery is None and kind != "terminal",
                 tech >= 9, basis, unquantified, network, interface,
                 one_hand))
            rules.append(rule)
            return rule

        for tech, model, mass, cost, battery in STANDARD:
            item(f"equipment.computer.laptop-tl-{tech}",
                 f"TL {tech} Laptop Computer", tech, model, mass, cost,
                 battery, "laptop", "published-table", False,
                 True, False, False)
            item(f"equipment.computer.hand-tl-{tech}",
                 f"TL {tech} Hand Computer", tech, model, None, cost*2,
                 battery, "hand-computer", "twice-standard-same-tl", True,
                 True, False, True)
        terminal = item(
            "equipment.computer.terminal", "Computer Terminal",
            7, 0, None, 200, None, "terminal", "fixed-description",
            True, False, True, False)
        locators = {}
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            heading = upsert_locator(
                connection, works[side], artifact, "heading",
                "Equipment > Computers", "computers", "Computers", 0)
            for order, rule in enumerate(rules):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = heading if order == 0 else upsert_locator(
                    connection, works[side], artifact,
                    "table_row" if "laptop" in code else "heading",
                    "Equipment > Computers", code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_computer_hardware", code,
                    {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            locators[(side, "computer-hand")] = upsert_locator(
                connection, works[side], artifact, "heading",
                "Equipment > Computers", "hand-computer-description",
                "Hand Computer (TL 7)", 20)
            locators[(side, "device-hand")] = upsert_locator(
                connection, works[side], artifact, "table_row",
                "Equipment > Personal Devices", "hand-computer-device",
                "Hand Computer", 8)
        issue_code = "equipment.computer.hand-computer-dual-listing"
        connection.execute(
            """INSERT INTO src_issue
               (issue_code,domain_code,issue_type,review_priority,
                issue_status,subject_code,title,problem_statement,
                published_value,calculated_value,reviewer_question,
                requested_evidence,engine_disposition,resolved_at,
                resolution_summary)
               VALUES (%s,'equipment.computer','source_conflict','medium',
                'accepted_as_published','hand-computer',
                'Hand Computer has scalable and fixed catalogue forms',
                %s,%s,%s,%s,%s,'preserve_rule',clock_timestamp(),%s)
               ON CONFLICT (issue_code) DO NOTHING""",
            (issue_code,
             "The Computers description starts Hand Computer at TL 7 and "
             "prices it at twice the same-TL standard computer; Personal "
             "Devices separately lists Hand Computer at TL 11.",
             "Computers: TL 7+, twice standard same-TL cost, mass unquantified",
             "Personal Devices: TL 11, Cr1,000, 0.5 kg",
             "Are these a scalable form factor and a specific handcomp?",
             "Publisher errata or explicit edition commentary.",
             "Raymond approved preserving the TL 7 scalable form and treating "
             "the TL 11 handcomp as a specific later catalogue device."))
        issue = get_id(connection, "SELECT source_issue_id FROM src_issue "
                       "WHERE issue_code=%s", (issue_code,))
        for side, location, role in (
            ("github", "computer-hand", "primary"),
            ("ogn", "computer-hand", "corroborating"),
            ("github", "device-hand", "conflicting"),
            ("ogn", "device-hand", "conflicting"),
        ):
            connection.execute(
                """INSERT INTO src_issue_locator VALUES (%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (issue, locators[(side, location)], role))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,
                decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-EQUIP-005')
               ON CONFLICT DO NOTHING""",
            (catalogue, "Raymond approved separate scalable hand-computer and "
             "fixed TL 11 handcomp identities."))
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 17 personal computer profiles and CE-EQUIP-005")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
