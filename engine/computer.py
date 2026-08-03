"""Deterministic Computer-0 basic operations."""
from dataclasses import dataclass
import psycopg


@dataclass(frozen=True)
class ComputerBasicOperationResult:
    command_public_id: str
    actor_public_id: str
    operation_code: str
    target_reference: str
    computer_skill_level: int
    performed_without_check: bool
    replayed: bool


def _load(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.operation_code,
                  receipt.target_reference,receipt.computer_skill_level,
                  receipt.performed_without_check
           FROM cmd_computer_basic_operation_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return ComputerBasicOperationResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4], replayed)


def perform_computer_basic_operation_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, operation_code: str,
    target_reference: str,
) -> ComputerBasicOperationResult:
    if not target_reference.strip():
        raise ValueError("Computer operation requires a target reference")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),).fetchone()
        if existing:
            if existing[2:] != ("perform_computer_basic_operation", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT actor.actor_id,actor_skill.skill_level
               FROM actor_actor actor
               JOIN rule_computer_basic_use rule ON true
               JOIN actor_skill ON actor_skill.actor_id=actor.actor_id
                AND actor_skill.skill_rule_id=rule.skill_rule_id
               WHERE actor.public_id=%s AND actor.controller_reference=%s
               FOR UPDATE OF actor,actor_skill""",
            (actor_public_id, initiator_reference),).fetchone()
        if state is None:
            raise ValueError("Basic operation requires controlled Computer-0 or better actor")
        if connection.execute(
            "SELECT 1 FROM rule_computer_basic_operation WHERE operation_code=%s",
            (operation_code,),).fetchone() is None:
            raise ValueError("Unknown Computer basic operation")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('perform_computer_basic_operation',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),).fetchone()
        connection.execute(
            """INSERT INTO cmd_computer_basic_operation_receipt
               VALUES (%s,%s,%s,%s,%s,true)""",
            (command_id, state[0], operation_code,
             target_reference.strip(), state[1]),)
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),)
        return _load(connection, command_id, public_id, False)
