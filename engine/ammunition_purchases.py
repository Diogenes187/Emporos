"""Audited purchase of source-defined personal ammunition reload units."""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class PersonalAmmunitionPurchaseResult:
    command_public_id: str
    actor_public_id: str
    ammunition_rule_code: str
    reload_units_purchased: int
    total_price: int
    supply_after: int
    balance_after: int
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,ammunition.rule_code,
                  receipt.reload_units_purchased,receipt.total_price_minor,
                  receipt.supply_after,balance.balance_minor
           FROM cmd_personal_ammunition_purchase_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule ammunition ON ammunition.rule_id=receipt.ammunition_rule_id
           JOIN fin_account_balance balance ON balance.account_id=receipt.payer_account_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return PersonalAmmunitionPurchaseResult(
        str(command_public_id), str(row[0]), row[1], row[2], row[3],
        row[4], row[5], replayed
    )


def purchase_personal_ammunition_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    campaign_public_id: str,
    actor_public_id: str,
    ammunition_rule_code: str,
    reload_units: int = 1,
) -> PersonalAmmunitionPurchaseResult:
    if reload_units <= 0 or reload_units > 100:
        raise ValueError("Ammunition purchase must be between 1 and 100 reload units")
    with connection.transaction():
        old = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s
               FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if old:
            if old[2:] != ("purchase_personal_ammunition", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, old[0], old[1], True)
        state = connection.execute(
            """SELECT campaign.campaign_id,actor.actor_id,definition.weapon_rule_id,
                      definition.ammunition_rule_id,definition.cost_credits,
                      account.account_id,balance.balance_minor,ammunition.name
               FROM camp_campaign campaign
               JOIN actor_actor actor ON actor.campaign_id=campaign.campaign_id
               JOIN rule_rule ammunition ON ammunition.rule_code=%s
                                         AND ammunition.rule_status='approved'
               JOIN inv_ammunition_definition definition
                 ON definition.ammunition_rule_id=ammunition.rule_id
               JOIN actor_item_holding holding ON holding.actor_id=actor.actor_id
                                              AND holding.item_rule_id=definition.weapon_rule_id
                                              AND holding.quantity>0
               JOIN fin_actor_account ownership ON ownership.actor_id=actor.actor_id
                                                AND ownership.campaign_id=campaign.campaign_id
               JOIN fin_account account ON account.account_id=ownership.account_id
                                       AND account.account_status='open'
               JOIN fin_account_balance balance ON balance.account_id=account.account_id
               WHERE campaign.public_id=%s AND campaign.owner_reference=%s
                 AND actor.public_id=%s
               ORDER BY account.account_id LIMIT 1
               FOR UPDATE OF actor,account""",
            (ammunition_rule_code, campaign_public_id, initiator_reference,
             actor_public_id),
        ).fetchone()
        if not state:
            raise ValueError("Ammunition is unavailable or the character holds no compatible weapon")
        total = state[4] * reload_units
        if state[6] < total:
            raise ValueError(f"Purchase costs Cr {total}; account holds Cr {state[6]}")
        existing = connection.execute(
            """SELECT reload_units_available FROM actor_ammunition_supply
               WHERE actor_id=%s AND ammunition_rule_id=%s FOR UPDATE""",
            (state[1], state[3]),
        ).fetchone()
        if (existing[0] if existing else 0) + reload_units > 32767:
            raise ValueError("Ammunition supply exceeds the supported limit")
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key)
               VALUES('purchase_personal_ammunition',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        transaction_id = None
        if total:
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
                (state[0], "Purchase " + state[7], command_id),
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO fin_entry
                   (transaction_id,campaign_id,currency_code,account_id,entry_order,amount_minor)
                   VALUES(%s,%s,'CR',%s,1,%s),(%s,%s,'CR',%s,2,%s)""",
                (transaction_id, state[0], state[5], -total,
                 transaction_id, state[0], vendor_id, total),
            )
            connection.execute("SELECT fin_post_transaction(%s)", (transaction_id,))
        supply_after = connection.execute(
            """INSERT INTO actor_ammunition_supply
               (actor_id,ammunition_rule_id,reload_units_available)
               VALUES(%s,%s,%s)
               ON CONFLICT(actor_id,ammunition_rule_id)
               DO UPDATE SET reload_units_available=
                 actor_ammunition_supply.reload_units_available+EXCLUDED.reload_units_available
               RETURNING reload_units_available""",
            (state[1], state[3], reload_units),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_personal_ammunition_purchase_receipt
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[2], state[3], state[5],
             reload_units, state[4], total, transaction_id, supply_after),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event(command_id,event_order,event_type)
               VALUES(%s,1,'personal_ammunition_purchased')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp()
               WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public_id, False)
