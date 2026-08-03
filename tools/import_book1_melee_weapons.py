"""Import the paired-source Book 1 melee catalogue for CE-EQUIP-028."""
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
ROWS = (
    ("unarmed-strike","Unarmed Strike",None,None,None,1,("bludgeoning",),
     None,("close-quarters",)),
    ("cudgel","Cudgel",0,10,1000,3,("bludgeoning",),9,
     ("close-quarters",)),
    ("dagger","Dagger",0,10,250,1,("piercing",),5,
     ("close-quarters","thrown")),
    ("spear","Spear",0,10,1500,3,("piercing",),8,
     ("extended-reach","thrown")),
    ("pike","Pike",1,40,8000,4,("piercing",),8,("extended-reach",)),
    ("sword","Sword",1,150,1000,3,("piercing","slashing"),8,
     ("extended-reach",)),
    ("broadsword","Broadsword",2,300,3000,4,("slashing",),8,
     ("extended-reach",)),
    ("halberd","Halberd",2,75,3000,4,("slashing",),8,
     ("extended-reach",)),
    ("bayonet","Bayonet",3,10,250,1,("piercing",),5,
     ("close-quarters",)),
    ("blade","Blade",3,50,350,2,("piercing",),8,("extended-reach",)),
    ("cutlass","Cutlass",3,100,1250,3,("slashing",),8,
     ("extended-reach",)),
    ("foil","Foil",3,100,500,3,("piercing",),8,("extended-reach",)),
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
    session.headers["User-Agent"] = "BaseCepheus Book 1 melee weapons/1.0"
    website, soup = fetch(session, URL)
    paired = (normalize(github.decode()), normalize(soup.get_text(" ")))
    for phrase in (
        "unarmed strike | — | — | — | melee (close quarters) | 1d6",
        "dagger | 0 | cr10 | 250g",
        "spear | 0 | cr10 | 1500g",
        "sword | 1 | cr150 | 1kg",
        "broadsword | 2 | cr300 | 3kg",
        "foil | 3 | cr100 | 500g",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired melee sources omit: {phrase}")
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
            code,name,tl,cost,mass,dice,damage_types,law,modes = row
            rule_code = (
                "combat.attack.unarmed-strike" if code=="unarmed-strike"
                else f"equipment.weapon.{code}")
            rule = publish_rule(
                connection,package,rule_code,name,
                "combat" if code=="unarmed-strike" else "equipment",
                f"Book 1 {name} melee catalogue entry.")
            if code!="unarmed-strike":
                connection.execute(
                    """INSERT INTO inv_item_definition
                       (rule_id,item_kind,minimum_tech_level,cost_credits,
                        mass_grams) VALUES (%s,'weapon',%s,%s,%s)
                       ON CONFLICT (rule_id) DO UPDATE SET
                       item_kind='weapon',
                       minimum_tech_level=EXCLUDED.minimum_tech_level,
                       cost_credits=EXCLUDED.cost_credits,
                       mass_grams=EXCLUDED.mass_grams""",
                    (rule,tl,cost,mass))
                connection.execute(
                    """INSERT INTO inv_weapon_definition VALUES (%s,%s,6,%s)
                       ON CONFLICT (item_rule_id) DO UPDATE SET
                       damage_dice_count=EXCLUDED.damage_dice_count,
                       damage_die_sides=6,
                       illegal_at_law_level=EXCLUDED.illegal_at_law_level""",
                    (rule,dice,law))
                for damage_type in damage_types:
                    connection.execute(
                        """INSERT INTO inv_weapon_damage_type VALUES (%s,%s)
                           ON CONFLICT DO NOTHING""", (rule,damage_type))
                for mode_order,mode in enumerate(modes,1):
                    connection.execute(
                        """INSERT INTO inv_weapon_attack_mode VALUES (%s,%s,%s)
                           ON CONFLICT (item_rule_id,attack_profile_code)
                           DO UPDATE SET display_order=EXCLUDED.display_order""",
                        (rule,mode,mode_order))
            connection.execute(
                """INSERT INTO rule_book1_melee_attack VALUES
                   (%s,%s,%s,%s,%s,%s,%s,6,%s)
                   ON CONFLICT DO NOTHING""",
                (rule,code,None if code=="unarmed-strike" else rule,
                 tl is None,cost is None,mass is None,dice,law))
            for mode_order,mode in enumerate(modes,1):
                connection.execute(
                    """INSERT INTO rule_book1_melee_attack_mode
                       VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (rule,mode,mode_order))
            payload = {
                "entry_code":code,"tech_level":tl,"cost_credits":cost,
                "mass_grams":mass,"damage_dice_count":dice,
                "damage_types":damage_types,"law_level":law,"modes":modes}
            for side in ("github","ogn"):
                artifact,batch = artifacts[side]
                locator = upsert_locator(
                    connection,works[side],artifact,"table_row",
                    "Equipment > Weapons > Common Personal Melee Weapons",
                    code,code,order)
                candidate,review = stage_candidate(
                    connection,batch,artifact,locator,
                    "book1_melee_weapon",code,payload)
                add_provenance(
                    connection,rule,package,locator,candidate,review,
                    "direct" if side=="github" else "corroborating",
                    side=="github")
        connection.execute("""UPDATE src_import_batch SET
            batch_status='published',
            completed_at=COALESCE(completed_at,clock_timestamp())
            WHERE import_batch_id=ANY(%s)""",
            ([value[1] for value in artifacts.values()],))
    print("published 12 Book 1 melee attacks, including 11 physical weapons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
