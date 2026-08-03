"""Import paired Book 1 melee description mechanics for CE-EQUIP-029."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, sha256, stage_candidate, upsert_artifact, upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-equipment/")
# code, min mm, max mm, basis, two hands, load ignored, utility, survival,
# emergency kit, lifeboat, shipboard, rifle attached, equivalent,
# standing tree, unloaded long gun, laser prohibited
ROWS = (
    ("bayonet",None,None,None,False,False,False,False,False,False,False,
     True,"dagger",False,False,False),
    ("blade",300,300,"approximate",False,False,True,True,True,True,False,
     False,None,False,False,False),
    ("broadsword",1000,1200,"range",True,False,False,False,False,False,
     False,False,None,False,False,False),
    ("cudgel",1000,2000,"range",False,False,False,False,False,False,False,
     False,None,True,True,True),
    ("cutlass",600,900,"range",False,False,False,False,False,False,True,
     False,None,False,False,False),
    ("dagger",200,200,"approximate",False,True,True,False,False,False,False,
     False,None,False,False,False),
    ("foil",800,800,"exact",False,False,False,False,False,False,False,
     False,None,False,False,False),
    ("halberd",2500,2500,"exact",True,False,False,False,False,False,False,
     False,None,False,False,False),
    ("pike",3000,4000,"range",True,False,False,False,False,False,False,
     False,None,False,False,False),
    ("spear",3000,3000,"exact",False,False,False,False,False,False,False,
     False,None,False,False,False),
    ("sword",700,950,"range",False,False,False,False,False,False,False,
     False,None,False,False,False),
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
    session.headers["User-Agent"] = "BaseCepheus melee capabilities/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "when not attached to a rifle, the bayonet performs as a dagger",
        "requires both hands to swing",
        "laser weapons are too delicate to be used as cudgels",
        "standard shipboard blade weapon",
        "that weight, however, does not count against the weight load",
        "length: 3000 to 4000mm",
        "blade length may vary from 700 to 950mm",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired melee descriptions omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
            AND package_version='9.1-draft'""", ())
        works = {side: get_id(connection, "SELECT source_work_id FROM src_work "
            "WHERE work_code=%s", (code,)) for side,code in (
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
        for order,row in enumerate(ROWS,1):
            code,*values = row
            rule = get_id(connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (f"equipment.weapon.{code}",))
            equivalent_code = values[11]
            equivalent = None if equivalent_code is None else get_id(
                connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (f"equipment.weapon.{equivalent_code}",))
            stored = (*values[:11],equivalent,*values[12:])
            connection.execute(
                """INSERT INTO rule_book1_melee_weapon_capability
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""", (rule,*stored))
            payload = {"weapon_code":code,"capabilities":stored}
            for side in ("github","ogn"):
                artifact,batch = artifacts[side]
                locator = upsert_locator(
                    connection,works[side],artifact,"paragraph",
                    "Equipment > Weapons > Melee Weapon Descriptions",
                    code,code,order)
                candidate,review = stage_candidate(
                    connection,batch,artifact,locator,
                    "book1_melee_capability",code,payload)
                add_provenance(
                    connection,rule,package,locator,candidate,review,
                    "direct" if side=="github" else "corroborating",
                    side=="github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published capabilities for 11 Book 1 melee weapons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
