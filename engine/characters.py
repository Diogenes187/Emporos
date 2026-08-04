"""Player-owned character identity and final-detail commands."""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class CharacterFinalDetailsResult:
    command_public_id: str
    actor_public_id: str
    revision_number: int
    character_name: str
    gender_identity: str | None
    appearance: str | None
    personal_goals: tuple[str, ...]
    actor_version_before: int
    actor_version_after: int
    replayed: bool


@dataclass(frozen=True)
class ActorSpeciesAssignmentResult:
    command_public_id: str
    actor_public_id: str
    species_code: str
    species_name: str
    assignment_revision: int
    assignment_kind: str
    maturity_age_years: int | None
    aging_start_age_years: int | None
    trait_codes: tuple[str, ...]
    skill_grants: tuple[tuple[str, int | None, int], ...]
    actor_version_before: int
    actor_version_after: int
    replayed: bool


def _load_final_details(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,profile.revision_number,
                  profile.character_name,profile.gender_identity,
                  profile.appearance,receipt.actor_version_before,
                  receipt.actor_version_after
           FROM cmd_character_final_details_receipt receipt
           JOIN actor_character_profile_revision profile
             ON profile.character_profile_revision_id=
                receipt.character_profile_revision_id
           JOIN actor_actor actor ON actor.actor_id=profile.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    goals = connection.execute(
        """SELECT goal.goal_text
           FROM cmd_character_final_details_receipt receipt
           JOIN actor_character_personal_goal goal
             ON goal.character_profile_revision_id=
                receipt.character_profile_revision_id
           WHERE receipt.command_id=%s ORDER BY goal.goal_order""",
        (command_id,),
    ).fetchall()
    return CharacterFinalDetailsResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        tuple(goal[0] for goal in goals), row[5], row[6], replayed,
    )


