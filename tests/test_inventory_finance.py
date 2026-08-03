import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class InventoryFinanceIntegrationTests(unittest.TestCase):
    def create_campaign(self, connection, name):
        return connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES (%s,'referee') RETURNING campaign_id""",
            (name,),
        ).fetchone()[0]

    def create_actor(self, connection, campaign_id, name):
        return connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,%s,'player') RETURNING actor_id""",
            (campaign_id, name),
        ).fetchone()[0]

    def create_rule(self, connection, code, name, category="equipment"):
        return connection.execute(
            """INSERT INTO rule_rule
               (content_package_id,rule_code,name,rule_category,rule_status)
               SELECT content_package_id,%s,%s,%s,'approved'
               FROM sys_content_package
               WHERE package_code='cepheus-engine'
               ORDER BY content_package_id LIMIT 1
               RETURNING rule_id""",
            (code, name, category),
        ).fetchone()[0]

    def create_item_definition(self, connection, code, mass_grams):
        rule_id = self.create_rule(
            connection,
            f"equipment.test.{code}",
            code.replace("-", " ").title(),
        )
        connection.execute(
            """INSERT INTO inv_item_definition
               (rule_id,item_kind,mass_grams)
               VALUES (%s,'equipment',%s)""",
            (rule_id, mass_grams),
        )
        return rule_id

    def create_item(self, connection, campaign_id, item_rule_id, name):
        return connection.execute(
            """INSERT INTO inv_item_instance
               (campaign_id,item_rule_id,instance_name)
               VALUES (%s,%s,%s) RETURNING item_instance_id""",
            (campaign_id, item_rule_id, name),
        ).fetchone()[0]

    def create_container(
        self,
        connection,
        campaign_id,
        name,
        capacity_mass_grams=None,
    ):
        return connection.execute(
            """INSERT INTO inv_container
               (campaign_id,name,capacity_mass_grams)
               VALUES (%s,%s,%s) RETURNING container_id""",
            (campaign_id, name, capacity_mass_grams),
        ).fetchone()[0]

    def create_location(self, connection, campaign_id):
        rule_id = self.create_rule(
            connection,
            "location.type.inventory-test",
            "Inventory Test Location",
            "world",
        )
        connection.execute(
            """INSERT INTO rule_location_type
               VALUES (%s,'inventory-test',true,true)""",
            (rule_id,),
        )
        return connection.execute(
            """INSERT INTO loc_location
               (campaign_id,location_type_rule_id,name)
               VALUES (%s,%s,'Store Room') RETURNING location_id""",
            (campaign_id, rule_id),
        ).fetchone()[0]

    def create_account(
        self,
        connection,
        campaign_id,
        actor_id,
        code,
    ):
        account_id = connection.execute(
            """INSERT INTO fin_account
               (campaign_id,currency_code,account_code,name,account_kind)
               VALUES (%s,'CR',%s,%s,'asset') RETURNING account_id""",
            (campaign_id, code, code.title()),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO fin_actor_account
               (account_id,campaign_id,actor_id)
               VALUES (%s,%s,%s)""",
            (account_id, campaign_id, actor_id),
        )
        return account_id

    def create_transaction(self, connection, campaign_id, description):
        return connection.execute(
            """INSERT INTO fin_transaction
               (campaign_id,currency_code,description)
               VALUES (%s,'CR',%s) RETURNING transaction_id""",
            (campaign_id, description),
        ).fetchone()[0]

    def add_entries(
        self,
        connection,
        transaction_id,
        campaign_id,
        entries,
    ):
        for order, (account_id, amount) in enumerate(entries, 1):
            connection.execute(
                """INSERT INTO fin_entry
                   (transaction_id,campaign_id,currency_code,
                    account_id,entry_order,amount_minor)
                   VALUES (%s,%s,'CR',%s,%s,%s)""",
                (
                    transaction_id,
                    campaign_id,
                    account_id,
                    order,
                    amount,
                ),
            )

    def test_inventory_positions_capacity_lots_and_campaign_scope(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection, "Inventory")
                other_campaign = self.create_campaign(connection, "Other")
                actor_id = self.create_actor(
                    connection, campaign_id, "Quartermaster")
                outsider = self.create_actor(
                    connection, other_campaign, "Outsider")
                location_id = self.create_location(connection, campaign_id)
                item_rule_id = self.create_item_definition(
                    connection, "field-kit", 600)
                first_item = self.create_item(
                    connection, campaign_id, item_rule_id, "First Kit")
                second_item = self.create_item(
                    connection, campaign_id, item_rule_id, "Second Kit")
                container_id = self.create_container(
                    connection, campaign_id, "Pack", 1000)

                connection.execute(
                    """INSERT INTO inv_actor_container
                       VALUES (%s,%s,%s)""",
                    (container_id, campaign_id, actor_id),
                )
                with self.assertRaises(UniqueViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO inv_location_container
                               VALUES (%s,%s,%s)""",
                            (container_id, campaign_id, location_id),
                        )

                connection.execute(
                    """INSERT INTO inv_item_owner
                       (item_instance_id,campaign_id,actor_id)
                       VALUES (%s,%s,%s)""",
                    (first_item, campaign_id, actor_id),
                )
                with self.assertRaises(ForeignKeyViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO inv_item_owner
                               (item_instance_id,campaign_id,actor_id)
                               VALUES (%s,%s,%s)""",
                            (second_item, campaign_id, outsider),
                        )

                connection.execute(
                    """INSERT INTO inv_container_item
                       (item_instance_id,campaign_id,container_id)
                       VALUES (%s,%s,%s)""",
                    (first_item, campaign_id, container_id),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "capacity exceeded",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO inv_container_item
                               (item_instance_id,campaign_id,container_id)
                               VALUES (%s,%s,%s)""",
                            (second_item, campaign_id, container_id),
                        )
                with self.assertRaisesRegex(
                    CheckViolation, "capacity exceeded",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE inv_container
                               SET capacity_mass_grams=500
                               WHERE container_id=%s""",
                            (container_id,),
                        )
                with self.assertRaises(UniqueViolation):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO loc_item_position
                               (item_instance_id,campaign_id,location_id)
                               VALUES (%s,%s,%s)""",
                            (first_item, campaign_id, location_id),
                        )

                lot_id = connection.execute(
                    """INSERT INTO inv_lot
                       (campaign_id,item_rule_id,quantity)
                       VALUES (%s,%s,10) RETURNING lot_id""",
                    (campaign_id, item_rule_id),
                ).fetchone()[0]
                first_store = self.create_container(
                    connection, campaign_id, "First Store")
                second_store = self.create_container(
                    connection, campaign_id, "Second Store")
                connection.execute(
                    """INSERT INTO inv_container_lot
                       (campaign_id,container_id,lot_id,quantity)
                       VALUES (%s,%s,%s,6)""",
                    (campaign_id, first_store, lot_id),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "exceeds authoritative quantity",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO inv_container_lot
                               (campaign_id,container_id,lot_id,quantity)
                               VALUES (%s,%s,%s,5)""",
                            (campaign_id, second_store, lot_id),
                        )

    def test_item_owned_containers_cannot_form_cycles(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection, "Containers")
                item_rule_id = self.create_item_definition(
                    connection, "container-shell", 100)
                first_item = self.create_item(
                    connection, campaign_id, item_rule_id, "First")
                second_item = self.create_item(
                    connection, campaign_id, item_rule_id, "Second")
                first_container = self.create_container(
                    connection, campaign_id, "First Interior")
                second_container = self.create_container(
                    connection, campaign_id, "Second Interior")
                connection.execute(
                    """INSERT INTO inv_item_container
                       VALUES (%s,%s,%s),(%s,%s,%s)""",
                    (
                        first_container,
                        campaign_id,
                        first_item,
                        second_container,
                        campaign_id,
                        second_item,
                    ),
                )
                connection.execute(
                    """INSERT INTO inv_container_item
                       (item_instance_id,campaign_id,container_id)
                       VALUES (%s,%s,%s)""",
                    (second_item, campaign_id, first_container),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "containment cycle",
                ):
                    with connection.transaction():
                        connection.execute(
                            """INSERT INTO inv_container_item
                               (item_instance_id,campaign_id,container_id)
                               VALUES (%s,%s,%s)""",
                            (
                                first_item,
                                campaign_id,
                                second_container,
                            ),
                        )

    def test_atomic_item_transfer_updates_state_and_history_together(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection, "Transfer")
                first_actor = self.create_actor(
                    connection, campaign_id, "Seller")
                second_actor = self.create_actor(
                    connection, campaign_id, "Buyer")
                location_id = self.create_location(connection, campaign_id)
                item_rule_id = self.create_item_definition(
                    connection, "transfer-item", 250)
                item_id = self.create_item(
                    connection, campaign_id, item_rule_id, "Parcel")
                container_id = self.create_container(
                    connection, campaign_id, "Buyer's Pack", 1000)
                connection.execute(
                    """INSERT INTO loc_item_position
                       (item_instance_id,campaign_id,location_id)
                       VALUES (%s,%s,%s)""",
                    (item_id, campaign_id, location_id),
                )
                connection.execute(
                    """INSERT INTO inv_item_owner
                       (item_instance_id,campaign_id,actor_id)
                       VALUES (%s,%s,%s)""",
                    (item_id, campaign_id, first_actor),
                )

                transfer_id = connection.execute(
                    """SELECT inv_transfer_item_atomic(
                           %s,%s,%s,NULL,%s,NULL,NULL,'Sale'
                       )""",
                    (
                        campaign_id,
                        item_id,
                        container_id,
                        second_actor,
                    ),
                ).fetchone()[0]
                state = connection.execute(
                    """SELECT placement.container_id,owner.actor_id,
                              transfer.transfer_status,
                              history.from_location_id,
                              history.to_container_id,
                              history.from_actor_id,
                              history.to_actor_id
                       FROM inv_container_item placement
                       JOIN inv_item_owner owner
                         ON owner.item_instance_id=
                            placement.item_instance_id
                       JOIN inv_item_transfer history
                         ON history.item_instance_id=
                            placement.item_instance_id
                       JOIN inv_transfer transfer
                         ON transfer.transfer_id=history.transfer_id
                       WHERE transfer.transfer_id=%s""",
                    (transfer_id,),
                ).fetchone()
                self.assertEqual(
                    state,
                    (
                        container_id,
                        second_actor,
                        "completed",
                        location_id,
                        container_id,
                        first_actor,
                        second_actor,
                    ),
                )
                self.assertIsNone(connection.execute(
                    """SELECT location_id FROM loc_item_position
                       WHERE item_instance_id=%s""",
                    (item_id,),
                ).fetchone())

                with self.assertRaisesRegex(
                    CheckViolation, "does not change",
                ):
                    with connection.transaction():
                        connection.execute(
                            """SELECT inv_transfer_item_atomic(
                                   %s,%s,%s,NULL,%s,NULL
                               )""",
                            (
                                campaign_id,
                                item_id,
                                container_id,
                                second_actor,
                            ),
                        )

    def test_balanced_ledger_reversals_and_obligation_payments(self):
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id = self.create_campaign(connection, "Finance")
                debtor_actor = self.create_actor(
                    connection, campaign_id, "Debtor")
                creditor_actor = self.create_actor(
                    connection, campaign_id, "Creditor")
                debtor = self.create_account(
                    connection, campaign_id, debtor_actor, "debtor-cash")
                creditor = self.create_account(
                    connection,
                    campaign_id,
                    creditor_actor,
                    "creditor-cash",
                )

                payment = self.create_transaction(
                    connection, campaign_id, "Payment")
                self.add_entries(
                    connection,
                    payment,
                    campaign_id,
                    ((debtor, -40), (creditor, 40)),
                )
                pending_balance = connection.execute(
                    """SELECT balance_minor
                       FROM fin_account_balance
                       WHERE account_id=%s""",
                    (creditor,),
                ).fetchone()[0]
                self.assertEqual(pending_balance, 0)
                connection.execute(
                    "SELECT fin_post_transaction(%s)",
                    (payment,),
                )
                balances = dict(connection.execute(
                    """SELECT account_id,balance_minor
                       FROM fin_account_balance
                       WHERE account_id IN (%s,%s)""",
                    (debtor, creditor),
                ).fetchall())
                self.assertEqual(balances, {debtor: -40, creditor: 40})

                with self.assertRaisesRegex(
                    CheckViolation, "immutable",
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE fin_entry SET amount_minor=-41
                               WHERE transaction_id=%s
                                 AND account_id=%s""",
                            (payment, debtor),
                        )

                unbalanced = self.create_transaction(
                    connection, campaign_id, "Unbalanced")
                self.add_entries(
                    connection,
                    unbalanced,
                    campaign_id,
                    ((debtor, -10), (creditor, 9)),
                )
                with self.assertRaisesRegex(
                    CheckViolation, "balance to zero",
                ):
                    with connection.transaction():
                        connection.execute(
                            "SELECT fin_post_transaction(%s)",
                            (unbalanced,),
                        )

                obligation = connection.execute(
                    """INSERT INTO fin_obligation
                       (campaign_id,currency_code,debtor_account_id,
                        creditor_account_id,principal_minor,
                        obligation_kind,description)
                       VALUES (%s,'CR',%s,%s,100,'loan','Test loan')
                       RETURNING obligation_id""",
                    (campaign_id, debtor, creditor),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO fin_obligation_payment
                       (obligation_id,transaction_id,campaign_id,
                        currency_code,amount_minor)
                       VALUES (%s,%s,%s,'CR',40)""",
                    (obligation, payment, campaign_id),
                )
                outstanding = connection.execute(
                    """SELECT outstanding_minor
                       FROM fin_obligation_balance
                       WHERE obligation_id=%s""",
                    (obligation,),
                ).fetchone()[0]
                self.assertEqual(outstanding, 60)

                reversal = connection.execute(
                    """INSERT INTO fin_transaction
                       (campaign_id,currency_code,description,
                        reversal_of_transaction_id)
                       VALUES (%s,'CR','Reverse payment',%s)
                       RETURNING transaction_id""",
                    (campaign_id, payment),
                ).fetchone()[0]
                self.add_entries(
                    connection,
                    reversal,
                    campaign_id,
                    ((debtor, 40), (creditor, -40)),
                )
                connection.execute(
                    "SELECT fin_post_transaction(%s)",
                    (reversal,),
                )
                connection.execute(
                    """UPDATE fin_transaction
                       SET transaction_status='reversed'
                       WHERE transaction_id=%s""",
                    (payment,),
                )
                reversed_balances = dict(connection.execute(
                    """SELECT account_id,balance_minor
                       FROM fin_account_balance
                       WHERE account_id IN (%s,%s)""",
                    (debtor, creditor),
                ).fetchall())
                self.assertEqual(
                    reversed_balances,
                    {debtor: 0, creditor: 0},
                )
                reversed_outstanding = connection.execute(
                    """SELECT outstanding_minor
                       FROM fin_obligation_balance
                       WHERE obligation_id=%s""",
                    (obligation,),
                ).fetchone()[0]
                self.assertEqual(reversed_outstanding, 100)


if __name__ == "__main__":
    unittest.main()
