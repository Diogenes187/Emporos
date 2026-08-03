"""Import paired-source Book 1 heavy weapon catalogue for CE-EQUIP-034."""
import argparse, os
import psycopg, requests
from import_foundation_rules import (
 GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch, normalize,
 publish_rule, sha256, stage_candidate, upsert_artifact, upsert_locator)
from import_ranged_weapons import EQUIPMENT_URL

SOURCE=ROOT/"sources/cepheus-srd/src/book1/equipment.md"
WEAPONS=(
 ("grenade-launcher","Grenade Launcher",7,400,6000,"1","shotgun",None,True,3),
 ("rocket-launcher","Rocket Launcher",7,2000,6000,"1","rocket",4,False,3),
 ("ram-grenade-launcher","RAM Grenade Launcher",8,800,6000,"1/3","assault-weapon",None,True,3),
 ("pgmp","PGMP",12,20000,10000,"1/4","rifle",10,True,2),
 ("fgmp","FGMP",14,100000,12000,"1/4","rifle",16,True,2))
AMMO=(
 ("grenade-launcher",7,180,500,6),("rocket-launcher",7,300,1000,1),
 ("ram-grenade-launcher",8,180,500,6),("pgmp",12,2500,6000,40),
 ("fgmp",14,65000,9000,40))

def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--dsn");a=p.parse_args()
 dsn=a.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
 if not dsn:p.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
 github=SOURCE.read_bytes();s=requests.Session();s.headers["User-Agent"]="BaseCepheus heavy weapons/1.0"
 website,soup=fetch(s,EQUIPMENT_URL);paired=(normalize(github.decode()),normalize(soup.get_text(" ")))
 for phrase in ("grenade launcher | 7 | 400 | 6 | 1 | ranged (shotgun) | by grenade",
  "rocket launcher | 7 | 2,000 | 6 | 1 | ranged (rocket) | 4d6",
  "ram grenade launcher | 8 | 800 | 6 | 1/3",
  "pgmp | 12 | 20,000 | 10 | 1/4 | ranged (rifle) | 10d6",
  "fgmp | 14 | 100,000 | 12 | 1/4 | ranged (rifle) | 16d6",
  "fgmp | 14 | 65,000 | 9 | 40"):
  if any(normalize(phrase) not in text for text in paired):
   raise ValueError(f"Paired heavy-weapon sources omit: {phrase}")
 with psycopg.connect(dsn) as c:
  package=get_id(c,"""SELECT content_package_id FROM sys_content_package
   WHERE package_code='cepheus-engine' AND package_version='9.1-draft'""",())
  works={side:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(code,))
   for side,code in (("github","cepheus-engine.github-v9.1"),("ogn","cepheus-engine.ogn"))}
  artifacts={}
  for side,data,uri,kind,revision,media in (
   ("github",github,"src/book1/equipment.md","repository_file",GITHUB_COMMIT,"text/markdown"),
   ("ogn",website,EQUIPMENT_URL,"web_page",None,"text/html")):
   art=upsert_artifact(c,works[side],kind,uri,revision,data,media)
   artifacts[side]=(art,import_batch(c,package,art,sha256(data)))
  ids={}
  for order,row in enumerate(WEAPONS,1):
   code,name,tl,cost,mass,rof,profile,dice,recoil,law=row
   rule_code=f"equipment.heavy-weapon.{code}"
   rule=publish_rule(c,package,rule_code,name,"equipment",f"Book 1 {name} heavy weapon.")
   ids[code]=rule
   c.execute("""INSERT INTO inv_item_definition VALUES (%s,'weapon',%s,%s,%s)
                ON CONFLICT (rule_id) DO NOTHING""",(rule,tl,cost,mass))
   c.execute("""INSERT INTO rule_book1_heavy_weapon VALUES
    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
    (rule,code,tl,cost,mass,profile,"fixed-dice" if dice else "selected-grenade",
     dice,6 if dice else None,recoil,law))
   values=[int(v) for v in rof.split("/")]
   c.execute("""INSERT INTO rule_book1_heavy_weapon_fire_profile VALUES (%s,1,%s)""",
             (rule,values[1] if len(values)>1 else None))
   for side in ("github","ogn"):
    art,batch=artifacts[side];loc=upsert_locator(c,works[side],art,"table_row",
     "Equipment > Weapons > Common Heavy Weapons",rule_code,rule_code,order)
    cand,review=stage_candidate(c,batch,art,loc,"book1_heavy_weapon",rule_code,
     {"code":code,"tl":tl,"cost":cost,"mass":mass,"rof":rof})
    add_provenance(c,rule,package,loc,cand,review,
     "direct" if side=="github" else "corroborating",side=="github")
  for order,(code,tl,cost,mass,rounds) in enumerate(AMMO,1):
   rule_code=f"equipment.heavy-ammunition.{code}"
   rule=publish_rule(c,package,rule_code,f"{dict((r[0],r[1]) for r in WEAPONS)[code]} Ammunition",
    "equipment",f"Book 1 {code} ammunition or power pack.")
   c.execute("""INSERT INTO inv_item_definition VALUES (%s,'equipment',%s,%s,%s)
                ON CONFLICT (rule_id) DO NOTHING""",(rule,tl,cost,mass))
   c.execute("""INSERT INTO rule_book1_heavy_ammunition
    VALUES (%s,%s,%s,%s,%s,%s,%s)""",(rule,ids[code],code,tl,cost,mass,rounds))
   for side in ("github","ogn"):
    art,batch=artifacts[side];loc=upsert_locator(c,works[side],art,"table_row",
     "Equipment > Weapons > Common Heavy Weapon Ammunition",rule_code,rule_code,order)
    cand,review=stage_candidate(c,batch,art,loc,"book1_heavy_ammunition",rule_code,
     {"weapon":code,"tl":tl,"cost":cost,"mass":mass,"rounds":rounds})
    add_provenance(c,rule,package,loc,cand,review,
     "direct" if side=="github" else "corroborating",side=="github")
  c.execute("""UPDATE src_import_batch SET batch_status='published',
   completed_at=COALESCE(completed_at,clock_timestamp())
   WHERE import_batch_id=ANY(%s)""",([v[1] for v in artifacts.values()],))
 print("published 5 heavy weapons and 5 ammunition profiles");return 0
if __name__=="__main__":raise SystemExit(main())
