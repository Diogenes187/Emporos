"""Import paired-source Personal Device capabilities for CE-EQUIP-014."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import ROOT, fetch, get_id, normalize

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-equipment/")
CAPABILITIES = (
    ("bioscanner", "detect-poisons-bacteria", None, None, None),
    ("bioscanner", "analyse-organic-matter", None, None, None),
    ("bioscanner", "search-life-signs", None, None, None),
    ("bioscanner", "classify-organisms", None, None, None),
    ("bioscanner", "interpret-data", None, None, None),
    ("densitometer", "three-dimensional-density-image", None, None, None),
    ("electromagnetic-probe", "equipment-diagnostics", None, None, 1),
    ("electromagnetic-probe", "detect-hidden-devices", None, None, None),
    ("hand-calculator", "mathematical-calculation", None, None, None),
    ("hand-computer-fixed", "small-computer-services", None, None, None),
    ("hand-computer-fixed", "linked-computer-terminal", None, None, None),
    ("holographic-projector", "three-dimensional-projection", 3, True, None),
    ("holographic-projector", "limited-animation", None, None, None),
    ("holographic-projector", "integrated-speakers", None, None, None),
    ("inertial-locator", "direction-and-distance-travelled", None, None, None),
    ("magnetic-compass", "magnetic-north", None, None, None),
    ("metal-detector", "metal-detection", 3, False, None),
    ("neural-activity-sensor", "neural-activity-detection", 500, False, None),
    ("neural-activity-sensor", "rough-intelligence-estimate", 500, False, None),
    ("neural-activity-sensor", "interpret-data", None, None, None),
    ("radiation-counter", "radioactivity-detection-and-intensity", 30, False, None),
    ("wrist-watch", "tell-time", None, None, None),
    ("wrist-watch", "tl9-multiple-world-times", None, None, None),
    ("wrist-watch", "tl9-time-alarms", None, None, None),
)
SKILLS = (
    ("bioscanner", "interpret-data", "skill.comms"),
    ("bioscanner", "interpret-data", "skill.life-sciences"),
    ("neural-activity-sensor", "interpret-data", "skill.comms"),
    ("neural-activity-sensor", "interpret-data", "skill.life-sciences"),
    ("neural-activity-sensor", "interpret-data", "skill.social-sciences"),
    ("electromagnetic-probe", "detect-hidden-devices", "skill.comms"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_text()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus device capabilities/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "detect poisons or bacteria", "three-dimensional image",
        "+1 dm to work out what's wrong", "range is approximately three meters",
        "within a 3 meter radius", "neural activity up to 500 meters",
        "radioactivity within a 30-meter radius",
        "tl 12 version can produce holograms", "at ten times the cost",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired device sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        devices = dict(connection.execute(
            """SELECT device_code,item_rule_id
               FROM inv_personal_device_definition""").fetchall())
        for code, capability, distance, approximate, modifier in CAPABILITIES:
            connection.execute(
                """INSERT INTO rule_personal_device_capability
                   VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (devices[code], capability, distance, approximate, modifier))
        for code, capability, skill_code in SKILLS:
            skill = get_id(connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (skill_code,))
            connection.execute(
                """INSERT INTO rule_personal_device_capability_skill
                   VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                (devices[code], capability, skill))
        projector = devices["holographic-projector"]
        connection.execute(
            """INSERT INTO rule_personal_holographic_projector_upgrade VALUES
               (%s,12,2,'check-to-disbelieve',true),
               (%s,13,10,'true-to-life',false)
               ON CONFLICT DO NOTHING""", (projector, projector))
    print("published 24 device capabilities, 6 skill links, and 2 upgrades")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
