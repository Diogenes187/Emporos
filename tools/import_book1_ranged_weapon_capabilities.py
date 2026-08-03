"""Import paired ranged-description mechanics for CE-EQUIP-031."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import ROOT, fetch, normalize
from import_ranged_weapons import EQUIPMENT_URL, WEAPONS

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus ranged capabilities/1.0"
    _, soup = fetch(session,EQUIPMENT_URL)
    paired = (normalize(SOURCE.read_text()),normalize(soup.get_text(" ")))
    for phrase in (
        "reloading a tl2 crossbow takes 6 minor actions",
        "at tl4 this is reduced to 3 minor actions",
        "even self-loading at tl9",
        "treated as a rifle until switched back to burst mode",
        "ammunition is interchangeable with submachinegun ammunition",
        "rifle and auto rifle magazines are interchangeable",
        "one combat round if the individual foregoes the benefit of evasion",
        "power packs are not interchangeable between the two weapons",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired ranged descriptions omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        ids = dict(connection.execute(
            """SELECT replace(rule_code,'equipment.weapon.',''),rule_id
               FROM rule_rule WHERE rule_code LIKE 'equipment.weapon.%'"""
        ).fetchall())
        for slug,*_ in WEAPONS:
            zero_g = slug in ("accelerator-rifle","snub-pistol")
            external = slug in ("laser-carbine","laser-pistol","laser-rifle")
            cable = slug in ("laser-carbine","laser-rifle")
            connection.execute(
                """INSERT INTO rule_book1_ranged_weapon_capability
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (ids[slug],zero_g,slug=="accelerator-rifle",
                 slug=="body-pistol",slug=="body-pistol",external,cable,
                 slug=="laser-carbine",2 if slug=="laser-carbine" else None))
        connection.execute(
            """INSERT INTO rule_book1_crossbow_reload_profile VALUES
               (%s,2,6,false),(%s,4,3,false),(%s,9,NULL,true)
               ON CONFLICT DO NOTHING""",
            (ids["crossbow"],ids["crossbow"],ids["crossbow"]))
        connection.execute(
            """INSERT INTO rule_book1_ranged_mode_switch
               VALUES (%s,'end-of-round-after-all-firing','rifle',1)
               ON CONFLICT DO NOTHING""", (ids["auto-rifle"],))
        connection.execute(
            """INSERT INTO rule_book1_revolver_reload_choice
               VALUES (%s,2,1,true) ON CONFLICT DO NOTHING""",
            (ids["revolver"],))
        for a,b,ammo,magazine in (
            ("auto-pistol","submachinegun",True,False),
            ("auto-rifle","rifle",True,True),
            ("laser-carbine","laser-rifle",False,False),
        ):
            first,second=sorted((ids[a],ids[b]))
            connection.execute(
                """INSERT INTO rule_book1_ammunition_compatibility
                   VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING""",
                (first,second,ammo,magazine))
    print("published operational capabilities for 18 ranged weapons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
