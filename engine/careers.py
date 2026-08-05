"""Source-governed entry into Cepheus Engine careers."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class CareerEntryAttemptResult:
    command_public_id: str
    actor_public_id: str
    attempted_career_code: str
    qualification_dice: tuple[int, ...]
    previous_careers: int
    qualification_modifier: int
    characteristic_modifier: int
    check_total: int | None
    target_number: int | None
    qualified: bool
    attempt_status: str
    resulting_career_code: str | None
    replayed: bool


@dataclass(frozen=True)
class CareerEntryFallbackResult:
    command_public_id: str
    actor_public_id: str
    attempted_career_code: str
    fallback_kind: str
    draft_dice: tuple[int, ...]
    resulting_career_code: str
    stint_order: int
    draft_uses: int
    replayed: bool


@dataclass(frozen=True)
class CareerBasicTrainingGrant:
    source_outcome_text: str
    granted_skill_rule_code: str
    prior_skill_level: int | None
    resulting_skill_level: int


@dataclass(frozen=True)
class CareerBasicTrainingResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    first_career: bool
    grants: tuple[CareerBasicTrainingGrant, ...]
    replayed: bool


@dataclass(frozen=True)
class CareerSurvivalResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    term_number: int
    survival_dice: tuple[int, ...]
    characteristic_rule_code: str
    characteristic_value: int
    characteristic_modifier: int
    check_total: int
    target_number: int
    natural_two: bool
    second_survival_dice: tuple[int, ...]
    second_check_total: int | None
    second_natural_two: bool | None
    second_survival_passed: bool | None
    survived: bool
    term_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerAnagathicDeclarationResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    term_number: int
    uses_anagathics: bool
    continuous_course_terms: int
    cost_die: int | None
    cost_credits: int
    declaration_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerRankZeroAwardResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    rank_title: str | None
    source_grant_text: str | None
    granted_skill_rule_code: str | None
    prior_skill_level: int | None
    resulting_skill_level: int | None
    replayed: bool


@dataclass(frozen=True)
class SurvivalMishapResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    mishap_roll: int
    outcome_code: str
    outcome_text: str
    elapsed_years: int
    debt_added: int
    all_career_benefits_forfeited: bool
    injury_required: bool
    resulting_age: int
    replayed: bool


@dataclass(frozen=True)
class CareerInjuryDeterminationResult:
    command_public_id: str
    actor_public_id: str
    injury_dice: tuple[int, ...]
    determination_kind: str
    injury_roll_value: int
    outcome_code: str
    outcome_text: str
    reduction_kind: str
    consequence_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerInjuryReduction:
    characteristic_rule_code: str
    reduction_amount: int
    prior_value: int
    resulting_value: int


@dataclass(frozen=True)
class CareerInjuryApplicationResult:
    command_public_id: str
    actor_public_id: str
    injury_reduction_dice: tuple[int, ...]
    reductions: tuple[CareerInjuryReduction, ...]
    crisis_started: bool
    consequence_status: str
    replayed: bool


@dataclass(frozen=True)
class InjuryCrisisCostResult:
    command_public_id: str
    actor_public_id: str
    cost_die: int
    medical_cost_credits: int
    cash_credits: int
    affordable: bool
    replayed: bool


@dataclass(frozen=True)
class InjuryCrisisResolutionResult:
    command_public_id: str
    actor_public_id: str
    resolution_kind: str
    medical_cost_credits: int
    cash_before: int
    cash_after: int
    lifepath_status: str
    restored_characteristic_codes: tuple[str, ...]
    replayed: bool


@dataclass(frozen=True)
class AgingCrisisCostResult:
    command_public_id: str
    actor_public_id: str
    cost_die: int
    medical_cost_credits: int
    cash_credits: int
    affordable: bool
    replayed: bool


@dataclass(frozen=True)
class AgingCrisisResolutionResult:
    command_public_id: str
    actor_public_id: str
    resolution_kind: str
    medical_cost_credits: int
    cash_before: int
    cash_after: int
    lifepath_status: str
    qualification_barred: bool
    restored_characteristic_codes: tuple[str, ...]
    replayed: bool


@dataclass(frozen=True)
class CareerRankAttemptResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    attempt_kind: str
    decision: str
    dice: tuple[int, ...]
    characteristic_rule_code: str | None
    characteristic_value: int | None
    characteristic_modifier: int | None
    check_total: int | None
    target_number: int | None
    succeeded: bool | None
    prior_rank: int
    resulting_rank: int
    rank_title: str | None
    granted_skill_rule_code: str | None
    prior_skill_level: int | None
    resulting_skill_level: int | None
    bonus_training_rolls: int
    replayed: bool


@dataclass(frozen=True)
class CareerTermTrainingResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    training_roll_order: int
    allowed_training_rolls: int
    training_table_code: str
    training_die: int
    source_outcome_text: str
    granted_rule_code: str
    prior_value: int | None
    resulting_value: int
    replayed: bool


@dataclass(frozen=True)
class CareerTermCompletionResult:
    command_public_id: str
    actor_public_id: str
    prior_age: int
    resulting_age: int
    prior_total_terms: int
    resulting_total_terms: int
    aging_required: bool
    replayed: bool


@dataclass(frozen=True)
class CareerAgingResult:
    command_public_id: str
    actor_public_id: str
    dice: tuple[int, ...]
    total_terms: int
    anagathic_modifier: int
    table_result: int
    effect_code: str
    source_effect_text: str
    aging_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerAgingApplicationResult:
    command_public_id: str
    actor_public_id: str
    reductions: tuple[CareerInjuryReduction, ...]
    crisis_started: bool
    aging_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerReenlistmentResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    dice: tuple[int, ...]
    target_number: int
    natural_total: int
    total_terms: int
    outcome: str
    continuation: bool | None
    retirement_required: bool
    replayed: bool


@dataclass(frozen=True)
class CareerReenlistmentDecisionResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    decision: str
    continuation: bool
    stint_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerMusterResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    eligible_term_benefits: int
    rank_bonus_benefits: int
    total_benefit_rolls: int
    annual_pension_credits: int
    muster_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerMedicalRestoration:
    characteristic_rule_code: str
    points_restored: int
    prior_value: int
    resulting_value: int


@dataclass(frozen=True)
class CareerMedicalCareResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    decision: str
    employer_dice: tuple[int, ...]
    rank_number: int
    employer_roll_total: int | None
    employer_coverage_percent: int
    gross_cost_credits: int
    employer_paid_credits: int
    character_cost_credits: int
    medical_debt_before: int
    medical_debt_after: int
    restorations: tuple[CareerMedicalRestoration, ...]
    replayed: bool


@dataclass(frozen=True)
class CareerBenefitRollResult:
    command_public_id: str
    actor_public_id: str
    career_code: str
    roll_order: int
    benefit_table_code: str
    dice: tuple[int, ...]
    roll_modifier: int
    table_result: int
    outcome_kind: str
    source_outcome_text: str
    cash_awarded: int
    medical_debt_paid: int
    anagathic_debt_paid: int
    cash_retained: int
    ship_shares_awarded: int
    award_status: str
    rolls_completed: int
    total_benefit_rolls: int
    muster_status: str
    replayed: bool


@dataclass(frozen=True)
class CareerWeaponBenefitResult:
    command_public_id: str
    actor_public_id: str
    weapon_rule_code: str
    resolution_kind: str
    skill_rule_code: str | None
    prior_value: int | None
    resulting_value: int
    muster_status: str
    replayed: bool


@dataclass(frozen=True)
class CharacterCreationCompletionResult:
    command_public_id: str
    actor_public_id: str
    age_years: int
    total_terms: int
    career_stints: int
    benefit_rolls_completed: int
    lifepath_status: str
    replayed: bool


def _draws(connection, command_id, group):
    return tuple(row[0] for row in connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group=%s ORDER BY draw_order""",
        (command_id, group),
    ).fetchall())


def _load_attempt(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,attempted.career_code,
                  attempt.previous_careers,
                  attempt.qualification_modifier,
                  attempt.characteristic_modifier,attempt.check_total,
                  attempt.target_number,attempt.qualified,
                  attempt.attempt_status,resulting.career_code
           FROM cmd_career_entry_attempt_receipt receipt
           JOIN actor_career_entry_attempt attempt
             ON attempt.career_entry_attempt_id=
                receipt.career_entry_attempt_id
           JOIN actor_actor actor ON actor.actor_id=attempt.actor_id
           JOIN rule_career attempted
             ON attempted.career_rule_id=
                attempt.attempted_career_rule_id
           LEFT JOIN actor_career_stint stint
             ON stint.career_stint_id=attempt.resolved_stint_id
           LEFT JOIN rule_career resulting
             ON resulting.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerEntryAttemptResult(
        str(public_id), str(row[0]), row[1],
        _draws(connection, command_id, "career_qualification"),
        row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9],
        replayed,
    )


