"""Import paired-source Admin and Advocate mechanics."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
OPS=('avoid-police-harassment','expedite-license','secure-application-approval','avoid-close-paper-inspection','deal-with-bureaucrat','pass-ship-inspection')
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();session=requests.Session();session.headers['User-Agent']='BaseCepheus regulatory/1.0';w,soup=fetch(session,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('avoiding police harassment','prompt issuance of licenses','approval of applications','deal with bureaucrats','difficulty based on base difficulty by law level table','anything illegal on board','suffers a -2 dm'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Admin/Advocate sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.admin-advocate.mechanics';rule=publish_rule(c,pkg,code,'Admin and Advocate Mechanics','skill','Law Level regulatory tasks, overlapping bureaucracy, and illegal ship-inspection modifier.');payload={'operations':list(OPS),'law_level_sets_difficulty':True,'illegal_ship_inspection_modifier':-2,'bribery_alternative_allowed':True}
  for side,art,batch in sides:
   for order,(heading,anchor,section) in enumerate((('Skills > Admin','admin-mechanics','admin'),('Skills > Advocate','advocate-mechanics','advocate'))):
    loc=upsert_locator(c,works[side],art,'paragraph',heading,anchor,heading.split(' > ')[1],order);cand,review=stage_candidate(c,batch,art,loc,'skill',code+'.'+section,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  admin=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.admin'",());advocate=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.advocate'",());c.execute("INSERT INTO rule_regulatory_mechanic VALUES(%s,true,-2,true) ON CONFLICT DO NOTHING",(rule,))
  for i,operation in enumerate(OPS,1):
   c.execute("INSERT INTO rule_regulatory_operation VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(rule,operation,i));skills=(admin,advocate) if operation=='deal-with-bureaucrat' else ((advocate,) if operation=='pass-ship-inspection' else (admin,))
   for skill in skills:c.execute("INSERT INTO rule_regulatory_operation_skill VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(rule,operation,skill))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source Admin and Advocate mechanics');return 0
if __name__=='__main__':raise SystemExit(main())
