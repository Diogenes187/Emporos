"""Import paired-source Fighting in Zero Gravity and CE-COMBAT-008."""
import argparse
import os
import psycopg
import requests
from import_foundation_rules import (
    GITHUB_COMMIT,ROOT,add_provenance,fetch,get_id,import_batch,normalize,
    publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator,
)
SOURCE=ROOT/"sources/cepheus-srd/src/book1/personal-combat.md"
URL=("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
     "cepheus-engine-personal-combat/")
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--dsn")
    args=parser.parse_args()
    dsn=args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn: parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    github=SOURCE.read_bytes(); session=requests.Session()
    session.headers["User-Agent"]="BaseCepheus zero-gravity importer/1.0"
    website,soup=fetch(session,URL)
    paired=(normalize(github.decode()),normalize(soup.get_text(" ")))
    for phrase in ("limited to lower","treated as unskilled",
                   "weapons with recoil suffer a dm -2"):
        if any(normalize(phrase) not in text for text in paired):
            raise ValueError(f"Paired Zero Gravity sources omit: {phrase}")
    with psycopg.connect(dsn) as c:
        package=get_id(c,"SELECT content_package_id FROM sys_content_package "
            "WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",())
        works={side:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",
            (code,)) for side,code in (("github","cepheus-engine.github-v9.1"),
                                      ("ogn","cepheus-engine.ogn"))}
        artifacts={}
        for side,data,uri,kind,revision,media in (
            ("github",github,"src/book1/personal-combat.md","repository_file",
             GITHUB_COMMIT,"text/markdown"),
            ("ogn",website,URL,"web_page",None,"text/html")):
            artifact=upsert_artifact(c,works[side],kind,uri,revision,data,media)
            artifacts[side]=(artifact,import_batch(c,package,artifact,sha256(data)))
        rule=publish_rule(c,package,"combat.zero-gravity","Fighting in Zero Gravity",
            "combat","Zero-G caps combat skill; recoil weapons receive DM-2.")
        payload={"skill_cap":"lower","missing_zero_g":"untrained",
                 "recoil_attack_modifier":-2}
        for side in ("github","ogn"):
            artifact,batch=artifacts[side]
            locator=upsert_locator(c,works[side],artifact,"heading",
                "Personal Combat > Fighting in Zero Gravity",
                "personal-zero-gravity","Fighting in Zero Gravity",0)
            candidate,review=stage_candidate(c,batch,artifact,locator,"combat",
                "combat.zero-gravity",payload)
            add_provenance(c,rule,package,locator,candidate,review,
                "direct" if side=="github" else "corroborating",side=="github")
        zero=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.zero-g'",())
        c.execute("INSERT INTO rule_personal_zero_gravity_combat VALUES "
                  "(%s,%s,true,true,-2) ON CONFLICT DO NOTHING",(rule,zero))
        c.execute("""INSERT INTO rule_interpretation
          (rule_id,interpretation_type,rationale,decision_register_entry)
          VALUES (%s,'agreed_interpretation',%s,'CE-COMBAT-008')
          ON CONFLICT DO NOTHING""",(rule,"Missing Zero-G uses the applicable "
          "combat skill untrained modifier; Level 0 counts as trained."))
        c.execute("UPDATE src_import_batch SET batch_status='published',"
                  "completed_at=COALESCE(completed_at,clock_timestamp()) "
                  "WHERE import_batch_id=ANY(%s)",
                  ([value[1] for value in artifacts.values()],))
    print("published Fighting in Zero Gravity and CE-COMBAT-008")
if __name__=="__main__": raise SystemExit(main())
