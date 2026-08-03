"""Source-defined local trade market and supplier stock generation."""
from dataclasses import dataclass
import secrets
import psycopg

@dataclass(frozen=True)
class MarketOpeningResult:
 command_public_id:str;market_public_id:str;system_public_id:str;market_name:str
 distinct_stock_count:int;total_quantity_tons:int;replayed:bool

def _load(c,cid,pub,replayed):
 row=c.execute("SELECT market.public_id,system.public_id,market.name,receipt.distinct_stock_count,receipt.total_quantity_tons FROM cmd_trade_market_opening_receipt receipt JOIN mkt_market market USING(market_id) JOIN loc_world_profile profile ON profile.world_profile_id=receipt.world_profile_id JOIN loc_celestial_body body ON body.location_id=profile.location_id JOIN loc_location system ON system.location_id=body.system_location_id WHERE receipt.command_id=%s",(cid,)).fetchone()
 return MarketOpeningResult(str(pub),str(row[0]),str(row[1]),row[2],row[3],int(row[4]),replayed)

def open_trade_market_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,system_public_id:str,market_name:str='Starport Exchange',random_source=None)->MarketOpeningResult:
 rng=random_source or secrets.SystemRandom();name=market_name.strip()
 if not name:raise ValueError('Market name cannot be blank')
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('open_trade_market','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  state=c.execute("""SELECT campaign.campaign_id,system.location_id,profile.world_profile_id,profile.location_id,clock.day_number,clock.second_of_day
  FROM camp_campaign campaign JOIN loc_location system ON system.campaign_id=campaign.campaign_id JOIN loc_star_system star ON star.location_id=system.location_id
  JOIN loc_celestial_body body ON body.system_location_id=star.location_id JOIN loc_world_profile profile ON profile.location_id=body.location_id AND profile.profile_status='current'
  JOIN camp_clock clock ON clock.campaign_id=campaign.campaign_id
  WHERE campaign.public_id=%s AND campaign.owner_reference=%s AND system.public_id=%s ORDER BY body.orbit_order NULLS LAST LIMIT 1 FOR UPDATE OF campaign""",(campaign_public_id,initiator_reference,system_public_id)).fetchone()
  if not state:raise ValueError('System has no current main-world profile')
  if c.execute("SELECT 1 FROM mkt_market WHERE campaign_id=%s AND location_id=%s AND market_status='active'",(state[0],state[3])).fetchone():raise ValueError('An active market already exists at this world')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('open_trade_market',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
  faction=c.execute("INSERT INTO actor_faction(campaign_id,name) VALUES(%s,%s) RETURNING faction_id",(state[0],name+' Suppliers')).fetchone()[0]
  market,market_pub=c.execute("INSERT INTO mkt_market(campaign_id,location_id,name,market_kind) VALUES(%s,%s,%s,'legal') RETURNING market_id,public_id",(state[0],state[3],name)).fetchone()
  expires_day=state[4]+7;session=c.execute("INSERT INTO mkt_session(market_id,campaign_id,opened_day,opened_second,expires_day,expires_second,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING market_session_id",(market,state[0],state[4],state[5],expires_day,state[5],cid)).fetchone()[0]
  supplier=c.execute("INSERT INTO mkt_supplier(market_session_id,campaign_id,faction_id,supplier_kind) VALUES(%s,%s,%s,'supplier') RETURNING supplier_id",(session,state[0],faction)).fetchone()[0]
  random_count=rng.randint(1,6);generation=c.execute("INSERT INTO mkt_supplier_stock_generation(campaign_id,market_session_id,supplier_id,world_profile_id,market_kind_snapshot,random_good_count_roll,source_command_id) VALUES(%s,%s,%s,%s,'legal',%s,%s) RETURNING supplier_stock_generation_id",(state[0],session,supplier,state[2],random_count,cid)).fetchone()[0]
  occurrences=[]
  commons=c.execute("SELECT trade_good_rule_id,availability_dice_count,availability_die_sides,availability_multiplier FROM rule_trade_good WHERE good_kind='common' ORDER BY good_code").fetchall()
  for order,good in enumerate(commons,1):occurrences.append(('common',order,*good))
  included=ignored=0
  for order in range(1,random_count+1):
   tens=rng.randint(1,6);ones=rng.randint(1,6);d66=tens*10+ones;good=c.execute("SELECT trade_good_rule_id,good_kind,black_market_only,availability_dice_count,availability_die_sides,availability_multiplier FROM rule_trade_good WHERE d66_result=%s",(d66,)).fetchone()
   outcome='unusual-referee' if good[1]=='unusual' else ('ignored-illegal' if good[2] else 'included')
   c.execute("INSERT INTO mkt_supplier_stock_selection_draw VALUES(%s,%s,%s,%s,%s,%s,%s)",(generation,order,tens,ones,d66,good[0],outcome))
   if outcome=='included':occurrences.append(('random',order,good[0],good[3],good[4],good[5]));included+=1
   else:ignored+=1
  quantities={};occurrence_counts={}
  for source_kind,source_order,good_id,dice_count,sides,multiplier in occurrences:
   total=0
   for die_order in range(1,dice_count+1):
    value=rng.randint(1,sides);total+=value*multiplier;c.execute("INSERT INTO mkt_supplier_stock_quantity_draw VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(generation,source_kind,source_order,good_id,die_order,sides,value,multiplier))
   quantities[good_id]=quantities.get(good_id,0)+total;occurrence_counts[good_id]=occurrence_counts.get(good_id,0)+1
  total_quantity=0
  for good_id,quantity in quantities.items():
   stock=c.execute("INSERT INTO mkt_stock(market_session_id,campaign_id,supplier_id,trade_good_rule_id,quantity_tons) VALUES(%s,%s,%s,%s,%s) RETURNING stock_id",(session,state[0],supplier,good_id,quantity)).fetchone()[0]
   c.execute("INSERT INTO mkt_supplier_stock_result VALUES(%s,%s,%s,%s,%s,%s)",(generation,good_id,stock,state[0],occurrence_counts[good_id],quantity));total_quantity+=quantity
  c.execute("INSERT INTO mkt_supplier_stock_final_receipt VALUES(%s,%s,%s,%s,%s,%s,clock_timestamp(),%s)",(generation,random_count,included,ignored,len(quantities),total_quantity,cid))
  c.execute("INSERT INTO cmd_trade_market_opening_receipt VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(cid,state[0],market,session,supplier,generation,state[2],len(quantities),total_quantity))
  c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'trade_market_opened')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
  return _load(c,cid,pub,False)
