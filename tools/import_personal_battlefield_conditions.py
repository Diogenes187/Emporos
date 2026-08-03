"""Import paired-source Battlefield Conditions and Battlefield Sensors."""

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
CONDITIONS = (
    ("low-light", "Low Light", "light", -1, False, True),
    ("complete-darkness", "Complete Darkness", "light", -4, False, True),
    ("smoke", "Smoke or Fog", "obscurant", -1, True, True),
    ("thick-smoke", "Thick Smoke or Fog", "obscurant", -2, True, True),
    ("extreme-weather-visibility", "Extreme Weather Visibility",
     "weather", -1, False, True),
    ("extreme-weather-interference", "Extreme Weather Interference",
     "weather", -1, False, False),
)
SENSORS = (
    ("bioscanner", "Bioscanner", False, False, False, False, False),
    ("infra-red", "Infra-Red Sensor", True, False, True, True, True),
    ("densitometer", "Densitometer", True, False, False, False, False),
    ("electromagnetic-detector", "Electromagnetic Detector",
     False, False, False, False, False),
    ("laser-assisted-targeting", "Laser-Assisted Targeting",
     True, False, False, False, False),
    ("light-intensification", "Light Intensification",
     True, True, False, False, False),
    ("motion-sensor", "Motion Sensor", True, False, False, False, False),
    ("neural-activity-sensor", "Neural Activity Sensor",
     True, False, False, False, False),
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
    session.headers["User-Agent"] = "BaseCepheus battlefield-condition importer/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "battlefield conditions", "complete darkness", "smoke or fog",
        "extreme weather", "battlefield sensors", "infra-red",
        "densitometer", "laser-assisted targeting", "light intensification",
        "neural activity sensor",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired battlefield sources omit: {phrase}")
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

        def sourced(code, name, summary, heading, payload):
            rule_id = publish_rule(
                connection, package, code, name, "combat", summary)
            for side in ("github", "ogn"):
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "heading", heading,
                    code.replace(".", "-"), name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator, "combat", code, payload)
                add_provenance(
                    connection, rule_id, package, locator, candidate, review,
                    "direct" if side == "github" else "corroborating",
                    side == "github")
            return rule_id

        weather_visibility_rule = None
        for code, name, group, modifier, laser, avoidable in CONDITIONS:
            rule_id = sourced(
                f"combat.battlefield-condition.{code}", name,
                f"{name} ranged-attack modifier.",
                "Personal Combat > Battlefield Conditions",
                {"condition": code, "group": group, "modifier": modifier,
                 "doubled_for_laser_weapons": laser,
                 "sensor_avoidable": avoidable})
            connection.execute(
                """INSERT INTO rule_personal_battlefield_condition
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO NOTHING""",
                (rule_id, code, group, modifier, laser, avoidable))
            if code == "extreme-weather-visibility":
                weather_visibility_rule = rule_id
        for code, name, weather, darkness, smoke, cover, jammed in SENSORS:
            rule_id = sourced(
                f"combat.battlefield-sensor.{code}", name,
                f"{name} battlefield sensing capability.",
                "Personal Combat > Battlefield Sensors",
                {"sensor": code, "qualifies_weather_visibility": weather,
                 "negates_darkness": darkness,
                 "negates_smoke_concealment": smoke,
                 "negates_soft_cover": cover, "can_be_jammed": jammed})
            connection.execute(
                """INSERT INTO rule_personal_battlefield_sensor
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (rule_id) DO NOTHING""",
                (rule_id, code, weather, darkness, smoke, cover, jammed))
        connection.execute(
            """INSERT INTO rule_interpretation
               (rule_id,interpretation_type,rationale,decision_register_entry)
               VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-004')
               ON CONFLICT DO NOTHING""",
            (weather_visibility_rule,
             "Six target-locating sensors qualify; Bioscanner and "
             "Electromagnetic Detector do not; blocked sensors give no benefit."))
        connection.execute(
            """UPDATE src_import_batch SET batch_status='published',
                      completed_at=COALESCE(completed_at,clock_timestamp())
               WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published Battlefield Conditions and Battlefield Sensors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
