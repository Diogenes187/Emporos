"""Transactional animal reaction resolution from canonical subtype rules."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class AnimalContext:
    command_public_id: str
    encounter_public_id: str
    animal_actor_public_id: str
    context_version: int
    replayed: bool


@dataclass(frozen=True)
class AnimalReaction:
    command_public_id: str
    encounter_public_id: str
    animal_actor_public_id: str
    provocation_number: int
    dice: tuple[int, int]
    roll_total: int
    attack_condition_met: bool
    flee_condition_met: bool
    outcome: str
    replayed: bool


def _existing(connection, initiator, key):
    return connection.execute(
        """SELECT command_id,public_id,command_type,command_status
           FROM cmd_command WHERE initiator_reference=%s
           AND idempotency_key=%s FOR UPDATE""", (initiator, key)
    ).fetchone()


def _owned_animal_encounter(connection, encounter_public_id, initiator):
    row = connection.execute(
        """SELECT e.encounter_id,c.campaign_id,c.owner_reference
           FROM enc_encounter e JOIN camp_campaign c
             ON c.campaign_id=e.campaign_id
           WHERE e.public_id=%s AND e.encounter_status='active'
             AND e.current_mode='animal_reaction' FOR UPDATE OF e""",
        (encounter_public_id,),
    ).fetchone()
    if row is None:
        raise ValueError("Active animal-reaction encounter does not exist")
    if row[2] != initiator:
        raise PermissionError("Initiator does not own this campaign")
    return row


def set_animal_reaction_context_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    animal_actor_public_id: str, animals_outnumber_characters: bool,
    animal_has_surprise: bool, animal_is_surprised: bool,
    animal_bigger_than_character: bool, attack_possible: bool,
) -> AnimalContext:
    with connection.transaction():
        existing = _existing(connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("set_animal_reaction_context", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,a.public_id,r.context_version
                   FROM cmd_animal_context_receipt r
                   JOIN enc_encounter e ON e.encounter_id=r.encounter_id
                   JOIN actor_actor a ON a.actor_id=r.animal_actor_id
                   WHERE r.command_id=%s""", (existing[0],)
            ).fetchone()
            return AnimalContext(
                str(existing[1]), str(row[0]), str(row[1]), row[2], True)
        if animal_has_surprise and animal_is_surprised:
            raise ValueError("Both sides cannot have surprise")
        encounter = _owned_animal_encounter(
            connection, encounter_public_id, initiator_reference)
        animal = connection.execute(
            """SELECT a.actor_id FROM actor_actor a
               JOIN actor_animal_profile p ON p.actor_id=a.actor_id
               JOIN enc_participant ep ON ep.actor_id=a.actor_id
               WHERE a.public_id=%s AND a.campaign_id=%s
                 AND ep.encounter_id=%s AND ep.participant_role='animal'""",
            (animal_actor_public_id, encounter[1], encounter[0]),
        ).fetchone()
        if animal is None:
            raise ValueError("Animal must be a profiled encounter participant")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('set_animal_reaction_context',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        current = connection.execute(
            """SELECT context_version FROM enc_animal_reaction_context
               WHERE encounter_id=%s AND animal_actor_id=%s FOR UPDATE""",
            (encounter[0], animal[0]),
        ).fetchone()
        version = current[0] + 1 if current else 1
        connection.execute(
            """INSERT INTO enc_animal_reaction_context
               (encounter_id,animal_actor_id,context_version,
                animals_outnumber_characters,animal_has_surprise,
                animal_is_surprised,animal_bigger_than_character,
                attack_possible)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (encounter_id,animal_actor_id) DO UPDATE SET
               context_version=EXCLUDED.context_version,
               animals_outnumber_characters=EXCLUDED.animals_outnumber_characters,
               animal_has_surprise=EXCLUDED.animal_has_surprise,
               animal_is_surprised=EXCLUDED.animal_is_surprised,
               animal_bigger_than_character=EXCLUDED.animal_bigger_than_character,
               attack_possible=EXCLUDED.attack_possible""",
            (encounter[0], animal[0], version, animals_outnumber_characters,
             animal_has_surprise, animal_is_surprised,
             animal_bigger_than_character, attack_possible))
        connection.execute(
            "INSERT INTO cmd_animal_context_receipt VALUES (%s,%s,%s,%s)",
            (command_id, encounter[0], animal[0], version))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'animal_reaction_context_set')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return AnimalContext(
            str(public_id), encounter_public_id,
            animal_actor_public_id, version, False)


