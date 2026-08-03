"""Import paired-source Dodge and weapon-bound Parry mechanics."""
import argparse
import os
import psycopg
import requests
from import_foundation_rules import (
    GITHUB_COMMIT,ROOT,add_provenance,fetch,get_id,import_batch,normalize,
    publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator)

SOURCE=ROOT/"sources/cepheus-srd/src/book1/personal-combat.md"
URL=("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
     "cepheus-engine-personal-combat/")

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--dsn"); args=parser.parse_args()
    dsn=args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn: parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github=SOURCE.read_bytes(); session=requests.Session()
    session.headers["User-Agent"]="BaseCepheus dodge-parry importer/1.0"
    website,soup=fetch(session,URL)
    paired=(normalize(github.decode()),normalize(soup.get_text(" ")))
    for phrase in ("being attacked may dodge","being attacked in melee can parry",
                   "defender's appropriate melee skill"):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired reaction sources omit: {phrase}")
    with psycopg.connect(dsn) as connection:
        package=get_id(connection,"""SELECT content_package_id FROM sys_content_package
          WHERE package_code='cepheus-engine' AND package_version='9.1-draft'""",())
        works={side:get_id(connection,"SELECT source_work_id FROM src_work WHERE work_code=%s",(code,))
               for side,code in (("github","cepheus-engine.github-v9.1"),("ogn","cepheus-engine.ogn"))}
        artifacts={}
        for side,data,uri,kind,revision,media in (
          ("github",github,"src/book1/personal-combat.md","repository_file",GITHUB_COMMIT,"text/markdown"),
          ("ogn",website,URL,"web_page",None,"text/html")):
            artifact=upsert_artifact(connection,works[side],kind,uri,revision,data,media)
            artifacts[side]=(artifact,import_batch(connection,package,artifact,sha256(data)))
        rows=(("dodge","Dodge",-1,-2,False,False,False),
              ("parry","Parry",None,None,True,True,True))
        for order,row in enumerate(rows,1):
            kind,name,modifier,cover,melee,weapon_bound,uses_skill=row
            code=f"combat.reaction.{kind}"
            rule=publish_rule(connection,package,code,name,"combat",
                              f"Source-defined {name.lower()} reaction.")
            payload={"reaction_kind":kind,"attack_modifier":modifier,
                     "cover_attack_modifier":cover,"melee_attack_only":melee,
                     "weapon_bound":weapon_bound,
                     "uses_weapon_supported_melee_skill":uses_skill}
            for side in ("github","ogn"):
                artifact,batch=artifacts[side]
                locator=upsert_locator(connection,works[side],artifact,"heading",
                    f"Personal Combat > Reactions > {name}",f"personal-{kind}",name,order)
                candidate,review=stage_candidate(connection,batch,artifact,locator,"combat",code,payload)
                add_provenance(connection,rule,package,locator,candidate,review,
                    "direct" if side=="ogn" else "corroborating",side=="ogn")
            connection.execute("""INSERT INTO rule_personal_reaction_option
              VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (rule_id) DO UPDATE SET
              reaction_kind=EXCLUDED.reaction_kind,attack_modifier=EXCLUDED.attack_modifier,
              cover_attack_modifier=EXCLUDED.cover_attack_modifier,
              melee_attack_only=EXCLUDED.melee_attack_only,weapon_bound=EXCLUDED.weapon_bound,
              uses_weapon_supported_melee_skill=EXCLUDED.uses_weapon_supported_melee_skill""",
              (rule,kind,modifier,cover,melee,weapon_bound,uses_skill))
        connection.execute("""UPDATE src_import_batch SET batch_status='published',
          completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)""",
          ([x[1] for x in artifacts.values()],))
    print("published paired-source Dodge and weapon-bound Parry mechanics")
    return 0
if __name__=="__main__": raise SystemExit(main())
