"""Import paired-source Book 1 vehicle profiles for CE-EQUIP-025."""
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
PROFILES = (
    ("steamship","Steamship","steamship",4,"skill.ocean-ships",-3,30,"kph",
     "closed",2,40,40,720000,(("crew",5),("passenger",10)),"none",0),
    ("biplane","Biplane","biplane",5,"skill.winged-aircraft",1,250,"kph",
     "closed",2,1,1,46000,(("pilot",1),("passenger",1)),"none",0),
    ("ground-car","Ground Car","ground-car",5,"skill.wheeled-vehicle",0,150,
     "kph","closed",6,3,2,6000,(("driver",1),("passenger",3)),"none",0),
    ("motor-boat","Motor Boat","motor-boat",5,"skill.motorboats",-3,120,"kph",
     "closed",3,16,17,530000,(("crew",5),("passenger",10)),"none",0),
    ("helicopter","Helicopter","helicopter",6,"skill.rotor-aircraft",1,100,
     "kph","closed",3,2,3,250000,(("pilot",1),("passenger",7)),"none",0),
    ("submersible","Submersible","submersible",6,"skill.submarine",-4,40,
     "kph","closed",3,85,85,1700000,(("crew",5),("passenger",10)),"none",0),
    ("twin-jet-aircraft","Twin Jet Aircraft","twin-engine-jet",6,
     "skill.winged-aircraft",1,600,"kph","closed",3,5,5,480000,
     (("pilot",2),("passenger",6)),"none",0),
    ("hovercraft","Hovercraft","hovercraft",7,"skill.rotor-aircraft",1,150,
     "kph","closed",3,7,8,880000,(("pilot",1),("passenger",15)),"none",0),
    ("air-raft","Air/Raft","air-raft",8,"skill.grav-vehicle",0,400,"kph",
     "open",6,2,2,275000,(("pilot",1),("passenger",3)),"none",0),
    ("speeder","Speeder","speeder",8,"skill.grav-vehicle",2,1500,"kph",
     "closed",3,1,2,890000,(("pilot",1),("passenger",1)),"none",0),
    ("destroyer","Destroyer","destroyer-watercraft",9,"skill.ocean-ships",-5,
     40,"kph","closed",8,63,63,4800000,
     (("crew",10),("gunner",8),("passenger",12)),"none",0),
    ("grav-floater","Grav Floater","grav-floater",11,"skill.grav-vehicle",-2,
     40,"kph","open",None,None,1,500,(("rider",1),),"none",0),
    ("afv","AFV","afv-tracked",12,"skill.tracked-vehicle",0,80,"kph",
     "closed",18,5,5,65000,(("driver",1),("passenger",9)),
     "triple-laser",3),
    ("atv","ATV","atv-tracked",12,"skill.tracked-vehicle",0,100,"kph",
     "closed",12,5,5,50000,(("driver",1),("passenger",15)),"none",0),
    ("grav-belt","Grav Belt",None,12,"skill.zero-g",2,300,None,
     "open",None,None,1,100000,(("wearer",1),),"none",0),
    ("g-carrier","G/Carrier","g-carrier",15,"skill.grav-vehicle",0,620,"kph",
     "closed",25,8,8,150000,(("driver",1),("gunner",1),("passenger",14)),
     "fusion-gun",1),
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
    session.headers["User-Agent"] = "BaseCepheus Book 1 vehicles/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "steamship | 4", "30 kph | 5 crew, 10 psgr",
        "air/raft | 8", "400 kph | 1 pilot, 3 psgr",
        "grav belt | 12", "300 | 1 wearer",
        "g/carrier | 15", "620 kph | 1 driver, 1 gunner, 14 psgr",
        "triple laser (turret)", "fusion gun (turret)",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Book 1 vehicle sources omit: {phrase}")
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
            ("ogn", website, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, data, media)
            artifacts[side] = (artifact, import_batch(
                connection, package, artifact, sha256(data)))
        catalogue = publish_rule(
            connection, package, "equipment.book1-vehicles",
            "Book 1 Vehicles", "vehicle", "Book 1 vehicle catalogue.")
        rules = [catalogue]
        for row in PROFILES:
            (code,name,class_code,tech,skill_code,agility,speed,unit,config,
             armor,hull,structure,cost,occupancy,weapon,count) = row
            rule = publish_rule(
                connection, package, f"vehicle.book1.{code}", name,
                "vehicle", f"Book 1 {name} profile.")
            skill = get_id(connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (skill_code,))
            vehicle_class = None if class_code is None else get_id(
                connection,
                "SELECT vehicle_class_rule_id FROM vehicle_class "
                "WHERE class_code=%s", (class_code,))
            connection.execute(
                """INSERT INTO rule_book1_vehicle_profile VALUES
                   (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (rule,code,vehicle_class,tech,skill,agility,speed,unit,
                 unit is None,config,armor,hull,structure,cost))
            for role, quantity in occupancy:
                connection.execute(
                    """INSERT INTO rule_book1_vehicle_occupancy
                       VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (rule,role,quantity))
            connection.execute(
                """INSERT INTO rule_book1_vehicle_weapon_summary
                   VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (rule,weapon,None if weapon=="none" else "turret",count))
            rules.append(rule)
        for side in ("github","ogn"):
            artifact,batch = artifacts[side]
            for order,rule in enumerate(rules):
                rule_code = connection.execute(
                    "SELECT rule_code FROM rule_rule WHERE rule_id=%s",
                    (rule,)).fetchone()[0]
                locator = upsert_locator(
                    connection,works[side],artifact,
                    "heading" if order==0 else "table_row",
                    "Equipment > Vehicles",rule_code,rule_code,order)
                candidate,review = stage_candidate(
                    connection,batch,artifact,locator,
                    "book1_vehicle",rule_code,{"rule_code":rule_code})
                add_provenance(
                    connection,rule,package,locator,candidate,review,
                    "direct" if side=="github" else "corroborating",
                    side=="github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 16 Book 1 vehicle profiles distinct from VDS designs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
