"""Import paired-source Sensory Aids capabilities for CE-EQUIP-020."""
import argparse
import os
import psycopg
import requests

from import_foundation_rules import ROOT, fetch, normalize

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
    session.headers["User-Agent"] = "BaseCepheus sensory capabilities/1.0"
    _, soup = fetch(session, URL)
    paired = (normalize(github), normalize(soup.get_text(" ")))
    for phrase in (
        "at tl 8 electronic enhancement allows images to be captured",
        "tl 12 pris", "from infrared to gamma rays",
        "last 3 days with continuous use",
        "wide cone of light up to 18 meters",
        "tight beam of light up to 36 meters",
        "illuminate a 10 meter radius",
        "last for about 6 hours of continuous use",
        "see exothermic (heat-emitting) sources in the dark",
        "anything less than total darkness",
        "clearly illuminates a 4.5 meter radius",
        "torch burns for 1 hour",
    ):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Sensory Aids sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        aids = dict(connection.execute(
            """SELECT sensory_aid_code,item_rule_id
               FROM inv_personal_sensory_aid_definition""").fetchall())
        capabilities = (
            ("torch","illumination",3600,False,False,False,False),
            ("oil-lamp","illumination",21600,False,False,False,False),
            ("binoculars","extended-viewing",None,None,False,False,True),
            ("electric-torch","illumination",21600,True,False,False,False),
            ("cold-light-lantern","illumination",259200,False,False,False,False),
            ("infrared-goggles","heat-vision",None,None,False,True,False),
            ("light-intensifier-goggles","amplified-vision",None,None,
             True,False,False),
        )
        for code, capability, duration, approximate, non_total, heat, unknown in capabilities:
            connection.execute(
                """INSERT INTO rule_personal_sensory_aid_capability
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (aids[code], capability, duration, approximate,
                 non_total, heat, unknown))
        modes = (
            ("torch","radial",1,6,12,None,None,False),
            ("oil-lamp","radial",2,4.5,9,None,None,False),
            ("electric-torch","wide-cone",5,None,None,18,6,False),
            ("electric-torch","tight-beam",None,None,None,36,1,True),
            ("electric-torch","area",None,10,None,None,None,True),
            ("cold-light-lantern","wide-cone",6,None,None,18,6,False),
            ("cold-light-lantern","tight-beam",6,None,None,36,1,False),
            ("cold-light-lantern","area",6,10,None,None,None,False),
        )
        for row in modes:
            code, mode, tech, clear, shadow, length, radius, unknown = row
            connection.execute(
                """INSERT INTO rule_personal_sensory_aid_illumination_mode
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT DO NOTHING""",
                (aids[code], mode, tech, clear, shadow, length, radius, unknown))
        binoculars = aids["binoculars"]
        connection.execute(
            """INSERT INTO rule_personal_binocular_upgrade VALUES
               (%s,8,750,true,true,false,NULL,NULL),
               (%s,12,3500,false,false,true,'infrared','gamma-rays')
               ON CONFLICT DO NOTHING""", (binoculars, binoculars))
    print("published 7 sensory capabilities, 8 light modes, and 2 upgrades")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
