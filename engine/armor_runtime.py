"""Transactional personal armor instance state and immutable receipts."""
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class ArmorEquipResult:
    command_public_id: str
    action: str
    actor_public_id: str
    item_public_id: str
    layers: tuple[tuple[str, int], ...]
    replayed: bool


@dataclass(frozen=True)
class ArmorUsageResult:
    command_public_id: str
    item_public_id: str
    laser_rating_before: int
    laser_rating_after: int
    life_support_before: int | None
    life_support_after: int | None
    state_version_after: int
    replayed: bool


def _load_equip(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT receipt.equip_action,actor.public_id,item.public_id
           FROM cmd_personal_armor_equip_receipt receipt
           JOIN actor_actor actor USING (actor_id)
           JOIN inv_item_instance item USING (item_instance_id)
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    layers = tuple(
        (str(item), order) for item, order in connection.execute(
            """SELECT item.public_id,layer.layer_order
               FROM cmd_personal_armor_layer_receipt layer
               JOIN inv_item_instance item USING (item_instance_id)
               WHERE layer.command_id=%s ORDER BY layer.layer_order""",
            (command_id,)).fetchall())
    return ArmorEquipResult(
        str(public_id), row[0], str(row[1]), str(row[2]), layers, replayed)


def _load_usage(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT item.public_id,receipt.laser_rating_before,
                  receipt.laser_rating_after,receipt.life_support_before,
                  receipt.life_support_after,receipt.state_version_after
           FROM cmd_personal_armor_usage_receipt receipt
           JOIN inv_item_instance item USING (item_instance_id)
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return ArmorUsageResult(
        str(public_id), str(row[0]), *row[1:], replayed)


def _existing(connection, initiator, key, command_type):
    row = connection.execute(
        """SELECT command_id,public_id,command_type,command_status
           FROM cmd_command WHERE initiator_reference=%s
             AND idempotency_key=%s FOR UPDATE""", (initiator, key)).fetchone()
    if row and row[2:] != (command_type, "completed"):
        raise RuntimeError("Idempotency key belongs to another command")
    return row


def equip_personal_armor_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, item_public_id: str,
    layer_order: int,
) -> ArmorEquipResult:
    if layer_order not in (1, 2):
        raise ValueError("Armor layer order must be 1 or 2")
    with connection.transaction():
        old = _existing(
            connection, initiator_reference, idempotency_key,
            "equip_personal_armor")
        if old:
            return _load_equip(connection, old[0], old[1], True)
        row = connection.execute(
            """SELECT actor.actor_id,actor.campaign_id,item.item_instance_id,
                      COALESCE(armor.laser_armor_rating,
                               armor.general_armor_rating),
                      support.duration_seconds,
                      exception.armor_rule_id IS NOT NULL
               FROM actor_actor actor
               JOIN inv_item_instance item
                 ON item.public_id=%s
                AND item.campaign_id=actor.campaign_id
                AND item.item_status='active'
               JOIN inv_item_owner owner
                 ON owner.item_instance_id=item.item_instance_id
                AND owner.campaign_id=item.campaign_id
                AND owner.actor_id=actor.actor_id
               JOIN inv_armor_definition armor
                 ON armor.item_rule_id=item.item_rule_id
               LEFT JOIN rule_armor_life_support support
                 ON support.armor_rule_id=item.item_rule_id
               LEFT JOIN rule_armor_layer_exception exception
                 ON exception.armor_rule_id=item.item_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor,item""",
            (item_public_id, actor_public_id, initiator_reference)).fetchone()
        if row is None:
            raise ValueError("Actor does not own this active armor item")
        actor_id, campaign_id, item_id, laser, life, new_exception = row
        current = connection.execute(
            """SELECT layer.item_instance_id,layer.layer_order,
                      exception.armor_rule_id IS NOT NULL
               FROM inv_actor_armor_layer layer
               JOIN inv_item_instance item USING (item_instance_id)
               LEFT JOIN rule_armor_layer_exception exception
                 ON exception.armor_rule_id=item.item_rule_id
               WHERE layer.actor_id=%s ORDER BY layer.layer_order
               FOR UPDATE OF layer""", (actor_id,)).fetchall()
        if any(item == item_id for item, _, _ in current):
            raise ValueError("Armor item is already equipped")
        if len(current) >= 2:
            raise ValueError("At most two personal armor layers are allowed")
        if not current and layer_order != 1:
            raise ValueError("A single armor item occupies layer 1")
        if current and not (new_exception ^ current[0][2]):
            raise ValueError("Two layers require exactly one Reflec")
        command = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('equip_personal_armor',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """INSERT INTO inv_armor_instance_state
               VALUES (%s,%s,%s,%s,1) ON CONFLICT DO NOTHING""",
            (item_id, campaign_id, laser, life))
        if current and layer_order == 1:
            connection.execute(
                """UPDATE inv_actor_armor_layer SET layer_order=2
                   WHERE actor_id=%s""", (actor_id,))
        connection.execute(
            """INSERT INTO inv_actor_armor_layer
               (actor_id,campaign_id,item_instance_id,layer_order,
                source_command_id) VALUES (%s,%s,%s,%s,%s)""",
            (actor_id, campaign_id, item_id, layer_order, command[0]))
        connection.execute(
            """INSERT INTO cmd_personal_armor_equip_receipt
               VALUES (%s,%s,%s,%s,'equip',%s,%s,%s)""",
            (command[0], campaign_id, actor_id, item_id, layer_order,
             len(current), len(current)+1))
        connection.execute(
            """INSERT INTO cmd_personal_armor_layer_receipt
               SELECT %s,item_instance_id,layer_order
               FROM inv_actor_armor_layer WHERE actor_id=%s""",
            (command[0], actor_id))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command[0],))
        return _load_equip(connection, command[0], command[1], False)


