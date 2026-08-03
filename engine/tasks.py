"""Deterministic, audited Cepheus actor task resolution."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class ActorTaskResult:
    command_public_id: str
    actor_public_id: str
    characteristic_rule_code: str
    skill_rule_code: str | None
    difficulty_rule_code: str
    task_context_code: str | None
    dice: tuple[int, ...]
    skill_modifier: int
    base_skill_modifier: int | None
    jack_of_all_trades_level: int | None
    jack_of_all_trades_reduction: int
    characteristic_modifier: int
    difficulty_modifier: int
    circumstance_modifier: int
    fatigue_modifier: int
    species_modifier: int
    law_level: int | None
    base_time_frame_rule_code: str | None
    time_frame_steps: int
    resolved_time_frame_rule_code: str | None
    task_time_roll: int | None
    task_time_quantity: int | None
    task_time_unit: str | None
    pace_modifier: int
    simultaneous_action_count: int
    simultaneous_action_modifier: int
    leadership_allocation_public_id: str | None
    leadership_modifier: int
    total: int
    target_number: int
    effect: int
    succeeded: bool
    replayed: bool


@dataclass(frozen=True)
class HiveMentalityResult:
    command_public_id: str
    actor_public_id: str
    family_group_reference: str
    perceived_benefit: str
    difficulty_rule_code: str
    dice: tuple[int, ...]
    intelligence_modifier: int
    difficulty_modifier: int
    total: int
    target_number: int
    effect: int
    avoided_risk: bool
    replayed: bool


@dataclass(frozen=True)
class NaturallyCuriousResult:
    command_public_id: str
    actor_public_id: str
    mystery_reference: str
    perceived_mystery: str
    difficulty_rule_code: str
    dice: tuple[int, ...]
    intelligence_modifier: int
    difficulty_modifier: int
    total: int
    target_number: int
    effect: int
    avoided_impulse: bool
    replayed: bool


@dataclass(frozen=True)
class LowLightVisibilityResult:
    command_public_id: str
    actor_public_id: str
    illumination_context: str
    human_visibility_metres: float
    distance_multiplier: int
    actor_visibility_metres: float
    retains_color: bool
    retains_detail: bool
    replayed: bool


def _load_actor_task(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,characteristic.rule_code,skill.rule_code,
                  difficulty.rule_code,receipt.task_context_code,
                  receipt.skill_modifier,receipt.base_skill_modifier,
                  receipt.jack_of_all_trades_level,
                  receipt.jack_of_all_trades_reduction,
                  receipt.characteristic_modifier,
                  receipt.difficulty_modifier,receipt.circumstance_modifier,
                  receipt.fatigue_modifier,
                  receipt.species_modifier,receipt.law_level,
                  base_frame.rule_code,receipt.time_frame_steps,
                  resolved_frame.rule_code,receipt.task_time_roll,
                  receipt.task_time_quantity,receipt.task_time_unit,
                  receipt.pace_modifier,receipt.simultaneous_action_count,
                  receipt.simultaneous_action_modifier,
                  allocation.public_id,receipt.leadership_modifier,
                  receipt.check_total,
                  receipt.target_number,receipt.effect,receipt.succeeded
           FROM cmd_actor_task_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule characteristic
             ON characteristic.rule_id=receipt.characteristic_rule_id
           LEFT JOIN rule_rule skill ON skill.rule_id=receipt.skill_rule_id
           JOIN rule_rule difficulty
             ON difficulty.rule_id=receipt.difficulty_rule_id
           LEFT JOIN rule_rule base_frame
             ON base_frame.rule_id=receipt.base_time_frame_rule_id
           LEFT JOIN rule_rule resolved_frame
             ON resolved_frame.rule_id=receipt.resolved_time_frame_rule_id
           LEFT JOIN camp_leadership_coordination_allocation allocation
             ON allocation.allocation_id=receipt.leadership_allocation_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    dice = tuple(item[0] for item in connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group='task'
           ORDER BY draw_order""",
        (command_id,),
    ).fetchall())
    return ActorTaskResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4], dice,
        row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12],
        row[13], row[14], row[15], row[16], row[17], row[18], row[19],
        row[20], row[21], row[22], row[23],
        None if row[24] is None else str(row[24]), row[25],
        row[26], row[27], row[28], row[29],
        replayed,
    )


