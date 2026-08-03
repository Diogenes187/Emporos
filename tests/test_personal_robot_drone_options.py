import os
import unittest

import psycopg
from psycopg.errors import RaiseException

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalRobotDroneOptionTests(unittest.TestCase):
    def test_option_mechanics_and_paired_provenance(self):
        with psycopg.connect(DSN) as connection:
            rows = connection.execute(
                """SELECT option_code,armor_increase,
                          robot_cost_increase_basis_points,
                          selected_item_cost_increase_basis_points,
                          fixed_surcharge_credits,requires_selected_item
                   FROM rule_personal_robot_drone_option
                   ORDER BY option_code"""
            ).fetchall()
            provenance = connection.execute(
                """SELECT count(*),count(*) FILTER (WHERE is_primary_citation)
                   FROM src_record_provenance provenance
                   JOIN rule_rule rule USING (rule_id)
                   WHERE rule.rule_code LIKE
                         'equipment.robot-drone-option.%'"""
            ).fetchone()
        self.assertEqual(rows, [
            ("armor", 5, 2500, None, None, False),
            ("integral-system", None, None, 5000, None, True),
            ("integral-weapon", None, None, None, 10000, True),
        ])
        self.assertEqual(provenance, (6, 3))

    def test_exact_receipt_arithmetic_and_immutability(self):
        with psycopg.connect(DSN) as connection:
            campaign = connection.execute(
                """INSERT INTO camp_campaign(name) VALUES ('Robot options')
                   RETURNING campaign_id"""
            ).fetchone()[0]
            chassis_rule, base_cost = connection.execute(
                """SELECT chassis.item_rule_id,item.cost_credits
                   FROM inv_personal_robot_drone_chassis chassis
                   JOIN inv_item_definition item
                     ON item.rule_id=chassis.item_rule_id
                   WHERE chassis.chassis_code='repair-robot'"""
            ).fetchone()
            instance = connection.execute(
                """INSERT INTO inv_item_instance
                   (campaign_id,item_rule_id,instance_name)
                   VALUES (%s,%s,'Option test robot')
                   RETURNING item_instance_id""",
                (campaign, chassis_rule)).fetchone()[0]
            option = connection.execute(
                """SELECT rule_id FROM rule_personal_robot_drone_option
                   WHERE option_code='armor'"""
            ).fetchone()[0]
            receipt = connection.execute(
                """INSERT INTO cmd_personal_robot_drone_option_receipt
                   (idempotency_key,campaign_id,robot_item_instance_id,
                    option_rule_id,base_robot_cost_credits,
                    surcharge_quarter_credits)
                   VALUES ('robot-option-test',%s,%s,%s,%s,%s)
                   RETURNING option_receipt_id""",
                (campaign, instance, option, base_cost, base_cost),
            ).fetchone()[0]
            stored = connection.execute(
                """SELECT base_robot_cost_credits,surcharge_quarter_credits
                   FROM cmd_personal_robot_drone_option_receipt
                   WHERE option_receipt_id=%s""", (receipt,)
            ).fetchone()
            self.assertEqual(stored, (10000, 10000))
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """UPDATE cmd_personal_robot_drone_option_receipt
                           SET surcharge_quarter_credits=0
                           WHERE option_receipt_id=%s""", (receipt,))
            connection.rollback()

    def test_invalid_integral_system_arithmetic_is_rejected(self):
        with psycopg.connect(DSN) as connection:
            campaign = connection.execute(
                """INSERT INTO camp_campaign(name) VALUES ('Bad robot option')
                   RETURNING campaign_id"""
            ).fetchone()[0]
            chassis_rule, base_cost = connection.execute(
                """SELECT chassis.item_rule_id,item.cost_credits
                   FROM inv_personal_robot_drone_chassis chassis
                   JOIN inv_item_definition item
                     ON item.rule_id=chassis.item_rule_id
                   WHERE chassis.chassis_code='repair-robot'"""
            ).fetchone()
            instance = connection.execute(
                """INSERT INTO inv_item_instance
                   (campaign_id,item_rule_id) VALUES (%s,%s)
                   RETURNING item_instance_id""",
                (campaign, chassis_rule)).fetchone()[0]
            option = connection.execute(
                """SELECT rule_id FROM rule_personal_robot_drone_option
                   WHERE option_code='integral-system'"""
            ).fetchone()[0]
            selected, selected_cost = connection.execute(
                """SELECT rule_id,cost_credits FROM inv_item_definition
                   WHERE cost_credits IS NOT NULL ORDER BY rule_id LIMIT 1"""
            ).fetchone()
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """INSERT INTO cmd_personal_robot_drone_option_receipt
                           (idempotency_key,campaign_id,
                            robot_item_instance_id,option_rule_id,
                            selected_item_rule_id,base_robot_cost_credits,
                            selected_item_cost_credits,
                            surcharge_quarter_credits)
                           VALUES ('bad-system',%s,%s,%s,%s,%s,%s,0)""",
                        (campaign, instance, option, selected, base_cost,
                         selected_cost))

    def test_multiple_integral_installations_are_allowed(self):
        with psycopg.connect(DSN) as connection:
            campaign = connection.execute(
                """INSERT INTO camp_campaign(name) VALUES ('Many systems')
                   RETURNING campaign_id"""
            ).fetchone()[0]
            chassis_rule, base_cost = connection.execute(
                """SELECT chassis.item_rule_id,item.cost_credits
                   FROM inv_personal_robot_drone_chassis chassis
                   JOIN inv_item_definition item
                     ON item.rule_id=chassis.item_rule_id
                   WHERE chassis.chassis_code='repair-robot'"""
            ).fetchone()
            instance = connection.execute(
                """INSERT INTO inv_item_instance(campaign_id,item_rule_id)
                   VALUES (%s,%s) RETURNING item_instance_id""",
                (campaign, chassis_rule)).fetchone()[0]
            option = connection.execute(
                """SELECT rule_id FROM rule_personal_robot_drone_option
                   WHERE option_code='integral-system'"""
            ).fetchone()[0]
            selected = connection.execute(
                """SELECT rule_id,cost_credits FROM inv_item_definition
                   WHERE cost_credits IS NOT NULL ORDER BY rule_id LIMIT 2"""
            ).fetchall()
            for order, (item_rule, item_cost) in enumerate(selected, 1):
                connection.execute(
                    """INSERT INTO cmd_personal_robot_drone_option_receipt
                       (idempotency_key,campaign_id,
                        robot_item_instance_id,option_rule_id,
                        selected_item_rule_id,base_robot_cost_credits,
                        selected_item_cost_credits,surcharge_quarter_credits)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (f"many-systems-{campaign}-{order}",
                     campaign, instance, option,
                     item_rule, base_cost, item_cost, item_cost * 6))
            count = connection.execute(
                """SELECT count(*)
                   FROM cmd_personal_robot_drone_option_receipt
                   WHERE robot_item_instance_id=%s""", (instance,)
            ).fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
