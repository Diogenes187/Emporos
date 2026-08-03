"""Import paired-source opposed Liaison negotiation mechanics."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');github=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus liaison-negotiation/1.0';web,soup=fetch(s,SKILL_URL);texts=(normalize(github.decode()),normalize(soup.get_text(' ')))
 for phrase in ('influencing others','change others attitudes','participants roll opposed liaison checks','see who gains the advantage','two diplomats'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Liaison sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides={}
  for side,data,uri,kind,rev,media in (('github',github,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',web,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides[side]=(art,import_batch(c,pkg,art,sha256(data)))
  code='skill.liaison.negotiation';rule=publish_rule(c,pkg,code,'Opposed Liaison Negotiation','skill','Opposed Liaison checks determine who gains the negotiating advantage.');payload={'minimum_participants':2,'opposed_checks':True,'winner':'highest-total','ties':'referee-resolution'}
  for side,(art,batch) in sides.items():
   loc=upsert_locator(c,works[side],art,'paragraph','Skills > Liaison > Influencing Others','liaison-influencing-others','Influencing Others',0);cand,review=stage_candidate(c,batch,art,loc,'skill',code,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  skill=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.liaison'",());c.execute("INSERT INTO rule_liaison_negotiation VALUES(%s,%s,2,true,true,true) ON CONFLICT(rule_id) DO NOTHING",(rule,skill));c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([v[1] for v in sides.values()],))
 print('published paired-source opposed Liaison negotiation mechanics');return 0
if __name__=='__main__':raise SystemExit(main())