def attempt_career_entry_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, career_code: str,
    assignment_code: str | None = None, random_source=None,
) -> CareerEntryAttemptResult:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("attempt_career_entry", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_attempt(
                connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor.actor_id
               FROM actor_actor actor
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise PermissionError("Initiator does not control this actor")
        actor_id = actor[0]
        system = connection.execute(
            """SELECT starting_age_years,
                      previous_career_qualification_modifier,
                      drifter_always_open
               FROM rule_career_system"""
        ).fetchone()
        species_maturity = connection.execute(
            """SELECT species.maturity_age_years
               FROM actor_current_species current_species
               JOIN rule_species species
                 ON species.species_rule_id=current_species.species_rule_id
               WHERE current_species.actor_id=%s""",
            (actor_id,),
        ).fetchone()
        starting_age = (
            species_maturity[0]
            if species_maturity and species_maturity[0] is not None
            else system[0]
        )
        connection.execute(
            """INSERT INTO actor_lifepath_state (actor_id,age_years)
               VALUES (%s,%s) ON CONFLICT (actor_id) DO NOTHING""",
            (actor_id, starting_age),
        )
        lifepath = connection.execute(
            """SELECT lifepath_status,retirement_required,
                      qualification_barred
               FROM actor_lifepath_state
               WHERE actor_id=%s""",
            (actor_id,),
        ).fetchone()
        if lifepath[0] != "active":
            raise ValueError("Actor lifepath is not active")
        if lifepath[1]:
            raise ValueError("Actor has reached mandatory retirement")
        blocked = connection.execute(
            """SELECT
                 EXISTS (
                    SELECT 1 FROM actor_career_stint
                    WHERE actor_id=%s AND stint_status='active'
                 ),
                 EXISTS (
                    SELECT 1 FROM actor_career_entry_attempt
                    WHERE actor_id=%s
                      AND attempt_status='awaiting_fallback'
                 ),
                 EXISTS (
                    SELECT 1 FROM actor_career_injury_requirement
                    WHERE actor_id=%s AND requirement_status='pending'
                 ),
                 EXISTS (
                    SELECT 1
                    FROM actor_career_stint stint
                    LEFT JOIN actor_career_muster muster
                      ON muster.career_stint_id=stint.career_stint_id
                    WHERE stint.actor_id=%s
                      AND stint.stint_status='left'
                      AND (
                          muster.career_muster_id IS NULL
                          OR muster.muster_status<>'completed'
                      )
                 )""",
            (actor_id, actor_id, actor_id, actor_id),
        ).fetchone()
        if blocked[0]:
            raise ValueError("Actor already has an active career stint")
        if blocked[1]:
            raise ValueError("A failed career entry still requires resolution")
        if blocked[2]:
            raise ValueError("A career injury still requires resolution")
        if blocked[3]:
            raise ValueError(
                "A departed career still requires completed benefits")
        career = connection.execute(
            """SELECT career.career_rule_id,career.career_code,
                      progression.qualification_characteristic_rule_id,
                      progression.qualification_target
               FROM rule_career career
               JOIN rule_career_progression progression
                 ON progression.career_rule_id=career.career_rule_id
                AND progression.assignment_rule_id IS NULL
               WHERE career.career_code=%s""",
            (career_code,),
        ).fetchone()
        if career is None:
            raise ValueError("Career does not exist")
        assignment_id = None
        assignments = connection.execute(
            """SELECT assignment.assignment_rule_id,
                      assignment.assignment_code
               FROM rule_career_assignment assignment
               WHERE assignment.career_rule_id=%s
               ORDER BY assignment.display_order""",
            (career[0],),
        ).fetchall()
        if assignments:
            selected = [
                row for row in assignments if row[1] == assignment_code]
            if len(selected) != 1:
                raise ValueError("This career requires a valid assignment")
            assignment_id = selected[0][0]
            career = connection.execute(
                """SELECT career.career_rule_id,career.career_code,
                          progression.qualification_characteristic_rule_id,
                          progression.qualification_target
                   FROM rule_career career
                   JOIN rule_career_progression progression
                     ON progression.career_rule_id=career.career_rule_id
                    AND progression.assignment_rule_id=%s
                   WHERE career.career_rule_id=%s""",
                (assignment_id, career[0]),
            ).fetchone()
        elif assignment_code is not None:
            raise ValueError("This career has no assignments")
        prior_same = connection.execute(
            """SELECT count(*) FROM actor_career_stint
               WHERE actor_id=%s AND career_rule_id=%s""",
            (actor_id, career[0]),
        ).fetchone()[0]
        if prior_same and career[1] != "drifter":
            raise ValueError("A departed career cannot be entered again")
        previous_careers = connection.execute(
            "SELECT count(*) FROM actor_career_stint WHERE actor_id=%s",
            (actor_id,),
        ).fetchone()[0]
        qualification_modifier = (
            previous_careers * system[1])
        automatic = career[1] == "drifter" and system[2]
        qualification_barred = lifepath[2]
        dice = ()
        characteristic_modifier = 0
        check_total = target_number = None
        qualified = automatic
        if not automatic and not qualification_barred:
            characteristic = connection.execute(
                """SELECT state.current_value
                   FROM actor_characteristic state
                   WHERE state.actor_id=%s
                     AND state.characteristic_rule_id=%s""",
                (actor_id, career[2]),
            ).fetchone()
            if characteristic is None:
                raise ValueError(
                    "Actor lacks the qualification characteristic")
            characteristic_modifier = connection.execute(
                """SELECT modifier
                   FROM rule_characteristic_modifier_band
                   WHERE (characteristic_rule_id IS NULL
                          OR characteristic_rule_id=%s)
                     AND score_range @> %s::integer
                   ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
                (career[2], characteristic[0]),
            ).fetchone()[0]
            core = connection.execute(
                "SELECT dice_count,die_sides FROM rule_check_system"
            ).fetchone()
            dice = tuple(rng.randint(1, core[1]) for _ in range(core[0]))
            check_total = (
                sum(dice) + characteristic_modifier
                + qualification_modifier
            )
            target_number = career[3]
            qualified = check_total >= target_number
        elif qualification_barred and not automatic:
            target_number = career[3]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('attempt_career_entry',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_qualification',%s,6,%s)""",
                (command_id, order, value),
            )
        stint_id = None
        if qualified:
            stint_order = previous_careers + 1
            stint_id = connection.execute(
                """INSERT INTO actor_career_stint
                   (actor_id,career_rule_id,assignment_rule_id,
                    entry_method,stint_order)
                   VALUES (%s,%s,%s,'qualified',%s)
                   RETURNING career_stint_id""",
                (actor_id, career[0], assignment_id, stint_order),
            ).fetchone()[0]
        attempt_id = connection.execute(
            """INSERT INTO actor_career_entry_attempt
               (actor_id,attempted_career_rule_id,assignment_rule_id,
                previous_careers,qualification_modifier,
                characteristic_modifier,check_total,target_number,
                qualified,attempt_status,resolved_stint_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING career_entry_attempt_id""",
            (actor_id, career[0], assignment_id, previous_careers,
             qualification_modifier, characteristic_modifier,
             check_total, target_number, qualified,
             "qualified" if qualified else "awaiting_fallback", stint_id),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_career_entry_attempt_receipt VALUES (%s,%s)""",
            (command_id, attempt_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_entry_qualified" if qualified
             else "career_entry_failed"),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (actor_id,),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_attempt(
            connection, command_id, public_id, False)


def _load_fallback(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,attempted.career_code,
                  receipt.fallback_kind,resulting.career_code,
                  stint.stint_order,lifepath.draft_uses
           FROM cmd_career_entry_fallback_receipt receipt
           JOIN actor_career_entry_attempt attempt
             ON attempt.career_entry_attempt_id=
                receipt.career_entry_attempt_id
           JOIN actor_actor actor ON actor.actor_id=attempt.actor_id
           JOIN rule_career attempted
             ON attempted.career_rule_id=
                attempt.attempted_career_rule_id
           JOIN rule_career resulting
             ON resulting.career_rule_id=
                receipt.resulting_career_rule_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=receipt.resulting_stint_id
           JOIN actor_lifepath_state lifepath
             ON lifepath.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerEntryFallbackResult(
        str(public_id), str(row[0]), row[1], row[2],
        _draws(connection, command_id, "career_draft"),
        row[3], row[4], row[5], replayed,
    )


def resolve_failed_career_entry_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, attempt_command_public_id: str,
    fallback_kind: str, random_source=None,
) -> CareerEntryFallbackResult:
    if fallback_kind not in {"drifter", "draft"}:
        raise ValueError("Fallback must be drifter or draft")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_failed_career_entry", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_fallback(
                connection, existing[0], existing[1], True)
        attempt = connection.execute(
            """SELECT attempt.career_entry_attempt_id,attempt.actor_id,
                      lifepath.draft_uses,system.draft_uses_allowed,
                      (SELECT count(*) FROM actor_career_stint stint
                       WHERE stint.actor_id=attempt.actor_id),
                      lifepath.qualification_barred
               FROM cmd_command source_command
               JOIN cmd_career_entry_attempt_receipt source_receipt
                 ON source_receipt.command_id=source_command.command_id
               JOIN actor_career_entry_attempt attempt
                 ON attempt.career_entry_attempt_id=
                    source_receipt.career_entry_attempt_id
               JOIN actor_actor actor ON actor.actor_id=attempt.actor_id
               JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=attempt.actor_id
               CROSS JOIN rule_career_system system
               WHERE source_command.public_id=%s
                 AND actor.controller_reference=%s
                 AND attempt.attempt_status='awaiting_fallback'
               FOR UPDATE OF attempt,actor,lifepath""",
            (attempt_command_public_id, initiator_reference),
        ).fetchone()
        if attempt is None:
            raise ValueError("Career entry is not awaiting fallback")
        draft_roll = None
        if fallback_kind == "draft":
            if attempt[5]:
                raise ValueError(
                    "A post-crisis character may only become a Drifter")
            if attempt[2] >= attempt[3]:
                raise ValueError("The actor has already used the permitted draft")
            draft_roll = rng.randint(1, 6)
            career_id = connection.execute(
                """SELECT career_rule_id FROM rule_career_draft_roll
                   WHERE roll_value=%s""",
                (draft_roll,),
            ).fetchone()[0]
            entry_method = "draft"
        else:
            career_id = connection.execute(
                """SELECT career_rule_id FROM rule_career
                   WHERE career_code='drifter'"""
            ).fetchone()[0]
            entry_method = "drifter_fallback"
        stint_id = connection.execute(
            """INSERT INTO actor_career_stint
               (actor_id,career_rule_id,entry_method,stint_order)
               VALUES (%s,%s,%s,%s) RETURNING career_stint_id""",
                (attempt[1], career_id, entry_method, attempt[4] + 1),
        ).fetchone()[0]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_failed_career_entry',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if draft_roll is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_draft',1,6,%s)""",
                (command_id, draft_roll),
            )
            connection.execute(
                """UPDATE actor_lifepath_state
                   SET draft_uses=draft_uses+1 WHERE actor_id=%s""",
                (attempt[1],),
            )
        connection.execute(
            """UPDATE actor_career_entry_attempt
               SET attempt_status='resolved',resolved_stint_id=%s
               WHERE career_entry_attempt_id=%s""",
            (stint_id, attempt[0]),
        )
        connection.execute(
            """INSERT INTO cmd_career_entry_fallback_receipt
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, attempt[0], fallback_kind, draft_roll,
             career_id, stint_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_entry_fallback_resolved')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (attempt[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_fallback(
            connection, command_id, public_id, False)


def _load_basic_training(connection, command_id, public_id, replayed):
    header = connection.execute(
        """SELECT actor.public_id,career.career_code,receipt.first_career
           FROM cmd_career_basic_training_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_career career
             ON career.career_rule_id=receipt.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    grants = connection.execute(
        """SELECT entry.source_outcome_text,rule.rule_code,
                  training_grant.prior_skill_level,
                  training_grant.resulting_skill_level
           FROM cmd_career_basic_training_grant training_grant
           JOIN rule_career_training_entry entry
             ON entry.career_training_entry_id=
                training_grant.source_training_entry_id
           JOIN rule_rule rule
             ON rule.rule_id=training_grant.granted_skill_rule_id
           WHERE training_grant.command_id=%s
           ORDER BY training_grant.grant_order""",
        (command_id,),
    ).fetchall()
    return CareerBasicTrainingResult(
        str(public_id), str(header[0]), header[1], header[2],
        tuple(CareerBasicTrainingGrant(*row) for row in grants), replayed,
    )


def apply_career_basic_training_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    selected_roll_value: int | None = None,
    cascade_specializations: dict[str, str] | None = None,
) -> CareerBasicTrainingResult:
    """Apply CE 9.1 basic training without allowing unresolved cascades."""
    specializations = cascade_specializations or {}
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "apply_career_basic_training", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_basic_training(
                connection, existing[0], existing[1], True)
        stint = connection.execute(
            """SELECT stint.career_stint_id,actor.actor_id,
                      career.career_rule_id,career.career_code,
                      stint.assignment_rule_id,stint.stint_order
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND NOT stint.basic_training_completed
               FOR UPDATE OF actor,stint""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if stint is None:
            raise ValueError(
                "Actor has no active career awaiting basic training")
        first_career = stint[5] == 1
        entries = connection.execute(
            """SELECT entry.career_training_entry_id,entry.roll_value,
                      entry.outcome_kind,entry.skill_rule_id,
                      entry.source_outcome_text,skill.cascade_skill,
                      rule.rule_code
               FROM rule_career_training_entry entry
               LEFT JOIN rule_skill skill ON skill.rule_id=entry.skill_rule_id
               LEFT JOIN rule_rule rule ON rule.rule_id=entry.skill_rule_id
               WHERE entry.career_rule_id=%s
                 AND entry.assignment_rule_id IS NOT DISTINCT FROM %s
                 AND entry.training_table_code='service'
               ORDER BY entry.roll_value""",
            (stint[2], stint[4]),
        ).fetchall()
        if len(entries) != 6:
            raise ValueError(
                "Career does not have a complete six-entry Service table")
        selected_entry_id = None
        if first_career:
            if selected_roll_value is not None:
                raise ValueError(
                    "First-career basic training grants all Service skills")
            chosen = entries
        else:
            if selected_roll_value not in range(1, 7):
                raise ValueError(
                    "Later-career basic training requires a Service roll choice")
            chosen = [
                row for row in entries if row[1] == selected_roll_value]
            selected_entry_id = chosen[0][0]
        grants = []
        used_specializations = set()
        for entry in chosen:
            if entry[2] != "skill" or entry[3] is None:
                raise ValueError(
                    "Basic training source entry is not a resolved skill")
            granted_skill_id = entry[3]
            if entry[5]:
                specialty_code = specializations.get(entry[6])
                if specialty_code is None:
                    raise ValueError(
                        f"Cascade skill {entry[6]} requires a specialization")
                specialty = connection.execute(
                    """SELECT specialty.specialty_rule_id
                       FROM rule_skill_specialty specialty
                       JOIN rule_rule rule
                         ON rule.rule_id=specialty.specialty_rule_id
                       WHERE specialty.parent_skill_rule_id=%s
                         AND rule.rule_code=%s""",
                    (entry[3], specialty_code),
                ).fetchone()
                if specialty is None:
                    raise ValueError(
                        f"{specialty_code} is not a specialty of {entry[6]}")
                granted_skill_id = specialty[0]
                used_specializations.add(entry[6])
        unused = set(specializations) - used_specializations
        if unused:
            raise ValueError(
                "Specializations supplied for unselected cascade skills: "
                + ", ".join(sorted(unused)))
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_career_basic_training',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, entry in enumerate(chosen, 1):
            granted_skill_id = entry[3]
            if entry[5]:
                granted_skill_id = connection.execute(
                    """SELECT specialty.specialty_rule_id
                       FROM rule_skill_specialty specialty
                       JOIN rule_rule rule
                         ON rule.rule_id=specialty.specialty_rule_id
                       WHERE specialty.parent_skill_rule_id=%s
                         AND rule.rule_code=%s""",
                    (entry[3], specializations[entry[6]]),
                ).fetchone()[0]
            prior = connection.execute(
                """SELECT skill_level FROM actor_skill
                   WHERE actor_id=%s AND skill_rule_id=%s""",
                (stint[1], granted_skill_id),
            ).fetchone()
            resulting = prior[0] if prior else 0
            if prior is None:
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       VALUES (%s,%s,0)""",
                    (stint[1], granted_skill_id),
                )
            grants.append((entry[0], prior[0] if prior else None, resulting))
        connection.execute(
            """INSERT INTO cmd_career_basic_training_receipt
               (command_id,career_stint_id,actor_id,career_rule_id,
                first_career,selected_training_entry_id)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, stint[0], stint[1], stint[2], first_career,
             selected_entry_id),
        )
        for order, (entry_id, prior, resulting) in enumerate(grants, 1):
            entry = next(row for row in chosen if row[0] == entry_id)
            granted_skill_id = entry[3]
            if entry[5]:
                granted_skill_id = connection.execute(
                    """SELECT specialty.specialty_rule_id
                       FROM rule_skill_specialty specialty
                       JOIN rule_rule rule
                         ON rule.rule_id=specialty.specialty_rule_id
                       WHERE specialty.parent_skill_rule_id=%s
                         AND rule.rule_code=%s""",
                    (entry[3], specializations[entry[6]]),
                ).fetchone()[0]
            connection.execute(
                """INSERT INTO cmd_career_basic_training_grant
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (command_id, order, entry_id, granted_skill_id,
                 prior, resulting),
            )
        connection.execute(
            """UPDATE actor_career_stint SET basic_training_completed=true
               WHERE career_stint_id=%s""",
            (stint[0],),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_basic_training_applied')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (stint[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_basic_training(
            connection, command_id, public_id, False)


def _load_rank_zero_award(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,rank.title,
                  rank.source_grant_text,skill.rule_code,
                  receipt.prior_skill_level,receipt.resulting_skill_level
           FROM cmd_career_rank_zero_award_receipt receipt
           JOIN actor_career_stint stint
             ON stint.career_stint_id=receipt.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           JOIN rule_career_rank rank
             ON rank.career_rank_id=receipt.career_rank_id
           LEFT JOIN rule_rule skill
             ON skill.rule_id=receipt.granted_skill_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerRankZeroAwardResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], replayed,
    )


def apply_career_rank_zero_award_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    cascade_specialization: str | None = None,
) -> CareerRankZeroAwardResult:
    """Apply the career's imported Rank 0 title and fixed skill award."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "apply_career_rank_zero_award", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_rank_zero_award(
                connection, existing[0], existing[1], True)
        stint = connection.execute(
            """SELECT stint.career_stint_id,actor.actor_id,
                      career.career_rule_id,career.career_code,
                      stint.assignment_rule_id,
                      stint.basic_training_completed
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND NOT stint.rank_zero_award_completed
               FOR UPDATE OF actor,stint""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if stint is None:
            raise ValueError(
                "Actor has no active career awaiting its Rank 0 award")
        if not stint[5]:
            raise ValueError(
                "Basic training must be completed before the Rank 0 award")
        rank = connection.execute(
            """SELECT rank.career_rank_id,rank.title,
                      rank.granted_skill_rule_id,rank.granted_skill_level,
                      rank.source_grant_text,skill.cascade_skill,
                      source_rule.rule_code
               FROM rule_career_rank rank
               LEFT JOIN rule_skill skill
                 ON skill.rule_id=rank.granted_skill_rule_id
               LEFT JOIN rule_rule source_rule
                 ON source_rule.rule_id=rank.granted_skill_rule_id
               WHERE rank.career_rule_id=%s
                 AND rank.assignment_rule_id IS NOT DISTINCT FROM %s
                 AND rank.rank_number=0""",
            (stint[2], stint[4]),
        ).fetchone()
        if rank is None:
            raise ValueError("Career has no resolved Rank 0 row")
        source_skill_id = rank[2]
        granted_skill_id = source_skill_id
        if source_skill_id is None:
            if cascade_specialization is not None:
                raise ValueError("Rank 0 has no cascade award")
        elif rank[5]:
            if cascade_specialization is None:
                raise ValueError(
                    f"Cascade skill {rank[6]} requires a specialization")
            specialty = connection.execute(
                """SELECT specialty.specialty_rule_id
                   FROM rule_skill_specialty specialty
                   JOIN rule_rule rule
                     ON rule.rule_id=specialty.specialty_rule_id
                   WHERE specialty.parent_skill_rule_id=%s
                     AND rule.rule_code=%s""",
                (source_skill_id, cascade_specialization),
            ).fetchone()
            if specialty is None:
                raise ValueError(
                    f"{cascade_specialization} is not a specialty of "
                    f"{rank[6]}")
            granted_skill_id = specialty[0]
        elif cascade_specialization is not None:
            raise ValueError("Rank 0 award is not a cascade skill")
        prior = resulting = None
        if granted_skill_id is not None:
            if rank[3] is None:
                raise ValueError("Rank 0 skill award has no resolved level")
            current = connection.execute(
                """SELECT skill_level FROM actor_skill
                   WHERE actor_id=%s AND skill_rule_id=%s""",
                (stint[1], granted_skill_id),
            ).fetchone()
            prior = current[0] if current else None
            resulting = max(prior if prior is not None else 0, rank[3])
            connection.execute(
                """INSERT INTO actor_skill
                   (actor_id,skill_rule_id,skill_level)
                   VALUES (%s,%s,%s)
                   ON CONFLICT (actor_id,skill_rule_id) DO UPDATE
                   SET skill_level=GREATEST(
                       actor_skill.skill_level,EXCLUDED.skill_level
                   )""",
                (stint[1], granted_skill_id, resulting),
            )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_career_rank_zero_award',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_career_rank_zero_award_receipt
               (command_id,career_stint_id,career_rank_id,
                source_skill_rule_id,granted_skill_rule_id,
                prior_skill_level,resulting_skill_level)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, stint[0], rank[0], source_skill_id,
             granted_skill_id, prior, resulting),
        )
        connection.execute(
            """UPDATE actor_career_stint
               SET rank_zero_award_completed=true
               WHERE career_stint_id=%s""",
            (stint[0],),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_rank_zero_award_applied')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (stint[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_rank_zero_award(
            connection, command_id, public_id, False)


def _load_anagathic_declaration(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,use.term_number,
                  use.uses_anagathics,use.continuous_course_terms,
                  use.cost_die,use.cost_credits,use.declaration_status
           FROM cmd_career_anagathic_declaration_receipt receipt
           JOIN actor_career_anagathic_term use
             ON use.career_anagathic_term_id=
                receipt.career_anagathic_term_id
           JOIN actor_actor actor ON actor.actor_id=use.actor_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=use.career_stint_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerAnagathicDeclarationResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], row[7], replayed,
    )


