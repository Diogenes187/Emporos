"""Import paired-source gameplay skill advancement."""
import argparse, os
import psycopg, requests
from import_foundation_rules import (GITHUB_COMMIT,ROOT,add_provenance,fetch,get_id,
 import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator)
SOURCE=ROOT/'sources/cepheus-srd/src/book1/skills.md'
URL='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-skills/'
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL')
 if not dsn:p.error('--dsn or BASE_CEPHEUS_DATABASE_URL is required')
 github=SOURCE.read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus skill-training/1.0';web,soup=fetch(s,URL)
 paired=(normalize(github.decode()),normalize(soup.get_text(' ')))
 for phrase in ('skill total is calculated by summing the levels of each skill','current skill total plus the desired level','only train one skill in a given week','jack of all trades skill cannot be learned'):
  if any(normalize(phrase) not in x for x in paired):raise ValueError(f'Paired skill sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",())
  works={'github':get_id(c,"SELECT source_work_id FROM src_work WHERE work_code='cepheus-engine.github-v9.1'",()),'ogn':get_id(c,"SELECT source_work_id FROM src_work WHERE work_code='cepheus-engine.ogn'",())}
  sides={}
  for side,data,uri,kind,rev,media in (('github',github,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',web,URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides[side]=(art,import_batch(c,pkg,art,sha256(data)))
  rule=publish_rule(c,pkg,'skill.gameplay-training','Gameplay Skill Training','skill','Training time and advancement during play.')
  payload={'skill_total':'sum of skill levels; zero counts as zero','required_weeks':'skill total + desired level','new_level_zero_minimum_weeks':1,'skills_per_week':1,'forbidden_skill':'skill.jack-of-all-trades'}
  for side,(art,batch) in sides.items():
   loc=upsert_locator(c,works[side],art,'heading','Gaining New Skill Levels during Game Play','gameplay-skill-training','Gaining New Skill Levels during Game Play',0)
   cand,review=stage_candidate(c,batch,art,loc,'skill','skill.gameplay-training',payload)
   add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  jot=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.jack-of-all-trades'",())
  c.execute("""INSERT INTO rule_gameplay_skill_training VALUES (%s,false,'desired_level',1,1,%s)
    ON CONFLICT(rule_id) DO UPDATE SET forbidden_skill_rule_id=EXCLUDED.forbidden_skill_rule_id""",(rule,jot))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([v[1] for v in sides.values()],))
 print('published paired-source gameplay skill training')
 return 0
if __name__=='__main__':raise SystemExit(main())
