import os
import unittest
import psycopg
from psycopg.errors import RaiseException

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")

@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1RangedWeaponOptionTests(unittest.TestCase):
    def test_catalogue_and_canonical_laser_price(self):
        with psycopg.connect(DSN) as connection:
            counts=connection.execute(
                """SELECT (SELECT count(*) FROM rule_book1_ranged_weapon_option),
                 (SELECT count(*) FROM rule_book1_ranged_weapon_option_effect),
                 (SELECT count(*) FROM rule_book1_ranged_weapon_option_upgrade),
                 (SELECT count(*) FROM rule_book1_ranged_weapon_option_eligibility)"""
            ).fetchone()
            laser=connection.execute(
                """SELECT canonical_cost_credits,
                          conflicting_source_table_cost_credits,
                          aimed_attack_modifier
                   FROM rule_book1_ranged_weapon_option o
                   JOIN rule_book1_ranged_weapon_option_effect e
                     ON e.option_rule_id=o.rule_id
                   WHERE option_code='laser-sights'""").fetchone()
        self.assertEqual(counts[:3],(10,10,2))
        self.assertGreater(counts[3],50)
        self.assertEqual(laser,(200,100,1))

    def test_installation_is_exact_eligible_and_immutable(self):
        with psycopg.connect(DSN) as connection:
            campaign=connection.execute(
                "INSERT INTO camp_campaign(name) VALUES ('Ranged option') RETURNING campaign_id"
            ).fetchone()[0]
            rows=dict(connection.execute(
                """SELECT rule_code,rule_id FROM rule_rule WHERE rule_code IN
                   ('equipment.weapon.rifle',
                    'equipment.weapon-option.folding-stocks')""").fetchall())
            ids=[]
            for rule,name in ((rows["equipment.weapon.rifle"],"Rifle"),
                              (rows["equipment.weapon-option.folding-stocks"],"Stock")):
                ids.append(connection.execute(
                    """INSERT INTO inv_item_instance(campaign_id,item_rule_id,instance_name)
                       VALUES (%s,%s,%s) RETURNING item_instance_id""",
                    (campaign,rule,name)).fetchone()[0])
            receipt=connection.execute(
                """INSERT INTO cmd_book1_ranged_weapon_option_receipt
                   (idempotency_key,campaign_id,weapon_item_instance_id,
                    option_item_instance_id,option_rule_id,
                    installed_cost_credits,installed_mass_grams)
                   VALUES (%s,%s,%s,%s,%s,100,500)
                   RETURNING option_receipt_id""",
                (f"folding-rifle-{campaign}",campaign,*ids,
                 rows["equipment.weapon-option.folding-stocks"])
            ).fetchone()[0]
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """UPDATE cmd_book1_ranged_weapon_option_receipt
                           SET installed_cost_credits=0 WHERE option_receipt_id=%s""",
                        (receipt,))

if __name__ == "__main__":
    unittest.main()