def update_character_final_details_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, character_name: str,
    gender_identity: str | None = None, appearance: str | None = None,
    personal_goals: tuple[str, ...] = (),
) -> CharacterFinalDetailsResult:
    """Create an append-only player-controlled Final Details revision."""
    name = character_name.strip()
    if not name:
        raise ValueError("Character name cannot be blank")

    def optional_text(value, label):
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError(f"{label} cannot be blank; use None to clear it")
        return cleaned

    identity = optional_text(gender_identity, "Gender identity")
    description = optional_text(appearance, "Appearance")
    goals = tuple(goal.strip() for goal in personal_goals)
    if any(not goal for goal in goals):
        raise ValueError("Personal goals cannot be blank")
    if len(goals) > 32767:
        raise ValueError("Too many personal goals")

    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("update_character_final_details", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_final_details(
                connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor.actor_id,actor.concurrency_version,
                      lifepath.lifepath_status
               FROM actor_actor actor
               LEFT JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=actor.actor_id
               WHERE actor.public_id=%s AND actor.controller_reference=%s
               FOR UPDATE OF actor""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Actor is absent or not controlled by this player")
        if actor[2] != "completed":
            raise ValueError(
                "Character must finish lifepath creation before being named"
            )
        revision = connection.execute(
            """SELECT COALESCE(MAX(revision_number),0)+1
               FROM actor_character_profile_revision WHERE actor_id=%s""",
            (actor[0],),
        ).fetchone()[0]
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('update_character_final_details',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        profile_id = connection.execute(
            """INSERT INTO actor_character_profile_revision
               (actor_id,revision_number,character_name,gender_identity,
                appearance)
               VALUES (%s,%s,%s,%s,%s)
               RETURNING character_profile_revision_id""",
            (actor[0], revision, name, identity, description),
        ).fetchone()[0]
        for order, goal in enumerate(goals, 1):
            connection.execute(
                """INSERT INTO actor_character_personal_goal
                   (character_profile_revision_id,goal_order,goal_text)
                   VALUES (%s,%s,%s)""",
                (profile_id, order, goal),
            )
        version_after = actor[1] + 1
        connection.execute(
            """UPDATE actor_actor SET name=%s,concurrency_version=%s
               WHERE actor_id=%s""",
            (name, version_after, actor[0]),
        )
        connection.execute(
            """INSERT INTO cmd_character_final_details_receipt
               VALUES (%s,%s,%s,%s)""",
            (command_id, profile_id, actor[1], version_after),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'character_final_details_updated')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_final_details(
            connection, command_id, command_public_id, False)


def _load_species_assignment(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,species.species_code,rule.name,
                  assignment.assignment_revision,
                  assignment.assignment_kind,species.maturity_age_years,
                  species.aging_start_age_years,
                  receipt.actor_version_before,receipt.actor_version_after
           FROM cmd_actor_species_assignment_receipt receipt
           JOIN actor_species_assignment assignment
             ON assignment.actor_species_assignment_id=
                receipt.actor_species_assignment_id
           JOIN actor_actor actor ON actor.actor_id=assignment.actor_id
           JOIN rule_species species
             ON species.species_rule_id=assignment.species_rule_id
           JOIN rule_rule rule ON rule.rule_id=species.species_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    traits = connection.execute(
        """SELECT trait.trait_code
           FROM cmd_actor_species_assignment_receipt receipt
           JOIN actor_species_assignment assignment
             ON assignment.actor_species_assignment_id=
                receipt.actor_species_assignment_id
           JOIN rule_species_trait_assignment species_trait
             ON species_trait.species_rule_id=assignment.species_rule_id
           JOIN rule_species_trait trait
             ON trait.species_trait_rule_id=
                species_trait.species_trait_rule_id
           WHERE receipt.command_id=%s
           ORDER BY species_trait.assignment_order""",
        (command_id,),
    ).fetchall()
    grants = connection.execute(
        """SELECT rule.rule_code,species_grant.prior_skill_level,
                  species_grant.resulting_skill_level
           FROM cmd_actor_species_assignment_receipt receipt
           JOIN actor_species_skill_grant species_grant
             ON species_grant.actor_species_assignment_id=
                receipt.actor_species_assignment_id
           JOIN rule_rule rule ON rule.rule_id=species_grant.skill_rule_id
           WHERE receipt.command_id=%s ORDER BY rule.rule_code""",
        (command_id,),
    ).fetchall()
    return ActorSpeciesAssignmentResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], tuple(item[0] for item in traits),
        tuple(grants), row[7], row[8], replayed,
    )


def assign_actor_species_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, species_code: str,
    assignment_kind: str,
) -> ActorSpeciesAssignmentResult:
    """Assign a source-catalogued species without mutating existing scores."""
    if assignment_kind not in {
        "character_creation", "import", "player_edit",
    }:
        raise ValueError("Invalid species assignment kind")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("assign_actor_species", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_species_assignment(
                connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor_id,concurrency_version
               FROM actor_actor
               WHERE public_id=%s AND controller_reference=%s
               FOR UPDATE""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Actor is absent or not controlled by this player")
        species = connection.execute(
            """SELECT species_rule_id FROM rule_species
               WHERE species_code=%s""",
            (species_code,),
        ).fetchone()
        if species is None:
            raise ValueError("Unknown species code")
        revision = connection.execute(
            """SELECT COALESCE(MAX(assignment_revision),0)+1
               FROM actor_species_assignment WHERE actor_id=%s""",
            (actor[0],),
        ).fetchone()[0]
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('assign_actor_species',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        assignment_id = connection.execute(
            """INSERT INTO actor_species_assignment
               (actor_id,species_rule_id,assignment_revision,assignment_kind)
               VALUES (%s,%s,%s,%s)
               RETURNING actor_species_assignment_id""",
            (actor[0], species[0], revision, assignment_kind),
        ).fetchone()[0]
        if assignment_kind == "character_creation":
            grants = connection.execute(
                """SELECT skill_grant.skill_rule_id,skill_grant.granted_level
                   FROM rule_species_trait_assignment assignment
                   JOIN rule_species_trait_skill_grant skill_grant
                     ON skill_grant.species_trait_rule_id=
                        assignment.species_trait_rule_id
                   WHERE assignment.species_rule_id=%s
                   GROUP BY skill_grant.skill_rule_id,
                            skill_grant.granted_level
                   ORDER BY skill_grant.skill_rule_id""",
                (species[0],),
            ).fetchall()
            for skill_id, granted_level in grants:
                prior = connection.execute(
                    """SELECT skill_level FROM actor_skill
                       WHERE actor_id=%s AND skill_rule_id=%s""",
                    (actor[0], skill_id),
                ).fetchone()
                prior_level = prior[0] if prior else None
                resulting = max(prior_level or 0, granted_level)
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       VALUES (%s,%s,%s)
                       ON CONFLICT (actor_id,skill_rule_id) DO UPDATE
                       SET skill_level=GREATEST(
                           actor_skill.skill_level,EXCLUDED.skill_level
                       )""",
                    (actor[0], skill_id, resulting),
                )
                connection.execute(
                    """INSERT INTO actor_species_skill_grant
                       (actor_species_assignment_id,skill_rule_id,
                        granted_level,prior_skill_level,
                        resulting_skill_level)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (assignment_id, skill_id, granted_level,
                     prior_level, resulting),
                )
        version_after = actor[1] + 1
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=%s
               WHERE actor_id=%s""",
            (version_after, actor[0]),
        )
        connection.execute(
            """INSERT INTO cmd_actor_species_assignment_receipt
               VALUES (%s,%s,%s,%s)""",
            (command_id, assignment_id, actor[1], version_after),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'actor_species_assigned')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_species_assignment(
            connection, command_id, command_public_id, False)
