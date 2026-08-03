import os,unittest,uuid
import psycopg
from engine.competitive_gambling import resolve_competitive_gambling_command
class R:
 def __init__(self,v):self.v=iter(v)
 def randint(self,a,b):return next(self.v)
class CompetitiveGamblingTests(unittest.TestCase):
 def actors(self,c,n=3):
  camp=c.execute("INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];out=[]
  for i in range(n):
   aid,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,%s,%s) RETURNING actor_id,public_id",(camp,f'P{i}',f'p{i}')).fetchone();c.execute("""INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,7,7 FROM rule_rule WHERE rule_code='characteristic.intelligence'""",(aid,));c.execute("INSERT INTO actor_skill SELECT %s,rule_id,0 FROM rule_rule WHERE rule_code='skill.gambling'",(aid,));out.append(str(pub))
  return out
 def parts(self,a,cheats):return [{'actor_public_id':x,'characteristic_rule_code':'characteristic.intelligence','cheating':i in cheats} for i,x in enumerate(a)]
 def test_caught_cheater_is_ineligible_and_honest_high_wins(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    a=self.actors(c,2);r=resolve_competitive_gambling_command(c,referee_reference='ref',idempotency_key='caught',venue_reference='club',game_reference='poker',pot_reference='pot-1',participants=self.parts(a,{0}),random_source=R((6,6,5,5,6,6)));self.assertEqual(r.status,'resolved');self.assertEqual(r.basis,'normal');self.assertEqual(r.winner_actor_public_id,a[1])
 def test_uncaught_cheaters_use_highest_cheat_total_and_ties_remain_open(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    a=self.actors(c,2);r=resolve_competitive_gambling_command(c,referee_reference='ref',idempotency_key='cheats',venue_reference='club',game_reference='cards',pot_reference='pot-2',participants=self.parts(a,{0,1}),random_source=R((1,1,1,1,6,5,4,4)));self.assertEqual(r.basis,'cheating');self.assertEqual(r.winner_actor_public_id,a[0])
    b=self.actors(c,2);t=resolve_competitive_gambling_command(c,referee_reference='ref',idempotency_key='tie',venue_reference='club',game_reference='dice',pot_reference='pot-3',participants=self.parts(b,set()),random_source=R((4,4,4,4)));self.assertEqual(t.status,'tied');self.assertIsNone(t.winner_actor_public_id)