def _condition_met(condition, roll, context):
    kind, threshold, alternate, possible = condition
    if possible and not context["attack_possible"]:
        return False
    if kind == "roll_at_least":
        return roll >= threshold
    if kind == "roll_at_most":
        return roll <= threshold
    if kind == "outnumbers_characters":
        return context["outnumbers"]
    if kind == "has_surprise":
        return context["has_surprise"]
    if kind == "is_surprised":
        return context["is_surprised"]
    if kind == "size_dependent_roll":
        return roll >= (threshold if context["bigger"] else alternate)
    raise ValueError(f"Unknown animal reaction condition: {kind}")


def resolve_animal_reaction_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    animal_actor_public_id: str, provocation_number: int,
    random_source=None,
) -> AnimalReaction:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = _existing(connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("resolve_animal_reaction", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,a.public_id,r.provocation_number,
                          r.roll_total,r.attack_condition_met,
                          r.flee_condition_met,r.reaction_outcome
                   FROM enc_animal_reaction_result r
                   JOIN enc_encounter e ON e.encounter_id=r.encounter_id
                   JOIN actor_actor a ON a.actor_id=r.animal_actor_id
                   WHERE r.command_id=%s""", (existing[0],)
            ).fetchone()
            dice = tuple(r[0] for r in connection.execute(
                """SELECT result FROM cmd_random_draw WHERE command_id=%s
                   AND draw_group='task' ORDER BY draw_order""",
                (existing[0],)).fetchall())
            return AnimalReaction(
                str(existing[1]), str(row[0]), str(row[1]), row[2],
                dice, row[3], row[4], row[5], row[6], True)
        encounter = _owned_animal_encounter(
            connection, encounter_public_id, initiator_reference)
        row = connection.execute(
            """SELECT a.actor_id,c.context_version,
                      c.animals_outnumber_characters,c.animal_has_surprise,
                      c.animal_is_surprised,c.animal_bigger_than_character,
                      c.attack_possible,p.subtype_rule_id
               FROM actor_actor a
               JOIN actor_animal_profile p ON p.actor_id=a.actor_id
               JOIN enc_animal_reaction_context c
                 ON c.animal_actor_id=a.actor_id AND c.encounter_id=%s
               WHERE a.public_id=%s FOR UPDATE OF c""",
            (encounter[0], animal_actor_public_id),
        ).fetchone()
        if row is None:
            raise ValueError("Animal reaction context is missing")
        system = connection.execute(
            """SELECT reaction_dice_count,reaction_die_sides
               FROM rule_animal_encounter_system""").fetchone()
        dice = tuple(rng.randint(1, system[1]) for _ in range(system[0]))
        total = sum(dice)
        conditions = connection.execute(
            """SELECT outcome,condition_kind,threshold,alternate_threshold,
                      requires_outcome_possible
               FROM rule_animal_reaction_condition WHERE subtype_rule_id=%s""",
            (row[7],),
        ).fetchall()
        context = {
            "outnumbers": row[2], "has_surprise": row[3],
            "is_surprised": row[4], "bigger": row[5],
            "attack_possible": row[6],
        }
        met = {
            outcome: _condition_met(
                (kind, threshold, alternate, possible), total, context)
            for outcome, kind, threshold, alternate, possible in conditions
        }
        attack, flee = met.get("attack", False), met.get("flee", False)
        outcome = ("requires_referee" if attack and flee else "attack" if attack
                   else "flee" if flee else "stand")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_animal_reaction',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, system[1], value))
        connection.execute(
            """INSERT INTO enc_animal_reaction_result
               (command_id,encounter_id,animal_actor_id,provocation_number,
                context_version,roll_total,attack_condition_met,
                flee_condition_met,reaction_outcome)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, encounter[0], row[0], provocation_number, row[1],
             total, attack, flee, outcome))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'animal_reaction_resolved')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return AnimalReaction(
            str(public_id), encounter_public_id, animal_actor_public_id,
            provocation_number, dice, total, attack, flee, outcome, False)