def declare_career_anagathics_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, uses_anagathics: bool,
    random_source=None,
) -> CareerAnagathicDeclarationResult:
    """Record the player's pre-survival anagathic choice and term cost."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("declare_career_anagathics", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_anagathic_declaration(
                connection, existing[0], existing[1], True)
        stint = connection.execute(
            """SELECT stint.career_stint_id,actor.actor_id,
                      career.career_code,stint.terms_completed
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
               FOR UPDATE OF actor,stint""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if stint is None:
            raise ValueError("Actor has no active career stint")
        term_number = stint[3] + 1
        if connection.execute(
            """SELECT 1 FROM actor_career_anagathic_term
               WHERE career_stint_id=%s AND term_number=%s""",
            (stint[0], term_number),
        ).fetchone():
            raise ValueError("Anagathic choice is already declared for this term")
        prior = connection.execute(
            """SELECT uses_anagathics,continuous_course_terms
               FROM actor_career_anagathic_term
               WHERE actor_id=%s ORDER BY career_anagathic_term_id DESC
               LIMIT 1""",
            (stint[1],),
        ).fetchone()
        prior_active = bool(prior and prior[0])
        course_terms = (
            (prior[1] if prior_active else 0) + 1
            if uses_anagathics else 0
        )
        cost_die = rng.randint(1, 6) if uses_anagathics else None
        cost = cost_die * 2500 if cost_die is not None else 0
        status = (
            "shock_required"
            if prior_active and not uses_anagathics else "ready"
        )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('declare_career_anagathics',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if cost_die is not None:
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_anagathic_cost',1,6,%s)""",
                (command_id, cost_die),
            )
        use_id = connection.execute(
            """INSERT INTO actor_career_anagathic_term
               (actor_id,career_stint_id,term_number,uses_anagathics,
                continuous_course_terms,cost_die,cost_credits,
                declaration_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING career_anagathic_term_id""",
            (stint[1], stint[0], term_number, uses_anagathics,
             course_terms, cost_die, cost, status),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO actor_financial_state (actor_id)
               VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
            (stint[1],),
        )
        if cost:
            connection.execute(
                """UPDATE actor_financial_state
                   SET debt_credits=debt_credits+%s,
                       anagathic_debt_credits=anagathic_debt_credits+%s
                   WHERE actor_id=%s""",
                (cost, cost, stint[1]),
            )
        connection.execute(
            """INSERT INTO cmd_career_anagathic_declaration_receipt
               VALUES (%s,%s)""",
            (command_id, use_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_anagathics_declared')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (stint[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_anagathic_declaration(
            connection, command_id, public_id, False)


def _load_survival(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,term.term_number,
                  characteristic.rule_code,
                  term.survival_characteristic_value,
                  term.survival_characteristic_modifier,
                  term.survival_check_total,term.survival_target,
                  term.survival_natural_two,
                  term.second_survival_check_total,
                  term.second_survival_natural_two,
                  term.second_survival_passed,
                  term.survived,term.term_status
           FROM cmd_career_survival_receipt receipt
           JOIN actor_career_term term
             ON term.career_term_id=receipt.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           JOIN rule_rule characteristic
             ON characteristic.rule_id=
                term.survival_characteristic_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerSurvivalResult(
        str(public_id), str(row[0]), row[1], row[2],
        _draws(connection, command_id, "career_survival"),
        row[3], row[4], row[5], row[6], row[7], row[8],
        _draws(connection, command_id, "career_anagathic_survival"),
        row[9], row[10], row[11], row[12], row[13], replayed,
    )


def attempt_career_survival_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> CareerSurvivalResult:
    """Resolve the mandatory CE 9.1 survival gate for one career term."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("attempt_career_survival", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_survival(
                connection, existing[0], existing[1], True)
        stint = connection.execute(
            """SELECT stint.career_stint_id,actor.actor_id,
                      career.career_rule_id,stint.assignment_rule_id,
                      stint.terms_completed,stint.basic_training_completed,
                      stint.rank_zero_award_completed
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
               FOR UPDATE OF actor,stint""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if stint is None:
            raise ValueError("Actor has no active career stint")
        if stint[4] == 0 and not stint[5]:
            raise ValueError(
                "First term requires completed basic training before survival")
        if stint[4] == 0 and not stint[6]:
            raise ValueError(
                "First term requires the Rank 0 award before survival")
        unresolved = connection.execute(
            """SELECT term_status FROM actor_career_term
               WHERE career_stint_id=%s AND term_status<>'completed'""",
            (stint[0],),
        ).fetchone()
        if unresolved is not None:
            raise ValueError(
                "Current career term has already reached the survival gate")
        if stint[4] > 0:
            reenlistment = connection.execute(
                """SELECT reenlistment.continuation,
                          reenlistment.decision_status
                   FROM actor_career_term term
                   JOIN actor_career_reenlistment reenlistment
                     ON reenlistment.career_term_id=term.career_term_id
                   WHERE term.career_stint_id=%s
                     AND term.term_status='completed'
                   ORDER BY term.term_number DESC LIMIT 1""",
                (stint[0],),
            ).fetchone()
            if (
                reenlistment is None
                or reenlistment[1] != "resolved"
                or not reenlistment[0]
            ):
                raise ValueError(
                    "The completed term requires continuation through "
                    "reenlistment before another term")
        term_number = stint[4] + 1
        anagathic = connection.execute(
            """SELECT career_anagathic_term_id,uses_anagathics,
                      declaration_status
               FROM actor_career_anagathic_term
               WHERE career_stint_id=%s AND term_number=%s
               FOR UPDATE""",
            (stint[0], term_number),
        ).fetchone()
        if anagathic is None:
            prior = connection.execute(
                """SELECT uses_anagathics
                   FROM actor_career_anagathic_term
                   WHERE actor_id=%s ORDER BY career_anagathic_term_id DESC
                   LIMIT 1""",
                (stint[1],),
            ).fetchone()
            if prior and prior[0]:
                raise ValueError(
                    "Stopping anagathics requires an explicit declaration "
                    "and immediate aging shock")
            anagathic = connection.execute(
                """INSERT INTO actor_career_anagathic_term
                   (actor_id,career_stint_id,term_number,uses_anagathics,
                    continuous_course_terms,cost_credits,declaration_status)
                   VALUES (%s,%s,%s,false,0,0,'ready')
                   RETURNING career_anagathic_term_id,uses_anagathics,
                             declaration_status""",
                (stint[1], stint[0], term_number),
            ).fetchone()
        if anagathic[2] != "ready":
            raise ValueError(
                "Anagathic stopping shock must be resolved before survival")
        progression = connection.execute(
            """SELECT progression.survival_characteristic_rule_id,
                      progression.survival_target
               FROM rule_career_progression progression
               WHERE progression.career_rule_id=%s
                 AND (progression.assignment_rule_id=%s
                      OR progression.assignment_rule_id IS NULL)
               ORDER BY (progression.assignment_rule_id IS NOT NULL) DESC
               LIMIT 1""",
            (stint[2], stint[3]),
        ).fetchone()
        if progression is None or progression[0] is None:
            raise ValueError("Career has no resolved survival rule")
        characteristic = connection.execute(
            """SELECT current_value FROM actor_characteristic
               WHERE actor_id=%s AND characteristic_rule_id=%s""",
            (stint[1], progression[0]),
        ).fetchone()
        if characteristic is None:
            raise ValueError("Actor lacks the survival characteristic")
        modifier = connection.execute(
            """SELECT modifier FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (progression[0], characteristic[0]),
        ).fetchone()[0]
        core = connection.execute(
            "SELECT dice_count,die_sides FROM rule_check_system"
        ).fetchone()
        dice = tuple(rng.randint(1, core[1]) for _ in range(core[0]))
        natural_two_rule = connection.execute(
            "SELECT survival_natural_two_fails FROM rule_career_system"
        ).fetchone()[0]
        natural_two = sum(dice) == 2
        check_total = sum(dice) + modifier
        survived = (
            check_total >= progression[1]
            and not (natural_two_rule and natural_two)
        )
        second_dice = ()
        second_check_total = None
        second_natural_two = None
        second_passed = None
        if anagathic[1] and survived:
            second_dice = tuple(
                rng.randint(1, core[1]) for _ in range(core[0]))
            second_natural_two = sum(second_dice) == 2
            second_check_total = sum(second_dice) + modifier
            second_passed = (
                second_check_total >= progression[1]
                and not (natural_two_rule and second_natural_two)
            )
            survived = second_passed
        term_status = (
            "survival_passed" if survived else "survival_failed")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('attempt_career_survival',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_survival',%s,%s,%s)""",
                (command_id, order, core[1], value),
            )
        for order, value in enumerate(second_dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_anagathic_survival',%s,%s,%s)""",
                (command_id, order, core[1], value),
            )
        term_id = connection.execute(
            """INSERT INTO actor_career_term
               (career_stint_id,term_number,term_status,
                survival_characteristic_rule_id,
                survival_characteristic_value,
                survival_characteristic_modifier,survival_target,
                survival_check_total,survival_natural_two,survived,
                anagathic_term_id,second_survival_check_required,
                second_survival_check_total,second_survival_natural_two,
                second_survival_passed)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s)
               RETURNING career_term_id""",
            (stint[0], term_number, term_status, progression[0],
             characteristic[0], modifier, progression[1], check_total,
             natural_two, survived, anagathic[0],
             bool(anagathic[1] and check_total >= progression[1]
                  and not (natural_two_rule and natural_two)),
             second_check_total, second_natural_two, second_passed),
        ).fetchone()[0]
        connection.execute(
            """UPDATE actor_career_anagathic_term
               SET career_term_id=%s,declaration_status='resolved'
               WHERE career_anagathic_term_id=%s""",
            (term_id, anagathic[0]),
        )
        connection.execute(
            """INSERT INTO cmd_career_survival_receipt VALUES (%s,%s)""",
            (command_id, term_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_survival_passed" if survived
             else "career_survival_failed"),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (stint[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_survival(
            connection, command_id, public_id, False)


def _load_mishap(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,mishap.roll_value,
                  mishap.outcome_code,mishap.outcome_text,
                  mishap.elapsed_years,mishap.debt_credits,
                  mishap.forfeit_all_career_benefits,
                  receipt.injury_requirement_id IS NOT NULL,
                  lifepath.age_years
           FROM cmd_survival_mishap_receipt receipt
           JOIN actor_career_term term
             ON term.career_term_id=receipt.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN actor_lifepath_state lifepath
             ON lifepath.actor_id=actor.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           JOIN rule_survival_mishap mishap
             ON mishap.mishap_rule_id=receipt.mishap_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return SurvivalMishapResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], row[7], row[8], row[9], replayed,
    )


def resolve_survival_mishap_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> SurvivalMishapResult:
    """Apply the optional CE survival mishap and force career departure."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_survival_mishap", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_mishap(
                connection, existing[0], existing[1], True)
        failed = connection.execute(
            """SELECT term.career_term_id,stint.career_stint_id,
                      actor.actor_id
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_term term
                 ON term.career_stint_id=stint.career_stint_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND term.term_status='survival_failed'
               FOR UPDATE OF actor,stint,term""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if failed is None:
            raise ValueError("Actor has no failed survival awaiting mishap")
        roll = rng.randint(1, 6)
        mishap = connection.execute(
            """SELECT mishap_rule_id,elapsed_years,debt_credits,
                      forfeit_all_career_benefits,injury_mode
               FROM rule_survival_mishap WHERE roll_value=%s""",
            (roll,),
        ).fetchone()
        finance = connection.execute(
            """INSERT INTO actor_financial_state (actor_id)
               VALUES (%s) ON CONFLICT (actor_id) DO UPDATE
               SET actor_id=EXCLUDED.actor_id
               RETURNING debt_credits""",
            (failed[2],),
        ).fetchone()
        debt_before = finance[0]
        debt_after = debt_before + mishap[2]
        connection.execute(
            """UPDATE actor_financial_state SET debt_credits=%s
               WHERE actor_id=%s""",
            (debt_after, failed[2]),
        )
        injury_id = None
        if mishap[4] is not None:
            injury_id = connection.execute(
                """INSERT INTO actor_career_injury_requirement
                   (career_term_id,actor_id,injury_mode)
                   VALUES (%s,%s,%s) RETURNING injury_requirement_id""",
                (failed[0], failed[2], mishap[4]),
            ).fetchone()[0]
        connection.execute(
            """UPDATE actor_career_term
               SET term_status='mishap',elapsed_years=%s,
                   benefit_roll_eligible=false,mishap_rule_id=%s
               WHERE career_term_id=%s""",
            (mishap[1], mishap[0], failed[0]),
        )
        connection.execute(
            """UPDATE actor_career_stint
               SET stint_status='left',
                   all_benefits_forfeited=%s
               WHERE career_stint_id=%s""",
            (mishap[3], failed[1]),
        )
        connection.execute(
            """UPDATE actor_lifepath_state
               SET age_years=age_years+%s WHERE actor_id=%s""",
            (mishap[1], failed[2]),
        )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_survival_mishap',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_random_draw
               (command_id,draw_group,draw_order,die_sides,result)
               VALUES (%s,'career_mishap',1,6,%s)""",
            (command_id, roll),
        )
        connection.execute(
            """INSERT INTO cmd_survival_mishap_receipt
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, failed[0], mishap[0], debt_before, debt_after,
             injury_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'survival_mishap_resolved')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (failed[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_mishap(
            connection, command_id, public_id, False)


def _load_injury_determination(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,result.determination_kind,
                  injury.roll_value,injury.outcome_code,
                  injury.outcome_text,injury.reduction_kind,
                  result.consequence_status
           FROM cmd_career_injury_determination_receipt receipt
           JOIN actor_career_injury_result result
             ON result.injury_result_id=receipt.injury_result_id
           JOIN actor_career_injury_requirement requirement
             ON requirement.injury_requirement_id=
                result.injury_requirement_id
           JOIN actor_actor actor ON actor.actor_id=requirement.actor_id
           JOIN rule_career_injury injury
             ON injury.injury_rule_id=result.injury_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerInjuryDeterminationResult(
        str(public_id), str(row[0]),
        _draws(connection, command_id, "career_injury"),
        row[1], row[2], row[3], row[4], row[5], row[6], replayed,
    )


def determine_career_injury_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    result_two_choice: str | None = None, random_source=None,
) -> CareerInjuryDeterminationResult:
    """Determine the injury-table row without choosing its characteristic loss."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("determine_career_injury", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_injury_determination(
                connection, existing[0], existing[1], True)
        requirement = connection.execute(
            """SELECT requirement.injury_requirement_id,
                      requirement.actor_id,requirement.injury_mode
               FROM actor_career_injury_requirement requirement
               JOIN actor_actor actor
                 ON actor.actor_id=requirement.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND requirement.requirement_status='pending'
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_injury_result result
                     WHERE result.injury_requirement_id=
                           requirement.injury_requirement_id
                 )
               FOR UPDATE OF actor,requirement""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if requirement is None:
            raise ValueError(
                "Actor has no undetermined career injury requirement")
        dice = ()
        if requirement[2] == "result_two_or_twice_lower":
            if result_two_choice not in {"fixed_two", "roll_twice_lower"}:
                raise ValueError(
                    "Injured in action requires fixed_two or roll_twice_lower")
            determination = result_two_choice
            if determination == "fixed_two":
                injury_roll = 2
            else:
                dice = (rng.randint(1, 6), rng.randint(1, 6))
                injury_roll = min(dice)
        else:
            if result_two_choice is not None:
                raise ValueError(
                    "Medical discharge uses one mandatory injury roll")
            determination = "roll_once"
            dice = (rng.randint(1, 6),)
            injury_roll = dice[0]
        injury = connection.execute(
            """SELECT injury_rule_id,reduction_kind
               FROM rule_career_injury WHERE roll_value=%s""",
            (injury_roll,),
        ).fetchone()
        status = (
            "resolved" if injury[1] == "none" else "awaiting_application")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_career_injury',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_injury',%s,6,%s)""",
                (command_id, order, value),
            )
        result_id = connection.execute(
            """INSERT INTO actor_career_injury_result
               (injury_requirement_id,injury_rule_id,
                determination_kind,consequence_status)
               VALUES (%s,%s,%s,%s) RETURNING injury_result_id""",
            (requirement[0], injury[0], determination, status),
        ).fetchone()[0]
        if status == "resolved":
            connection.execute(
                """UPDATE actor_career_injury_requirement
                   SET requirement_status='resolved'
                   WHERE injury_requirement_id=%s""",
                (requirement[0],),
            )
        connection.execute(
            """INSERT INTO cmd_career_injury_determination_receipt
               VALUES (%s,%s)""",
            (command_id, result_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_injury_determined')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (requirement[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_injury_determination(
            connection, command_id, public_id, False)


def _load_injury_application(connection, command_id, public_id, replayed):
    header = connection.execute(
        """SELECT actor.public_id,receipt.crisis_started,
                  result.consequence_status
           FROM cmd_career_injury_application_receipt receipt
           JOIN actor_career_injury_result result
             ON result.injury_result_id=receipt.injury_result_id
           JOIN actor_career_injury_requirement requirement
             ON requirement.injury_requirement_id=
                result.injury_requirement_id
           JOIN actor_actor actor ON actor.actor_id=requirement.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    rows = connection.execute(
        """SELECT rule.rule_code,reduction.reduction_amount,
                  reduction.prior_current_value,
                  reduction.resulting_current_value
           FROM cmd_career_injury_application_receipt receipt
           JOIN actor_career_injury_reduction reduction
             ON reduction.injury_result_id=receipt.injury_result_id
           JOIN rule_rule rule
             ON rule.rule_id=reduction.characteristic_rule_id
           WHERE receipt.command_id=%s
           ORDER BY reduction.reduction_order""",
        (command_id,),
    ).fetchall()
    return CareerInjuryApplicationResult(
        str(public_id), str(header[0]),
        _draws(connection, command_id, "career_injury_reduction"),
        tuple(CareerInjuryReduction(*row) for row in rows),
        header[1], header[2], replayed,
    )


def apply_career_injury_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    primary_characteristic_code: str,
    other_reduction_mode: str | None = None,
    other_characteristic_code: str | None = None,
    random_source=None,
) -> CareerInjuryApplicationResult:
    """Apply a determined injury using the player's legal allocation."""
    rng = random_source or secrets.SystemRandom()
    physical = {
        "characteristic.strength",
        "characteristic.dexterity",
        "characteristic.endurance",
    }
    if primary_characteristic_code not in physical:
        raise ValueError("Primary injury target must be a physical characteristic")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("apply_career_injury", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_injury_application(
                connection, existing[0], existing[1], True)
        injury = connection.execute(
            """SELECT result.injury_result_id,requirement.injury_requirement_id,
                      requirement.actor_id,rule.reduction_kind
               FROM actor_career_injury_result result
               JOIN actor_career_injury_requirement requirement
                 ON requirement.injury_requirement_id=
                    result.injury_requirement_id
               JOIN actor_actor actor ON actor.actor_id=requirement.actor_id
               JOIN rule_career_injury rule
                 ON rule.injury_rule_id=result.injury_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND result.consequence_status='awaiting_application'
               FOR UPDATE OF actor,requirement,result""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if injury is None:
            raise ValueError("Actor has no career injury awaiting application")
        kind = injury[3]
        if kind == "strength_or_dexterity_two" and (
            primary_characteristic_code == "characteristic.endurance"
        ):
            raise ValueError("Missing eye or limb may reduce only Strength or Dexterity")
        dice = ()
        allocations = []
        if kind == "one_physical_d6_and_others":
            dice = (rng.randint(1, 6),)
            allocations.append((primary_characteristic_code, dice[0]))
            remaining = sorted(physical - {primary_characteristic_code})
            if other_reduction_mode == "split_two_each":
                allocations.extend((code, 2) for code in remaining)
                if other_characteristic_code is not None:
                    raise ValueError("Split reduction does not choose one other target")
            elif other_reduction_mode == "one_other_four":
                if other_characteristic_code not in remaining:
                    raise ValueError("Four-point target must be another physical characteristic")
                allocations.append((other_characteristic_code, 4))
            else:
                raise ValueError(
                    "Nearly killed requires split_two_each or one_other_four")
        elif kind == "one_physical_d6":
            if other_reduction_mode is not None or other_characteristic_code is not None:
                raise ValueError("Severe injury has only one target")
            dice = (rng.randint(1, 6),)
            allocations.append((primary_characteristic_code, dice[0]))
        else:
            if other_reduction_mode is not None or other_characteristic_code is not None:
                raise ValueError("This injury has only one target")
            amount = 2 if kind in {
                "strength_or_dexterity_two", "one_physical_two"
            } else 1
            allocations.append((primary_characteristic_code, amount))
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_career_injury',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_injury_reduction',%s,6,%s)""",
                (command_id, order, value),
            )
        crisis = False
        for order, (code, amount) in enumerate(allocations, 1):
            state = connection.execute(
                """SELECT characteristic.rule_id,state.maximum_value,
                          state.current_value
                   FROM rule_rule rule
                   JOIN rule_characteristic characteristic
                     ON characteristic.rule_id=rule.rule_id
                   JOIN actor_characteristic state
                     ON state.characteristic_rule_id=characteristic.rule_id
                    AND state.actor_id=%s
                   WHERE rule.rule_code=%s
                   FOR UPDATE OF state""",
                (injury[2], code),
            ).fetchone()
            if state is None:
                raise ValueError("Actor lacks an allocated characteristic")
            resulting_max = max(0, state[1] - amount)
            resulting_current = max(0, state[2] - amount)
            crisis = crisis or resulting_max == 0 or resulting_current == 0
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=%s,current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (resulting_max, min(resulting_current, resulting_max),
                 injury[2], state[0]),
            )
            connection.execute(
                """INSERT INTO actor_career_injury_reduction
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (injury[0], order, state[0], amount, state[1], state[2],
                 resulting_max, min(resulting_current, resulting_max)),
            )
        status = "awaiting_crisis" if crisis else "applied"
        connection.execute(
            """UPDATE actor_career_injury_result SET consequence_status=%s
               WHERE injury_result_id=%s""",
            (status, injury[0]),
        )
        if not crisis:
            connection.execute(
                """UPDATE actor_career_injury_requirement
                   SET requirement_status='resolved'
                   WHERE injury_requirement_id=%s""",
                (injury[1],),
            )
        connection.execute(
            """INSERT INTO cmd_career_injury_application_receipt
               VALUES (%s,%s,%s)""",
            (command_id, injury[0], crisis),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_injury_crisis_started" if crisis
             else "career_injury_applied"),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (injury[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_injury_application(
            connection, command_id, public_id, False)


def _load_injury_crisis_cost(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,crisis.medical_cost_die,
                  crisis.medical_cost_credits,finance.cash_credits
           FROM cmd_injury_crisis_cost_receipt receipt
           JOIN actor_career_injury_crisis crisis
             ON crisis.injury_crisis_id=receipt.injury_crisis_id
           JOIN actor_actor actor ON actor.actor_id=crisis.actor_id
           JOIN actor_financial_state finance
             ON finance.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return InjuryCrisisCostResult(
        str(public_id), str(row[0]), row[1], row[2], row[3],
        row[3] >= row[2], replayed,
    )


def determine_injury_crisis_cost_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> InjuryCrisisCostResult:
    """Roll and retain the CE injury-crisis medical price."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("determine_injury_crisis_cost", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_injury_crisis_cost(
                connection, existing[0], existing[1], True)
        injury = connection.execute(
            """SELECT result.injury_result_id,requirement.actor_id
               FROM actor_career_injury_result result
               JOIN actor_career_injury_requirement requirement
                 ON requirement.injury_requirement_id=
                    result.injury_requirement_id
               JOIN actor_actor actor ON actor.actor_id=requirement.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND result.consequence_status='awaiting_crisis'
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_injury_crisis crisis
                     WHERE crisis.injury_result_id=result.injury_result_id
                 )
               FOR UPDATE OF actor,requirement,result""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if injury is None:
            raise ValueError("Actor has no unpriced injury crisis")
        die = rng.randint(1, 6)
        cost = die * 10000
        connection.execute(
            """INSERT INTO actor_financial_state (actor_id)
               VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
            (injury[1],),
        )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_injury_crisis_cost',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_random_draw
               (command_id,draw_group,draw_order,die_sides,result)
               VALUES (%s,'career_injury_crisis_cost',1,6,%s)""",
            (command_id, die),
        )
        crisis_id = connection.execute(
            """INSERT INTO actor_career_injury_crisis
               (injury_result_id,actor_id,medical_cost_die,
                medical_cost_credits)
               VALUES (%s,%s,%s,%s) RETURNING injury_crisis_id""",
            (injury[0], injury[1], die, cost),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_injury_crisis_cost_receipt VALUES (%s,%s)""",
            (command_id, crisis_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'injury_crisis_cost_determined')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (injury[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_injury_crisis_cost(
            connection, command_id, public_id, False)


def _load_injury_crisis_resolution(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,receipt.resolution_kind,
                  crisis.medical_cost_credits,receipt.cash_before,
                  receipt.cash_after,lifepath.lifepath_status
           FROM cmd_injury_crisis_resolution_receipt receipt
           JOIN actor_career_injury_crisis crisis
             ON crisis.injury_crisis_id=receipt.injury_crisis_id
           JOIN actor_actor actor ON actor.actor_id=crisis.actor_id
           JOIN actor_lifepath_state lifepath
             ON lifepath.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    restored = connection.execute(
        """SELECT rule.rule_code
           FROM cmd_injury_crisis_restoration restoration
           JOIN rule_rule rule
             ON rule.rule_id=restoration.characteristic_rule_id
           WHERE restoration.command_id=%s
           ORDER BY rule.rule_code""",
        (command_id,),
    ).fetchall()
    return InjuryCrisisResolutionResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], tuple(item[0] for item in restored), replayed,
    )


def resolve_injury_crisis_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, resolution_kind: str,
) -> InjuryCrisisResolutionResult:
    if resolution_kind not in {"pay", "accept_death"}:
        raise ValueError("Injury crisis resolution must be pay or accept_death")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_injury_crisis", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_injury_crisis_resolution(
                connection, existing[0], existing[1], True)
        crisis = connection.execute(
            """SELECT crisis.injury_crisis_id,crisis.actor_id,
                      crisis.medical_cost_credits,
                      finance.cash_credits,result.injury_result_id,
                      requirement.injury_requirement_id
               FROM actor_career_injury_crisis crisis
               JOIN actor_actor actor ON actor.actor_id=crisis.actor_id
               JOIN actor_financial_state finance
                 ON finance.actor_id=actor.actor_id
               JOIN actor_career_injury_result result
                 ON result.injury_result_id=crisis.injury_result_id
               JOIN actor_career_injury_requirement requirement
                 ON requirement.injury_requirement_id=
                    result.injury_requirement_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND crisis.crisis_status='awaiting_decision'
               FOR UPDATE OF actor,finance,crisis,result,requirement""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if crisis is None:
            raise ValueError("Actor has no priced injury crisis")
        cash_before = crisis[3]
        restorations = ()
        if resolution_kind == "pay":
            if cash_before < crisis[2]:
                raise ValueError("Actor cannot afford injury-crisis medical care")
            cash_after = cash_before - crisis[2]
            connection.execute(
                """UPDATE actor_financial_state SET cash_credits=%s
                   WHERE actor_id=%s""",
                (cash_after, crisis[1]),
            )
            restorations = connection.execute(
                """SELECT characteristic_rule_id,maximum_value,current_value
                   FROM actor_characteristic
                   WHERE actor_id=%s
                     AND (maximum_value=0 OR current_value=0)
                   FOR UPDATE""",
                (crisis[1],),
            ).fetchall()
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=GREATEST(maximum_value,1),
                       current_value=GREATEST(current_value,1)
                   WHERE actor_id=%s
                     AND (maximum_value=0 OR current_value=0)""",
                (crisis[1],),
            )
            lifepath_status = "active"
            event_type = "injury_crisis_paid"
        else:
            cash_after = cash_before
            lifepath_status = "deceased"
            event_type = "injury_crisis_death_accepted"
        connection.execute(
            """UPDATE actor_lifepath_state
               SET lifepath_status=%s,
                   qualification_barred=(
                       qualification_barred OR %s
                   )
               WHERE actor_id=%s""",
            (lifepath_status, resolution_kind == "pay", crisis[1]),
        )
        connection.execute(
            """UPDATE actor_career_injury_crisis SET crisis_status=%s
               WHERE injury_crisis_id=%s""",
            ("paid" if resolution_kind == "pay" else "death", crisis[0]),
        )
        connection.execute(
            """UPDATE actor_career_injury_result
               SET consequence_status='resolved'
               WHERE injury_result_id=%s""",
            (crisis[4],),
        )
        connection.execute(
            """UPDATE actor_career_injury_requirement
               SET requirement_status='resolved'
               WHERE injury_requirement_id=%s""",
            (crisis[5],),
        )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_injury_crisis',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_injury_crisis_resolution_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, crisis[0], resolution_kind,
             cash_before, cash_after),
        )
        for characteristic_id, prior_maximum, prior_current in restorations:
            connection.execute(
                """INSERT INTO cmd_injury_crisis_restoration
                   VALUES (%s,%s,%s,%s)""",
                (command_id, characteristic_id,
                 prior_maximum, prior_current),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event_type),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (crisis[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_injury_crisis_resolution(
            connection, command_id, public_id, False)


def _load_career_rank_attempt(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,receipt.attempt_kind,
                  receipt.decision,characteristic.rule_code,
                  receipt.characteristic_value,
                  receipt.characteristic_modifier,receipt.check_total,
                  receipt.target_number,receipt.succeeded,
                  receipt.prior_rank,receipt.resulting_rank,rank.title,
                  granted.rule_code,receipt.prior_skill_level,
                  receipt.resulting_skill_level,term.bonus_training_rolls
           FROM cmd_career_rank_attempt_receipt receipt
           JOIN actor_career_term term
             ON term.career_term_id=receipt.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           LEFT JOIN rule_rule characteristic
             ON characteristic.rule_id=receipt.characteristic_rule_id
           LEFT JOIN rule_career_rank rank
             ON rank.career_rank_id=receipt.awarded_career_rank_id
           LEFT JOIN rule_rule granted
             ON granted.rule_id=receipt.granted_skill_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerRankAttemptResult(
        str(public_id), str(row[0]), row[1], row[2], row[3],
        _draws(connection, command_id, f"career_{row[2]}"),
        row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11],
        row[12], row[13], row[14], row[15], row[16], replayed,
    )


def resolve_career_rank_attempt_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, attempt_kind: str,
    decision: str, cascade_specialization: str | None = None,
    random_source=None,
) -> CareerRankAttemptResult:
    """Resolve one optional commission or advancement decision."""
    if attempt_kind not in {"commission", "advancement"}:
        raise ValueError("Rank attempt must be commission or advancement")
    if decision not in {"attempt", "decline"}:
        raise ValueError("Rank decision must be attempt or decline")
    if decision == "decline" and cascade_specialization is not None:
        raise ValueError("A declined attempt cannot select a specialization")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_career_rank_attempt", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_career_rank_attempt(
                connection, existing[0], existing[1], True)
        term = connection.execute(
            """SELECT term.career_term_id,stint.career_stint_id,
                      actor.actor_id,career.career_rule_id,
                      career.career_code,stint.assignment_rule_id,
                      stint.entry_method,stint.rank_number,term.term_number
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_term term
                 ON term.career_stint_id=stint.career_stint_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND term.term_status='survival_passed'
               FOR UPDATE OF actor,stint,term""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if term is None:
            raise ValueError("Actor has no survived term awaiting progression")
        if connection.execute(
            """SELECT 1 FROM cmd_career_rank_attempt_receipt
               WHERE career_term_id=%s AND attempt_kind=%s""",
            (term[0], attempt_kind),
        ).fetchone():
            raise ValueError(f"{attempt_kind.title()} already decided this term")
        progression = connection.execute(
            """SELECT commission_characteristic_rule_id,commission_target,
                      advancement_characteristic_rule_id,advancement_target
               FROM rule_career_progression
               WHERE career_rule_id=%s
                 AND (assignment_rule_id=%s OR assignment_rule_id IS NULL)
               ORDER BY (assignment_rule_id IS NOT NULL) DESC LIMIT 1""",
            (term[3], term[5]),
        ).fetchone()
        offset = 0 if attempt_kind == "commission" else 2
        characteristic_id, target = progression[offset:offset + 2]
        if characteristic_id is None:
            raise ValueError(f"Career does not offer {attempt_kind}")
        if attempt_kind == "commission":
            if term[7] != 0:
                raise ValueError("Commission is available only at Rank 0")
            if term[6] == "draft" and term[8] == 1:
                raise ValueError(
                    "A draftee cannot attempt commission in the first term")
        else:
            if term[7] < 1:
                raise ValueError("Advancement requires Rank 1 or higher")
            if term[7] >= 6:
                raise ValueError("Rank 6 cannot advance further")
        dice = ()
        value = modifier = check_total = succeeded = None
        resulting_rank = term[7]
        rank = None
        source_skill_id = granted_skill_id = None
        prior_skill = resulting_skill = None
        if decision == "attempt":
            value_row = connection.execute(
                """SELECT current_value FROM actor_characteristic
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (term[2], characteristic_id),
            ).fetchone()
            if value_row is None:
                raise ValueError("Actor lacks the rank-check characteristic")
            value = value_row[0]
            modifier = connection.execute(
                """SELECT modifier FROM rule_characteristic_modifier_band
                   WHERE (characteristic_rule_id IS NULL
                          OR characteristic_rule_id=%s)
                     AND score_range @> %s::integer
                   ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
                (characteristic_id, value),
            ).fetchone()[0]
            core = connection.execute(
                "SELECT dice_count,die_sides FROM rule_check_system"
            ).fetchone()
            dice = tuple(rng.randint(1, core[1]) for _ in range(core[0]))
            check_total = sum(dice) + modifier
            succeeded = check_total >= target
            if succeeded:
                resulting_rank = 1 if attempt_kind == "commission" else term[7] + 1
                rank = connection.execute(
                    """SELECT career_rank_id,title,granted_skill_rule_id,
                              granted_skill_level,source_grant_text,
                              skill.cascade_skill,rule.rule_code
                       FROM rule_career_rank rank
                       LEFT JOIN rule_skill skill
                         ON skill.rule_id=rank.granted_skill_rule_id
                       LEFT JOIN rule_rule rule
                         ON rule.rule_id=rank.granted_skill_rule_id
                       WHERE rank.career_rule_id=%s
                         AND rank.assignment_rule_id IS NOT DISTINCT FROM %s
                         AND rank.rank_number=%s""",
                    (term[3], term[5], resulting_rank),
                ).fetchone()
                if rank is None:
                    raise ValueError("Resulting rank row is unresolved")
                source_skill_id = rank[2]
                granted_skill_id = source_skill_id
                if source_skill_id is not None and rank[5]:
                    if cascade_specialization is None:
                        raise ValueError(
                            f"Cascade skill {rank[6]} requires a specialization")
                    specialty = connection.execute(
                        """SELECT specialty.specialty_rule_id
                           FROM rule_skill_specialty specialty
                           JOIN rule_rule rule
                             ON rule.rule_id=specialty.specialty_rule_id
                           WHERE specialty.parent_skill_rule_id=%s
                             AND rule.rule_code=%s""",
                        (source_skill_id, cascade_specialization),
                    ).fetchone()
                    if specialty is None:
                        raise ValueError(
                            f"{cascade_specialization} is not a specialty "
                            f"of {rank[6]}")
                    granted_skill_id = specialty[0]
                elif cascade_specialization is not None:
                    raise ValueError("Resulting rank has no cascade award")
                if granted_skill_id is not None:
                    current = connection.execute(
                        """SELECT skill_level FROM actor_skill
                           WHERE actor_id=%s AND skill_rule_id=%s""",
                        (term[2], granted_skill_id),
                    ).fetchone()
                    prior_skill = current[0] if current else None
                    resulting_skill = max(
                        prior_skill if prior_skill is not None else 0, rank[3])
                    connection.execute(
                        """INSERT INTO actor_skill
                           (actor_id,skill_rule_id,skill_level)
                           VALUES (%s,%s,%s)
                           ON CONFLICT (actor_id,skill_rule_id) DO UPDATE
                           SET skill_level=GREATEST(
                               actor_skill.skill_level,EXCLUDED.skill_level)""",
                        (term[2], granted_skill_id, resulting_skill),
                    )
                connection.execute(
                    """UPDATE actor_career_stint SET rank_number=%s
                       WHERE career_stint_id=%s""",
                    (resulting_rank, term[1]),
                )
                connection.execute(
                    """UPDATE actor_career_term
                       SET bonus_training_rolls=bonus_training_rolls+1
                       WHERE career_term_id=%s""",
                    (term[0],),
                )
        elif cascade_specialization is not None:
            raise ValueError("Declined attempt has no rank award")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_career_rank_attempt',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,%s,%s,6,%s)""",
                (command_id, f"career_{attempt_kind}", order, die),
            )
        connection.execute(
            """INSERT INTO cmd_career_rank_attempt_receipt
               (command_id,career_term_id,attempt_kind,decision,
                characteristic_rule_id,characteristic_value,
                characteristic_modifier,target_number,check_total,succeeded,
                prior_rank,resulting_rank,awarded_career_rank_id,
                source_skill_rule_id,granted_skill_rule_id,
                prior_skill_level,resulting_skill_level)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, term[0], attempt_kind, decision,
             characteristic_id if decision == "attempt" else None,
             value, modifier, target if decision == "attempt" else None,
             check_total, succeeded, term[7], resulting_rank,
             rank[0] if rank else None, source_skill_id, granted_skill_id,
             prior_skill, resulting_skill),
        )
        event = (
            "career_rank_attempt_declined" if decision == "decline"
            else "career_rank_gained" if succeeded
            else "career_rank_attempt_failed"
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (term[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_career_rank_attempt(
            connection, command_id, public_id, False)


def _load_career_term_training(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,
                  receipt.training_roll_order,receipt.allowed_training_rolls,
                  entry.training_table_code,entry.roll_value,
                  entry.source_outcome_text,
                  COALESCE(skill.rule_code,characteristic.rule_code),
                  COALESCE(receipt.prior_skill_level,
                           receipt.prior_characteristic_current),
                  COALESCE(receipt.resulting_skill_level,
                           receipt.resulting_characteristic_current)
           FROM cmd_career_term_training_receipt receipt
           JOIN actor_career_term term
             ON term.career_term_id=receipt.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           JOIN rule_career_training_entry entry
             ON entry.career_training_entry_id=receipt.training_entry_id
           LEFT JOIN rule_rule skill
             ON skill.rule_id=receipt.granted_skill_rule_id
           LEFT JOIN rule_rule characteristic
             ON characteristic.rule_id=receipt.characteristic_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerTermTrainingResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], row[7], row[8], row[9], replayed,
    )


def apply_career_term_training_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    training_table_code: str,
    cascade_specialization: str | None = None,
    cascade_specializations: dict[str, str] | None = None,
    random_source=None,
) -> CareerTermTrainingResult:
    """Apply one player-selected CE Skills and Training table roll."""
    valid_tables = {
        "personal_development", "service", "specialist",
        "advanced_education",
    }
    if training_table_code not in valid_tables:
        raise ValueError("Unknown career training table")
    if cascade_specialization is not None and cascade_specializations:
        raise ValueError(
            "Supply either one legacy specialization or keyed specializations"
        )
    specializations = cascade_specializations or {}
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("apply_career_term_training", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_career_term_training(
                connection, existing[0], existing[1], True)
        term = connection.execute(
            """SELECT term.career_term_id,stint.career_stint_id,
                      actor.actor_id,career.career_rule_id,
                      stint.assignment_rule_id,stint.rank_number,
                      term.bonus_training_rolls,
                      term.training_rolls_completed,
                      progression.commission_characteristic_rule_id
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_term term
                 ON term.career_stint_id=stint.career_stint_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               JOIN rule_career_progression progression
                 ON progression.career_rule_id=career.career_rule_id
                AND progression.assignment_rule_id
                    IS NOT DISTINCT FROM stint.assignment_rule_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND term.term_status='survival_passed'
               FOR UPDATE OF actor,stint,term""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if term is None:
            raise ValueError("Actor has no survived term awaiting training")
        hierarchy = term[8] is not None
        rank_decisions = connection.execute(
            """SELECT attempt_kind,succeeded
               FROM cmd_career_rank_attempt_receipt
               WHERE career_term_id=%s""",
            (term[0],),
        ).fetchall()
        decisions = {row[0]: row[1] for row in rank_decisions}
        if hierarchy:
            if term[5] == 0 and "commission" not in decisions:
                raise ValueError(
                    "Commission decision is required before term training")
            if term[5] >= 1 and "advancement" not in decisions:
                raise ValueError(
                    "Advancement decision is required before term training")
        base_rolls = 1 if hierarchy else 2
        allowed_rolls = base_rolls + term[6]
        if term[7] >= allowed_rolls:
            raise ValueError("All training rolls for this term are complete")
        if training_table_code == "advanced_education":
            education = connection.execute(
                """SELECT state.current_value
                   FROM actor_characteristic state
                   JOIN rule_rule rule
                     ON rule.rule_id=state.characteristic_rule_id
                   WHERE state.actor_id=%s
                     AND rule.rule_code='characteristic.education'""",
                (term[2],),
            ).fetchone()
            if education is None or education[0] < 8:
                raise ValueError("Advanced Education requires Education 8+")
        die = rng.randint(1, 6)
        entry = connection.execute(
            """SELECT entry.career_training_entry_id,entry.outcome_kind,
                      entry.skill_rule_id,entry.characteristic_rule_id,
                      entry.characteristic_increase,
                      entry.source_outcome_text,skill.cascade_skill,
                      skill_rule.rule_code
               FROM rule_career_training_entry entry
               LEFT JOIN rule_skill skill ON skill.rule_id=entry.skill_rule_id
               LEFT JOIN rule_rule skill_rule
                 ON skill_rule.rule_id=entry.skill_rule_id
               WHERE entry.career_rule_id=%s
                 AND entry.assignment_rule_id IS NOT DISTINCT FROM %s
                 AND entry.training_table_code=%s
                 AND entry.roll_value=%s""",
            (term[3], term[4], training_table_code, die),
        ).fetchone()
        if entry is None or entry[1] == "text":
            raise ValueError("Training outcome is unresolved in the source data")
        granted_skill_id = characteristic_id = None
        prior_skill = resulting_skill = None
        prior_maximum = prior_current = resulting_maximum = resulting_current = None
        if entry[1] == "skill":
            granted_skill_id = entry[2]
            if entry[6]:
                selected_specialization = (
                    specializations.get(entry[7])
                    if specializations else cascade_specialization
                )
                if selected_specialization is None:
                    raise ValueError(
                        f"Cascade skill {entry[7]} requires a specialization")
                specialty = connection.execute(
                    """SELECT specialty.specialty_rule_id
                       FROM rule_skill_specialty specialty
                       JOIN rule_rule rule
                         ON rule.rule_id=specialty.specialty_rule_id
                       WHERE specialty.parent_skill_rule_id=%s
                         AND rule.rule_code=%s""",
                    (entry[2], selected_specialization),
                ).fetchone()
                if specialty is None:
                    raise ValueError(
                        f"{selected_specialization} is not a specialty "
                        f"of {entry[7]}")
                granted_skill_id = specialty[0]
            elif cascade_specialization is not None:
                raise ValueError("Training outcome is not a cascade skill")
            current = connection.execute(
                """SELECT skill_level FROM actor_skill
                   WHERE actor_id=%s AND skill_rule_id=%s""",
                (term[2], granted_skill_id),
            ).fetchone()
            prior_skill = current[0] if current else None
            resulting_skill = 1 if current is None else prior_skill + 1
            connection.execute(
                """INSERT INTO actor_skill
                   (actor_id,skill_rule_id,skill_level)
                   VALUES (%s,%s,%s)
                   ON CONFLICT (actor_id,skill_rule_id) DO UPDATE
                   SET skill_level=EXCLUDED.skill_level""",
                (term[2], granted_skill_id, resulting_skill),
            )
            if entry[6]:
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,specialty_rule_id,0
                       FROM rule_skill_specialty
                       WHERE parent_skill_rule_id=%s
                         AND specialty_rule_id<>%s
                       ON CONFLICT (actor_id,skill_rule_id) DO NOTHING""",
                    (term[2], entry[2], granted_skill_id),
                )
        else:
            if cascade_specialization is not None:
                raise ValueError(
                    "Characteristic training has no specialization")
            characteristic_id = entry[3]
            state = connection.execute(
                """SELECT maximum_value,current_value
                   FROM actor_characteristic
                   WHERE actor_id=%s AND characteristic_rule_id=%s
                   FOR UPDATE""",
                (term[2], characteristic_id),
            ).fetchone()
            if state is None:
                raise ValueError("Actor lacks the improved characteristic")
            prior_maximum, prior_current = state
            resulting_maximum = prior_maximum + entry[4]
            resulting_current = prior_current + entry[4]
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=%s,current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (resulting_maximum, resulting_current,
                 term[2], characteristic_id),
            )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_career_term_training',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_random_draw
               (command_id,draw_group,draw_order,die_sides,result)
               VALUES (%s,'career_training',1,6,%s)""",
            (command_id, die),
        )
        connection.execute(
            """INSERT INTO cmd_career_term_training_receipt
               (command_id,career_term_id,training_roll_order,
                base_training_rolls,allowed_training_rolls,training_entry_id,
                granted_skill_rule_id,prior_skill_level,resulting_skill_level,
                characteristic_rule_id,prior_characteristic_maximum,
                prior_characteristic_current,resulting_characteristic_maximum,
                resulting_characteristic_current)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, term[0], term[7] + 1, base_rolls, allowed_rolls,
             entry[0], granted_skill_id, prior_skill, resulting_skill,
             characteristic_id, prior_maximum, prior_current,
             resulting_maximum, resulting_current),
        )
        connection.execute(
            """UPDATE actor_career_term
               SET training_rolls_completed=training_rolls_completed+1
               WHERE career_term_id=%s""",
            (term[0],),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_term_training_applied')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (term[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_career_term_training(
            connection, command_id, public_id, False)


def _load_term_completion(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.prior_age_years,
                  receipt.resulting_age_years,receipt.prior_total_terms,
                  receipt.resulting_total_terms,system.retirement_terms,
                  COALESCE(
                      species.aging_start_age_years,
                      system.starting_age_years + system.term_years*4
                  )
           FROM cmd_career_term_completion_receipt receipt
           JOIN actor_career_term term
             ON term.career_term_id=receipt.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           LEFT JOIN actor_current_species current_species
             ON current_species.actor_id=actor.actor_id
           LEFT JOIN rule_species species
             ON species.species_rule_id=current_species.species_rule_id
           CROSS JOIN rule_career_system system
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerTermCompletionResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[2] >= row[6], replayed,
    )


def complete_career_term_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
) -> CareerTermCompletionResult:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("complete_career_term", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_term_completion(
                connection, existing[0], existing[1], True)
        term = connection.execute(
            """SELECT term.career_term_id,stint.career_stint_id,
                      actor.actor_id,term.training_rolls_completed,
                      lifepath.age_years,lifepath.total_terms,
                      system.term_years,
                      training.allowed_training_rolls
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_term term
                 ON term.career_stint_id=stint.career_stint_id
               JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=actor.actor_id
               CROSS JOIN rule_career_system system
               LEFT JOIN LATERAL (
                   SELECT max(receipt.allowed_training_rolls)
                          AS allowed_training_rolls
                   FROM cmd_career_term_training_receipt receipt
                   WHERE receipt.career_term_id=term.career_term_id
               ) training ON true
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND term.term_status='survival_passed'
               FOR UPDATE OF actor,stint,term,lifepath""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if term is None:
            raise ValueError("Actor has no trained term awaiting completion")
        if term[7] is None or term[3] != term[7]:
            raise ValueError("All allowed training rolls must be completed")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('complete_career_term',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE actor_lifepath_state
               SET age_years=age_years+%s,total_terms=total_terms+1
               WHERE actor_id=%s""",
            (term[6], term[2]),
        )
        connection.execute(
            """UPDATE actor_career_stint
               SET terms_completed=terms_completed+1
               WHERE career_stint_id=%s""",
            (term[1],),
        )
        connection.execute(
            """UPDATE actor_career_term
               SET term_status='completed',elapsed_years=%s,
                   benefit_roll_eligible=true
               WHERE career_term_id=%s""",
            (term[6], term[0]),
        )
        connection.execute(
            """INSERT INTO cmd_career_term_completion_receipt
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, term[0], term[4], term[4] + term[6],
             term[5], term[5] + 1),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_term_completed')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (term[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_term_completion(
            connection, command_id, public_id, False)


