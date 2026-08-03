"""Relational, source-audited Liaison negotiations."""

from dataclasses import dataclass
import secrets

import psycopg

from engine.tasks import resolve_actor_task_command


@dataclass(frozen=True)
class LiaisonNegotiationParticipant:
    actor_public_id: str
    characteristic_rule_code: str
    task_command_public_id: str
    check_total: int
    gained_advantage: bool


@dataclass(frozen=True)
class LiaisonNegotiationResult:
    command_public_id: str
    negotiation_public_id: str
    status: str
    winner_actor_public_id: str | None
    winning_total: int
    participants: tuple[LiaisonNegotiationParticipant, ...]
    replayed: bool


def _load(connection, command_id, command_public_id, replayed):
    header = connection.execute(
        """SELECT negotiation.public_id,negotiation.negotiation_status,
                  winner.public_id,receipt.winning_total
           FROM cmd_liaison_negotiation_receipt receipt
           JOIN camp_liaison_negotiation negotiation USING(negotiation_id)
           LEFT JOIN actor_actor winner
             ON winner.actor_id=negotiation.winner_actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    rows = connection.execute(
        """SELECT actor.public_id,characteristic.rule_code,task.public_id,
                  participant.check_total,participant.gained_advantage
           FROM cmd_liaison_negotiation_participant participant
           JOIN actor_actor actor ON actor.actor_id=participant.actor_id
           JOIN rule_rule characteristic
             ON characteristic.rule_id=participant.characteristic_rule_id
           JOIN cmd_command task ON task.command_id=participant.task_command_id
           WHERE participant.command_id=%s
           ORDER BY participant.participant_order""",
        (command_id,),
    ).fetchall()
    return LiaisonNegotiationResult(
        str(command_public_id), str(header[0]), header[1],
        None if header[2] is None else str(header[2]), header[3],
        tuple(LiaisonNegotiationParticipant(
            str(row[0]), row[1], str(row[2]), row[3], row[4])
              for row in rows),
        replayed,
    )


def resolve_liaison_negotiation_command(
    connection: psycopg.Connection, *, referee_reference: str,
    idempotency_key: str, scene_reference: str, subject_reference: str,
    participants: list[dict], random_source=None,
) -> LiaisonNegotiationResult:
    """Resolve opposed Liaison checks; equal highest totals remain tied."""
    rng = random_source or secrets.SystemRandom()
    if len(participants) < 2:
        raise ValueError("Liaison negotiation requires at least two participants")
    if any(not item.get("actor_public_id")
           or not item.get("characteristic_rule_code") for item in participants):
        raise ValueError("Each participant requires an actor and characteristic")
    actor_public_ids = [item["actor_public_id"] for item in participants]
    if len(set(actor_public_ids)) != len(actor_public_ids):
        raise ValueError("Liaison negotiation participants must be unique")
    if not scene_reference.strip() or not subject_reference.strip():
        raise ValueError("Liaison negotiation requires scene and subject references")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (referee_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_liaison_negotiation", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        actors = connection.execute(
            """SELECT actor.public_id,actor.actor_id,actor.campaign_id,
                      actor.controller_reference
               FROM actor_actor actor
               JOIN camp_campaign campaign USING(campaign_id)
               WHERE actor.public_id=ANY(%s) AND campaign.owner_reference=%s
               FOR UPDATE OF actor""",
            (actor_public_ids, referee_reference),
        ).fetchall()
        by_public = {str(row[0]): row for row in actors}
        if set(by_public) != set(actor_public_ids):
            raise ValueError("All participants must belong to the referee's campaign")
        campaigns = {row[2] for row in actors}
        if len(campaigns) != 1:
            raise ValueError("All participants must belong to one campaign")
        resolved = []
        for order, item in enumerate(participants, 1):
            actor = by_public[item["actor_public_id"]]
            task = resolve_actor_task_command(
                connection, initiator_reference=actor[3],
                idempotency_key=(
                    f"liaison-negotiation:{referee_reference}:"
                    f"{idempotency_key}:{order}"),
                actor_public_id=item["actor_public_id"],
                characteristic_rule_code=item["characteristic_rule_code"],
                skill_rule_code="skill.liaison",
                difficulty_rule_code="difficulty.average",
                random_source=rng,
            )
            task_command_id = connection.execute(
                "SELECT command_id FROM cmd_command WHERE public_id=%s",
                (task.command_public_id,),
            ).fetchone()[0]
            resolved.append((order, item, actor, task, task_command_id))
        winning_total = max(item[3].total for item in resolved)
        leaders = [item for item in resolved if item[3].total == winning_total]
        tied = len(leaders) != 1
        winner_actor_id = None if tied else leaders[0][2][1]
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_liaison_negotiation',%s,%s)
               RETURNING command_id,public_id""",
            (referee_reference, idempotency_key),
        ).fetchone()
        rule_id = connection.execute(
            "SELECT rule_id FROM rule_liaison_negotiation").fetchone()[0]
        negotiation_id, negotiation_public_id = connection.execute(
            """INSERT INTO camp_liaison_negotiation
               (campaign_id,scene_reference,subject_reference,
                negotiation_status,winner_actor_id,source_command_id)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING negotiation_id,public_id""",
            (next(iter(campaigns)), scene_reference.strip(),
             subject_reference.strip(), "tied" if tied else "resolved",
             winner_actor_id, command_id),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_liaison_negotiation_receipt
               (command_id,negotiation_id,rule_id,participant_count,
                winning_total,tied_at_winning_total)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, negotiation_id, rule_id, len(resolved),
             winning_total, tied),
        )
        for order, item, actor, task, task_command_id in resolved:
            characteristic_id = connection.execute(
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s",
                (item["characteristic_rule_code"],),
            ).fetchone()[0]
            connection.execute(
                """INSERT INTO cmd_liaison_negotiation_participant
                   (command_id,participant_order,actor_id,
                    characteristic_rule_id,task_command_id,check_total,
                    gained_advantage) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (command_id, order, actor[1], characteristic_id,
                 task_command_id, task.total,
                 not tied and task.total == winning_total),
            )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load(connection, command_id, command_public_id, False)
