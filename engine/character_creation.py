"""Character initialization before the existing Cepheus lifepath commands."""

from __future__ import annotations

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class InitialCharacteristic:
    rule_code: str
    name: str
    abbreviation: str
    score: int
    dice: tuple[int, ...]


@dataclass(frozen=True)
class CharacterInitializationResult:
    command_public_id: str
    campaign_public_id: str
    actor_public_id: str
    character_name: str
    characteristics: tuple[InitialCharacteristic, ...]
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    identity = connection.execute(
        """
        SELECT campaign.public_id,actor.public_id,receipt.character_name
          FROM cmd_character_initialization_receipt receipt
          JOIN camp_campaign campaign USING (campaign_id)
          JOIN actor_actor actor USING (actor_id)
         WHERE receipt.command_id=%s
        """,
        (command_id,),
    ).fetchone()
    scores = []
    for row in connection.execute(
        """
        SELECT rule.rule_code,rule.name,characteristic.abbreviation,
               score.resulting_score,score.display_order
          FROM cmd_character_initialization_score score
          JOIN rule_characteristic characteristic
            ON characteristic.rule_id=score.characteristic_rule_id
          JOIN rule_rule rule ON rule.rule_id=characteristic.rule_id
         WHERE score.command_id=%s
         ORDER BY score.display_order
        """,
        (command_id,),
    ).fetchall():
        dice = tuple(
            draw[0] for draw in connection.execute(
                """
                SELECT result FROM cmd_random_draw
                 WHERE command_id=%s AND draw_group='character_creation'
                   AND draw_order BETWEEN %s AND %s
                 ORDER BY draw_order
                """,
                (command_id, (row[4] - 1) * 2 + 1, row[4] * 2),
            ).fetchall()
        )
        scores.append(InitialCharacteristic(row[0], row[1], row[2], row[3], dice))
    return CharacterInitializationResult(
        str(command_public_id),str(identity[0]),str(identity[1]),identity[2],
        tuple(scores),replayed,
    )


def initialize_character_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    campaign_public_id: str,
    character_name: str,
    random_source=None,
) -> CharacterInitializationResult:
    """Create an actor and roll every normal source-defined characteristic."""
    name = character_name.strip()
    if not name:
        raise ValueError("Character name cannot be blank")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """
            SELECT command_id,public_id,command_type,command_status
              FROM cmd_command
             WHERE initiator_reference=%s AND idempotency_key=%s
             FOR UPDATE
            """,
            (initiator_reference,idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("initialize_character","completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection,existing[0],existing[1],True)
        campaign = connection.execute(
            """
            SELECT campaign_id FROM camp_campaign
             WHERE public_id=%s AND owner_reference=%s
               AND campaign_status='active'
             FOR UPDATE
            """,
            (campaign_public_id,initiator_reference),
        ).fetchone()
        if campaign is None:
            raise PermissionError("Campaign is absent or not controlled by this player")
        definitions = connection.execute(
            """
            SELECT characteristic.rule_id,rule.rule_code,rule.name,
                   characteristic.abbreviation,characteristic.display_order,
                   characteristic.normal_dice_count,
                   characteristic.normal_die_sides,
                   characteristic.minimum_score,characteristic.maximum_score
              FROM rule_characteristic characteristic
              JOIN rule_rule rule ON rule.rule_id=characteristic.rule_id
             WHERE characteristic.normal_dice_count IS NOT NULL
             ORDER BY characteristic.display_order
            """
        ).fetchall()
        if not definitions:
            raise RuntimeError("No initial characteristic definitions are installed")
        command_id, command_public = connection.execute(
            """
            INSERT INTO cmd_command
                (command_type,initiator_reference,idempotency_key)
            VALUES ('initialize_character',%s,%s)
            RETURNING command_id,public_id
            """,
            (initiator_reference,idempotency_key),
        ).fetchone()
        actor_id, actor_public = connection.execute(
            """
            INSERT INTO actor_actor
                (campaign_id,name,controller_reference)
            VALUES (%s,%s,%s)
            RETURNING actor_id,public_id
            """,
            (campaign[0],name,initiator_reference),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO cmd_character_initialization_receipt
                (command_id,campaign_id,actor_id,character_name,
                 actor_version_after)
            VALUES (%s,%s,%s,%s,1)
            """,
            (command_id,campaign[0],actor_id,name),
        )
        draw_order = 0
        for definition in definitions:
            dice = []
            for _ in range(definition[5]):
                result = rng.randint(1,definition[6])
                dice.append(result)
                draw_order += 1
                connection.execute(
                    """
                    INSERT INTO cmd_random_draw
                        (command_id,draw_group,draw_order,die_sides,result)
                    VALUES (%s,'character_creation',%s,%s,%s)
                    """,
                    (command_id,draw_order,definition[6],result),
                )
            score = sum(dice)
            if definition[7] is not None:
                score = max(score,definition[7])
            if definition[8] is not None:
                score = min(score,definition[8])
            connection.execute(
                """
                INSERT INTO actor_characteristic
                    (actor_id,characteristic_rule_id,maximum_value,current_value)
                VALUES (%s,%s,%s,%s)
                """,
                (actor_id,definition[0],score,score),
            )
            connection.execute(
                """
                INSERT INTO cmd_character_initialization_score
                    (command_id,characteristic_rule_id,display_order,
                     dice_total,resulting_score)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (command_id,definition[0],definition[4],sum(dice),score),
            )
        connection.execute(
            """
            INSERT INTO cmd_domain_event (command_id,event_order,event_type)
            VALUES (%s,1,'character_initialized')
            """,
            (command_id,),
        )
        connection.execute(
            """
            UPDATE cmd_command
               SET command_status='completed',completed_at=clock_timestamp()
             WHERE command_id=%s
            """,
            (command_id,),
        )
        return _load(connection,command_id,command_public,False)

