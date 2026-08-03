import os,unittest,uuid
from decimal import Decimal
import psycopg
from engine.gambling import resolve_house_gambling_command
class R:
 def __init__(self,v):self.v=iter(v)
 def randint(self,a,b):return next(self.v)
class GamblingTests(unittest.TestCase):
 def actor(self,c):
  camp=c.execute("INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",(str(uuid.uuid4()),)).fetchone()[0];aid,pub=c.execute("INSERT INTO actor_actor(campaign_id,name,controller_reference) VALUES(%s,'Gambler','p') RETURNING actor_id,public_id",(camp,)).fetchone();c.execute("""INSERT INTO actor_characteristic(actor_id,characteristic_rule_id,maximum_value,current_value) SELECT %s,rule_id,9,9 FROM rule_rule WHERE rule_code='characteristic.intelligence'""",(aid,));c.execute("""INSERT INTO actor_skill SELECT %s,rule_id,1 FROM rule_rule WHERE rule_code='skill.gambling'""",(aid,));return str(pub)
 def test_house_win_payoff_and_natural_two_override(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    a=self.actor(c);win=resolve_house_gambling_command(c,initiator_reference='p',idempotency_key='win',actor_public_id=a,characteristic_rule_code='characteristic.intelligence',odds_code='high',venue_reference='casino',game_reference='blackjack',bet_credits=30,random_source=R((3,3)));self.assertTrue(win.won);self.assertEqual(win.winnings_credits,Decimal('20'))
    loss=resolve_house_gambling_command(c,initiator_reference='p',idempotency_key='loss',actor_public_id=a,characteristic_rule_code='characteristic.intelligence',odds_code='high',venue_reference='casino',game_reference='slots',bet_credits=30,random_source=R((1,1)));self.assertTrue(loss.natural_two);self.assertFalse(loss.won)
 def test_maximum_bet_and_rigged_terms(self):
  with psycopg.connect(os.environ['BASE_CEPHEUS_DATABASE_URL']) as c:
   with c.transaction(force_rollback=True):
    a=self.actor(c)
    with self.assertRaises(ValueError):resolve_house_gambling_command(c,initiator_reference='p',idempotency_key='too-big',actor_public_id=a,characteristic_rule_code='characteristic.intelligence',odds_code='high',venue_reference='v',game_reference='g',bet_credits=51,random_source=R((6,6)))
    with self.assertRaises(ValueError):resolve_house_gambling_command(c,initiator_reference='p',idempotency_key='rigged',actor_public_id=a,characteristic_rule_code='characteristic.intelligence',odds_code='rigged',venue_reference='v',game_reference='g',bet_credits=1,random_source=R((6,6)))
