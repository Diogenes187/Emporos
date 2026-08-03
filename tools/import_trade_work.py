"""Import paired trade-work prose and approved weekly wage."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
TRAVEL_URL='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-off-world-travel/'
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');session=requests.Session();session.headers['User-Agent']='BaseCepheus trade-work/1.0';gskills=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();gtravel=(ROOT/'sources/cepheus-srd/src/book2/off-world-travel.md').read_bytes();wskills,ss=fetch(session,SKILL_URL);wtravel,ts=fetch(session,TRAVEL_URL)
 for text in (gskills.decode(),ss.get_text(' ')):
  for phrase in ('electronics','engineering','gravitics','mechanics','paycheck for every week of dedicated work'):
   if normalize(phrase) not in normalize(text):raise ValueError(f'Trade skill source omits {phrase}')
 for text in (gtravel.decode(),ts.get_text(' ')):
  if 'salary is cr1000 per month' not in normalize(text):raise ValueError('Salary source omits Cr1000 technician benchmark')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};items=(('github',gskills,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown','Skills > Trade Skills'),('ogn',wskills,SKILL_URL,'web_page',None,'text/html','Skills > Trade Skills'),('github',gtravel,'src/book2/off-world-travel.md','repository_file',GITHUB_COMMIT,'text/markdown','Off-World Travel > Crew Salaries'),('ogn',wtravel,TRAVEL_URL,'web_page',None,'text/html','Off-World Travel > Crew Salaries'));sides=[]
  for side,data,uri,kind,rev,media,section in items:
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);batch=import_batch(c,pkg,art,sha256(data));sides.append((side,art,batch,section))
  code='skill.trade-work.weekly-pay';rule=publish_rule(c,pkg,code,'Dedicated Trade Work Weekly Pay','skill','Four technical trades earn Cr250 per dedicated week by campaign adjudication.');payload={'skills':['electronics','engineering','gravitics','mechanics'],'dedicated_seconds':604800,'published_technician_monthly_credits':1000,'adjudicated_weekly_credits':250}
  for order,(side,art,batch,section) in enumerate(sides):
   loc=upsert_locator(c,works[side],art,'paragraph',section,'trade-work-wage','Trade Work and Technician Salary',order);cand,review=stage_candidate(c,batch,art,loc,'skill',code,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if order<2 else 'corroborating',order==1)
  c.execute("INSERT INTO rule_trade_work_policy VALUES(%s,604800,1000,250,true) ON CONFLICT(rule_id) DO NOTHING",(rule,))
  for order,name in enumerate(('electronics','engineering','gravitics','mechanics'),1):c.execute("INSERT INTO rule_trade_work_skill SELECT rule_id,%s,%s FROM rule_rule WHERE rule_code=%s ON CONFLICT(skill_rule_id) DO NOTHING",(rule,order,f'skill.{name}'))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source trade work and approved Cr250 weekly wage');return 0
if __name__=='__main__':raise SystemExit(main())
