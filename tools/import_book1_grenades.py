"""Import paired-source Book 1 grenades for CE-EQUIP-033."""
import argparse
import os
import psycopg
import requests
from import_foundation_rules import (
 GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch, normalize,
 publish_rule, sha256, stage_candidate, upsert_artifact, upsert_locator)
from import_ranged_weapons import EQUIPMENT_URL

SOURCE=ROOT/"sources/cepheus-srd/src/book1/equipment.md"
GRENADES=(("frag","Frag",6,180,"blast-damage"),
 ("smoke","Smoke",6,90,"obscurant"),("aerosol","Aerosol",9,90,"laser-diffusion"),
 ("stun","Stun",9,180,"stun"))

def main()->int:
 parser=argparse.ArgumentParser(); parser.add_argument("--dsn"); args=parser.parse_args()
 dsn=args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
 if not dsn: parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
 github=SOURCE.read_bytes(); session=requests.Session()
 session.headers["User-Agent"]="BaseCepheus grenades/1.0"
 website,soup=fetch(session,EQUIPMENT_URL)
 paired=(normalize(github.decode()),normalize(soup.get_text(" ")))
 for phrase in ("price in credits (cr) for a case of six grenades",
  "weight per grenade","frag | 6 | 180 | 0.5 | 5d6/3d6/1d6",
  "mist six meters in radius","laser attack made through the mist has its damage reduced by 10",
  "laser communications through the mist are completely blocked",
  "all attacks within or through the cloud","doubled for laser weapons",
  "mist dissipates in 1d6","negative dm equal to the damage",
  "if this endurance check is failed the character is knocked unconscious"):
  if any(normalize(phrase) not in text for text in paired):
   raise ValueError(f"Paired grenade sources omit: {phrase}")
 with psycopg.connect(dsn) as connection:
  package=get_id(connection,"""SELECT content_package_id FROM sys_content_package
   WHERE package_code='cepheus-engine' AND package_version='9.1-draft'""",())
  works={s:get_id(connection,"SELECT source_work_id FROM src_work WHERE work_code=%s",(c,))
   for s,c in (("github","cepheus-engine.github-v9.1"),("ogn","cepheus-engine.ogn"))}
  artifacts={}
  for side,data,uri,kind,revision,media in (
   ("github",github,"src/book1/equipment.md","repository_file",GITHUB_COMMIT,"text/markdown"),
   ("ogn",website,EQUIPMENT_URL,"web_page",None,"text/html")):
   artifact=upsert_artifact(connection,works[side],kind,uri,revision,data,media)
   artifacts[side]=(artifact,import_batch(connection,package,artifact,sha256(data)))
  ids={}
  for order,(code,name,tl,cost,kind) in enumerate(GRENADES,1):
   rule_code=f"equipment.grenade.{code}"
   rule=publish_rule(connection,package,rule_code,name,"equipment",f"Book 1 {name} grenade.")
   ids[code]=rule
   connection.execute("""INSERT INTO inv_item_definition
    VALUES (%s,'weapon',%s,%s,500) ON CONFLICT (rule_id) DO NOTHING""",(rule,tl,cost))
   connection.execute("""INSERT INTO rule_book1_grenade
    VALUES (%s,%s,%s,%s,6,500,1,%s)""",(rule,code,tl,cost,kind))
   connection.execute("""INSERT INTO rule_book1_grenade_delivery_mode VALUES
    (%s,'thrown','thrown'),(%s,'launcher','shotgun')""",(rule,rule))
   for side in ("github","ogn"):
    artifact,batch=artifacts[side]
    locator=upsert_locator(connection,works[side],artifact,"table_row",
     "Equipment > Weapons > Grenades",rule_code,rule_code,order)
    candidate,review=stage_candidate(connection,batch,artifact,locator,
     "book1_grenade",rule_code,{"code":code,"tl":tl,"case_cost":cost})
    add_provenance(connection,rule,package,locator,candidate,review,
     "direct" if side=="github" else "corroborating",side=="github")
  connection.execute("""INSERT INTO rule_book1_frag_grenade_damage_band VALUES
   (%s,3,5,6),(%s,6,3,6),(%s,9,1,6)""",(ids["frag"],)*3)
  connection.execute("""INSERT INTO rule_book1_grenade_field_effect VALUES
   (%s,6,1,6,3,-2,-4,NULL,true,false,true),
   (%s,6,1,6,3,NULL,NULL,10,false,true,true)""",(ids["smoke"],ids["aerosol"]))
  endurance=get_id(connection,"SELECT rule_id FROM rule_rule WHERE rule_code='characteristic.endurance'",())
  connection.execute("""INSERT INTO rule_book1_stun_grenade_effect
   VALUES (%s,6,3,6,%s,true,true,true,false)""",(ids["stun"],endurance))
  connection.execute("""UPDATE src_import_batch SET batch_status='published',
   completed_at=COALESCE(completed_at,clock_timestamp())
   WHERE import_batch_id=ANY(%s)""",([v[1] for v in artifacts.values()],))
 print("published 4 Book 1 grenades and typed effects"); return 0
if __name__=="__main__": raise SystemExit(main())
