"""General encounter commands; combat is an explicit mode transition."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class CommittedEncounter:
    command_public_id: str
    encounter_public_id: str
    encounter_type: str
    current_mode: str
    replayed: bool


@dataclass(frozen=True)
class CommittedModeTransition:
    command_public_id: str
    encounter_public_id: str
    from_mode: str
    to_mode: str
    transition_order: int
    replayed: bool


@dataclass(frozen=True)
class CommittedParticipant:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    role: str
    side_code: str
    replayed: bool


@dataclass(frozen=True)
class CommittedAttitude:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    attitude_code: str
    replayed: bool


@dataclass(frozen=True)
class CommittedInfluence:
    command_public_id: str
    encounter_public_id: str
    acting_actor_public_id: str
    target_actor_public_id: str
    dice: tuple[int, int]
    total: int
    effect: int
    initial_attitude: str
    final_attitude: str
    shift: int
    replayed: bool


def _existing_command(connection, initiator, key):
    return connection.execute(
        """SELECT command_id,public_id,command_type,command_status
           FROM cmd_command WHERE initiator_reference=%s
           AND idempotency_key=%s FOR UPDATE""", (initiator, key)
    ).fetchone()


def _owned_encounter(connection, encounter_public_id, initiator):
    row = connection.execute(
        """SELECT e.encounter_id,e.current_mode,c.campaign_id,c.owner_reference
           FROM enc_encounter e JOIN camp_campaign c
             ON c.campaign_id=e.campaign_id
           WHERE e.public_id=%s AND e.encounter_status='active'
           FOR UPDATE OF e""", (encounter_public_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Active encounter does not exist")
    if row[3] != initiator:
        raise PermissionError("Initiator does not own this campaign")
    return row


def create_encounter_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    campaign_public_id: str,
    encounter_type_code: str,
) -> CommittedEncounter:
    with connection.transaction():
        existing = _existing_command(
            connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("create_encounter", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,t.encounter_type_code,e.current_mode
                   FROM cmd_encounter_receipt receipt
                   JOIN enc_encounter e ON e.encounter_id=receipt.encounter_id
                   JOIN rule_encounter_type t
                     ON t.rule_id=e.encounter_type_rule_id
                   WHERE receipt.command_id=%s""", (existing[0],)
            ).fetchone()
            return CommittedEncounter(
                str(existing[1]), str(row[0]), row[1], row[2], True)
        campaign = connection.execute(
            """SELECT campaign_id,owner_reference FROM camp_campaign
               WHERE public_id=%s FOR UPDATE""", (campaign_public_id,)
        ).fetchone()
        if campaign is None:
            raise ValueError("Campaign does not exist")
        if campaign[1] != initiator_reference:
            raise PermissionError("Initiator does not own this campaign")
        encounter_type = connection.execute(
            """SELECT rule_id FROM rule_encounter_type
               WHERE encounter_type_code=%s""", (encounter_type_code,)
        ).fetchone()
        if encounter_type is None:
            raise ValueError("Encounter type is not installed")
        initial_mode = {
            "animal": "animal_reaction",
            "starship": "starship",
        }.get(encounter_type_code, "social")
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('create_encounter',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        encounter_id, encounter_public = connection.execute(
            """INSERT INTO enc_encounter
               (campaign_id,encounter_type_rule_id,current_mode)
               VALUES (%s,%s,%s) RETURNING encounter_id,public_id""",
            (campaign[0], encounter_type[0], initial_mode),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_encounter_receipt
               VALUES (%s,%s,%s)""", (command_id, encounter_id, initial_mode))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'encounter_created')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedEncounter(
            str(command_public), str(encounter_public),
            encounter_type_code, initial_mode, False)


def transition_encounter_mode_command(
    connection: psycopg.Connection,
    *,
    initiator_reference: str,
    idempotency_key: str,
    encounter_public_id: str,
    to_mode: str,
    reason: str,
) -> CommittedModeTransition:
    with connection.transaction():
        existing = _existing_command(
            connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("transition_encounter_mode", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,r.from_mode,r.to_mode,t.transition_order
                   FROM cmd_encounter_transition_receipt r
                   JOIN enc_mode_transition t
                     ON t.mode_transition_id=r.mode_transition_id
                   JOIN enc_encounter e ON e.encounter_id=r.encounter_id
                   WHERE r.command_id=%s""", (existing[0],)
            ).fetchone()
            return CommittedModeTransition(
                str(existing[1]), str(row[0]), row[1], row[2], row[3], True)
        encounter = connection.execute(
            """SELECT e.encounter_id,e.current_mode,c.owner_reference
               FROM enc_encounter e JOIN camp_campaign c
                 ON c.campaign_id=e.campaign_id
               WHERE e.public_id=%s AND e.encounter_status='active'
               FOR UPDATE OF e""", (encounter_public_id,)
        ).fetchone()
        if encounter is None:
            raise ValueError("Active encounter does not exist")
        if encounter[2] != initiator_reference:
            raise PermissionError("Initiator does not own this campaign")
        if not reason.strip():
            raise ValueError("Mode transition requires a reason")
        if encounter[1] == to_mode:
            raise ValueError("Encounter is already in that mode")
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('transition_encounter_mode',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        order = connection.execute(
            """SELECT COALESCE(max(transition_order),0)+1
               FROM enc_mode_transition WHERE encounter_id=%s""",
            (encounter[0],),
        ).fetchone()[0]
        transition_id = connection.execute(
            """INSERT INTO enc_mode_transition
               (encounter_id,transition_order,from_mode,to_mode,
                transition_reason,command_id)
               VALUES (%s,%s,%s,%s,%s,%s)
               RETURNING mode_transition_id""",
            (encounter[0], order, encounter[1], to_mode, reason, command_id),
        ).fetchone()[0]
        connection.execute(
            "UPDATE enc_encounter SET current_mode=%s WHERE encounter_id=%s",
            (to_mode, encounter[0]))
        connection.execute(
            """INSERT INTO cmd_encounter_transition_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, transition_id, encounter[0], encounter[1], to_mode))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'encounter_mode_transitioned')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedModeTransition(
            str(command_public), encounter_public_id,
            encounter[1], to_mode, order, False)


def add_encounter_participant_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    participant_role: str, side_code: str,
) -> CommittedParticipant:
    with connection.transaction():
        existing = _existing_command(connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("add_encounter_participant", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,a.public_id,r.participant_role,r.side_code
                   FROM cmd_encounter_participant_receipt r
                   JOIN enc_encounter e ON e.encounter_id=r.encounter_id
                   JOIN actor_actor a ON a.actor_id=r.actor_id
                   WHERE r.command_id=%s""", (existing[0],)
            ).fetchone()
            return CommittedParticipant(
                str(existing[1]), str(row[0]), str(row[1]), row[2], row[3], True)
        encounter = _owned_encounter(
            connection, encounter_public_id, initiator_reference)
        actor = connection.execute(
            """SELECT actor_id FROM actor_actor
               WHERE public_id=%s AND campaign_id=%s""",
            (actor_public_id, encounter[2]),
        ).fetchone()
        if actor is None:
            raise ValueError("Actor is not in the encounter campaign")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('add_encounter_participant',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO enc_side (
                   encounter_id,campaign_id,side_code,
                   side_name,display_order
               )
               SELECT %s,%s,%s,%s,
                      coalesce(max(display_order),0)+1
               FROM enc_side
               WHERE encounter_id=%s
               ON CONFLICT (encounter_id,side_code) DO NOTHING""",
            (
                encounter[0], encounter[2], side_code,
                side_code, encounter[0],
            ),
        )
        connection.execute(
            """INSERT INTO enc_participant
               (encounter_id,campaign_id,actor_id,
                participant_role,side_code)
               VALUES (%s,%s,%s,%s,%s)""",
            (
                encounter[0], encounter[2], actor[0],
                participant_role, side_code,
            ))
        connection.execute(
            """INSERT INTO cmd_encounter_participant_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, encounter[0], actor[0], participant_role, side_code))
        bad_impression_pairs = connection.execute(
            """SELECT reacting.actor_id,bad_actor.actor_id,
                      attitude.attitude_rule_id,unfriendly.rule_id
               FROM enc_participant reacting
               JOIN actor_current_species reacting_species
                 ON reacting_species.actor_id=reacting.actor_id
               CROSS JOIN enc_participant bad_actor
               JOIN actor_current_species bad_species
                 ON bad_species.actor_id=bad_actor.actor_id
               JOIN rule_species_trait_assignment assignment
                 ON assignment.species_rule_id=bad_species.species_rule_id
               JOIN rule_species_trait trait
                 ON trait.species_trait_rule_id=
                    assignment.species_trait_rule_id
                AND trait.trait_code='bad-first-impression'
               JOIN rule_attitude unfriendly
                 ON unfriendly.attitude_code='unfriendly'
               LEFT JOIN enc_attitude_state attitude
                 ON attitude.encounter_id=reacting.encounter_id
                AND attitude.actor_id=reacting.actor_id
               WHERE reacting.encounter_id=%s
                 AND bad_actor.encounter_id=reacting.encounter_id
                 AND reacting.participant_role IN (
                     'non_player_character','crew','other'
                 )
                 AND reacting.actor_id <> bad_actor.actor_id
                 AND reacting_species.species_rule_id <>
                     bad_species.species_rule_id
                 AND (
                     reacting.actor_id=%s OR bad_actor.actor_id=%s
                 )
               ORDER BY reacting.actor_id,bad_actor.actor_id""",
            (encounter[0], actor[0], actor[0]),
        ).fetchall()
        for reacting_id, bad_actor_id, prior_attitude, unfriendly_id in (
            bad_impression_pairs
        ):
            connection.execute(
                """INSERT INTO enc_attitude_state
                   (encounter_id,actor_id,attitude_rule_id,set_by)
                   VALUES (%s,%s,%s,'source_rule')
                   ON CONFLICT (encounter_id,actor_id) DO UPDATE SET
                   attitude_rule_id=EXCLUDED.attitude_rule_id,
                   set_by='source_rule',changed_at=clock_timestamp()""",
                (encounter[0], reacting_id, unfriendly_id),
            )
            connection.execute(
                """INSERT INTO cmd_species_bad_first_impression_receipt
                   (command_id,encounter_id,reacting_actor_id,
                    bad_impression_actor_id,prior_attitude_rule_id,
                    source_attitude_rule_id)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (command_id, encounter[0], reacting_id, bad_actor_id,
                 prior_attitude, unfriendly_id),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'encounter_participant_added')""", (command_id,))
        if bad_impression_pairs:
            connection.execute(
                """INSERT INTO cmd_domain_event
                   (command_id,event_order,event_type)
                   VALUES (%s,2,'encounter_attitude_set')""",
                (command_id,),
            )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedParticipant(
            str(public_id), encounter_public_id, actor_public_id,
            participant_role, side_code, False)


def set_encounter_attitude_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    attitude_code: str,
) -> CommittedAttitude:
    with connection.transaction():
        existing = _existing_command(connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("set_encounter_attitude", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,a.public_id,t.attitude_code
                   FROM cmd_attitude_set_receipt r
                   JOIN enc_encounter e ON e.encounter_id=r.encounter_id
                   JOIN actor_actor a ON a.actor_id=r.actor_id
                   JOIN rule_attitude t ON t.rule_id=r.attitude_rule_id
                   WHERE r.command_id=%s""", (existing[0],)
            ).fetchone()
            return CommittedAttitude(
                str(existing[1]), str(row[0]), str(row[1]), row[2], True)
        encounter = _owned_encounter(
            connection, encounter_public_id, initiator_reference)
        participant = connection.execute(
            """SELECT p.actor_id,p.participant_role FROM enc_participant p
               JOIN actor_actor a ON a.actor_id=p.actor_id
               WHERE p.encounter_id=%s AND a.public_id=%s""",
            (encounter[0], actor_public_id),
        ).fetchone()
        if participant is None:
            raise ValueError("Actor is not an encounter participant")
        if participant[1] == "player_character":
            raise ValueError("Player-character attitudes are player-controlled")
        attitude = connection.execute(
            "SELECT rule_id FROM rule_attitude WHERE attitude_code=%s",
            (attitude_code,),
        ).fetchone()
        if attitude is None:
            raise ValueError("Attitude does not exist")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('set_encounter_attitude',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO enc_attitude_state
               (encounter_id,actor_id,attitude_rule_id,set_by)
               VALUES (%s,%s,%s,'referee')
               ON CONFLICT (encounter_id,actor_id) DO UPDATE SET
               attitude_rule_id=EXCLUDED.attitude_rule_id,
               set_by='referee',changed_at=clock_timestamp()""",
            (encounter[0], participant[0], attitude[0]))
        connection.execute(
            "INSERT INTO cmd_attitude_set_receipt VALUES (%s,%s,%s,%s)",
            (command_id, encounter[0], participant[0], attitude[0]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'encounter_attitude_set')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedAttitude(
            str(public_id), encounter_public_id, actor_public_id,
            attitude_code, False)


def attempt_attitude_influence_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    acting_actor_public_id: str, target_actor_public_id: str,
    skill_modifier: int, characteristic_modifier: int,
    circumstance_modifiers: tuple[int, ...] = (), random_source=None,
) -> CommittedInfluence:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = _existing_command(connection, initiator_reference, idempotency_key)
        if existing:
            if existing[2:] != ("attempt_attitude_influence", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            row = connection.execute(
                """SELECT e.public_id,aa.public_id,ta.public_id,
                          i.check_total,i.effect,initial.attitude_code,
                          final.attitude_code,i.attitude_shift
                   FROM enc_influence_attempt i
                   JOIN enc_encounter e ON e.encounter_id=i.encounter_id
                   JOIN actor_actor aa ON aa.actor_id=i.acting_actor_id
                   JOIN actor_actor ta ON ta.actor_id=i.target_actor_id
                   JOIN rule_attitude initial
                     ON initial.rule_id=i.initial_attitude_rule_id
                   JOIN rule_attitude final
                     ON final.rule_id=i.final_attitude_rule_id
                   WHERE i.command_id=%s""", (existing[0],)
            ).fetchone()
            dice = tuple(r[0] for r in connection.execute(
                """SELECT result FROM cmd_random_draw WHERE command_id=%s
                   AND draw_group='task' ORDER BY draw_order""",
                (existing[0],)).fetchall())
            return CommittedInfluence(
                str(existing[1]), str(row[0]), str(row[1]), str(row[2]),
                dice, row[3], row[4], row[5], row[6], row[7], True)
        encounter = _owned_encounter(
            connection, encounter_public_id, initiator_reference)
        if encounter[1] != "social":
            raise ValueError("Attitude influence requires social encounter mode")
        participants = connection.execute(
            """SELECT a.public_id,p.actor_id,p.participant_role
               FROM enc_participant p JOIN actor_actor a ON a.actor_id=p.actor_id
               WHERE p.encounter_id=%s AND a.public_id=ANY(%s)""",
            (encounter[0], [acting_actor_public_id, target_actor_public_id]),
        ).fetchall()
        by_public = {str(row[0]): row for row in participants}
        if set(by_public) != {acting_actor_public_id, target_actor_public_id}:
            raise ValueError("Both actors must be encounter participants")
        target = by_public[target_actor_public_id]
        if target[2] == "player_character":
            raise ValueError("Interaction skills cannot force player characters")
        initial = connection.execute(
            """SELECT t.rule_id,t.attitude_code,t.source_order
               FROM enc_attitude_state s JOIN rule_attitude t
                 ON t.rule_id=s.attitude_rule_id
               WHERE s.encounter_id=%s AND s.actor_id=%s FOR UPDATE OF s""",
            (encounter[0], target[1]),
        ).fetchone()
        if initial is None:
            raise ValueError("Target requires a starting attitude")
        system = connection.execute(
            """SELECT d.modifier,i.success_shift,i.exceptional_success_shift,
                      i.failure_shift,i.exceptional_failure_shift,
                      c.dice_count,c.die_sides,c.target_number
               FROM rule_attitude_influence_system i
               JOIN rule_difficulty d ON d.rule_id=i.difficulty_rule_id
               CROSS JOIN rule_check_system c""").fetchone()
        dice = tuple(rng.randint(1, system[6]) for _ in range(system[5]))
        total = (sum(dice) + skill_modifier + characteristic_modifier
                 + system[0] + sum(circumstance_modifiers))
        effect = total - system[7]
        shift = (system[2] if effect >= 6 else system[1] if effect >= 0
                 else system[4] if effect <= -6 else system[3])
        final_order = max(1, min(5, initial[2] + shift))
        final = connection.execute(
            """SELECT rule_id,attitude_code FROM rule_attitude
               WHERE source_order=%s""", (final_order,)
        ).fetchone()
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('attempt_attitude_influence',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, system[6], value))
        for order, value in enumerate(circumstance_modifiers, 1):
            connection.execute(
                "INSERT INTO cmd_influence_modifier VALUES (%s,%s,%s)",
                (command_id, order, value))
        connection.execute(
            """INSERT INTO enc_influence_attempt
               (command_id,encounter_id,acting_actor_id,target_actor_id,
                initial_attitude_rule_id,final_attitude_rule_id,skill_modifier,
                characteristic_modifier,circumstance_modifier_total,
                difficulty_modifier,check_total,target_number,effect,
                attitude_shift)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, encounter[0], by_public[acting_actor_public_id][1],
             target[1], initial[0], final[0], skill_modifier,
             characteristic_modifier, sum(circumstance_modifiers), system[0],
             total, system[7], effect, final_order - initial[2]))
        connection.execute(
            """UPDATE enc_attitude_state SET attitude_rule_id=%s,
               set_by='influence_result',changed_at=clock_timestamp()
               WHERE encounter_id=%s AND actor_id=%s""",
            (final[0], encounter[0], target[1]))
        event = ("encounter_attitude_changed"
                 if final_order != initial[2]
                 else "encounter_attitude_unchanged")
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return CommittedInfluence(
            str(public_id), encounter_public_id, acting_actor_public_id,
            target_actor_public_id, dice, total, effect, initial[1], final[1],
            final_order - initial[2], False)
