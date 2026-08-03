"""Import paired-source Bribery offense mechanics."""
import argparse,os
import psycopg,requests
from import_foundation_rules import (GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator)
ROWS=(('petty','Petty Crime or Infraction',2,10),('minor','Misdemeanor, Minor Infraction',0,50),('serious','Serious Crime or Infraction',-2,100),('capital','Capital Crime or Infraction',-4,500))
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL')
 if not dsn:p.error('--dsn or BASE_CEPHEUS_DATABASE_URL is required')
 source=ROOT/'sources/cepheus-srd/src/book1/skills.md';github=source.read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus bribery/1.0';web,soup=fetch(s,SKILL_URL);texts=(normalize(github.decode()),normalize(soup.get_text(' ')))
 for phrase in ('bribery checks by offense','less than the minimum bribe required','second attempt at twice the previous value','brought up on charges of attempted bribery','cr200'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Bribery sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides={}
  for side,data,uri,kind,rev,media in (('github',github,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',web,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides[side]=(art,import_batch(c,pkg,art,sha256(data)))
  for order,(code,name,dm,mult) in enumerate(ROWS,1):
   rule=publish_rule(c,pkg,f'skill.bribery.offense.{code}',name,'skill','Bribery offense category and minimum offer.')
   payload={'offense_code':code,'check_modifier':dm,'minimum_bribe':'1D6','credits_per_die':mult,'maximum_attempts':2,'second_offer_multiplier':2}
   for side,(art,batch) in sides.items():
    loc=upsert_locator(c,works[side],art,'table_row','Skills > Bribery > Bribery Checks By Offense',f'bribery-{code}',name,order)
    cand,review=stage_candidate(c,batch,art,loc,'skill',f'skill.bribery.offense.{code}',payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
   c.execute("""INSERT INTO rule_bribery_offense VALUES(%s,%s,%s,1,6,%s,%s) ON CONFLICT(rule_id) DO UPDATE SET check_modifier=EXCLUDED.check_modifier,credits_per_die=EXCLUDED.credits_per_die""",(rule,code,dm,mult,order))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[1] for x in sides.values()],))
 print('published four paired-source Bribery offense rows');return 0
if __name__=='__main__':raise SystemExit(main())