def _load_aging(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,lifepath.total_terms,
                  aging.anagathic_modifier,aging.table_result,
                  effect.aging_effect_code,effect.source_effect_text,
                  aging.aging_status
           FROM cmd_career_aging_determination_receipt receipt
           JOIN actor_career_aging aging
             ON aging.career_aging_id=receipt.career_aging_id
           JOIN rule_career_aging_effect effect
             ON effect.aging_effect_code=aging.aging_effect_code
           LEFT JOIN actor_career_term term
             ON term.career_term_id=aging.career_term_id
           LEFT JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           LEFT JOIN actor_career_anagathic_term use
             ON use.career_anagathic_term_id=
                aging.career_anagathic_term_id
           JOIN actor_actor actor
             ON actor.actor_id=COALESCE(stint.actor_id,use.actor_id)
           JOIN actor_lifepath_state lifepath
             ON lifepath.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerAgingResult(
        str(public_id), str(row[0]),
        _draws(connection, command_id, "career_aging"),
        row[1], row[2], row[3], row[4], row[5], row[6], replayed,
    )


def determine_career_aging_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> CareerAgingResult:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("determine_career_aging", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_aging(connection, existing[0], existing[1], True)
        term = connection.execute(
            """SELECT term.career_term_id,actor.actor_id,lifepath.total_terms,
                      COALESCE(use.continuous_course_terms,0)
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_term term
                 ON term.career_stint_id=stint.career_stint_id
               JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=actor.actor_id
               LEFT JOIN actor_career_anagathic_term use
                 ON use.career_anagathic_term_id=term.anagathic_term_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND term.term_status='completed'
                 AND lifepath.age_years>=COALESCE(
                     (
                         SELECT species.aging_start_age_years
                         FROM actor_current_species current_species
                         JOIN rule_species species
                           ON species.species_rule_id=
                              current_species.species_rule_id
                         WHERE current_species.actor_id=actor.actor_id
                     ),
                     (
                         SELECT starting_age_years + term_years*4
                         FROM rule_career_system
                     )
                 )
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_aging aging
                     WHERE aging.career_term_id=term.career_term_id)
               ORDER BY term.career_term_id DESC LIMIT 1
               FOR UPDATE OF actor,term,lifepath""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if term is None:
            raise ValueError("Actor has no completed term requiring aging")
        dice = (rng.randint(1, 6), rng.randint(1, 6))
        table_result = sum(dice) - term[2] + term[3]
        effect = connection.execute(
            """SELECT aging_effect_code,physical_reduction_pattern
               FROM rule_career_aging_effect
               WHERE %s<=maximum_table_result
               ORDER BY maximum_table_result LIMIT 1""",
            (table_result,),
        ).fetchone()
        status = (
            "no_effect" if effect[1] == "none" else "awaiting_allocation")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_career_aging',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_aging',%s,6,%s)""",
                (command_id, order, die),
            )
        aging_id = connection.execute(
            """INSERT INTO actor_career_aging
               (career_term_id,aging_effect_code,natural_total,
                term_modifier,anagathic_modifier,table_result,aging_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING career_aging_id""",
            (term[0], effect[0], sum(dice), -term[2], term[3],
             table_result, status),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_career_aging_determination_receipt
               VALUES (%s,%s)""",
            (command_id, aging_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_aging_determined')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (term[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_aging(connection, command_id, public_id, False)


def determine_anagathic_stopping_shock_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> CareerAgingResult:
    """Roll the immediate aging-table shock required when treatment stops."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("determine_career_aging", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_aging(connection, existing[0], existing[1], True)
        use = connection.execute(
            """SELECT use.career_anagathic_term_id,actor.actor_id,
                      lifepath.total_terms
               FROM actor_actor actor
               JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=actor.actor_id
               JOIN actor_career_anagathic_term use
                 ON use.actor_id=actor.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND use.declaration_status='shock_required'
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_aging aging
                     WHERE aging.career_anagathic_term_id=
                           use.career_anagathic_term_id
                 )
               ORDER BY use.career_anagathic_term_id DESC LIMIT 1
               FOR UPDATE OF actor,lifepath,use""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if use is None:
            raise ValueError("Actor has no anagathic stopping shock to resolve")
        dice = (rng.randint(1, 6), rng.randint(1, 6))
        table_result = sum(dice) - use[2]
        effect = connection.execute(
            """SELECT aging_effect_code,physical_reduction_pattern
               FROM rule_career_aging_effect
               WHERE %s<=maximum_table_result
               ORDER BY maximum_table_result LIMIT 1""",
            (table_result,),
        ).fetchone()
        status = (
            "no_effect" if effect[1] == "none" else "awaiting_allocation")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_career_aging',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_aging',%s,6,%s)""",
                (command_id, order, die),
            )
        aging_id = connection.execute(
            """INSERT INTO actor_career_aging
               (career_anagathic_term_id,aging_effect_code,natural_total,
                term_modifier,anagathic_modifier,table_result,aging_status)
               VALUES (%s,%s,%s,%s,0,%s,%s) RETURNING career_aging_id""",
            (use[0], effect[0], sum(dice), -use[2], table_result, status),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_career_aging_determination_receipt
               VALUES (%s,%s)""",
            (command_id, aging_id),
        )
        if status == "no_effect":
            connection.execute(
                """UPDATE actor_career_anagathic_term
                   SET declaration_status='resolved'
                   WHERE career_anagathic_term_id=%s""",
                (use[0],),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_aging_determined')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (use[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_aging(connection, command_id, public_id, False)


def _load_aging_application(connection, command_id, public_id, replayed):
    header = connection.execute(
        """SELECT actor.public_id,receipt.crisis_started,aging.aging_status
           FROM cmd_career_aging_application_receipt receipt
           JOIN actor_career_aging aging
             ON aging.career_aging_id=receipt.career_aging_id
           LEFT JOIN actor_career_term term
             ON term.career_term_id=aging.career_term_id
           LEFT JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           LEFT JOIN actor_career_anagathic_term use
             ON use.career_anagathic_term_id=
                aging.career_anagathic_term_id
           JOIN actor_actor actor
             ON actor.actor_id=COALESCE(stint.actor_id,use.actor_id)
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    rows = connection.execute(
        """SELECT rule.rule_code,reduction.reduction_amount,
                  reduction.prior_current_value,
                  reduction.resulting_current_value
           FROM cmd_career_aging_application_receipt receipt
           JOIN actor_career_aging_reduction reduction
             ON reduction.career_aging_id=receipt.career_aging_id
           JOIN rule_rule rule
             ON rule.rule_id=reduction.characteristic_rule_id
           WHERE receipt.command_id=%s ORDER BY reduction.reduction_order""",
        (command_id,),
    ).fetchall()
    return CareerAgingApplicationResult(
        str(public_id), str(header[0]),
        tuple(CareerInjuryReduction(*row) for row in rows),
        header[1], header[2], replayed,
    )


def apply_career_aging_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    physical_characteristic_codes: tuple[str, ...],
    mental_characteristic_code: str | None = None,
) -> CareerAgingApplicationResult:
    physical = {
        "characteristic.strength", "characteristic.dexterity",
        "characteristic.endurance",
    }
    mental = {
        "characteristic.intelligence", "characteristic.education",
        "characteristic.social-standing",
    }
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("apply_career_aging", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_aging_application(
                connection, existing[0], existing[1], True)
        aging = connection.execute(
            """SELECT aging.career_aging_id,actor.actor_id,
                      effect.physical_reduction_pattern,
                      effect.mental_reduction_amount
               FROM actor_career_aging aging
               JOIN rule_career_aging_effect effect
                 ON effect.aging_effect_code=aging.aging_effect_code
               LEFT JOIN actor_career_term term
                 ON term.career_term_id=aging.career_term_id
               LEFT JOIN actor_career_stint stint
                 ON stint.career_stint_id=term.career_stint_id
               LEFT JOIN actor_career_anagathic_term use
                 ON use.career_anagathic_term_id=
                    aging.career_anagathic_term_id
               JOIN actor_actor actor
                 ON actor.actor_id=COALESCE(stint.actor_id,use.actor_id)
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND aging.aging_status='awaiting_allocation'
               FOR UPDATE OF actor,aging""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if aging is None:
            raise ValueError("Actor has no aging reduction awaiting allocation")
        amounts_by_pattern = {
            "two_two_two": (2, 2, 2), "two_two_one": (2, 2, 1),
            "two_one_one": (2, 1, 1), "one_one_one": (1, 1, 1),
            "one_one": (1, 1), "one": (1,),
        }
        amounts = amounts_by_pattern[aging[2]]
        if len(physical_characteristic_codes) != len(amounts):
            raise ValueError("Aging allocation has the wrong number of physical targets")
        if (
            len(set(physical_characteristic_codes)) != len(amounts)
            or any(code not in physical for code in physical_characteristic_codes)
        ):
            raise ValueError("Aging physical targets must be distinct and legal")
        if aging[3]:
            if mental_characteristic_code not in mental:
                raise ValueError("Aging requires one legal mental target")
        elif mental_characteristic_code is not None:
            raise ValueError("This aging result has no mental reduction")
        allocations = list(zip(physical_characteristic_codes, amounts))
        if aging[3]:
            allocations.append((mental_characteristic_code, aging[3]))
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_career_aging',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        crisis = False
        for order, (code, amount) in enumerate(allocations, 1):
            state = connection.execute(
                """SELECT state.characteristic_rule_id,state.maximum_value,
                          state.current_value
                   FROM actor_characteristic state
                   JOIN rule_rule rule
                     ON rule.rule_id=state.characteristic_rule_id
                   WHERE state.actor_id=%s AND rule.rule_code=%s
                   FOR UPDATE OF state""",
                (aging[1], code),
            ).fetchone()
            if state is None:
                raise ValueError("Actor lacks an aging characteristic")
            new_max = max(0, state[1] - amount)
            new_current = min(max(0, state[2] - amount), new_max)
            crisis = crisis or new_max == 0 or new_current == 0
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=%s,current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (new_max, new_current, aging[1], state[0]),
            )
            connection.execute(
                """INSERT INTO actor_career_aging_reduction
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (aging[0], order, state[0], amount, state[1], state[2],
                 new_max, new_current),
            )
        status = "crisis" if crisis else "applied"
        connection.execute(
            """UPDATE actor_career_aging SET aging_status=%s
               WHERE career_aging_id=%s""",
            (status, aging[0]),
        )
        if status == "applied":
            connection.execute(
                """UPDATE actor_career_anagathic_term use
                   SET declaration_status='resolved'
                   FROM actor_career_aging aging
                   WHERE aging.career_aging_id=%s
                     AND use.career_anagathic_term_id=
                         aging.career_anagathic_term_id""",
                (aging[0],),
            )
        connection.execute(
            """INSERT INTO cmd_career_aging_application_receipt
               VALUES (%s,%s,%s)""",
            (command_id, aging[0], crisis),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_aging_crisis_started" if crisis
             else "career_aging_applied"),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (aging[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_aging_application(
            connection, command_id, public_id, False)


def _load_aging_crisis_cost(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,crisis.medical_cost_die,
                  crisis.medical_cost_credits,finance.cash_credits
           FROM cmd_aging_crisis_cost_receipt receipt
           JOIN actor_career_aging_crisis crisis
             ON crisis.aging_crisis_id=receipt.aging_crisis_id
           JOIN actor_actor actor ON actor.actor_id=crisis.actor_id
           JOIN actor_financial_state finance
             ON finance.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return AgingCrisisCostResult(
        str(public_id), str(row[0]), row[1], row[2], row[3],
        row[3] >= row[2], replayed,
    )


def determine_aging_crisis_cost_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> AgingCrisisCostResult:
    """Roll and retain the CE aging-crisis medical price."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("determine_aging_crisis_cost", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_aging_crisis_cost(
                connection, existing[0], existing[1], True)
        aging = connection.execute(
            """SELECT aging.career_aging_id,actor.actor_id
               FROM actor_career_aging aging
               LEFT JOIN actor_career_term term
                 ON term.career_term_id=aging.career_term_id
               LEFT JOIN actor_career_stint stint
                 ON stint.career_stint_id=term.career_stint_id
               LEFT JOIN actor_career_anagathic_term use
                 ON use.career_anagathic_term_id=
                    aging.career_anagathic_term_id
               JOIN actor_actor actor
                 ON actor.actor_id=COALESCE(stint.actor_id,use.actor_id)
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND aging.aging_status='crisis'
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_aging_crisis crisis
                     WHERE crisis.career_aging_id=aging.career_aging_id
                 )
               FOR UPDATE OF actor,aging""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if aging is None:
            raise ValueError("Actor has no unpriced aging crisis")
        die = rng.randint(1, 6)
        cost = die * 10000
        connection.execute(
            """INSERT INTO actor_financial_state (actor_id)
               VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
            (aging[1],),
        )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_aging_crisis_cost',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_random_draw
               (command_id,draw_group,draw_order,die_sides,result)
               VALUES (%s,'career_aging_crisis_cost',1,6,%s)""",
            (command_id, die),
        )
        crisis_id = connection.execute(
            """INSERT INTO actor_career_aging_crisis
               (career_aging_id,actor_id,medical_cost_die,
                medical_cost_credits)
               VALUES (%s,%s,%s,%s) RETURNING aging_crisis_id""",
            (aging[0], aging[1], die, cost),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_aging_crisis_cost_receipt VALUES (%s,%s)""",
            (command_id, crisis_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'aging_crisis_cost_determined')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (aging[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_aging_crisis_cost(
            connection, command_id, public_id, False)


def _load_aging_crisis_resolution(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,receipt.resolution_kind,
                  crisis.medical_cost_credits,receipt.cash_before,
                  receipt.cash_after,lifepath.lifepath_status,
                  lifepath.qualification_barred
           FROM cmd_aging_crisis_resolution_receipt receipt
           JOIN actor_career_aging_crisis crisis
             ON crisis.aging_crisis_id=receipt.aging_crisis_id
           JOIN actor_actor actor ON actor.actor_id=crisis.actor_id
           JOIN actor_lifepath_state lifepath
             ON lifepath.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    restored = connection.execute(
        """SELECT rule.rule_code
           FROM cmd_aging_crisis_restoration restoration
           JOIN rule_rule rule
             ON rule.rule_id=restoration.characteristic_rule_id
           WHERE restoration.command_id=%s ORDER BY rule.rule_code""",
        (command_id,),
    ).fetchall()
    return AgingCrisisResolutionResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], tuple(item[0] for item in restored), replayed,
    )


def resolve_aging_crisis_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, resolution_kind: str,
) -> AgingCrisisResolutionResult:
    """Apply the player's pay-or-die choice for a priced aging crisis."""
    if resolution_kind not in {"pay", "accept_death"}:
        raise ValueError("Aging crisis resolution must be pay or accept_death")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_aging_crisis", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_aging_crisis_resolution(
                connection, existing[0], existing[1], True)
        crisis = connection.execute(
            """SELECT crisis.aging_crisis_id,crisis.actor_id,
                      crisis.medical_cost_credits,finance.cash_credits,
                      aging.career_aging_id
               FROM actor_career_aging_crisis crisis
               JOIN actor_actor actor ON actor.actor_id=crisis.actor_id
               JOIN actor_financial_state finance
                 ON finance.actor_id=actor.actor_id
               JOIN actor_career_aging aging
                 ON aging.career_aging_id=crisis.career_aging_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND crisis.crisis_status='awaiting_decision'
               FOR UPDATE OF actor,finance,crisis,aging""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if crisis is None:
            raise ValueError("Actor has no priced aging crisis")
        cash_before = crisis[3]
        restorations = ()
        if resolution_kind == "pay":
            if cash_before < crisis[2]:
                raise ValueError("Actor cannot afford aging-crisis medical care")
            cash_after = cash_before - crisis[2]
            connection.execute(
                """UPDATE actor_financial_state SET cash_credits=%s
                   WHERE actor_id=%s""",
                (cash_after, crisis[1]),
            )
            restorations = connection.execute(
                """SELECT characteristic_rule_id,maximum_value,current_value
                   FROM actor_characteristic
                   WHERE actor_id=%s
                     AND (maximum_value=0 OR current_value=0)
                   FOR UPDATE""",
                (crisis[1],),
            ).fetchall()
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=GREATEST(maximum_value,1),
                       current_value=GREATEST(current_value,1)
                   WHERE actor_id=%s
                     AND (maximum_value=0 OR current_value=0)""",
                (crisis[1],),
            )
            cash_status = "paid"
            lifepath_status = "active"
            aging_status = "applied"
            event_type = "aging_crisis_paid"
        else:
            cash_after = cash_before
            cash_status = "death"
            lifepath_status = "deceased"
            aging_status = "crisis"
            event_type = "aging_crisis_death_accepted"
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_aging_crisis',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE actor_lifepath_state
               SET lifepath_status=%s,
                   qualification_barred=(
                       qualification_barred OR %s
                   )
               WHERE actor_id=%s""",
            (lifepath_status, resolution_kind == "pay", crisis[1]),
        )
        connection.execute(
            """UPDATE actor_career_aging_crisis SET crisis_status=%s
               WHERE aging_crisis_id=%s""",
            (cash_status, crisis[0]),
        )
        connection.execute(
            """UPDATE actor_career_aging SET aging_status=%s
               WHERE career_aging_id=%s""",
            (aging_status, crisis[4]),
        )
        connection.execute(
            """UPDATE actor_career_anagathic_term use
               SET declaration_status='resolved'
               FROM actor_career_aging aging
               WHERE aging.career_aging_id=%s
                 AND use.career_anagathic_term_id=
                     aging.career_anagathic_term_id""",
            (crisis[4],),
        )
        connection.execute(
            """INSERT INTO cmd_aging_crisis_resolution_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, crisis[0], resolution_kind, cash_before, cash_after),
        )
        for characteristic_id, prior_maximum, prior_current in restorations:
            connection.execute(
                """INSERT INTO cmd_aging_crisis_restoration
                   VALUES (%s,%s,%s,%s)""",
                (command_id, characteristic_id,
                 prior_maximum, prior_current),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event_type),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (crisis[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_aging_crisis_resolution(
            connection, command_id, public_id, False)


def _load_reenlistment(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,
                  reenlistment.target_number,reenlistment.natural_total,
                  reenlistment.total_terms_snapshot,reenlistment.outcome,
                  reenlistment.continuation,
                  reenlistment.retirement_required
           FROM cmd_career_reenlistment_determination_receipt receipt
           JOIN actor_career_reenlistment reenlistment
             ON reenlistment.career_reenlistment_id=
                receipt.career_reenlistment_id
           JOIN actor_career_term term
             ON term.career_term_id=reenlistment.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerReenlistmentResult(
        str(public_id), str(row[0]), row[1],
        _draws(connection, command_id, "career_reenlistment"),
        row[2], row[3], row[4], row[5], row[6], row[7], replayed,
    )


def determine_career_reenlistment_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, random_source=None,
) -> CareerReenlistmentResult:
    """Roll CE 9.1 reenlistment after the completed term and its aging."""
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
                "determine_career_reenlistment", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_reenlistment(
                connection, existing[0], existing[1], True)
        term = connection.execute(
            """SELECT term.career_term_id,stint.career_stint_id,
                      actor.actor_id,career.career_code,
                      progression.reenlistment_target,
                      lifepath.total_terms,system.retirement_terms,
                      aging.aging_status
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN rule_career career
                 ON career.career_rule_id=stint.career_rule_id
               JOIN rule_career_progression progression
                 ON progression.career_rule_id=stint.career_rule_id
                AND progression.assignment_rule_id
                    IS NOT DISTINCT FROM stint.assignment_rule_id
               JOIN actor_career_term term
                 ON term.career_stint_id=stint.career_stint_id
               JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=actor.actor_id
               CROSS JOIN rule_career_system system
               LEFT JOIN actor_career_aging aging
                 ON aging.career_term_id=term.career_term_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND term.term_status='completed'
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_reenlistment prior
                     WHERE prior.career_term_id=term.career_term_id
                 )
               ORDER BY term.term_number DESC LIMIT 1
               FOR UPDATE OF actor,stint,term,lifepath""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if term is None:
            raise ValueError(
                "Actor has no completed term awaiting reenlistment")
        if term[5] >= 4 and term[7] not in ("no_effect", "applied"):
            raise ValueError(
                "Career aging must be resolved before reenlistment")
        core = connection.execute(
            "SELECT dice_count,die_sides FROM rule_check_system"
        ).fetchone()
        dice = tuple(rng.randint(1, core[1]) for _ in range(core[0]))
        natural_total = sum(dice)
        if natural_total == 12:
            outcome = "forced_continue_natural_12"
            decision_status = "resolved"
            continuation = True
            retirement_required = False
            event_type = "career_reenlistment_forced_continue"
        elif term[5] >= term[6]:
            outcome = "mandatory_retirement"
            decision_status = "resolved"
            continuation = False
            retirement_required = True
            event_type = "career_retirement_required"
        elif natural_total < term[4]:
            outcome = "forced_leave_failed"
            decision_status = "resolved"
            continuation = False
            retirement_required = False
            event_type = "career_reenlistment_forced_departure"
        else:
            outcome = "choice_available"
            decision_status = "awaiting_choice"
            continuation = None
            retirement_required = False
            event_type = "career_reenlistment_choice_offered"
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('determine_career_reenlistment',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_reenlistment',%s,%s,%s)""",
                (command_id, order, core[1], value),
            )
        reenlistment_id = connection.execute(
            """INSERT INTO actor_career_reenlistment
               (career_term_id,target_number,natural_total,
                total_terms_snapshot,outcome,decision_status,continuation,
                retirement_required)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING career_reenlistment_id""",
            (term[0], term[4], natural_total, term[5], outcome,
             decision_status, continuation, retirement_required),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_career_reenlistment_determination_receipt
               VALUES (%s,%s)""",
            (command_id, reenlistment_id),
        )
        if continuation is False:
            connection.execute(
                """UPDATE actor_career_stint SET stint_status='left'
                   WHERE career_stint_id=%s""",
                (term[1],),
            )
        if retirement_required:
            connection.execute(
                """UPDATE actor_lifepath_state SET retirement_required=true
                   WHERE actor_id=%s""",
                (term[2],),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event_type),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (term[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_reenlistment(
            connection, command_id, public_id, False)


def _load_reenlistment_decision(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,
                  receipt.selected_continuation,stint.stint_status
           FROM cmd_career_reenlistment_decision_receipt receipt
           JOIN actor_career_reenlistment reenlistment
             ON reenlistment.career_reenlistment_id=
                receipt.career_reenlistment_id
           JOIN actor_career_term term
             ON term.career_term_id=reenlistment.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    decision = "continue" if row[2] else "leave"
    return CareerReenlistmentDecisionResult(
        str(public_id), str(row[0]), row[1], decision, row[2], row[3],
        replayed,
    )


def decide_career_reenlistment_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, decision: str,
) -> CareerReenlistmentDecisionResult:
    """Apply the player's choice after an ordinary successful check."""
    if decision not in ("continue", "leave"):
        raise ValueError("Reenlistment decision must be continue or leave")
    continuation = decision == "continue"
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("decide_career_reenlistment", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_reenlistment_decision(
                connection, existing[0], existing[1], True)
        reenlistment = connection.execute(
            """SELECT reenlistment.career_reenlistment_id,
                      stint.career_stint_id,actor.actor_id
               FROM actor_career_reenlistment reenlistment
               JOIN actor_career_term term
                 ON term.career_term_id=reenlistment.career_term_id
               JOIN actor_career_stint stint
                 ON stint.career_stint_id=term.career_stint_id
               JOIN actor_actor actor ON actor.actor_id=stint.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='active'
                 AND reenlistment.outcome='choice_available'
                 AND reenlistment.decision_status='awaiting_choice'
               FOR UPDATE OF actor,stint,reenlistment""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if reenlistment is None:
            raise ValueError(
                "Actor has no optional reenlistment choice awaiting decision")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('decide_career_reenlistment',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE actor_career_reenlistment
               SET decision_status='resolved',continuation=%s
               WHERE career_reenlistment_id=%s""",
            (continuation, reenlistment[0]),
        )
        if not continuation:
            connection.execute(
                """UPDATE actor_career_stint SET stint_status='left'
                   WHERE career_stint_id=%s""",
                (reenlistment[1],),
            )
        connection.execute(
            """INSERT INTO cmd_career_reenlistment_decision_receipt
               VALUES (%s,%s,%s)""",
            (command_id, reenlistment[0], continuation),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_reenlistment_chosen" if continuation
             else "career_departure_chosen"),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (reenlistment[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_reenlistment_decision(
            connection, command_id, public_id, False)


def _complete_retired_lifepath_if_ready(connection, actor_id):
    ready = connection.execute(
        """SELECT lifepath.retirement_required
                  AND NOT EXISTS (
                      SELECT 1
                      FROM actor_career_stint stint
                      LEFT JOIN actor_career_muster muster
                        ON muster.career_stint_id=stint.career_stint_id
                      WHERE stint.actor_id=lifepath.actor_id
                        AND stint.stint_status='left'
                        AND (
                            muster.career_muster_id IS NULL
                            OR muster.muster_status<>'completed'
                        )
                  )
           FROM actor_lifepath_state lifepath WHERE actor_id=%s""",
        (actor_id,),
    ).fetchone()[0]
    if ready:
        connection.execute(
            """UPDATE actor_lifepath_state SET lifepath_status='completed'
               WHERE actor_id=%s""",
            (actor_id,),
        )


def _load_career_medical_care(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,care.decision,
                  stint.rank_number,care.employer_roll_total,
                  care.employer_coverage_percent,care.gross_cost_credits,
                  care.employer_paid_credits,care.character_cost_credits,
                  care.medical_debt_before,care.medical_debt_after
           FROM cmd_career_medical_care_receipt receipt
           JOIN actor_career_medical_care care
             ON care.career_medical_care_id=receipt.career_medical_care_id
           JOIN actor_career_injury_result result
             ON result.injury_result_id=care.injury_result_id
           JOIN actor_career_injury_requirement requirement
             ON requirement.injury_requirement_id=
                result.injury_requirement_id
           JOIN actor_career_term term
             ON term.career_term_id=requirement.career_term_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=term.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    restorations = connection.execute(
        """SELECT rule.rule_code,restoration.points_restored,
                  restoration.prior_current_value,
                  restoration.resulting_current_value
           FROM cmd_career_medical_care_receipt receipt
           JOIN actor_career_medical_restoration restoration
             ON restoration.career_medical_care_id=
                receipt.career_medical_care_id
           JOIN rule_rule rule
             ON rule.rule_id=restoration.characteristic_rule_id
           WHERE receipt.command_id=%s
           ORDER BY restoration.restoration_order""",
        (command_id,),
    ).fetchall()
    return CareerMedicalCareResult(
        str(public_id), str(row[0]), row[1], row[2],
        _draws(connection, command_id, "career_medical_employer"),
        row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10],
        tuple(CareerMedicalRestoration(*item) for item in restorations),
        replayed,
    )


def resolve_career_medical_care_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, decision: str,
    restoration_points: dict[str, int] | None = None,
    random_source=None,
) -> CareerMedicalCareResult:
    """Resolve optional post-injury restoration and employer contribution."""
    if decision not in {"purchase", "decline"}:
        raise ValueError("Medical-care decision must be purchase or decline")
    requested = restoration_points or {}
    if decision == "decline" and requested:
        raise ValueError("Declined medical care cannot restore points")
    if decision == "purchase" and not requested:
        raise ValueError("Purchased medical care requires restoration points")
    if any(not isinstance(value, int) or value <= 0 for value in requested.values()):
        raise ValueError("Medical restoration points must be positive integers")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_career_medical_care", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_career_medical_care(
                connection, existing[0], existing[1], True)
        injury = connection.execute(
            """SELECT result.injury_result_id,actor.actor_id,
                      stint.career_stint_id,stint.rank_number,
                      coverage.percent_at_4,coverage.percent_at_8,
                      coverage.percent_at_12,finance.debt_credits,
                      finance.medical_debt_credits
               FROM actor_career_injury_result result
               JOIN actor_career_injury_requirement requirement
                 ON requirement.injury_requirement_id=
                    result.injury_requirement_id
               JOIN actor_career_term term
                 ON term.career_term_id=requirement.career_term_id
               JOIN actor_career_stint stint
                 ON stint.career_stint_id=term.career_stint_id
               JOIN actor_actor actor ON actor.actor_id=stint.actor_id
               JOIN rule_career_medical_coverage coverage
                 ON coverage.career_rule_id=stint.career_rule_id
               LEFT JOIN actor_financial_state finance
                 ON finance.actor_id=actor.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='left'
                 AND result.consequence_status IN ('applied','resolved')
                 AND EXISTS (
                     SELECT 1 FROM actor_career_injury_reduction reduction
                     WHERE reduction.injury_result_id=result.injury_result_id
                 )
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_medical_care care
                     WHERE care.injury_result_id=result.injury_result_id
                 )
               ORDER BY term.career_term_id LIMIT 1
               FOR UPDATE OF actor,stint,result""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if injury is None:
            raise ValueError(
                "Actor has no resolved injury awaiting medical-care decision")
        connection.execute(
            """INSERT INTO actor_financial_state (actor_id)
               VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
            (injury[1],),
        )
        finance = connection.execute(
            """SELECT debt_credits,medical_debt_credits
               FROM actor_financial_state WHERE actor_id=%s FOR UPDATE""",
            (injury[1],),
        ).fetchone()
        reductions = connection.execute(
            """SELECT rule.rule_code,reduction.characteristic_rule_id,
                      reduction.prior_maximum_value,
                      reduction.prior_current_value,
                      state.maximum_value,state.current_value
               FROM actor_career_injury_reduction reduction
               JOIN rule_rule rule
                 ON rule.rule_id=reduction.characteristic_rule_id
               JOIN actor_characteristic state
                 ON state.actor_id=%s
                AND state.characteristic_rule_id=
                    reduction.characteristic_rule_id
               WHERE reduction.injury_result_id=%s
               ORDER BY reduction.reduction_order
               FOR UPDATE OF state""",
            (injury[1], injury[0]),
        ).fetchall()
        by_code = {row[0]: row for row in reductions}
        unknown = set(requested) - set(by_code)
        if unknown:
            raise ValueError(
                "Medical care can restore only this injury's characteristics")
        planned = []
        for code, points in requested.items():
            row = by_code[code]
            maximum_headroom = row[2] - row[4]
            current_headroom = row[3] - row[5]
            if points > maximum_headroom or points > current_headroom:
                raise ValueError(
                    f"Medical care exceeds restorable loss for {code}")
            planned.append((code, row, points))
        dice = ()
        employer_total = None
        coverage_percent = 0
        if decision == "purchase":
            core = connection.execute(
                "SELECT dice_count,die_sides FROM rule_check_system"
            ).fetchone()
            dice = tuple(
                rng.randint(1, core[1]) for _ in range(core[0]))
            employer_total = sum(dice) + injury[3]
            if employer_total >= 12:
                coverage_percent = injury[6]
            elif employer_total >= 8:
                coverage_percent = injury[5]
            elif employer_total >= 4:
                coverage_percent = injury[4]
        gross_cost = sum(requested.values()) * 5000
        employer_paid = gross_cost * coverage_percent // 100
        character_cost = gross_cost - employer_paid
        medical_before = finance[1]
        medical_after = medical_before + character_cost
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_career_medical_care',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'career_medical_employer',%s,6,%s)""",
                (command_id, order, value),
            )
        care_id = connection.execute(
            """INSERT INTO actor_career_medical_care
               (injury_result_id,decision,employer_roll_total,
                employer_coverage_percent,gross_cost_credits,
                employer_paid_credits,character_cost_credits,
                medical_debt_before,medical_debt_after)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING career_medical_care_id""",
            (injury[0], decision, employer_total, coverage_percent,
             gross_cost, employer_paid, character_cost,
             medical_before, medical_after),
        ).fetchone()[0]
        for order, (code, row, points) in enumerate(planned, 1):
            resulting_maximum = row[4] + points
            resulting_current = row[5] + points
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=%s,current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (resulting_maximum, resulting_current, injury[1], row[1]),
            )
            connection.execute(
                """INSERT INTO actor_career_medical_restoration
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (care_id, order, row[1], points, row[4], row[5],
                 resulting_maximum, resulting_current),
            )
        connection.execute(
            """UPDATE actor_financial_state
               SET debt_credits=debt_credits+%s,
                   medical_debt_credits=medical_debt_credits+%s
               WHERE actor_id=%s""",
            (character_cost, character_cost, injury[1]),
        )
        connection.execute(
            """INSERT INTO cmd_career_medical_care_receipt VALUES (%s,%s)""",
            (command_id, care_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_medical_care_purchased"
             if decision == "purchase"
             else "career_medical_care_declined"),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (injury[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_career_medical_care(
            connection, command_id, public_id, False)


def _load_career_muster(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,
                  muster.eligible_term_benefits,
                  muster.rank_bonus_benefits,muster.total_benefit_rolls,
                  receipt.annual_pension_credits,muster.muster_status
           FROM cmd_career_muster_initialization_receipt receipt
           JOIN actor_career_muster muster
             ON muster.career_muster_id=receipt.career_muster_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=muster.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerMusterResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], replayed,
    )


def initialize_career_muster_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
) -> CareerMusterResult:
    """Calculate source-defined benefit rolls and any service pension."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("initialize_career_muster", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_career_muster(
                connection, existing[0], existing[1], True)
        stint = connection.execute(
            """SELECT stint.career_stint_id,actor.actor_id,
                      stint.terms_completed,stint.rank_number,
                      stint.all_benefits_forfeited,system.retirement_terms
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               CROSS JOIN rule_career_system system
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND stint.stint_status='left'
                 AND NOT EXISTS (
                     SELECT 1 FROM actor_career_muster muster
                     WHERE muster.career_stint_id=stint.career_stint_id
                 )
               ORDER BY stint.stint_order LIMIT 1
               FOR UPDATE OF actor,stint""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if stint is None:
            raise ValueError("Actor has no departed career awaiting benefits")
        unresolved_medical = connection.execute(
            """SELECT EXISTS (
                   SELECT 1
                   FROM actor_career_term term
                   JOIN actor_career_injury_requirement requirement
                     ON requirement.career_term_id=term.career_term_id
                   JOIN actor_career_injury_result result
                     ON result.injury_requirement_id=
                        requirement.injury_requirement_id
                   WHERE term.career_stint_id=%s
                     AND EXISTS (
                         SELECT 1
                         FROM actor_career_injury_reduction reduction
                         WHERE reduction.injury_result_id=
                            result.injury_result_id
                     )
                     AND NOT EXISTS (
                         SELECT 1 FROM actor_career_medical_care care
                         WHERE care.injury_result_id=result.injury_result_id
                     )
               )""",
            (stint[0],),
        ).fetchone()[0]
        if unresolved_medical:
            raise ValueError(
                "Career medical-care decision is required before benefits")
        eligible = 0 if stint[4] else connection.execute(
            """SELECT count(*) FROM actor_career_term
               WHERE career_stint_id=%s AND benefit_roll_eligible""",
            (stint[0],),
        ).fetchone()[0]
        rank_bonus = 0
        if not stint[4]:
            rank_bonus = {4: 1, 5: 2, 6: 3}.get(stint[3], 0)
        total = eligible + rank_bonus
        status = "completed" if total == 0 else "rolling"
        pension = (
            10000 + 2000 * (stint[2] - 5)
            if stint[2] >= 5 else 0
        )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('initialize_career_muster',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        muster_id = connection.execute(
            """INSERT INTO actor_career_muster
               (career_stint_id,eligible_term_benefits,
                rank_bonus_benefits,total_benefit_rolls,muster_status)
               VALUES (%s,%s,%s,%s,%s) RETURNING career_muster_id""",
            (stint[0], eligible, rank_bonus, total, status),
        ).fetchone()[0]
        if pension:
            connection.execute(
                """INSERT INTO actor_retirement_pension
                   (career_stint_id,qualifying_terms,annual_credits)
                   VALUES (%s,%s,%s)""",
                (stint[0], stint[2], pension),
            )
        connection.execute(
            """INSERT INTO cmd_career_muster_initialization_receipt
               VALUES (%s,%s,%s)""",
            (command_id, muster_id, pension),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'career_muster_initialized')""",
            (command_id,),
        )
        if pension:
            connection.execute(
                """INSERT INTO cmd_domain_event
                   (command_id,event_order,event_type)
                   VALUES (%s,2,'career_pension_awarded')""",
                (command_id,),
            )
        if status == "completed":
            _complete_retired_lifepath_if_ready(connection, stint[1])
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (stint[1],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_career_muster(
            connection, command_id, public_id, False)


def _load_career_benefit(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,career.career_code,roll.roll_order,
                  roll.benefit_table_code,roll.roll_modifier,
                  roll.table_result,benefit.outcome_kind,
                  benefit.source_outcome_text,roll.cash_awarded,
                  roll.medical_debt_paid,roll.anagathic_debt_paid,
                  roll.cash_retained,
                  roll.ship_shares_awarded,roll.award_status,
                  muster.rolls_completed,muster.total_benefit_rolls,
                  muster.muster_status
           FROM cmd_career_benefit_roll_receipt receipt
           JOIN actor_career_benefit_roll roll
             ON roll.career_benefit_roll_id=receipt.career_benefit_roll_id
           JOIN rule_career_benefit benefit
             ON benefit.career_benefit_id=roll.career_benefit_id
           JOIN actor_career_muster muster
             ON muster.career_muster_id=roll.career_muster_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=muster.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_career career
             ON career.career_rule_id=stint.career_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerBenefitRollResult(
        str(public_id), str(row[0]), row[1], row[2], row[3],
        _draws(connection, command_id, "career_benefit"),
        row[4], row[5], row[6], row[7], row[8], row[9], row[10],
        row[11], row[12], row[13], row[14], row[15], row[16], replayed,
    )


def roll_career_benefit_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    benefit_table_code: str, random_source=None,
) -> CareerBenefitRollResult:
    """Roll one player-selected Cash or Material mustering-out benefit."""
    if benefit_table_code not in ("cash", "material"):
        raise ValueError("Benefit table must be cash or material")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("roll_career_benefit", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_career_benefit(
                connection, existing[0], existing[1], True)
        muster = connection.execute(
            """SELECT muster.career_muster_id,stint.career_stint_id,
                      actor.actor_id,stint.career_rule_id,
                      muster.rolls_completed,muster.total_benefit_rolls,
                      muster.cash_rolls_taken,stint.rank_number,
                      lifepath.retirement_required
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_muster muster
                 ON muster.career_stint_id=stint.career_stint_id
               JOIN actor_lifepath_state lifepath
                 ON lifepath.actor_id=actor.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND muster.muster_status='rolling'
               ORDER BY stint.stint_order LIMIT 1
               FOR UPDATE OF actor,stint,muster,lifepath""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if muster is None:
            raise ValueError("Actor has no career benefit roll available")
        if benefit_table_code == "cash" and muster[6] >= 3:
            raise ValueError("No more than three Cash benefit rolls are allowed")
        natural_roll = rng.randint(1, 6)
        if benefit_table_code == "cash":
            gambling = connection.execute(
                """SELECT EXISTS (
                       SELECT 1 FROM actor_skill skill
                       JOIN rule_rule rule ON rule.rule_id=skill.skill_rule_id
                       WHERE skill.actor_id=%s
                         AND rule.rule_code='skill.gambling'
                   )""",
                (muster[2],),
            ).fetchone()[0]
            modifier = 1 if gambling or muster[8] else 0
        else:
            modifier = 1 if muster[7] in (5, 6) else 0
        table_result = min(7, natural_roll + modifier)
        benefit = connection.execute(
            """SELECT career_benefit_id,outcome_kind,cash_credits,
                      characteristic_rule_id,characteristic_increase,
                      passage_class,ship_share_dice_count,
                      ship_share_die_sides,membership_code,
                      vessel_access_code
               FROM rule_career_benefit
               WHERE career_rule_id=%s AND benefit_table_code=%s
                 AND roll_value=%s""",
            (muster[3], benefit_table_code, table_result),
        ).fetchone()
        if benefit is None:
            raise ValueError("Career benefit table is incomplete")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('roll_career_benefit',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """INSERT INTO cmd_random_draw
               (command_id,draw_group,draw_order,die_sides,result)
               VALUES (%s,'career_benefit',1,6,%s)""",
            (command_id, natural_roll),
        )
        cash_awarded = 0
        medical_debt_paid = 0
        anagathic_debt_paid = 0
        cash_retained = 0
        shares_awarded = 0
        award_status = "resolved"
        if benefit[1] == "cash":
            cash_awarded = benefit[2]
            connection.execute(
                """INSERT INTO actor_financial_state (actor_id)
                   VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
                (muster[2],),
            )
            finance = connection.execute(
                """SELECT medical_debt_credits,anagathic_debt_credits
                   FROM actor_financial_state WHERE actor_id=%s FOR UPDATE""",
                (muster[2],),
            ).fetchone()
            anagathic_debt_paid = min(cash_awarded, finance[1])
            remainder = cash_awarded - anagathic_debt_paid
            medical_debt_paid = min(remainder, finance[0])
            cash_retained = remainder - medical_debt_paid
            connection.execute(
                """UPDATE actor_financial_state
                   SET cash_credits=cash_credits+%s,
                       debt_credits=debt_credits-%s,
                       medical_debt_credits=medical_debt_credits-%s,
                       anagathic_debt_credits=anagathic_debt_credits-%s
                   WHERE actor_id=%s""",
                (cash_retained,
                 medical_debt_paid + anagathic_debt_paid,
                 medical_debt_paid, anagathic_debt_paid, muster[2]),
            )
        elif benefit[1] == "characteristic":
            connection.execute(
                """UPDATE actor_characteristic
                   SET maximum_value=maximum_value+%s,
                       current_value=current_value+%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (benefit[4], benefit[4], muster[2], benefit[3]),
            )
        elif benefit[1] == "passage":
            connection.execute(
                """INSERT INTO actor_passage_holding
                   (actor_id,passage_class,quantity) VALUES (%s,%s,1)
                   ON CONFLICT (actor_id,passage_class) DO UPDATE
                   SET quantity=actor_passage_holding.quantity+1""",
                (muster[2], benefit[5]),
            )
        elif benefit[1] == "ship_shares":
            share_dice = tuple(
                rng.randint(1, benefit[7]) for _ in range(benefit[6]))
            shares_awarded = sum(share_dice)
            for order, value in enumerate(share_dice, 1):
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (
                           %s,'career_benefit_ship_shares',%s,%s,%s
                       )""",
                    (command_id, order, benefit[7], value),
                )
            connection.execute(
                """INSERT INTO actor_ship_share_state (actor_id,shares)
                   VALUES (%s,%s) ON CONFLICT (actor_id) DO UPDATE
                   SET shares=actor_ship_share_state.shares+EXCLUDED.shares""",
                (muster[2], shares_awarded),
            )
        elif benefit[1] == "membership":
            connection.execute(
                """INSERT INTO actor_membership (actor_id,membership_code)
                   VALUES (%s,%s) ON CONFLICT DO NOTHING""",
                (muster[2], benefit[8]),
            )
        elif benefit[1] == "vessel_access":
            connection.execute(
                """INSERT INTO actor_vessel_access
                   (actor_id,vessel_access_code,quantity) VALUES (%s,%s,1)
                   ON CONFLICT (actor_id,vessel_access_code) DO UPDATE
                   SET quantity=actor_vessel_access.quantity+1""",
                (muster[2], benefit[9]),
            )
        elif benefit[1] == "weapon":
            award_status = "awaiting_weapon_choice"
        elif benefit[1] != "no_award":
            raise ValueError("Career benefit outcome is not implemented")
        roll_id = connection.execute(
            """INSERT INTO actor_career_benefit_roll
               (career_muster_id,roll_order,benefit_table_code,natural_roll,
                roll_modifier,table_result,career_benefit_id,award_status,
                cash_awarded,medical_debt_paid,anagathic_debt_paid,cash_retained,
                ship_shares_awarded)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING career_benefit_roll_id""",
            (muster[0], muster[4] + 1, benefit_table_code, natural_roll,
             modifier, table_result, benefit[0], award_status,
             cash_awarded, medical_debt_paid, anagathic_debt_paid, cash_retained,
             shares_awarded),
        ).fetchone()[0]
        if award_status == "awaiting_weapon_choice":
            next_status = "awaiting_weapon_choice"
        else:
            completed = muster[4] + 1
            next_status = (
                "completed" if completed == muster[5] else "rolling")
            connection.execute(
                """UPDATE actor_career_muster
                   SET rolls_completed=%s,muster_status=%s,
                       cash_rolls_taken=cash_rolls_taken+%s
                   WHERE career_muster_id=%s""",
                (completed, next_status,
                 1 if benefit_table_code == "cash" else 0, muster[0]),
            )
        if award_status == "awaiting_weapon_choice":
            connection.execute(
                """UPDATE actor_career_muster
                   SET muster_status='awaiting_weapon_choice',
                       cash_rolls_taken=cash_rolls_taken+%s
                   WHERE career_muster_id=%s""",
                (1 if benefit_table_code == "cash" else 0, muster[0]),
            )
        connection.execute(
            """INSERT INTO cmd_career_benefit_roll_receipt VALUES (%s,%s)""",
            (command_id, roll_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_weapon_benefit_choice_required"
             if award_status == "awaiting_weapon_choice"
             else "career_benefit_awarded"),
        )
        if next_status == "completed":
            _complete_retired_lifepath_if_ready(connection, muster[2])
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (muster[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_career_benefit(
            connection, command_id, public_id, False)


def _load_weapon_benefit(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,weapon.rule_code,receipt.resolution_kind,
                  skill.rule_code,receipt.prior_value,
                  receipt.resulting_value,muster.muster_status
           FROM cmd_career_weapon_benefit_receipt receipt
           JOIN actor_career_benefit_roll roll
             ON roll.career_benefit_roll_id=receipt.career_benefit_roll_id
           JOIN actor_career_muster muster
             ON muster.career_muster_id=roll.career_muster_id
           JOIN actor_career_stint stint
             ON stint.career_stint_id=muster.career_stint_id
           JOIN actor_actor actor ON actor.actor_id=stint.actor_id
           JOIN rule_rule weapon ON weapon.rule_id=receipt.weapon_rule_id
           LEFT JOIN rule_rule skill ON skill.rule_id=receipt.skill_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CareerWeaponBenefitResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], row[6], replayed,
    )


def resolve_career_weapon_benefit_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, weapon_rule_code: str,
    resolution_kind: str, skill_rule_code: str | None = None,
) -> CareerWeaponBenefitResult:
    """Resolve the player's source-authorized weapon or later skill choice."""
    if resolution_kind not in ("item", "skill"):
        raise ValueError("Weapon benefit resolution must be item or skill")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_career_weapon_benefit", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_weapon_benefit(
                connection, existing[0], existing[1], True)
        pending = connection.execute(
            """SELECT roll.career_benefit_roll_id,
                      muster.career_muster_id,muster.rolls_completed,
                      muster.total_benefit_rolls,actor.actor_id
               FROM actor_actor actor
               JOIN actor_career_stint stint ON stint.actor_id=actor.actor_id
               JOIN actor_career_muster muster
                 ON muster.career_stint_id=stint.career_stint_id
               JOIN actor_career_benefit_roll roll
                 ON roll.career_muster_id=muster.career_muster_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND muster.muster_status='awaiting_weapon_choice'
                 AND roll.award_status='awaiting_weapon_choice'
               FOR UPDATE OF actor,muster,roll""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if pending is None:
            raise ValueError("Actor has no weapon benefit awaiting choice")
        weapon = connection.execute(
            """SELECT weapon.item_rule_id
               FROM inv_weapon_definition weapon
               JOIN rule_rule rule ON rule.rule_id=weapon.item_rule_id
               WHERE rule.rule_code=%s""",
            (weapon_rule_code,),
        ).fetchone()
        if weapon is None:
            raise ValueError("Selected weapon does not exist")
        holding = connection.execute(
            """SELECT quantity FROM actor_item_holding
               WHERE actor_id=%s AND item_rule_id=%s FOR UPDATE""",
            (pending[4], weapon[0]),
        ).fetchone()
        prior = resulting = None
        skill_id = None
        if resolution_kind == "item":
            prior = holding[0] if holding else 0
            resulting = prior + 1
            connection.execute(
                """INSERT INTO actor_item_holding
                   (actor_id,item_rule_id,quantity) VALUES (%s,%s,1)
                   ON CONFLICT (actor_id,item_rule_id) DO UPDATE
                   SET quantity=actor_item_holding.quantity+1""",
                (pending[4], weapon[0]),
            )
            connection.execute(
                """INSERT INTO actor_weapon_state (actor_id,weapon_rule_id)
                   VALUES (%s,%s) ON CONFLICT DO NOTHING""",
                (pending[4], weapon[0]),
            )
            if skill_rule_code is not None:
                raise ValueError("Item choice does not accept a skill")
        else:
            if holding is None or holding[0] < 1:
                raise ValueError(
                    "A weapon must already be held before taking its skill")
            skill = connection.execute(
                """SELECT DISTINCT required.rule_id
                   FROM inv_weapon_attack_mode mode
                   JOIN combat_attack_profile profile
                     ON profile.attack_profile_code=mode.attack_profile_code
                   JOIN rule_rule required
                     ON required.rule_id=profile.required_skill_rule_id
                   WHERE mode.item_rule_id=%s
                     AND required.rule_code=%s""",
                (weapon[0], skill_rule_code),
            ).fetchone()
            if skill is None:
                raise ValueError("Skill is not associated with this weapon")
            skill_id = skill[0]
            current = connection.execute(
                """SELECT skill_level FROM actor_skill
                   WHERE actor_id=%s AND skill_rule_id=%s FOR UPDATE""",
                (pending[4], skill_id),
            ).fetchone()
            prior = current[0] if current else None
            resulting = (prior or 0) + 1
            connection.execute(
                """INSERT INTO actor_skill
                   (actor_id,skill_rule_id,skill_level) VALUES (%s,%s,%s)
                   ON CONFLICT (actor_id,skill_rule_id) DO UPDATE
                   SET skill_level=EXCLUDED.skill_level""",
                (pending[4], skill_id, resulting),
            )
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_career_weapon_benefit',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE actor_career_benefit_roll SET award_status='resolved'
               WHERE career_benefit_roll_id=%s""",
            (pending[0],),
        )
        completed = pending[2] + 1
        next_status = (
            "completed" if completed == pending[3] else "rolling")
        connection.execute(
            """UPDATE actor_career_muster
               SET rolls_completed=%s,muster_status=%s
               WHERE career_muster_id=%s""",
            (completed, next_status, pending[1]),
        )
        connection.execute(
            """INSERT INTO cmd_career_weapon_benefit_receipt
               (command_id,career_benefit_roll_id,weapon_rule_id,
                resolution_kind,skill_rule_id,prior_value,resulting_value)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, pending[0], weapon[0], resolution_kind, skill_id,
             prior, resulting),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "career_weapon_item_awarded"
             if resolution_kind == "item"
             else "career_weapon_skill_awarded"),
        )
        if next_status == "completed":
            _complete_retired_lifepath_if_ready(connection, pending[4])
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (pending[4],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_weapon_benefit(
            connection, command_id, public_id, False)


def _load_character_creation_completion(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT actor.public_id,receipt.age_years,receipt.total_terms,
                  receipt.career_stints,receipt.benefit_rolls_completed,
                  lifepath.lifepath_status
           FROM cmd_character_creation_completion_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN actor_lifepath_state lifepath
             ON lifepath.actor_id=actor.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return CharacterCreationCompletionResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4],
        row[5], replayed,
    )


def finish_character_creation_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
) -> CharacterCreationCompletionResult:
    """Apply the player's checklist choice to finish prior experience."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("finish_character_creation", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_character_creation_completion(
                connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor_id FROM actor_actor
               WHERE public_id=%s AND controller_reference=%s
               FOR UPDATE""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise PermissionError("Initiator does not control this actor")
        starting_age = connection.execute(
            """SELECT COALESCE(
                   (
                       SELECT species.maturity_age_years
                       FROM actor_current_species current_species
                       JOIN rule_species species
                         ON species.species_rule_id=
                            current_species.species_rule_id
                       WHERE current_species.actor_id=%s
                   ),
                   (SELECT starting_age_years FROM rule_career_system)
               )""",
            (actor[0],),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO actor_lifepath_state (actor_id,age_years)
               VALUES (%s,%s) ON CONFLICT (actor_id) DO NOTHING""",
            (actor[0], starting_age),
        )
        state = connection.execute(
            """SELECT lifepath_status,age_years,total_terms
               FROM actor_lifepath_state WHERE actor_id=%s FOR UPDATE""",
            (actor[0],),
        ).fetchone()
        if state[0] != "active":
            raise ValueError("Actor lifepath is not active")
        blocked = connection.execute(
            """SELECT
                 EXISTS (
                     SELECT 1 FROM actor_career_stint
                     WHERE actor_id=%s AND stint_status='active'
                 ),
                 EXISTS (
                     SELECT 1 FROM actor_career_entry_attempt
                     WHERE actor_id=%s
                       AND attempt_status='awaiting_fallback'
                 ),
                 EXISTS (
                     SELECT 1 FROM actor_career_injury_requirement
                     WHERE actor_id=%s AND requirement_status='pending'
                 ),
                 EXISTS (
                     SELECT 1
                     FROM actor_career_stint stint
                     LEFT JOIN actor_career_muster muster
                       ON muster.career_stint_id=stint.career_stint_id
                     WHERE stint.actor_id=%s
                       AND stint.stint_status='left'
                       AND (
                           muster.career_muster_id IS NULL
                           OR muster.muster_status<>'completed'
                       )
                 )""",
            (actor[0], actor[0], actor[0], actor[0]),
        ).fetchone()
        messages = (
            "An active career must be left before character creation ends",
            "A failed career entry still requires resolution",
            "A career injury still requires resolution",
            "All departed career benefits must be completed",
        )
        for is_blocked, message in zip(blocked, messages):
            if is_blocked:
                raise ValueError(message)
        career_stints, benefit_rolls = connection.execute(
            """SELECT
                   (SELECT count(*) FROM actor_career_stint
                    WHERE actor_id=%s),
                   (SELECT count(*)
                    FROM actor_career_benefit_roll roll
                    JOIN actor_career_muster muster
                      ON muster.career_muster_id=roll.career_muster_id
                    JOIN actor_career_stint stint
                      ON stint.career_stint_id=muster.career_stint_id
                    WHERE stint.actor_id=%s
                      AND roll.award_status='resolved')""",
            (actor[0], actor[0]),
        ).fetchone()
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('finish_character_creation',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE actor_lifepath_state SET lifepath_status='completed'
               WHERE actor_id=%s""",
            (actor[0],),
        )
        connection.execute(
            """INSERT INTO cmd_character_creation_completion_receipt
               (command_id,actor_id,age_years,total_terms,career_stints,
                benefit_rolls_completed)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, actor[0], state[1], state[2], career_stints,
             benefit_rolls),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'character_creation_completed')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (actor[0],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_character_creation_completion(
            connection, command_id, public_id, False)
