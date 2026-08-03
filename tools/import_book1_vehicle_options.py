"""Import paired-source Book 1 vehicle options for CE-EQUIP-027."""
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
OPTIONS = (
    ("autopilot","Autopilot",11,1,"fixed",3000,None,None,None,0,0,0,None,
     False,1,1,1),
    ("enclosed","Enclosed",None,1,"base-percent",None,None,None,10,-1,-10,0,
     None,True,None,None,None),
    ("extended-life-support","Extended Life Support",None,1,"base-percent",
     None,None,None,10,0,0,0,64800,False,None,None,None),
    ("heavy-armor","Heavy Armor",None,1,"base-percent",None,None,None,25,0,0,
     5,None,False,None,None,None),
    ("high-performance","High Performance",None,1,"base-percent",None,None,
     None,50,0,20,0,None,False,None,None,None),
    ("on-board-computer","On-board Computer",None,None,
     "selected-hand-computer",None,None,None,None,0,0,0,None,False,
     None,None,None),
    ("sealed","Sealed",None,1,"base-percent",None,None,None,20,0,0,0,7200,
     False,None,None,None),
    ("style","Style",None,1,"bounded-fixed",None,200,2000,None,0,0,0,None,
     False,None,None,None),
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
    session.headers["User-Agent"] = "BaseCepheus Book 1 vehicle options/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "with the exception of on-board computer",
        "model 1 computer specialized to run intellect/1",
        "reduces agility by 1 and top speed by 10%",
        "increases the duration to 18 hours per person",
        "increasing the armor of a vehicle by 5",
        "increasing its top speed by 20%",
        "costs the same as a hand computer",
        "provides life support for its passengers and crew for two hours",
        "costs cr200 to cr2,000",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired vehicle-option sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        works = {side: get_id(connection, "SELECT source_work_id FROM src_work "
            "WHERE work_code=%s", (code,)) for side, code in (
                ("github","cepheus-engine.github-v9.1"),
                ("ogn","cepheus-engine.ogn"))}
        artifacts = {}
        for side,data,uri,kind,revision,media in (
            ("github",github,"src/book1/equipment.md","repository_file",
             GITHUB_COMMIT,"text/markdown"),
            ("ogn",website,URL,"web_page",None,"text/html"),
        ):
            artifact = upsert_artifact(
                connection,works[side],kind,uri,revision,data,media)
            artifacts[side] = (artifact,import_batch(
                connection,package,artifact,sha256(data)))
        for order,row in enumerate(OPTIONS,1):
            code,name,*mechanics = row
            rule_code = f"vehicle.book1.option.{code}"
            rule = publish_rule(connection,package,rule_code,name,"vehicle",
                                f"Book 1 {name} option.")
            connection.execute(
                """INSERT INTO rule_book1_vehicle_option VALUES
                   (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""", (rule,code,*mechanics))
            payload = {"option_code":code,"mechanics":mechanics}
            for side in ("github","ogn"):
                artifact,batch = artifacts[side]
                locator = upsert_locator(
                    connection,works[side],artifact,"heading",
                    "Equipment > Vehicles > Vehicle Options",
                    rule_code,rule_code,order)
                candidate,review = stage_candidate(
                    connection,batch,artifact,locator,
                    "book1_vehicle_option",rule_code,payload)
                add_provenance(
                    connection,rule,package,locator,candidate,review,
                    "direct" if side=="github" else "corroborating",
                    side=="github")
        connection.execute(
            """INSERT INTO rule_book1_vehicle_included_option
               SELECT profile.rule_id,option.rule_id
               FROM rule_book1_vehicle_profile profile
               CROSS JOIN rule_book1_vehicle_option option
               WHERE profile.profile_code IN ('atv','afv','g-carrier','speeder')
                 AND option.option_code='sealed'
               ON CONFLICT DO NOTHING""")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 8 Book 1 vehicle options and 4 inclusions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
