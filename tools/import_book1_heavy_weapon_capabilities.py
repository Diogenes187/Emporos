"""Import paired Book 1 heavy weapon capabilities for CE-EQUIP-035."""
import argparse,os
import psycopg,requests
from import_foundation_rules import ROOT,fetch,normalize
from import_ranged_weapons import EQUIPMENT_URL
SOURCE=ROOT/"sources/cepheus-srd/src/book1/equipment.md"
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--dsn");a=p.parse_args()
 dsn=a.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
 if not dsn:p.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
 s=requests.Session();s.headers["User-Agent"]="BaseCepheus heavy capabilities/1.0"
 _,soup=fetch(s,EQUIPMENT_URL);paired=(normalize(SOURCE.read_text()),normalize(soup.get_text(" ")))
 for phrase in ("minimum strength 9","each firing of an fgmp emits 2d6 x 20 rads",
  "not interchangeable with handheld grenades","strength of 12 or more",
  "every point by which a user",
  "cannot fire in burst mode","takes two minor actions to reload",
  "up to 1.5 meters behind a rocket launcher","takes 3d6 damage",
  "vehicle-mounted rocket launchers lose this side-effect",
  "takes three minor actions to reload","do not add the effect",
  "50% chance (4+ on 1d6)","6 effect meters away in a random direction"):
  if any(normalize(phrase) not in text for text in paired):
   raise ValueError(f"Paired heavy-weapon descriptions omit: {phrase}")
 with psycopg.connect(dsn) as c:
  ids=dict(c.execute("SELECT weapon_code,rule_id FROM rule_book1_heavy_weapon").fetchall())
  rows={
   "grenade-launcher":(None,None,False,None,False,False,None,None,None,False,None,None,None,None,False),
   "ram-grenade-launcher":(None,None,False,2,False,True,False,None,None,False,None,None,None,None,False),
   "rocket-launcher":(None,None,False,3,None,False,None,1.5,3,True,None,None,None,None,False),
   "pgmp":(12,-1,False,None,None,False,None,None,None,False,None,None,None,None,False),
   "fgmp":(9,None,True,None,None,False,None,None,None,False,2,6,20,True,True)}
  for code,values in rows.items():
   c.execute("""INSERT INTO rule_book1_heavy_weapon_capability
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(ids[code],*values))
  c.execute("""INSERT INTO rule_book1_rocket_impact
   VALUES (%s,false,6,6,4,6,-1,true,true)""",(ids["rocket-launcher"],))
 print("published operational capabilities for 5 heavy weapons");return 0
if __name__=="__main__":raise SystemExit(main())
