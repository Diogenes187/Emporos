"""Import paired-source spacecraft and vehicle operating capabilities."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
ROWS=(('grav-vehicle',True,True,True,False),('mole',True,True,False,False),('motorboats',True,True,False,False),('ocean-ships',True,True,False,False),('rotor-aircraft',True,True,True,False),('sailing-ships',True,True,False,False),('submarine',True,True,False,False),('tracked-vehicle',True,True,False,False),('wheeled-vehicle',True,True,False,False),('winged-aircraft',True,True,False,True))
HEADINGS={'grav-vehicle':'Grav Vehicle','mole':'Mole','motorboats':'Motorboats','ocean-ships':'Ocean Ships','rotor-aircraft':'Rotor Aircraft','sailing-ships':'Sailing Ships','submarine':'Submarine','tracked-vehicle':'Tracked Vehicle','wheeled-vehicle':'Wheeled Vehicle','winged-aircraft':'Winged Aircraft'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book1/skills.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus transport/1.0';w,soup=fetch(s,SKILL_URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('operation of interplanetary and interstellar spacecraft','check is usually only made when circumstances become challenging','properly maneuver and perform basic routine maintenance','winged aircraft must keep moving forwards'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired transport sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book1/skills.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,SKILL_URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  code='skill.transport.operations';rule=publish_rule(c,pkg,code,'Transport Operations','skill','Spacecraft Piloting and vehicle maneuver and routine-maintenance boundaries.');payload={'vehicle_skills':[r[0] for r in ROWS],'piloting_challenging_check_only':True,'riding_deferred_to_animal_domain':True}
  sections=[('piloting','Piloting')]+[(r[0],HEADINGS[r[0]]) for r in ROWS]
  for side,art,batch in sides:
   for order,(section,heading) in enumerate(sections):
    loc=upsert_locator(c,works[side],art,'paragraph','Skills > '+heading,'transport-'+section,heading,order);cand,review=stage_candidate(c,batch,art,loc,'skill',code+'.'+section,payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  c.execute("INSERT INTO rule_transport_operation_mechanic VALUES(%s) ON CONFLICT DO NOTHING",(rule,));pilot=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.piloting'",());c.execute("INSERT INTO rule_transport_skill_capability VALUES(%s,%s,'ship',true,false,true,false,false) ON CONFLICT DO NOTHING",(rule,pilot))
  for skill,maneuver,maintenance,hover,forward in ROWS:
   sid=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code=%s",('skill.'+skill,));c.execute("INSERT INTO rule_transport_skill_capability VALUES(%s,%s,'vehicle',%s,%s,false,%s,%s) ON CONFLICT DO NOTHING",(rule,sid,maneuver,maintenance,hover,forward))
  c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source transport operations');return 0
if __name__=='__main__':raise SystemExit(main())
