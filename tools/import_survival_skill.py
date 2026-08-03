"""Import paired-source Survival skill mechanics."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
OPS=('hunt-animals','trap-animals','avoid-exposure','locate-food','locate-fresh-water','produce-fire','find-shelter','avoid-dangerous-flora-fauna','avoid-getting-lost','handle-hazardous-climate');GATED={'locate-food','locate-fresh-water','produce-fire'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus survival/1.0';w,soup=fetch(s,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('hunting or trapping animals','avoiding exposure','food and fresh water if available','producing fires where possible','finding shelter','dangerous flora and fauna','avoiding getting lost','hazardous climates'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Survival sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.survival.mechanics';rule=publish_rule(c,pkg,code,'Survival Mechanics','skill','Wilderness sustenance, shelter, navigation, exposure, and hazard capabilities.');payload={'operations':list(OPS),'availability_gated':sorted(GATED),'difficulty':'referee-selected'}
  for side,art,batch in sides:
   loc=upsert_locator(c,works[side],art,'paragraph','Skills > Survival','survival-mechanics','Survival',0);cand,review=stage_candidate(c,batch,art,loc,'skill',code,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  skill=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.survival'",());c.execute("INSERT INTO rule_survival_mechanic VALUES(%s,%s) ON CONFLICT DO NOTHING",(rule,skill))
  for i,op in enumerate(OPS,1):c.execute("INSERT INTO rule_survival_operation VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING",(rule,op,op in GATED,i))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source Survival mechanics');return 0
if __name__=='__main__':raise SystemExit(main())
