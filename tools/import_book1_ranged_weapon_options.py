"""Import paired-source ranged weapon options for CE-EQUIP-032."""
import argparse
import os
import psycopg
import requests
from import_foundation_rules import (
 GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch, normalize,
 publish_rule, sha256, stage_candidate, upsert_artifact, upsert_locator)
from import_ranged_weapons import EQUIPMENT_URL, WEAPONS

SOURCE = ROOT / "sources/cepheus-srd/src/book1/equipment.md"
OPTIONS = (
 ("shoulder-stocks","Shoulder Stocks",5,75,1000),
 ("folding-stocks","Folding Stocks",6,100,500),
 ("telescopic-sights","Telescopic Sights",6,200,800),
 ("grenade-launcher","Grenade Launcher",8,1000,None),
 ("laser-sights","Laser Sights",8,200,1500),
 ("silencer","Silencer",8,250,None),
 ("gyrostabilizer","Gyrostabilizer",9,300,None),
 ("laser-telescopic-sights","Laser Telescopic Sights",9,3000,1800),
 ("secure-weapon","Secure Weapon",10,100,None),
 ("intelligent-weapon","Intelligent Weapon",11,1000,None))

def main() -> int:
 parser=argparse.ArgumentParser(); parser.add_argument("--dsn"); args=parser.parse_args()
 dsn=args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
 if not dsn: parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
 session=requests.Session(); session.headers["User-Agent"]="BaseCepheus ranged options/1.0"
 github=SOURCE.read_bytes(); website,soup=fetch(session,EQUIPMENT_URL)
 paired=(normalize(github.decode()),normalize(soup.get_text(" ")))
 for phrase in ("reduce the overall length of the weapon by 300mm",
  "takes four minor actions to reload","reducing the recoil penalty by one point",
  "the tl 13 upgrade adds model /1","laser sights give an extra +1 dm bonus",
  "requires authentication in some fashion",
  "attaching the stock (or detaching it) requires five combat rounds",
  "rof 4 or less","will always miss","laser sights | 8 | cr100 | 1.5"):
  if any(normalize(phrase) not in text for text in paired):
   raise ValueError(f"Paired ranged-option sources omit: {phrase}")
 with psycopg.connect(dsn) as connection:
  package=get_id(connection,"""SELECT content_package_id FROM sys_content_package
   WHERE package_code='cepheus-engine' AND package_version='9.1-draft'""",())
  works={side:get_id(connection,"SELECT source_work_id FROM src_work WHERE work_code=%s",
                    (code,)) for side,code in
         (("github","cepheus-engine.github-v9.1"),("ogn","cepheus-engine.ogn"))}
  artifacts={}
  for side,data,uri,kind,revision,media in (
   ("github",github,"src/book1/equipment.md","repository_file",GITHUB_COMMIT,"text/markdown"),
   ("ogn",website,EQUIPMENT_URL,"web_page",None,"text/html")):
   artifact=upsert_artifact(connection,works[side],kind,uri,revision,data,media)
   artifacts[side]=(artifact,import_batch(connection,package,artifact,sha256(data)))
  weapons=dict(connection.execute(
   """SELECT replace(rule_code,'equipment.weapon.',''),rule_id
      FROM rule_rule WHERE rule_code LIKE 'equipment.weapon.%'""").fetchall())
  option_ids={}
  for order,(code,name,tl,cost,mass) in enumerate(OPTIONS,1):
   rule_code=f"equipment.weapon-option.{code}"
   rule=publish_rule(connection,package,rule_code,name,"equipment",
                     f"Book 1 {name} ranged weapon option.")
   option_ids[code]=rule
   connection.execute("""INSERT INTO inv_item_definition VALUES (%s,'equipment',%s,%s,%s)
                         ON CONFLICT (rule_id) DO NOTHING""",(rule,tl,cost,mass))
   connection.execute("""INSERT INTO rule_book1_ranged_weapon_option
                         VALUES (%s,%s,%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""",
                      (rule,code,tl,cost,mass,100 if code=="laser-sights" else None))
   for side in ("github","ogn"):
    artifact,batch=artifacts[side]
    locator=upsert_locator(connection,works[side],artifact,"heading",
      "Equipment > Weapons > Ranged Weapon Options",rule_code,rule_code,order)
    candidate,review=stage_candidate(connection,batch,artifact,locator,
      "book1_ranged_weapon_option",rule_code,
      {"option_code":code,"tl":tl,"canonical_cost":cost,"mass_grams":mass})
    add_provenance(connection,rule,package,locator,candidate,review,
                   "direct" if side=="github" else "corroborating",
                   side=="github")
  effects={
   "folding-stocks":(300,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,False),
   "grenade-launcher":(None,1,4,False,None,None,None,None,None,None,None,None,None,None,None,None,None,None,False),
   "gyrostabilizer":(None,None,None,None,1,-1,None,None,None,None,None,None,None,None,None,None,None,None,False),
   "intelligent-weapon":(None,None,None,None,None,None,0,None,None,None,None,None,None,None,None,None,None,None,False),
   "laser-sights":(None,None,None,None,None,None,None,1,10,None,None,None,None,None,None,None,None,None,False),
   "laser-telescopic-sights":(None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,True),
   "secure-weapon":(None,None,None,None,None,None,None,None,None,True,None,None,None,None,None,None,None,None,False),
   "shoulder-stocks":(None,None,None,None,None,None,None,None,None,None,"shotgun",5,True,None,None,None,None,None,False),
   "silencer":(None,None,None,None,None,None,None,None,None,None,None,None,None,-4,None,None,None,None,False),
   "telescopic-sights":(None,None,None,None,None,None,None,1,None,None,None,None,None,None,8,2,6,True,True)}
  for code,values in effects.items():
   connection.execute("""INSERT INTO rule_book1_ranged_weapon_option_effect
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
    (option_ids[code],*values))
  connection.execute("""INSERT INTO rule_book1_ranged_weapon_option_upgrade
                        VALUES (%s,13,5000,1,false),(%s,10,100,NULL,true)""",
                     (option_ids["intelligent-weapon"],option_ids["laser-sights"]))
  all_weapons=set(weapons); profiles={r[0]:r[6] for r in WEAPONS}
  recoil={r[0]:r[9] for r in WEAPONS}; rof={r[0]:[int(v) for v in r[5].split("/")] for r in WEAPONS}
  eligible={
   "shoulder-stocks":{"auto-pistol","body-pistol","laser-pistol","revolver","snub-pistol"},
   "folding-stocks":{s for s,p in profiles.items() if p in {"rifle","shotgun"}},
   "grenade-launcher":{s for s,p in profiles.items() if p=="rifle"},
   "gyrostabilizer":{s for s,v in recoil.items() if v},
   "silencer":{s for s,v in rof.items() if max(v)<=4 and not s.startswith("laser-")
               and s not in {"accelerator-rifle","gauss-rifle"}}}
  for code in ("intelligent-weapon","laser-sights","laser-telescopic-sights",
               "secure-weapon","telescopic-sights"): eligible[code]=all_weapons
  for code,slugs in eligible.items():
   connection.cursor().executemany(
    """INSERT INTO rule_book1_ranged_weapon_option_eligibility
       VALUES (%s,%s) ON CONFLICT DO NOTHING""",
    [(option_ids[code],weapons[s]) for s in sorted(slugs)])
  connection.execute("""UPDATE src_import_batch SET batch_status='published',
   completed_at=COALESCE(completed_at,clock_timestamp())
   WHERE import_batch_id=ANY(%s)""",([v[1] for v in artifacts.values()],))
 print("published 10 ranged weapon options and operational eligibility"); return 0
if __name__=="__main__": raise SystemExit(main())