def resolve_actor_task_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    characteristic_rule_code: str, skill_rule_code: str | None = None,
    difficulty_rule_code: str | None = None,
    task_context_code: str | None = None, circumstance_modifier: int = 0,
    law_level: int | None = None, time_frame_rule_code: str | None = None,
    time_frame_steps: int = 0, simultaneous_action_count: int = 1,
    leadership_allocation_public_id: str | None = None,
    goal_reference: str | None = None,
    random_source=None,
) -> ActorTaskResult:
    """Resolve one source-standard 2D6 actor check with audited modifiers."""
    rng = random_source or secrets.SystemRandom()
    if law_level is not None and law_level < 0:
        raise ValueError("Law Level cannot be negative")
    if time_frame_steps not in range(-2, 3):
        raise ValueError("Task pace may move at most two time-frame rows")
    if time_frame_rule_code is None and time_frame_steps:
        raise ValueError("A pace shift requires a base time frame")
    if simultaneous_action_count < 1:
        raise ValueError("Simultaneous action count must be positive")
    if law_level is None and difficulty_rule_code is None:
        raise ValueError("Task requires a difficulty or a Law Level")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_actor_task", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_actor_task(
                connection, existing[0], existing[1], True)
        if law_level is not None:
            derived = connection.execute(
                """SELECT rule.rule_code FROM rule_law_level_difficulty map
                   JOIN rule_rule rule ON rule.rule_id=map.difficulty_rule_id
                   WHERE map.law_level_range @> %s::integer""",
                (law_level,),).fetchone()
            if derived is None:
                raise ValueError("Law Level has no task difficulty mapping")
            if difficulty_rule_code is not None and difficulty_rule_code != derived[0]:
                raise ValueError("Supplied difficulty conflicts with Law Level")
            difficulty_rule_code = derived[0]
        state = connection.execute(
            """SELECT actor.actor_id,characteristic.rule_id,
                      characteristic_state.current_value,skill.rule_id,
                      skill_rule.permits_untrained,
                      skill_rule.untrained_modifier,
                      actor_skill.skill_level,difficulty.rule_id,
                      difficulty_rule.modifier,core.dice_count,core.die_sides,
                      core.target_number
               FROM actor_actor actor
               JOIN rule_rule characteristic
                 ON characteristic.rule_code=%s
               JOIN actor_characteristic characteristic_state
                 ON characteristic_state.actor_id=actor.actor_id
                AND characteristic_state.characteristic_rule_id=
                    characteristic.rule_id
               LEFT JOIN rule_rule skill ON skill.rule_code=%s
               LEFT JOIN rule_skill skill_rule ON skill_rule.rule_id=skill.rule_id
               LEFT JOIN actor_skill
                 ON actor_skill.actor_id=actor.actor_id
                AND actor_skill.skill_rule_id=skill.rule_id
               JOIN rule_rule difficulty ON difficulty.rule_code=%s
               JOIN rule_difficulty difficulty_rule
                 ON difficulty_rule.rule_id=difficulty.rule_id
               CROSS JOIN rule_check_system core
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor""",
            (characteristic_rule_code, skill_rule_code,
             difficulty_rule_code, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Task context is not legal for this actor")
        if skill_rule_code is not None and state[3] is None:
            raise ValueError("Task skill does not exist")
        if skill_rule_code is not None and state[6] is None and not state[4]:
            raise ValueError("Skill does not permit untrained checks")
        base_skill_modifier = None
        jack_of_all_trades_level = None
        jack_of_all_trades_reduction = 0
        if skill_rule_code is None:
            skill_modifier = 0
        elif state[6] is not None:
            base_skill_modifier = state[6]
            skill_modifier = state[6]
        else:
            base_skill_modifier = state[5]
            jack_of_all_trades = connection.execute(
                """SELECT actor_skill.skill_level
                   FROM rule_jack_of_all_trades rule
                   LEFT JOIN actor_skill
                     ON actor_skill.actor_id=%s
                    AND actor_skill.skill_rule_id=rule.skill_rule_id""",
                (state[0],),
            ).fetchone()
            jack_of_all_trades_level = (
                jack_of_all_trades[0]
                if jack_of_all_trades and jack_of_all_trades[0] is not None
                else 0)
            jack_of_all_trades_reduction = min(
                max(0, -base_skill_modifier), jack_of_all_trades_level)
            skill_modifier = min(
                0, base_skill_modifier + jack_of_all_trades_reduction)
        characteristic_modifier = connection.execute(
            """SELECT modifier
               FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (state[1], state[2]),
        ).fetchone()[0]
        species_rows = connection.execute(
            """SELECT modifier.trait_task_modifier_id,
                      modifier.modifier
               FROM actor_current_species current_species
               JOIN rule_species_trait_assignment assignment
                 ON assignment.species_rule_id=current_species.species_rule_id
               JOIN rule_species_trait_task_modifier modifier
                 ON modifier.species_trait_rule_id=
                    assignment.species_trait_rule_id
               WHERE current_species.actor_id=%s
                 AND (
                     modifier.skill_rule_id=%s
                     OR modifier.task_context_code=%s
                 )
               ORDER BY modifier.trait_task_modifier_id""",
            (state[0], state[3], task_context_code),
        ).fetchall()
        species_modifier = sum(item[1] for item in species_rows)
        fatigue_modifier = connection.execute(
            """SELECT CASE WHEN condition.fatigued THEN -2 ELSE 0 END
               FROM actor_personal_condition condition
               WHERE condition.actor_id=%s""",
            (state[0],),
        ).fetchone()
        fatigue_modifier = fatigue_modifier[0] if fatigue_modifier else 0
        leadership = None
        if leadership_allocation_public_id is not None:
            if not goal_reference or not goal_reference.strip():
                raise ValueError("Leadership allocation requires its common goal")
            leadership = connection.execute(
                """SELECT allocation.allocation_id,allocation.points
                   FROM camp_leadership_coordination_allocation allocation
                   JOIN camp_leadership_coordination coordination USING(coordination_id)
                   WHERE allocation.public_id=%s
                     AND allocation.recipient_actor_id=%s
                     AND allocation.allocation_status='pending'
                     AND coordination.goal_reference=%s
                   FOR UPDATE OF allocation""",
                (leadership_allocation_public_id,state[0],goal_reference.strip())).fetchone()
            if leadership is None:
                raise ValueError("Leadership allocation is unavailable for this actor and goal")
        leadership_modifier = leadership[1] if leadership else 0
        frame = None
        time_die = None
        if time_frame_rule_code is not None:
            frame = connection.execute(
                """SELECT base.rule_id,resolved.rule_id,resolved.increment_unit
                   FROM rule_rule base_rule JOIN rule_time_frame base ON base.rule_id=base_rule.rule_id
                   JOIN rule_time_frame resolved ON resolved.display_order=base.display_order+%s
                   WHERE base_rule.rule_code=%s""",
                (time_frame_steps,time_frame_rule_code),).fetchone()
            if frame is None:
                raise ValueError("Task pace moves beyond the published time-frame table")
        pace_modifier = time_frame_steps
        simultaneous_modifier = -2 * (simultaneous_action_count - 1)
        dice = tuple(
            rng.randint(1, state[10]) for _ in range(state[9]))
        if frame is not None:
            time_die = rng.randint(1, 6)
        total = (
            sum(dice) + skill_modifier + characteristic_modifier
            + state[8] + circumstance_modifier + fatigue_modifier
            + species_modifier + pace_modifier + simultaneous_modifier
            + leadership_modifier)
        effect = total - state[11]
        succeeded = total >= state[11]
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_actor_task',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, state[10], die),
            )
        if time_die is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task_time',1,6,%s)""",(command_id,time_die))
        if leadership is not None:
            connection.execute(
                """UPDATE camp_leadership_coordination_allocation
                   SET allocation_status='consumed',consumed_task_command_id=%s
                   WHERE allocation_id=%s""",(command_id,leadership[0]))
        connection.execute(
            """INSERT INTO cmd_actor_task_receipt
               (command_id,actor_id,characteristic_rule_id,skill_rule_id,
                difficulty_rule_id,task_context_code,skill_modifier,
                characteristic_modifier,difficulty_modifier,
                circumstance_modifier,fatigue_modifier,species_modifier,
                law_level,base_time_frame_rule_id,time_frame_steps,
                resolved_time_frame_rule_id,task_time_roll,task_time_quantity,
                task_time_unit,pace_modifier,simultaneous_action_count,
                simultaneous_action_modifier,leadership_allocation_id,
                leadership_modifier,base_skill_modifier,
                jack_of_all_trades_level,jack_of_all_trades_reduction,
                check_total,target_number,effect,succeeded)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[3], state[7],
             task_context_code, skill_modifier, characteristic_modifier,
             state[8], circumstance_modifier, fatigue_modifier,
             species_modifier,law_level,frame[0] if frame else None,
             time_frame_steps,frame[1] if frame else None,time_die,time_die,
             frame[2] if frame else None,pace_modifier,
             simultaneous_action_count,simultaneous_modifier,
             leadership[0] if leadership else None,leadership_modifier,
             base_skill_modifier,jack_of_all_trades_level,
             jack_of_all_trades_reduction,total,state[11],effect,succeeded),
        )
        for order, (modifier_id, modifier) in enumerate(species_rows, 1):
            connection.execute(
                """INSERT INTO cmd_actor_task_species_modifier
                   (command_id,modifier_order,trait_task_modifier_id,
                    modifier)
                   VALUES (%s,%s,%s,%s)""",
                (command_id, order, modifier_id, modifier),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,%s)""",
            (command_id, (
                "actor_task_succeeded" if succeeded
                else "actor_task_failed")),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_actor_task(
            connection, command_id, command_public, False)


def _load_hive_mentality(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.family_group_reference,
                  receipt.perceived_benefit,difficulty.rule_code,
                  receipt.intelligence_modifier,
                  receipt.difficulty_modifier,receipt.check_total,
                  receipt.target_number,receipt.effect,receipt.avoided_risk
           FROM cmd_species_hive_mentality_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule difficulty
             ON difficulty.rule_id=receipt.difficulty_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    dice = tuple(item[0] for item in connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group='task'
           ORDER BY draw_order""",
        (command_id,),
    ).fetchall())
    return HiveMentalityResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], dice,
        row[4], row[5], row[6], row[7], row[8], row[9], replayed,
    )


def resolve_species_hive_mentality_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    family_group_reference: str, perceived_benefit: str,
    difficulty_rule_code: str = "difficulty.average", random_source=None,
) -> HiveMentalityResult:
    """Check whether a Hive Mentality actor avoids a family-benefiting risk."""
    if not family_group_reference.strip():
        raise ValueError("Family group reference is required")
    if not perceived_benefit.strip():
        raise ValueError("Perceived family-group benefit is required")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_species_hive_mentality", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_hive_mentality(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT actor.actor_id,intelligence.rule_id,
                      characteristic.current_value,difficulty.rule_id,
                      difficulty_rule.modifier,core.dice_count,core.die_sides,
                      core.target_number
               FROM actor_actor actor
               JOIN rule_rule intelligence
                 ON intelligence.rule_code='characteristic.intelligence'
               JOIN actor_characteristic characteristic
                 ON characteristic.actor_id=actor.actor_id
                AND characteristic.characteristic_rule_id=
                    intelligence.rule_id
               JOIN rule_rule difficulty ON difficulty.rule_code=%s
               JOIN rule_difficulty difficulty_rule
                 ON difficulty_rule.rule_id=difficulty.rule_id
               CROSS JOIN rule_check_system core
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND difficulty_rule.modifier BETWEEN -2 AND 2
                 AND EXISTS (
                     SELECT 1
                     FROM actor_current_species current_species
                     JOIN rule_species_trait_assignment assignment
                       ON assignment.species_rule_id=
                          current_species.species_rule_id
                     JOIN rule_species_trait trait
                       ON trait.species_trait_rule_id=
                          assignment.species_trait_rule_id
                     WHERE current_species.actor_id=actor.actor_id
                       AND trait.trait_code='hive-mentality'
                 )
               FOR UPDATE OF actor""",
            (difficulty_rule_code, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError(
                "Hive Mentality check is not legal for this actor")
        intelligence_modifier = connection.execute(
            """SELECT modifier
               FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (state[1], state[2]),
        ).fetchone()[0]
        dice = tuple(
            rng.randint(1, state[6]) for _ in range(state[5]))
        total = sum(dice) + intelligence_modifier + state[4]
        effect = total - state[7]
        avoided_risk = total >= state[7]
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_species_hive_mentality',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, state[6], die),
            )
        connection.execute(
            """INSERT INTO cmd_species_hive_mentality_receipt
               (command_id,actor_id,family_group_reference,
                perceived_benefit,difficulty_rule_id,
                intelligence_modifier,difficulty_modifier,check_total,
                target_number,effect,avoided_risk)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], family_group_reference,
             perceived_benefit, state[3], intelligence_modifier, state[4],
             total, state[7], effect, avoided_risk),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,%s)""",
            (command_id, (
                "species_hive_mentality_resisted" if avoided_risk
                else "species_hive_mentality_compelled")),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_hive_mentality(
            connection, command_id, command_public, False)


def _load_naturally_curious(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.mystery_reference,
                  receipt.perceived_mystery,difficulty.rule_code,
                  receipt.intelligence_modifier,
                  receipt.difficulty_modifier,receipt.check_total,
                  receipt.target_number,receipt.effect,
                  receipt.avoided_impulse
           FROM cmd_species_naturally_curious_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule difficulty
             ON difficulty.rule_id=receipt.difficulty_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    dice = tuple(item[0] for item in connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group='task'
           ORDER BY draw_order""",
        (command_id,),
    ).fetchall())
    return NaturallyCuriousResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], dice,
        row[4], row[5], row[6], row[7], row[8], row[9], replayed,
    )


