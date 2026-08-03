"""Import paired-source Broker operations and Carousing influence."""
import argparse,os
import psycopg,requests
from import_foundation_rules import GITHUB_COMMIT,ROOT,SKILL_URL,add_provenance,fetch,get_id,import_batch,normalize,publish_rule,sha256,stage_candidate,upsert_artifact,upsert_locator
TRADE_URL='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-trade-and-commerce/'
SOCIAL_URL='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-social-encounters/'
def main():
 p=argparse.ArgumentParser();p.add_argument('--dsn');a=p.parse_args();dsn=a.dsn or os.environ.get('BASE_CEPHEUS_DATABASE_URL');session=requests.Session();session.headers['User-Agent']='BaseCepheus Broker Carousing/1.0';files={'skills':ROOT/'sources/cepheus-srd/src/book1/skills.md','trade':ROOT/'sources/cepheus-srd/src/book2/trade-and-commerce.md','social':ROOT/'sources/cepheus-srd/src/book3/social-encounters.md'};urls={'skills':SKILL_URL,'trade':TRADE_URL,'social':SOCIAL_URL};data={};soups={}
 for key in files:data['g-'+key]=files[key].read_bytes();data['w-'+key],soups[key]=fetch(session,urls[key])
 pairs={key:(normalize(data['g-'+key].decode()),normalize(soups[key].get_text(' '))) for key in files}
 for key,phrases in {'skills':('locating suppliers and buyers','interacting and socializing with others'),'trade':('finding a supplier','determining the purchase price','find a buyer'),'social':('various interaction skills','liaison and carousing')}.items():
  for phrase in phrases:
   if any(normalize(phrase) not in text for text in pairs[key]):raise ValueError(f'Paired {key} sources omit: {phrase}')
 with psycopg.connect(dsn) as c:
  pkg=get_id(c,"SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine' AND package_version='9.1-draft'",());works={k:get_id(c,"SELECT source_work_id FROM src_work WHERE work_code=%s",(v,)) for k,v in {'github':'cepheus-engine.github-v9.1','ogn':'cepheus-engine.ogn'}.items()};artifacts={};batches=[]
  for key in files:
   for side,blob,uri,kind,rev,media in (('github',data['g-'+key],str(files[key].relative_to(ROOT/'sources/cepheus-srd')).replace('\\','/'),'repository_file',GITHUB_COMMIT,'text/markdown'),('ogn',data['w-'+key],urls[key],'web_page',None,'text/html')):
    art=upsert_artifact(c,works[side],kind,uri,rev,blob,media);batch=import_batch(c,pkg,art,sha256(blob));artifacts[(side,key)]=(art,batch);batches.append(batch)
  broker=publish_rule(c,pkg,'skill.broker.operations','Broker Operations','skill','Supplier and buyer searches and speculative trade price determination.');carousing=publish_rule(c,pkg,'skill.carousing.influence','Carousing Influence','skill','Carousing used as an interaction skill to influence attitudes.')
  for rule,code,sections in ((broker,'skill.broker.operations',(('skills','Skills > Broker','Broker'),('trade','Trade and Commerce > Find a Supplier','Find a Supplier'))),(carousing,'skill.carousing.influence',(('skills','Skills > Carousing','Carousing'),('social','Social Encounters > Influencing Attitudes','Influencing Attitudes')))):
   for side in ('github','ogn'):
    for order,(key,path,heading) in enumerate(sections):
     art,batch=artifacts[(side,key)];loc=upsert_locator(c,works[side],art,'paragraph',path,code.split('.')[-1]+'-'+key,heading,order);cand,review=stage_candidate(c,batch,art,loc,'skill',code,{'dedicated_command':True});add_provenance(c,rule,pkg,loc,cand,review,'direct' if side=='ogn' else 'corroborating',side=='ogn')
  c.execute("INSERT INTO rule_broker_operation_mechanic VALUES(%s) ON CONFLICT DO NOTHING",(broker,));skill=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.broker'",());difficulty=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='difficulty.average'",());days=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='time-frame.days'",());ksec=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='time-frame.kiloseconds'",())
  for order,(op,frame) in enumerate((('find-supplier',days),('find-buyer',days),('determine-purchase-price',ksec),('determine-sale-price',ksec)),1):c.execute("INSERT INTO rule_broker_operation VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",(broker,op,skill,difficulty,frame,order))
  influence=get_id(c,"SELECT rule_id FROM rule_attitude_influence_system",());carouse_skill=get_id(c,"SELECT rule_id FROM rule_rule WHERE rule_code='skill.carousing'",());c.execute("INSERT INTO rule_carousing_influence_mechanic VALUES(%s,%s,%s) ON CONFLICT DO NOTHING",(carousing,carouse_skill,influence));c.execute("UPDATE src_import_batch SET batch_status='published',completed_at=COALESCE(completed_at,clock_timestamp()) WHERE import_batch_id=ANY(%s)",(batches,))
 print('published paired-source Broker and Carousing mechanics');return 0
if __name__=='__main__':raise SystemExit(main())
