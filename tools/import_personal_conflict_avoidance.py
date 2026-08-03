"""Import paired-source asymmetric-awareness conflict avoidance."""
import argparse,os,psycopg,requests
from import_foundation_rules import (GITHUB_COMMIT,ROOT,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator)
SOURCE=ROOT/"sources/cepheus-srd/src/book1/personal-combat.md"
URL="https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-personal-combat/"
def main():
 p=argparse.ArgumentParser();p.add_argument("--dsn");a=p.parse_args();dsn=a.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
 if not dsn:p.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
 github=SOURCE.read_bytes();s=requests.Session();s.headers["User-Agent"]="BaseCepheus avoidance importer/1.0";website,soup=fetch(s,URL)
 phrase="characters that are aware of a group, and that group is unaware of them, may elect to avoid conflict entirely"
 if any(normalize(phrase) not in normalize(x) for x in (github.decode(),soup.get_text(" "))):raise ValueError("Paired sources omit conflict avoidance")
 with psycopg.connect(dsn) as c:
  package=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",())
  works={side:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(code,)) for side,code in (("github","cepheus-engine.github-v9.1"),("ogn","cepheus-engine.ogn"))};arts={}
  for side,data,uri,kind,rev,media in (("github",github,"src/book1/personal-combat.md","repository_file",GITHUB_COMMIT,"text/markdown"),("ogn",website,URL,"web_page",None,"text/html")):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);arts[side]=(art,import_batch(c,package,art,sha256(data)))
  rule=publish_rule(c,package,"combat.conflict-avoidance","Conflict Avoidance","combat","An aware group unseen by its opponents may avoid conflict.")
  payload={"avoiding_group_must_be_aware":True,"opposing_group_must_be_unaware":True,"voluntary":True,"ends_conflict":True}
  for side in ("github","ogn"):
   art,batch=arts[side];loc=upsert_locator(c,works[side],art,"paragraph","Personal Combat > Initiative","personal-conflict-avoidance","Conflict Avoidance",0);cand,review=stage_candidate(c,batch,art,loc,"combat","combat.conflict-avoidance",payload);add_provenance(c,rule,package,loc,cand,review,"direct" if side=="ogn" else "corroborating",side=="ogn")
  c.execute("INSERT INTO rule_personal_conflict_avoidance VALUES(%s,true,true,true,true) ON CONFLICT(rule_id) DO NOTHING",(rule,));c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[1] for x in arts.values()],))
 print("published paired-source conflict avoidance")
 return 0
if __name__=="__main__":raise SystemExit(main())
