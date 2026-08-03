"""Import paired-source personal communicator catalogue for CE-EQUIP-004."""
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

DEVICES = (
    ("long-range", "Long Range Communicator", 6, 500, 15000,
     10, 500000, "fixed", None, False, False, False),
    ("medium-range", "Medium Range Communicator", 5, 200, 10000,
     5, 30000, "fixed", None, False, False, False),
    ("short-range", "Short Range Communicator", 5, 100, 5000,
     3, 10000, "fixed", None, False, False, False),
    ("personal", "Personal Communicator", 8, 250, 300,
     1, None, "satellite-network", 8, True, False, True),
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
    session.headers["User-Agent"] = "BaseCepheus communicator importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "routine use of these devices does not require a skill check",
        "contact with ships in orbit", "ten separate channels",
        "contact with official radio channels", "much shorter underground",
        "single channel communication device",
        "the channel is private, but not secure",
        "tech level of 7 or less, personal communicators will not work",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired communicator sources omit: {phrase}")
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
        usage = publish_rule(
            connection, package, "equipment.personal-communicators",
            "Personal Communicators", "equipment",
            "Routine and exceptional use of personal communications devices.")
        comms = get_id(connection, "SELECT rule_id FROM rule_rule "
                       "WHERE rule_code='skill.comms'", ())
        connection.execute(
            """INSERT INTO rule_personal_communicator_usage
               VALUES (%s,false,%s) ON CONFLICT DO NOTHING""", (usage, comms))
        all_rules = [usage]
        for order, device in enumerate(DEVICES, 1):
            (code, name, tech, cost, mass, channels, range_meters,
             range_kind, world_tl, private, secure, fee) = device
            rule = publish_rule(
                connection, package, f"equipment.communicator.{code}",
                name, "equipment", f"{name} communications equipment.")
            all_rules.append(rule)
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
                """INSERT INTO inv_communicator_definition
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (item_rule_id) DO NOTHING""",
                (rule, channels, range_meters, range_kind, world_tl,
                 private, secure, fee))
            base_form = {
                "long-range": "backpack", "medium-range": "belt-or-sling",
                "short-range": "belt", "personal": "handheld"}[code]
            connection.execute(
                """INSERT INTO inv_communicator_tech_profile
                   VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule, tech, mass, base_form))
            upgrades = {
                "long-range": (1500, "belt-or-sling"),
                "medium-range": (500, "belt-or-sling"),
                "short-range": (300, "handheld"),
            }
            if code in upgrades:
                connection.execute(
                    """INSERT INTO inv_communicator_tech_profile
                       VALUES (%s,7,%s,%s) ON CONFLICT DO NOTHING""",
                    (rule, *upgrades[code]))
            capabilities = {
                "long-range": ("orbital-ship-contact",),
                "medium-range": ("official-radio-channels",),
                "personal": ("worldwide-satellite-addressing",),
            }.get(code, ())
            for capability in capabilities:
                connection.execute(
                    """INSERT INTO rule_communicator_contact_capability
                       VALUES (%s,%s) ON CONFLICT DO NOTHING""",
                    (rule, capability))
            if code == "short-range":
                for environment in ("underground", "underwater"):
                    connection.execute(
                        """INSERT INTO rule_communicator_environment_effect
                           VALUES (%s,%s,'unquantified-range-reduction')
                           ON CONFLICT DO NOTHING""", (rule, environment))
        for side in ("github", "ogn"):
            artifact, batch = artifacts[side]
            heading = upsert_locator(
                connection, works[side], artifact, "heading",
                "Equipment > Communicators", "communicators",
                "Communicators", 0)
            for order, rule in enumerate(all_rules):
                code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = heading if order == 0 else upsert_locator(
                    connection, works[side], artifact, "table_row",
                    "Equipment > Communicators", code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_communicator", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,
                decision_register_entry)
               VALUES (%s,'explicit_source',%s,NULL)
               ON CONFLICT DO NOTHING""",
            (usage, "CE-EQUIP-004 preserves all published communicator "
             "limits; unquantified reductions remain unquantified."))
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 4 personal communicators and CE-EQUIP-004")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
