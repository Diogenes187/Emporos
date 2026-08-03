"""Authoritative campaign lifecycle commands."""

from __future__ import annotations

from dataclasses import dataclass

import psycopg


PLAY_MODES = {
    "player_directed",
    "human_refereed",
    "ai_assisted",
    "ai_refereed",
}


@dataclass(frozen=True)
class CampaignCreationResult:
    command_public_id: str
    campaign_public_id: str
    name: str
    play_mode: str
    day_number: int
    second_of_day: int
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """
        SELECT campaign.public_id,campaign.name,campaign.play_mode,
               receipt.initial_day_number,receipt.initial_second_of_day
          FROM cmd_campaign_creation_receipt receipt
          JOIN camp_campaign campaign
            ON campaign.campaign_id=receipt.campaign_id
         WHERE receipt.command_id=%s
        """,
        (command_id,),
    ).fetchone()
    return CampaignCreationResult(
        str(command_public_id), str(row[0]), row[1], row[2], row[3], row[4],
        replayed,
    )


def create_campaign_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    name: str,
    play_mode: str = "ai_refereed",
    day_number: int = 0,
    second_of_day: int = 0,
) -> CampaignCreationResult:
    """Create a campaign, clock, event, and receipt in one transaction."""
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Campaign name cannot be blank")
    if play_mode not in PLAY_MODES:
        raise ValueError("Unknown campaign play mode")
    if not initiator_reference.strip():
        raise ValueError("Initiator reference cannot be blank")
    if not idempotency_key.strip():
        raise ValueError("Idempotency key cannot be blank")
    if not 0 <= second_of_day <= 86399:
        raise ValueError("Second of day must be between 0 and 86399")

    with connection.transaction():
        existing = connection.execute(
            """
            SELECT command_id,public_id,command_type,command_status
              FROM cmd_command
             WHERE initiator_reference=%s AND idempotency_key=%s
             FOR UPDATE
            """,
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("create_campaign", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)

        command_id, command_public_id = connection.execute(
            """
            INSERT INTO cmd_command
                (command_type,initiator_reference,idempotency_key)
            VALUES ('create_campaign',%s,%s)
            RETURNING command_id,public_id
            """,
            (initiator_reference, idempotency_key),
        ).fetchone()
        campaign_id, campaign_public_id = connection.execute(
            """
            INSERT INTO camp_campaign (name,owner_reference,play_mode)
            VALUES (%s,%s,%s)
            RETURNING campaign_id,public_id
            """,
            (clean_name, initiator_reference, play_mode),
        ).fetchone()
        connection.execute(
            """
            UPDATE camp_clock
               SET day_number=%s,second_of_day=%s,
                   concurrency_version=concurrency_version+1,
                   advanced_at=clock_timestamp()
             WHERE campaign_id=%s
            """,
            (day_number, second_of_day, campaign_id),
        )
        connection.execute(
            """
            INSERT INTO cmd_campaign_creation_receipt
                (command_id,campaign_id,initial_day_number,initial_second_of_day)
            VALUES (%s,%s,%s,%s)
            """,
            (command_id, campaign_id, day_number, second_of_day),
        )
        connection.execute(
            """
            INSERT INTO cmd_domain_event (command_id,event_order,event_type)
            VALUES (%s,1,'campaign_created')
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
        return CampaignCreationResult(
            str(command_public_id), str(campaign_public_id), clean_name,
            play_mode, day_number, second_of_day, False,
        )
