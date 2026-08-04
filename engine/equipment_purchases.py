"""Audited purchase and custody of catalogued personal equipment."""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class PersonalEquipmentPurchaseResult:
    command_public_id: str
    actor_public_id: str
    item_public_id: str
    item_rule_code: str
    item_name: str
    unit_price: int
    balance_after: int
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,item.public_id,rule.rule_code,rule.name,
                  receipt.unit_price_minor,balance.balance_minor
           FROM cmd_personal_equipment_purchase_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN inv_item_instance item ON item.item_instance_id=receipt.item_instance_id
           JOIN rule_rule rule ON rule.rule_id=receipt.item_rule_id
           JOIN fin_account_balance balance ON balance.account_id=receipt.payer_account_id
           WHERE receipt.command_id=%s
           """,
        (command_id,),
    ).fetchone()
    return PersonalEquipmentPurchaseResult(
        str(command_public_id), str(row[0]), str(row[1]), row[2], row[3],
        row[4], row[5], replayed
    )


def purchase_personal_equipment_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    campaign_public_id: str,
    actor_public_id: str,
    item_rule_code: str,
) -> PersonalEquipmentPurchaseResult:
    with connection.transaction():
        old = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command
               WHERE initiator_reference=%s AND idempotency_key=%s
               FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if old:
            if old[2:] != ("purchase_personal_equipment", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, old[0], old[1], True)

        state = connection.execute(
            """SELECT campaign.campaign_id,actor.actor_id,actor.name,
                      definition.rule_id,rule.name,definition.cost_credits,
                      definition.item_kind,account.account_id,balance.balance_minor
               FROM camp_campaign campaign
               JOIN actor_actor actor ON actor.campaign_id=campaign.campaign_id
               JOIN rule_rule rule ON rule.rule_code=%s AND rule.rule_status='approved'
               JOIN inv_item_definition definition ON definition.rule_id=rule.rule_id
               JOIN fin_actor_account ownership ON ownership.actor_id=actor.actor_id
                                                AND ownership.campaign_id=campaign.campaign_id
               JOIN fin_account account ON account.account_id=ownership.account_id
                                       AND account.account_status='open'
               JOIN fin_account_balance balance ON balance.account_id=account.account_id
               WHERE campaign.public_id=%s AND campaign.owner_reference=%s
                 AND actor.public_id=%s AND definition.cost_credits IS NOT NULL
                 AND definition.item_kind IN ('weapon','armor','equipment')
               ORDER BY account.account_id LIMIT 1
               FOR UPDATE OF actor,account""",
            (item_rule_code, campaign_public_id, initiator_reference, actor_public_id),
        ).fetchone()
        if not state:
            raise ValueError("Item is not purchasable by this controlled character")
        price = state[5]
        if state[8] < price:
            raise ValueError(f"Purchase costs Cr {price}; account holds Cr {state[8]}")

        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key)
               VALUES('purchase_personal_equipment',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        container = connection.execute(
            """SELECT container.container_id
               FROM inv_actor_container custody
               JOIN inv_container container USING(container_id,campaign_id)
               WHERE custody.actor_id=%s AND container.container_status='active'
               ORDER BY container.container_id LIMIT 1""",
            (state[1],),
        ).fetchone()
        if container:
            container_id = container[0]
        else:
            container_id = connection.execute(
                """INSERT INTO inv_container(campaign_id,name)
                   VALUES(%s,%s) RETURNING container_id""",
                (state[0], state[2] + " Personal Gear"),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO inv_actor_container VALUES(%s,%s,%s)",
                (container_id, state[0], state[1]),
            )

        transaction_id = None
        if price:
            vendor = connection.execute(
                """SELECT account_id FROM fin_account
                   WHERE campaign_id=%s AND account_code='personal-outfitter'""",
                (state[0],),
            ).fetchone()
            if vendor:
                vendor_id = vendor[0]
            else:
                vendor_id = connection.execute(
                    """INSERT INTO fin_account
                       (campaign_id,currency_code,account_code,name,account_kind)
                       VALUES(%s,'CR','personal-outfitter','Personal Outfitter','external')
                       RETURNING account_id""",
                    (state[0],),
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO fin_external_account VALUES(%s,%s,'Equipment vendors')",
                    (vendor_id, state[0]),
                )
            transaction_id = connection.execute(
                """INSERT INTO fin_transaction
                   (campaign_id,currency_code,description,command_id)
                   VALUES(%s,'CR',%s,%s) RETURNING transaction_id""",
                (state[0], "Purchase " + state[4], command_id),
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO fin_entry
                   (transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor)
                   VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)""",
                (transaction_id, state[0], state[7], -price,
                 transaction_id, state[0], vendor_id, price),
            )
            connection.execute("SELECT fin_post_transaction(%s)", (transaction_id,))

        transfer_id = connection.execute(
            """INSERT INTO inv_transfer
               (campaign_id,transfer_kind,transfer_status,command_id,description,completed_at)
               VALUES(%s,'custody_and_ownership','completed',%s,%s,clock_timestamp())
               RETURNING transfer_id""",
            (state[0], command_id, "Purchase " + state[4]),
        ).fetchone()[0]
        item_id = connection.execute(
            """INSERT INTO inv_item_instance
               (campaign_id,item_rule_id,instance_name,source_command_id)
               VALUES(%s,%s,%s,%s) RETURNING item_instance_id""",
            (state[0], state[3], state[4], command_id),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO inv_item_owner VALUES(%s,%s,%s,NULL,clock_timestamp(),%s)",
            (item_id, state[0], state[1], transfer_id),
        )
        connection.execute(
            "INSERT INTO inv_container_item VALUES(%s,%s,%s,clock_timestamp(),%s)",
            (item_id, state[0], container_id, transfer_id),
        )
        connection.execute(
            """INSERT INTO actor_item_holding(actor_id,item_rule_id,quantity)
               VALUES(%s,%s,1)
               ON CONFLICT(actor_id,item_rule_id)
               DO UPDATE SET quantity=actor_item_holding.quantity+1""",
            (state[1], state[3]),
        )
        if state[6] == "weapon":
            connection.execute(
                """INSERT INTO actor_weapon_state(actor_id,weapon_rule_id)
                   VALUES(%s,%s) ON CONFLICT DO NOTHING""",
                (state[1], state[3]),
            )
        connection.execute(
            """INSERT INTO cmd_personal_equipment_purchase_receipt
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[3], item_id, container_id,
             state[7], price, transaction_id, transfer_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event(command_id,event_order,event_type)
               VALUES(%s,1,'personal_equipment_purchased')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp()
               WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public_id, False)
