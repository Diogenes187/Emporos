"""Audited pre-career characteristic rerolls."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class CharacteristicRerollResult:
    command_public_id: str
    actor_public_id: str
    scores: tuple[tuple[str, int, int], ...]
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    actor_public_id = connection.execute(
        """SELECT actor.public_id FROM cmd_characteristic_reroll_receipt receipt
           JOIN actor_actor actor USING(actor_id) WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()[0]
    scores = connection.execute(
        """SELECT rule.rule_code,score.prior_score,score.resulting_score
           FROM cmd_characteristic_reroll_score score
           JOIN rule_rule rule ON rule.rule_id=score.characteristic_rule_id
           WHERE score.command_id=%s ORDER BY score.display_order""",
        (command_id,),
    ).fetchall()
    return CharacteristicRerollResult(
        str(command_public_id), str(actor_public_id), tuple(scores), replayed
    )


def reroll_characteristics_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> CharacteristicRerollResult:
    """Reroll all six characteristics before any career is entered."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("reroll_characteristics", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor.actor_id,actor.concurrency_version,
                      lifepath.lifepath_status
               FROM actor_actor actor
               LEFT JOIN actor_lifepath_state lifepath USING(actor_id)
               WHERE actor.public_id=%s AND actor.controller_reference=%s
               FOR UPDATE OF actor""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Actor is absent or not controlled by this player")
        has_career = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM actor_career_stint WHERE actor_id=%s)",
            (actor[0],),
        ).fetchone()[0]
        if has_career or actor[2] in ("completed", "deceased"):
            raise ValueError("Characteristics may be rerolled only before entering a career")
        definitions = connection.execute(
            """SELECT state.characteristic_rule_id,definition.display_order,
                      definition.normal_dice_count,definition.normal_die_sides,
                      definition.minimum_score,definition.maximum_score,
                      state.current_value
               FROM actor_characteristic state
               JOIN rule_characteristic definition
                 ON definition.rule_id=state.characteristic_rule_id
               WHERE state.actor_id=%s
               ORDER BY definition.display_order""",
            (actor[0],),
        ).fetchall()
        if len(definitions) != 6:
            raise RuntimeError("Character does not have six normal characteristics")
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('reroll_characteristics',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        version_after = actor[1] + 1
        connection.execute(
            """INSERT INTO cmd_characteristic_reroll_receipt
               (command_id,actor_id,actor_version_before,actor_version_after)
               VALUES (%s,%s,%s,%s)""",
            (command_id, actor[0], actor[1], version_after),
        )
        draw_order = 0
        for definition in definitions:
            dice = []
            for _ in range(definition[2]):
                result = rng.randint(1, definition[3])
                dice.append(result)
                draw_order += 1
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (%s,'character_creation',%s,%s,%s)""",
                    (command_id, draw_order, definition[3], result),
                )
            score = sum(dice)
            if definition[4] is not None:
                score = max(score, definition[4])
            if definition[5] is not None:
                score = min(score, definition[5])
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=%s,current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (score, score, actor[0], definition[0]),
            )
            connection.execute(
                """INSERT INTO cmd_characteristic_reroll_score
                   (command_id,characteristic_rule_id,display_order,prior_score,
                    dice_total,resulting_score)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (command_id, definition[0], definition[1], definition[6],
                 sum(dice), score),
            )
        connection.execute(
            "UPDATE actor_actor SET concurrency_version=%s WHERE actor_id=%s",
            (version_after, actor[0]),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event (command_id,event_order,event_type)
               VALUES (%s,1,'characteristics_rerolled')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public_id, False)
