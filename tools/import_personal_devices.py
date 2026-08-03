"""Import paired-source Personal Devices catalogue for CE-EQUIP-013."""
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
    ("magnetic-compass", "Magnetic Compass", 3, 10, None),
    ("wrist-watch", "Wrist Watch", 4, 100, None),
    ("radiation-counter", "Radiation Counter", 5, 250, 1000),
    ("metal-detector", "Metal Detector", 6, 300, 1000),
    ("hand-calculator", "Hand Calculator", 7, 10, 100),
    ("inertial-locator", "Inertial Locator", 9, 1200, 1500),
    ("electromagnetic-probe", "Electromagnetic Probe", 10, 1000, None),
    ("hand-computer-fixed", "Hand Computer (Fixed Device)", 11, 1000, 500),
    ("holographic-projector", "Holographic Projector", 11, 1000, 1000),
    ("densitometer", "Densitometer", 14, 20000, 5000),
    ("bioscanner", "Bioscanner", 15, 350000, 3500),
    ("neural-activity-sensor", "Neural Activity Sensor", 15, 35000, 10000),
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
    session.headers["User-Agent"] = "BaseCepheus personal devices importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "magnetic compass | 3 | cr10",
        "radiation counter | 5 | cr250 | 1",
        "hand computer | 11 | cr1,000 | 0.5",
        "holographic projector | 11 | cr1,000 | 1",
        "bioscanner | 15 | cr350,000 | 3.5",
        "neural activity sensor | 15 | cr35,000 | 10",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Personal Devices sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        works = {side: get_id(connection, """SELECT source_work_id FROM src_work
            WHERE work_code=%s""", (code,)) for side, code in (
                ("github", "cepheus-engine.github-v9.1"),
                ("ogn", "cepheus-engine.ogn"))}
        artifacts = {}
        for side, data, uri, kind, revision, media in (
            ("github", github, "src/book1/equipment.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", website, URL, "web_page", None, "text/html")):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        catalogue = publish_rule(
            connection, package, "equipment.personal-devices",
            "Personal Devices", "equipment", "Personal Devices catalogue.")
        rules = [catalogue]
        for code, name, tech, cost, mass in DEVICES:
            rule = publish_rule(
                connection, package, f"equipment.device.{code}", name,
                "equipment", f"{name} device.")
            connection.execute(
                """INSERT INTO inv_item_definition VALUES
                   (%s,'equipment',%s,%s,%s)
                   ON CONFLICT (rule_id) DO UPDATE SET
                     minimum_tech_level=EXCLUDED.minimum_tech_level,
                     cost_credits=EXCLUDED.cost_credits,
                     mass_grams=EXCLUDED.mass_grams""",
                (rule, tech, cost, mass))
            connection.execute(
                """INSERT INTO inv_personal_device_definition
                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule, code, mass is None))
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
                    "Equipment > Personal Devices", code, code, order)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    "personal_device", code, {"rule_code": code})
                add_provenance(
                    connection, rule, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 12 personal devices and CE-EQUIP-013")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
