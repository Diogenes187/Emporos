"""Recoverably discard an unfinished pre-career character."""

import psycopg


def abandon_unfinished_character_command(
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
            if existing[2:] != ("abandon_unfinished_character", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return str(existing[1])
        actor = connection.execute(
            """SELECT actor_id,concurrency_version,lifecycle_status
               FROM actor_actor WHERE public_id=%s
                 AND controller_reference=%s FOR UPDATE""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Actor is absent or not controlled by this player")
        if actor[2] != "active":
            raise ValueError("Character is already discarded")
        if connection.execute(
            "SELECT EXISTS(SELECT 1 FROM actor_career_stint WHERE actor_id=%s)",
            (actor[0],),
        ).fetchone()[0]:
            raise ValueError("Only a character that has not entered a career may be discarded")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('abandon_unfinished_character',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        version_after = actor[1] + 1
        connection.execute(
            """UPDATE actor_actor SET lifecycle_status='abandoned',
                      concurrency_version=%s WHERE actor_id=%s""",
            (version_after, actor[0]),
        )
        connection.execute(
            """INSERT INTO cmd_character_abandonment_receipt
               (command_id,actor_id,actor_version_before,actor_version_after)
               VALUES (%s,%s,%s,%s)""",
            (command_id, actor[0], actor[1], version_after),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event(command_id,event_order,event_type)
               VALUES (%s,1,'unfinished_character_abandoned')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return str(public_id)
