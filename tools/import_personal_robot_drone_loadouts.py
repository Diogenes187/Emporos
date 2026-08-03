"""Import paired-source robot/drone loadouts for CE-EQUIP-017."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import ROOT, fetch, get_id, normalize

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-equipment/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github = SOURCE.read_text()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus robot loadouts/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "specialized model 1 computer", "intellect/1",
        "expert mechanics/2", "every sensor available at tl 11 and below",
        "operating range of five hundred kilometers",
        "fly at a speed of 300 kph", "medicine/2",
        "must be piloted with the comms skill",
        "attacks are made using the appropriate weapon skill",
        "expert liaison/2 and translator/1 available",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired robot loadout sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        chassis = dict(connection.execute(
            """SELECT chassis_code,item_rule_id
               FROM inv_personal_robot_drone_chassis""").fetchall())
        skills = {code: get_id(connection,
            "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (code,))
            for code in (
                "skill.comms","skill.mechanics","skill.medicine",
                "skill.steward","skill.natural-weapons",
                "skill.slashing-weapons","skill.engineering",
                "skill.carousing","skill.gambling")}
        software = dict(connection.execute(
            """SELECT software_code,rule_id
               FROM rule_personal_software_family""").fetchall())
        systems = {
            "cargo-robot": (("huge",None,None),("specialized-model-1",None,None)),
            "repair-robot": (("mechanical-toolkit",None,None),("specialized-model-1",None,None)),
            "personal-drone": (("tiny",None,None),("comm-audio-visual",None,None),
                ("grav-floater",None,None),("holographic-projector",11,None)),
            "probe-drone": (("comm-audio-visual",None,None),("grav-belt",None,None),
                ("holographic-projector",11,None),("all-sensors",11,"tl-at-or-below")),
            "autodoc": (("medikit",12,None),("specialized-model-1",None,None)),
            "combat-drone": (("grav-floater",None,None),("integral-weapon",None,"any")),
            "servitor": (("computer-model-3",None,None),),
        }
        for code, rows in systems.items():
            for system_code, tech, scope in rows:
                connection.execute(
                    """INSERT INTO inv_personal_robot_drone_system
                       VALUES (%s,%s,%s,1,%s) ON CONFLICT DO NOTHING""",
                    (chassis[code], system_code, tech, scope))
        programs = (
            ("cargo-robot",1,"intellect","Intellect",1,None,None,"installed",None),
            ("cargo-robot",2,"expert","Expert",1,None,"appropriate skill","installed",None),
            ("repair-robot",1,"intellect","Intellect",1,None,None,"installed",None),
            ("repair-robot",2,"expert","Expert",2,"skill.mechanics","Mechanics","installed",None),
            ("repair-robot",3,"expert","Expert",2,"skill.engineering","Engineering","alternative",2),
            ("autodoc",1,"intellect","Intellect",1,None,None,"installed",None),
            ("autodoc",2,None,"Medicine",2,"skill.medicine","Medicine","installed",None),
            ("servitor",1,"intellect","Intellect",1,None,None,"installed",None),
            ("servitor",2,"expert","Expert",2,"skill.steward","Steward","installed",None),
            ("servitor",3,"expert","Expert",2,None,"Liaison","available-on-demand",None),
            ("servitor",4,"translator","Translator",1,None,None,"available-on-demand",None),
            ("servitor",5,"expert","Expert",None,"skill.carousing","Carousing","reprogram-option",None),
            ("servitor",6,"expert","Expert",None,"skill.gambling","Gambling","reprogram-option",None),
        )
        for code, order, family, name, rating, skill_code, label, status, alternative in programs:
            connection.execute(
                """INSERT INTO inv_personal_robot_drone_program
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (chassis[code], order, software.get(family), name, rating,
                 skills.get(skill_code), label, status, alternative))
        weapons = (
            ("cargo-robot",1,"Crushing Strength","Natural Weapons",
             "skill.natural-weapons",3,6,False),
            ("repair-robot",1,"Tools","Natural Weapons",
             "skill.natural-weapons",1,6,False),
            ("autodoc",1,"Surgical Tools","Slashing Weapons",
             "skill.slashing-weapons",1,6,False),
            ("combat-drone",1,"Any gun","appropriate weapon skill",
             None,None,None,True),
            ("servitor",1,"Robot Punch","Natural Weapons",
             "skill.natural-weapons",1,6,False),
        )
        for code, order, name, printed, skill_code, dice, sides, open_slot in weapons:
            connection.execute(
                """INSERT INTO inv_personal_robot_drone_weapon
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (chassis[code], order, name, printed, skills.get(skill_code),
                 dice, sides, open_slot))
        connection.execute(
            """INSERT INTO rule_personal_robot_drone_mobility
               VALUES (%s,500,300) ON CONFLICT DO NOTHING""",
            (chassis["probe-drone"],))
        connection.execute(
            """INSERT INTO rule_personal_combat_drone_operation
               VALUES (%s,%s,true,true,true) ON CONFLICT DO NOTHING""",
            (chassis["combat-drone"], skills["skill.comms"]))
    print("published robot/drone systems, programs, weapons, and operation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