def unequip_personal_armor_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, item_public_id: str,
) -> ArmorEquipResult:
    with connection.transaction():
        old = _existing(
            connection, initiator_reference, idempotency_key,
            "unequip_personal_armor")
        if old:
            return _load_equip(connection, old[0], old[1], True)
        row = connection.execute(
            """SELECT actor.actor_id,actor.campaign_id,item.item_instance_id
               FROM actor_actor actor
               JOIN inv_item_instance item
                 ON item.public_id=%s AND item.campaign_id=actor.campaign_id
               JOIN inv_actor_armor_layer layer
                 ON layer.item_instance_id=item.item_instance_id
                AND layer.actor_id=actor.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor,layer""",
            (item_public_id, actor_public_id, initiator_reference)).fetchone()
        if row is None:
            raise ValueError("Armor item is not equipped by this actor")
        actor_id, campaign_id, item_id = row
        count = connection.execute(
            "SELECT count(*) FROM inv_actor_armor_layer WHERE actor_id=%s",
            (actor_id,)).fetchone()[0]
        command = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('unequip_personal_armor',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            "DELETE FROM inv_actor_armor_layer WHERE item_instance_id=%s",
            (item_id,))
        connection.execute(
            """UPDATE inv_actor_armor_layer SET layer_order=1
               WHERE actor_id=%s""", (actor_id,))
        connection.execute(
            """INSERT INTO cmd_personal_armor_equip_receipt
               VALUES (%s,%s,%s,%s,'unequip',NULL,%s,%s)""",
            (command[0], campaign_id, actor_id, item_id, count, count-1))
        connection.execute(
            """INSERT INTO cmd_personal_armor_layer_receipt
               SELECT %s,item_instance_id,layer_order
               FROM inv_actor_armor_layer WHERE actor_id=%s""",
            (command[0], actor_id))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command[0],))
        return _load_equip(connection, command[0], command[1], False)


def apply_personal_armor_usage_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, item_public_id: str,
    laser_hits: int = 0, life_support_seconds_used: int = 0,
) -> ArmorUsageResult:
    if laser_hits < 0 or life_support_seconds_used < 0:
        raise ValueError("Armor resource usage cannot be negative")
    if laser_hits + life_support_seconds_used == 0:
        raise ValueError("Armor usage must consume a resource")
    with connection.transaction():
        old = _existing(
            connection, initiator_reference, idempotency_key,
            "apply_personal_armor_usage")
        if old:
            return _load_usage(connection, old[0], old[1], True)
        row = connection.execute(
            """SELECT actor.actor_id,actor.campaign_id,item.item_instance_id,
                      state.current_laser_armor_rating,
                      state.life_support_seconds_remaining,
                      state.concurrency_version,
                      degradation.armor_rating_loss_per_hit
               FROM actor_actor actor
               JOIN inv_item_instance item
                 ON item.public_id=%s AND item.campaign_id=actor.campaign_id
               JOIN inv_actor_armor_layer layer
                 ON layer.item_instance_id=item.item_instance_id
                AND layer.actor_id=actor.actor_id
               JOIN inv_armor_instance_state state
                 ON state.item_instance_id=item.item_instance_id
               LEFT JOIN rule_armor_degradation degradation
                 ON degradation.armor_rule_id=item.item_rule_id
                AND degradation.damage_type='laser'
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor,state""",
            (item_public_id, actor_public_id, initiator_reference)).fetchone()
        if row is None:
            raise ValueError("Equipped armor state does not exist")
        actor_id, campaign_id, item_id, laser_before, life_before, version, loss = row
        if laser_hits and loss is None:
            raise ValueError("This armor does not degrade from laser hits")
        if life_support_seconds_used and life_before is None:
            raise ValueError("This armor has no life-support resource")
        if life_before is not None and life_support_seconds_used > life_before:
            raise ValueError("Life-support use exceeds remaining supply")
        laser_after = max(laser_before-laser_hits*(loss or 0), 0)
        life_after = (
            None if life_before is None
            else life_before-life_support_seconds_used)
        command = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_personal_armor_usage',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """UPDATE inv_armor_instance_state
               SET current_laser_armor_rating=%s,
                   life_support_seconds_remaining=%s,
                   concurrency_version=concurrency_version+1
               WHERE item_instance_id=%s""",
            (laser_after, life_after, item_id))
        connection.execute(
            """INSERT INTO cmd_personal_armor_usage_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command[0], campaign_id, actor_id, item_id, laser_hits,
             life_support_seconds_used, laser_before, laser_after,
             life_before, life_after, version, version+1))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command[0],))
        return _load_usage(connection, command[0], command[1], False)
