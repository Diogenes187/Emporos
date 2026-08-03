"""Import paired-source spacecraft journey execution boundaries."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
URL='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-off-world-travel/'
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');g=(ROOT/'sources/cepheus-srd/src/book2/off-world-travel.md').read_bytes();s=requests.Session();s.headers['User-Agent']='BaseCepheus journey execution/1.0';w,soup=fetch(s,URL);texts=(normalize(g.decode()),normalize(soup.get_text(' ')))
 for phrase in ('accelerate halfway there, then reverse thrust and decelerate','suitable set of course vectors','all normal jumps take roughly one week','travels to the destination world'):
  if any(normalize(phrase) not in x for x in texts):raise ValueError(f'Paired travel sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};sides=[]
  for side,data,uri,kind,rev,media in (('github',g,'src/book2/off-world-travel.md','repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',w,URL,'web_page',None,'text/html')):
   art=upsert_artifact(c,works[side],kind,uri,rev,data,media);sides.append((side,art,import_batch(c,pkg,art,sha256(data))))
  rule=publish_rule(c,pkg,'travel.spacecraft.journey-execution','Spacecraft Journey Execution','travel','Atomic departure, elapsed-time, resource-consumption, and arrival transitions.');payload={'jump_duration':'148+6D6 hours','safe_route_required':True,'consume_planned_resources_on_departure':True,'move_ship_on_arrival':True,'advance_campaign_clock':True}
  for side,art,batch in sides:
   loc=upsert_locator(c,works[side],art,'paragraph','Off-World Travel > Starship Operations','spacecraft-journey-execution','Starship Operations',0);cand,review=stage_candidate(c,batch,art,loc,'travel','travel.spacecraft.journey-execution',payload);add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  system=c.execute("SELECT duration_base_hours,duration_dice_count,duration_die_sides FROM rule_jump_travel_system WHERE jump_system_code='cepheus-standard'").fetchone();c.execute("INSERT INTO rule_spacecraft_journey_execution VALUES(%s,%s,%s,%s,true,true,true,true) ON CONFLICT DO NOTHING",(rule,*system));c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",([x[2] for x in sides],))
 print('published paired-source spacecraft journey execution');return 0
if __name__=='__main__':raise SystemExit(main())