def resolve_species_naturally_curious_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, mystery_reference: str,
    perceived_mystery: str,
    difficulty_rule_code: str = "difficulty.average", random_source=None,
) -> NaturallyCuriousResult:
    """Check whether a Naturally Curious actor avoids a mysterious impulse."""
    if not mystery_reference.strip():
        raise ValueError("Mystery reference is required")
    if not perceived_mystery.strip():
        raise ValueError("Perceived mystery is required")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_species_naturally_curious", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_naturally_curious(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT actor.actor_id,intelligence.rule_id,
                      characteristic.current_value,difficulty.rule_id,
                      difficulty_rule.modifier,core.dice_count,core.die_sides,
                      core.target_number
               FROM actor_actor actor
               JOIN rule_rule intelligence
                 ON intelligence.rule_code='characteristic.intelligence'
               JOIN actor_characteristic characteristic
                 ON characteristic.actor_id=actor.actor_id
                AND characteristic.characteristic_rule_id=
                    intelligence.rule_id
               JOIN rule_rule difficulty ON difficulty.rule_code=%s
               JOIN rule_difficulty difficulty_rule
                 ON difficulty_rule.rule_id=difficulty.rule_id
               CROSS JOIN rule_check_system core
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND difficulty_rule.modifier BETWEEN -2 AND 2
                 AND EXISTS (
                     SELECT 1
                     FROM actor_current_species current_species
                     JOIN rule_species_trait_assignment assignment
                       ON assignment.species_rule_id=
                          current_species.species_rule_id
                     JOIN rule_species_trait trait
                       ON trait.species_trait_rule_id=
                          assignment.species_trait_rule_id
                     WHERE current_species.actor_id=actor.actor_id
                       AND trait.trait_code='naturally-curious'
                 )
               FOR UPDATE OF actor""",
            (difficulty_rule_code, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError(
                "Naturally Curious check is not legal for this actor")
        intelligence_modifier = connection.execute(
            """SELECT modifier
               FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (state[1], state[2]),
        ).fetchone()[0]
        dice = tuple(
            rng.randint(1, state[6]) for _ in range(state[5]))
        total = sum(dice) + intelligence_modifier + state[4]
        effect = total - state[7]
        avoided_impulse = total >= state[7]
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_species_naturally_curious',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, state[6], die),
            )
        connection.execute(
            """INSERT INTO cmd_species_naturally_curious_receipt
               (command_id,actor_id,mystery_reference,perceived_mystery,
                difficulty_rule_id,intelligence_modifier,
                difficulty_modifier,check_total,target_number,effect,
                avoided_impulse)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], mystery_reference, perceived_mystery,
             state[3], intelligence_modifier, state[4], total, state[7],
             effect, avoided_impulse),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,%s)""",
            (command_id, (
                "species_natural_curiosity_resisted" if avoided_impulse
                else "species_natural_curiosity_compelled")),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_naturally_curious(
            connection, command_id, command_public, False)


def _load_low_light_visibility(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,receipt.illumination_context,
                  receipt.human_visibility_metres,
                  receipt.distance_multiplier,
                  receipt.actor_visibility_metres,receipt.retains_color,
                  receipt.retains_detail
           FROM cmd_species_low_light_visibility_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return LowLightVisibilityResult(
        str(public_id), str(row[0]), row[1], float(row[2]), row[3],
        float(row[4]), row[5], row[6], replayed,
    )


def evaluate_species_low_light_visibility_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    illumination_context: str, human_visibility_metres: float,
) -> LowLightVisibilityResult:
    """Apply Low-Light Vision in a source-defined poor-light context."""
    if human_visibility_metres <= 0:
        raise ValueError("Human visibility distance must be positive")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "evaluate_species_low_light_visibility", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_low_light_visibility(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT actor.actor_id,rule.distance_multiplier,
                      rule.retains_color,rule.retains_detail
               FROM actor_actor actor
               JOIN actor_current_species current_species
                 ON current_species.actor_id=actor.actor_id
               JOIN rule_species_trait_assignment assignment
                 ON assignment.species_rule_id=current_species.species_rule_id
               JOIN rule_species_trait trait
                 ON trait.species_trait_rule_id=
                    assignment.species_trait_rule_id
                AND trait.trait_code='low-light-vision'
               JOIN rule_species_low_light_vision rule
                 ON rule.species_trait_rule_id=
                    trait.species_trait_rule_id
               JOIN rule_species_low_light_context context
                 ON context.species_trait_rule_id=
                    rule.species_trait_rule_id
                AND context.illumination_context=%s
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor""",
            (illumination_context, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError(
                "Low-Light Vision evaluation is not legal in this context")
        actor_visibility = human_visibility_metres * state[1]
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('evaluate_species_low_light_visibility',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_species_low_light_visibility_receipt
               (command_id,actor_id,illumination_context,
                human_visibility_metres,distance_multiplier,
                actor_visibility_metres,retains_color,retains_detail)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], illumination_context,
             human_visibility_metres, state[1], actor_visibility,
             state[2], state[3]),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'species_low_light_visibility_evaluated')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_low_light_visibility(
            connection, command_id, command_public, False)
