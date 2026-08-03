"""Import paired-source Recon capabilities."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
OPS=(('scout-danger','observation'),('spot-threat','observation'),('spot-unusual-object','observation'),('spot-out-of-place-person','observation'),('remain-unseen','concealment'),('remain-unheard','concealment'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();session=requests.Session();session.headers['User-Agent']='BaseCepheus recon/1.0';w,soup=fetch(session,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('scout out dangers','spot threats','unusual objects','out of place people','staying unseen and unheard'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Recon sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.recon.mechanics';rule=publish_rule(c,pkg,code,'Recon Mechanics','skill','Scouting, observation, and unseen or unheard movement capabilities.');payload={'operations':[x[0] for x in OPS],'difficulty':'referee-selected','characteristic':'referee-selected','opposed_check_prescribed':False}
  for side,art,batch in sides:
   loc=upsert_locator(c,works[side],art,'paragraph','Skills > Recon','recon-mechanics','Recon',0);cand,review=stage_candidate(c,batch,art,loc,'skill',code,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  skill=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.recon'",());c.execute("INSERT INTO rule_recon_mechanic VALUES(%s,%s) ON CONFLICT(rule_id) DO NOTHING",(rule,skill))
  for i,(operation,group) in enumerate(OPS,1):c.execute("INSERT INTO rule_recon_operation VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",(rule,operation,group,i))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source Recon mechanics');return 0
if __name__=='__main__':raise SystemExit(main())
