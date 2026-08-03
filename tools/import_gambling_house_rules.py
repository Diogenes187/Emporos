"""Import paired-source non-competitive Gambling rules."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
ROWS=(('rigged','Rigged',-8,None,None,None),('remote','Remote',-6,10,1,5000),('small','Small',-4,8,1,1000),('low','Low',-2,4,1,500),('average','Average',0,2,1,100),('high','High',2,2,3,50))
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');github=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus gambling/1.0';web,soup=fetch(s,SKILL_URL);texts=(normalize(github.decode()),normalize(soup.get_text(' ')))
 for phrase in ('non-competitive games','house always wins on a natural 2','remote','cr5,000','2:3'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired Gambling sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides={}
  for side,data,uri,kind,rev,media in (('github',github,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',web,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides[side]=(art,import_batch(c,pkg,art,sha256(data)))
  for order,(code,name,dm,num,den,maximum) in enumerate(ROWS,1):
   rule=publish_rule(c,pkg,f'skill.gambling.house.{code}',name,'skill','Non-competitive Gambling odds band.');payload={'odds':code,'modifier':dm,'payoff':None if num is None else f'{den}:{num}','maximum_bet_credits':maximum,'natural_two_house_win':True}
   for side,(art,batch) in sides.items():
    loc=upsert_locator(c,works[side],art,'table_row','Skills > Gambling > Gambling by Odds of Winning',f'gambling-house-{code}',name,order);cand,review=stage_candidate(c,batch,art,loc,'skill',f'skill.gambling.house.{code}',payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
   c.execute("INSERT INTO rule_gambling_house_odds VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(rule_id) DO UPDATE SET check_modifier=EXCLUDED.check_modifier",(rule,code,dm,num,den,maximum,order))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([v[1] for v in sides.values()],))
 print('published six paired-source house Gambling odds');return 0
if __name__=='__main__':raise SystemExit(main())
