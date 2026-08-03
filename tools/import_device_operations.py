"""Import paired-source Demolitions and device-disabling operations."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
ROWS=(('use-demolition-charge','explosive','demolitions'),('assemble-bomb','explosive','demolitions'),('disarm-bomb','explosive','demolitions'),('disarm-electronic-alarm','electronic','electronics'),('pick-electronic-lock','electronic','electronics'),('disable-malfunctioning-robot','electronic','electronics'),('similar-electronic-device','electronic','electronics'),('disable-mechanical-alarm','mechanical','mechanics'),('pick-mechanical-lock','mechanical','mechanics'),('similar-mechanical-device','mechanical','mechanics'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus devices/1.0';w,soup=fetch(s,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('demolition charges and other explosive devices','assembling or disarming bombs','disarming alarm systems','picking electronic locks','disabling a malfunctioning robot','mechanical alarm systems','picking mechanical locks'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired device-operation sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.device.operations';rule=publish_rule(c,pkg,code,'Demolitions and Device Operations','skill','Explosive, electronic, and mechanical device operations.');payload={'operations':[r[0] for r in ROWS]}
  for side,art,batch in sides:
   for order,heading in enumerate(('Demolitions','Electronics','Mechanics')):
    section=heading.lower();loc=upsert_locator(c,works[side],art,'paragraph','Skills > '+heading,'device-'+section,heading,order);cand,review=stage_candidate(c,batch,art,loc,'skill',code+'.'+section,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  c.execute("INSERT INTO rule_device_operation_mechanic VALUES(%s) ON CONFLICT DO NOTHING",(rule,))
  for i,(op,domain,skill) in enumerate(ROWS,1):sid=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code=%s",('skill.'+skill,));c.execute("INSERT INTO rule_device_operation VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",(rule,op,domain,sid,i))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source device operations');return 0
if __name__=='__main__':raise SystemExit(main())
