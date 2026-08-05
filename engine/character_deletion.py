"""Delete a character from gameplay while preserving relational history."""

import psycopg


def delete_character_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
):
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("delete_character", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return str(existing[1])
        actor = connection.execute(
            """SELECT actor_id,name,concurrency_version,lifecycle_status
               FROM actor_actor WHERE public_id=%s
                 AND controller_reference=%s FOR UPDATE""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Character is absent or not controlled by this player")
        if actor[3] != "active":
            raise ValueError("Character is already deleted")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('delete_character',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        version_after = actor[2] + 1
        connection.execute(
            """UPDATE actor_actor SET lifecycle_status='deleted',
                      concurrency_version=%s WHERE actor_id=%s""",
            (version_after, actor[0]),
        )
        connection.execute(
            """UPDATE iam_character_controller SET controller_status='revoked',
                      ended_at=clock_timestamp()
               WHERE actor_id=%s AND controller_status='active'""",
            (actor[0],),
        )
        connection.execute(
            """INSERT INTO cmd_character_deletion_receipt
               (command_id,actor_id,actor_version_before,actor_version_after,
                deleted_character_name)
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, actor[0], actor[2], version_after, actor[1]),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event(command_id,event_order,event_type)
               VALUES (%s,1,'character_deleted')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return str(public_id)
