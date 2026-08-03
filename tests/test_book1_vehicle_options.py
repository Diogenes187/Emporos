import os
import unittest

import psycopg
from psycopg.errors import RaiseException

DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class Book1VehicleOptionTests(unittest.TestCase):
    def _vehicle(self, connection, profile_code, tl, name):
        campaign = connection.execute(
            "INSERT INTO camp_campaign(name) VALUES (%s) RETURNING campaign_id",
            (name,)).fetchone()[0]
        profile = connection.execute(
            """SELECT rule_id FROM rule_book1_vehicle_profile
               WHERE profile_code=%s""", (profile_code,)).fetchone()[0]
        vehicle = connection.execute(
            """INSERT INTO camp_book1_vehicle_instance
               (campaign_id,vehicle_profile_rule_id,instance_name,
                manufactured_tech_level)
               VALUES (%s,%s,%s,%s) RETURNING vehicle_instance_id""",
            (campaign,profile,name,tl)).fetchone()[0]
        return campaign, vehicle

    def _option(self, connection, code):
        return connection.execute(
            """SELECT rule_id FROM rule_book1_vehicle_option
               WHERE option_code=%s""", (code,)).fetchone()[0]

    def test_eight_options_and_four_inclusions_have_paired_provenance(self):
        with psycopg.connect(DSN) as connection:
            counts = connection.execute(
                """SELECT (SELECT count(*) FROM rule_book1_vehicle_option),
                          (SELECT count(*) FROM
                           rule_book1_vehicle_included_option),
                          (SELECT count(*) FROM src_record_provenance p
                           JOIN rule_rule r USING (rule_id)
                           WHERE r.rule_code LIKE
                                 'vehicle.book1.option.%')"""
            ).fetchone()
            enclosed = connection.execute(
                """SELECT base_cost_percent,agility_modifier,
                          top_speed_percent_modifier,
                          changes_configuration_to_closed
                   FROM rule_book1_vehicle_option
                   WHERE option_code='enclosed'"""
            ).fetchone()
        self.assertEqual(counts, (8,4,16))
        self.assertEqual(enclosed, (10,-1,-10,True))

    def test_prerequisites_and_exact_immutable_receipts(self):
        with psycopg.connect(DSN) as connection:
            campaign, vehicle = self._vehicle(
                connection,"air-raft",11,"Leather-lined air raft")
            extended = self._option(connection,"extended-life-support")
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """INSERT INTO cmd_book1_vehicle_option_receipt
                           (idempotency_key,campaign_id,vehicle_instance_id,
                            option_rule_id,installation_number,
                            base_vehicle_cost_credits,surcharge_credits,
                            agility_modifier,top_speed_percent_modifier,
                            armor_increase,life_support_seconds_per_person,
                            changes_configuration_to_closed)
                        VALUES (%s,%s,%s,%s,1,275000,27500,
                                   0,0,0,64800,false)""",
                        (f"too-soon-{campaign}",campaign,vehicle,extended))
            enclosed = self._option(connection,"enclosed")
            sealed = self._option(connection,"sealed")
            receipts = []
            for key,option,cost,agility,speed,life,closed in (
                ("enclose",enclosed,27500,-1,-10,None,True),
                ("seal",sealed,55000,0,0,7200,False),
                ("life",extended,27500,0,0,64800,False),
            ):
                receipts.append(connection.execute(
                    """INSERT INTO cmd_book1_vehicle_option_receipt
                       (idempotency_key,campaign_id,vehicle_instance_id,
                        option_rule_id,installation_number,
                        base_vehicle_cost_credits,surcharge_credits,
                        agility_modifier,top_speed_percent_modifier,
                        armor_increase,life_support_seconds_per_person,
                        changes_configuration_to_closed)
                       VALUES (%s,%s,%s,%s,1,275000,%s,%s,%s,0,%s,%s)
                       RETURNING option_receipt_id""",
                    (f"{key}-{campaign}",campaign,vehicle,option,cost,
                     agility,speed,life,
                     closed)).fetchone()[0])
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """UPDATE cmd_book1_vehicle_option_receipt
                           SET surcharge_credits=0
                           WHERE option_receipt_id=%s""", (receipts[0],))

    def test_repeatable_on_board_computers_and_grav_belt_prohibition(self):
        with psycopg.connect(DSN) as connection:
            campaign, vehicle = self._vehicle(
                connection,"ground-car",11,"Computer car")
            option = self._option(connection,"on-board-computer")
            computers = connection.execute(
                """SELECT computer.item_rule_id,item.cost_credits
                   FROM inv_personal_computer_definition computer
                   JOIN inv_item_definition item
                     ON item.rule_id=computer.item_rule_id
                   WHERE computer.computer_kind='hand-computer'
                     AND computer.optimum_tech_level<=11
                   ORDER BY computer.optimum_tech_level LIMIT 2"""
            ).fetchall()
            for number,(computer,cost) in enumerate(computers,1):
                connection.execute(
                    """INSERT INTO cmd_book1_vehicle_option_receipt
                       (idempotency_key,campaign_id,vehicle_instance_id,
                        option_rule_id,installation_number,
                        selected_hand_computer_rule_id,
                        base_vehicle_cost_credits,
                        selected_hand_computer_cost_credits,surcharge_credits,
                        agility_modifier,top_speed_percent_modifier,
                        armor_increase,changes_configuration_to_closed)
                       VALUES (%s,%s,%s,%s,%s,%s,6000,%s,%s,0,0,0,false)""",
                    (f"computer-{campaign}-{number}",campaign,vehicle,option,
                     number,computer,cost,cost))
            self.assertEqual(len(computers), 2)
            belt_campaign,belt = self._vehicle(
                connection,"grav-belt",12,"No-options belt")
            style = self._option(connection,"style")
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """INSERT INTO cmd_book1_vehicle_option_receipt
                           (idempotency_key,campaign_id,vehicle_instance_id,
                            option_rule_id,installation_number,
                            base_vehicle_cost_credits,surcharge_credits,
                            agility_modifier,top_speed_percent_modifier,
                            armor_increase,changes_configuration_to_closed)
                           VALUES (%s,%s,%s,%s,1,100000,200,
                                   0,0,0,false)""",
                        (f"belt-style-{belt_campaign}",
                         belt_campaign,belt,style))

    def test_vehicle_tech_level_and_installed_snapshot_identity_are_guarded(self):
        with psycopg.connect(DSN) as connection:
            campaign = connection.execute(
                """INSERT INTO camp_campaign(name)
                   VALUES ('Vehicle invariant') RETURNING campaign_id"""
            ).fetchone()[0]
            profile = connection.execute(
                """SELECT rule_id FROM rule_book1_vehicle_profile
                   WHERE profile_code='g-carrier'"""
            ).fetchone()[0]
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """INSERT INTO camp_book1_vehicle_instance
                           (campaign_id,vehicle_profile_rule_id,instance_name,
                            manufactured_tech_level)
                           VALUES (%s,%s,'Too primitive',14)""",
                        (campaign,profile))
            car_campaign,car = self._vehicle(
                connection,"ground-car",11,"Stable identity")
            style = self._option(connection,"style")
            connection.execute(
                """INSERT INTO cmd_book1_vehicle_option_receipt
                   (idempotency_key,campaign_id,vehicle_instance_id,
                    option_rule_id,installation_number,
                    base_vehicle_cost_credits,surcharge_credits,
                    agility_modifier,top_speed_percent_modifier,
                    armor_increase,changes_configuration_to_closed)
                   VALUES (%s,%s,%s,%s,1,6000,200,0,0,0,false)""",
                (f"stable-style-{car_campaign}",car_campaign,car,style))
            with self.assertRaises(RaiseException):
                with connection.transaction():
                    connection.execute(
                        """UPDATE camp_book1_vehicle_instance
                           SET manufactured_tech_level=12
                           WHERE vehicle_instance_id=%s""", (car,))


if __name__ == "__main__":
    unittest.main()
