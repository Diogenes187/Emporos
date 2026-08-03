"""Import paired-source Farming, Riding, and Veterinary Medicine operations."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
ROWS=(('grow-crops','farming','farming',False,False),('harvest-crops','farming','farming',False,False),('raise-animals','farming','farming',False,False),('hydroponic-farming','farming','farming',False,True),('clone-harvesting','farming','farming',False,True),('maneuver-riding-animal','riding','riding',True,False),('routine-riding-care','riding','riding',True,False),('emergency-animal-care','veterinary','veterinary-medicine',True,False),('short-term-animal-care','veterinary','veterinary-medicine',True,False),('long-term-animal-care','veterinary','veterinary-medicine',True,False),('treat-animal-disease','veterinary','veterinary-medicine',True,False),('treat-animal-poison','veterinary','veterinary-medicine',True,False),('treat-animal-injury','veterinary','veterinary-medicine',True,False))
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus animal skills/1.0';w,soup=fetch(s,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('grow and harvest crops and raise animals','hydroponic farming and clone harvesting','properly maneuver and provide basic, routine care','emergency care, short term care, long-term care','diseases, poisons and debilitating injuries'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired animal-skill sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.animal.operations';rule=publish_rule(c,pkg,code,'Animal Skill Operations','skill','Farming, Riding, and Veterinary Medicine operation boundaries.');payload={'operations':[r[0] for r in ROWS],'fixed_difficulties':False,'fixed_outcome_amounts':False}
  for side,art,batch in sides:
   for order,heading in enumerate(('Farming','Riding','Veterinary Medicine')):
    section=heading.lower().replace(' ','-');loc=upsert_locator(c,works[side],art,'paragraph','Skills > '+heading,'animal-skill-'+section,heading,order);cand,review=stage_candidate(c,batch,art,loc,'skill',code+'.'+section,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  c.execute("INSERT INTO rule_animal_skill_operation_mechanic VALUES(%s) ON CONFLICT DO NOTHING",(rule,))
  for i,(op,domain,skill,subject,high_tech) in enumerate(ROWS,1):sid=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code=%s",('skill.'+skill,));c.execute("INSERT INTO rule_animal_skill_operation VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",(rule,op,domain,sid,subject,high_tech,i))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source animal skill operations');return 0
if __name__=='__main__':raise SystemExit(main())
