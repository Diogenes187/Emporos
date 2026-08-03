"""Import paired-source Navigation mechanics."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();session=requests.Session();session.headers['User-Agent']='BaseCepheus navigation/1.0';w,soup=fetch(session,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('new location after a jump ends','plotting a standard course through normal space','plotting a jump route through jump space','cannot make a jump safely without a jump route'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Navigation sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.navigation.mechanics';rule=publish_rule(c,pkg,code,'Navigation Mechanics','skill','Position fixing, normal and Jump course plotting, and the safe-Jump route requirement.');payload={'determine_post_jump_location':True,'plot_normal_space_course':True,'plot_jump_route':True,'safe_jump_requires_route':True}
  for side,art,batch in sides:
   loc=upsert_locator(c,works[side],art,'paragraph','Skills > Navigation','navigation-mechanics','Navigation',0);cand,review=stage_candidate(c,batch,art,loc,'skill',code,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  skill=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.navigation'",());c.execute("INSERT INTO rule_navigation_mechanic VALUES(%s,%s,true,true,true,true) ON CONFLICT(rule_id) DO NOTHING",(rule,skill));c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source Navigation mechanics');return 0
if __name__=='__main__':raise SystemExit(main())
