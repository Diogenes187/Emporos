"""Import paired-source personal armor capabilities for CE-EQUIP-002."""
import argparse
import os

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, fetch, get_id, import_batch, normalize, sha256,
    stage_candidate, upsert_artifact, upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-equipment/")


def armor_id(connection, code):
    return get_id(connection, "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                  (f"equipment.armor.{code}",))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_bytes()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus armor capabilities importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    phrases = (
        "each laser hit on ablat reduces its armor value",
        "boosting his strength and dexterity by +4",
        "model 2 computer running an expert tactics-2 program",
        "provides life support for six hours",
        "decreasing radiation exposure by 180 rads",
        "reflec can be worn with other armor",
        "decreasing exposure by up to 40 rads",
    )
    for phrase in phrases:
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired armor sources omit: {phrase}")
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
            ("github", github, "src/book1/equipment.md", "repository_file",
             GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        ids = {code: armor_id(connection, code) for code in (
            "ablat", "battle-dress", "combat-armor",
            "hostile-environment-vacc-suit", "reflec", "vacc-suit")}
        strength = get_id(connection, "SELECT rule_id FROM rule_rule "
                          "WHERE rule_code='characteristic.strength'", ())
        dexterity = get_id(connection, "SELECT rule_id FROM rule_rule "
                           "WHERE rule_code='characteristic.dexterity'", ())
        tactics = get_id(connection, "SELECT rule_id FROM rule_rule "
                        "WHERE rule_code='skill.tactics'", ())
        connection.execute("""INSERT INTO rule_armor_degradation
            VALUES (%s,'laser',1,0) ON CONFLICT DO NOTHING""", (ids["ablat"],))
        connection.execute("""INSERT INTO rule_armor_layer_exception
            VALUES (%s,true,2,true) ON CONFLICT DO NOTHING""", (ids["reflec"],))
        for characteristic in (strength, dexterity):
            connection.execute("""INSERT INTO rule_armor_characteristic_modifier
                VALUES (%s,%s,4,false) ON CONFLICT DO NOTHING""",
                               (ids["battle-dress"], characteristic))
        connection.execute("""INSERT INTO rule_armor_computer_system
            VALUES (%s,2,%s,2) ON CONFLICT DO NOTHING""",
                           (ids["battle-dress"], tactics))
        for code in ("battle-dress", "combat-armor",
                     "hostile-environment-vacc-suit", "vacc-suit"):
            connection.execute("""INSERT INTO rule_armor_life_support
                VALUES (%s,21600,true) ON CONFLICT DO NOTHING""", (ids[code],))
        for hazard in (
            "hard-vacuum", "temperature-extremes", "low-pressure",
            "radiation", "flame", "high-pressure",
            "toxic-corrosive-atmosphere", "nbc",
        ):
            connection.execute(
                "INSERT INTO rule_environmental_hazard VALUES (%s) "
                "ON CONFLICT DO NOTHING", (hazard,))
        protections = (
            ("vacc-suit", "hard-vacuum", "standard", None),
            ("vacc-suit", "temperature-extremes", "standard", None),
            ("vacc-suit", "low-pressure", "standard", None),
            ("vacc-suit", "radiation", "reduction", 40),
            ("combat-armor", "hard-vacuum", "standard", None),
            ("hostile-environment-vacc-suit", "hard-vacuum", "full", None),
            ("hostile-environment-vacc-suit", "temperature-extremes",
             "full", None),
            ("hostile-environment-vacc-suit", "low-pressure", "full", None),
            ("hostile-environment-vacc-suit", "radiation", "reduction", 180),
            ("hostile-environment-vacc-suit", "flame", "impervious", None),
            ("hostile-environment-vacc-suit", "high-pressure",
             "impervious", None),
            ("hostile-environment-vacc-suit", "toxic-corrosive-atmosphere",
             "impervious", None),
        )
        for code, hazard, kind, rads in protections:
            connection.execute("""INSERT INTO rule_armor_environmental_protection
                VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                               (ids[code], hazard, kind, rads))
        connection.execute("""INSERT INTO rule_armor_capability_inheritance
            VALUES (%s,%s) ON CONFLICT DO NOTHING""",
                           (ids["battle-dress"],
                            ids["hostile-environment-vacc-suit"]))
        connection.execute("""INSERT INTO rule_armor_environmental_protection
            VALUES (%s,'nbc','full',NULL) ON CONFLICT DO NOTHING""",
                           (ids["battle-dress"],))
        mechanics = {
            "ablat": ("laser-degradation",),
            "battle-dress": ("characteristic-boost", "computer",
                             "life-support", "environmental-protection"),
            "combat-armor": ("life-support", "hard-vacuum"),
            "hostile-environment-vacc-suit":
                ("life-support", "environmental-protection"),
            "reflec": ("layer-exception",),
            "vacc-suit": ("life-support", "environmental-protection"),
        }
        for code, codes in mechanics.items():
            display = code.replace("-", " ").title()
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading",
                    f"Equipment > Armor > {display}",
                    f"armor-{code}-capabilities", display, 0)
                for mechanic in codes:
                    candidate, _ = stage_candidate(
                        connection, batch, artifact, locator,
                        "personal_armor_capability",
                        f"equipment.armor.{code}.{mechanic}",
                        {"armor": code, "mechanic": mechanic})
                    connection.execute("""INSERT INTO
                        src_armor_mechanic_provenance VALUES
                        (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                        (ids[code], mechanic, locator, candidate,
                         "direct" if side == "github" else "corroborating",
                         side == "github"))
        connection.execute("""UPDATE src_import_batch
            SET batch_status='published',
                completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published CE-EQUIP-002 personal armor capabilities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
