"""Source-governed psionic activation, expenditure, and recovery."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import secrets

import psycopg


@dataclass(frozen=True)
class PsionicActivationResult:
    command_public_id: str
    actor_public_id: str
    power_rule_code: str
    target_actor_public_id: str | None
    activation_dice: tuple[int, ...]
    timing_dice: tuple[int, ...]
    check_total: int
    target_number: int
    effect: int
    succeeded: bool
    psionic_cost: int
    psionic_strength_before: int
    psionic_strength_after: int
    overexertion_damage: int
    endurance_before: int
    endurance_after: int
    timing_total: int | None
    timing_unit: str | None
    replayed: bool


@dataclass(frozen=True)
class PsionicRecoveryResult:
    command_public_id: str
    actor_public_id: str
    recovered_at: datetime
    points_available: int
    points_recovered: int
    psionic_strength_before: int
    psionic_strength_after: int
    next_recovery_at: datetime | None
    replayed: bool


@dataclass(frozen=True)
class TelepathicShieldResult:
    command_public_id: str
    actor_public_id: str
    shield_before: bool
    shield_after: bool
    replayed: bool


@dataclass(frozen=True)
class LifeDetectionObservation:
    general_mind_type: str
    approximate_location: str
    detected_actor_public_id: str | None = None
    recognized_known_individual: bool = False
    recognition_basis: str | None = None


@dataclass(frozen=True)
class ProbeQuestion:
    question_text: str
    divulged_information: str
    deliberate_untruth_detected: bool = False


def _prepare_awareness_effect(
    connection, actor_id, power_code, variable_points,
    regeneration_allocations,
):
    if power_code == "suspended-animation":
        if regeneration_allocations:
            raise ValueError("Suspended Animation has no healing allocations")
        return {"kind": "suspended_animation"}
    if power_code in ("enhanced-strength", "enhanced-endurance"):
        if regeneration_allocations:
            raise ValueError("Characteristic enhancement has no allocations")
        characteristic_code = (
            "characteristic.strength"
            if power_code == "enhanced-strength"
            else "characteristic.endurance"
        )
        row = connection.execute(
            """SELECT characteristic.characteristic_rule_id,
                      characteristic.current_value,skill.skill_level,
                      15+COALESCE(generation.racial_maximum_modifier,0)
               FROM actor_characteristic characteristic
               JOIN rule_rule characteristic_rule
                 ON characteristic_rule.rule_id=
                    characteristic.characteristic_rule_id
                AND characteristic_rule.rule_code=%s
               JOIN actor_skill skill ON skill.actor_id=characteristic.actor_id
               JOIN rule_rule skill_rule ON skill_rule.rule_id=skill.skill_rule_id
                AND skill_rule.rule_code='skill.psionic-awareness'
               LEFT JOIN actor_current_species species
                 ON species.actor_id=characteristic.actor_id
               LEFT JOIN rule_species_characteristic_generation generation
                 ON generation.species_rule_id=species.species_rule_id
                AND generation.characteristic_rule_id=
                    characteristic.characteristic_rule_id
               WHERE characteristic.actor_id=%s
               FOR UPDATE OF characteristic,skill""",
            (characteristic_code, actor_id),
        ).fetchone()
        if row is None:
            raise ValueError("Enhancement requires its physical characteristic")
        if variable_points > row[2]:
            raise ValueError("Enhancement exceeds the current Awareness level")
        if row[1] + variable_points > row[3]:
            raise ValueError("Enhancement exceeds the racial maximum")
        return {
            "kind": "characteristic_enhancement",
            "characteristic_rule_id": row[0],
            "wounded_value": row[1],
            "awareness_level": row[2],
            "racial_maximum": row[3],
            "points": variable_points,
        }
    if power_code == "regeneration":
        if not regeneration_allocations:
            raise ValueError("Regeneration requires healing allocations")
        if connection.execute(
            """SELECT 1 FROM camp_psi_regeneration_recovery_lock
               WHERE actor_id=%s""",
            (actor_id,),
        ).fetchone():
            raise ValueError(
                "Regeneration remains unavailable until spent Psi is recovered")
        if sum(points for _, points in regeneration_allocations) != variable_points:
            raise ValueError("Regeneration allocations must equal points spent")
        if len({code for code, _ in regeneration_allocations}) != len(
            regeneration_allocations
        ):
            raise ValueError("Regeneration characteristics must be unique")
        rows = connection.execute(
            """SELECT rule.rule_code,state.characteristic_rule_id,
                      state.current_value,state.maximum_value
               FROM actor_characteristic state
               JOIN rule_rule rule
                 ON rule.rule_id=state.characteristic_rule_id
               WHERE state.actor_id=%s
                 AND rule.rule_code IN (
                   'characteristic.strength','characteristic.dexterity',
                   'characteristic.endurance'
                 )
               FOR UPDATE OF state""",
            (actor_id,),
        ).fetchall()
        states = {row[0]: row[1:] for row in rows}
        prepared = []
        for order, (code, points) in enumerate(regeneration_allocations, 1):
            if points <= 0 or code not in states:
                raise ValueError("Invalid Regeneration allocation")
            rule_id, before, maximum = states[code]
            if before + points > maximum:
                raise ValueError("Regeneration cannot exceed the wounded maximum")
            prepared.append((order, rule_id, points, before, before + points,
                             maximum))
        psi_maximum = connection.execute(
            """SELECT maximum_value FROM actor_characteristic
               WHERE actor_id=%s AND characteristic_rule_id=(
                 SELECT characteristic_rule_id FROM psi_system
               )""",
            (actor_id,),
        ).fetchone()[0]
        return {
            "kind": "regeneration",
            "points": variable_points,
            "psi_maximum": psi_maximum,
            "requests": regeneration_allocations,
            "allocations": prepared,
        }
    if regeneration_allocations:
        raise ValueError("Only Regeneration accepts healing allocations")
    return None


def _record_awareness_effect(
    connection, command_id, actor_id, activated_at, prepared,
):
    if prepared is None:
        return
    connection.execute(
        """INSERT INTO cmd_psi_awareness_effect_receipt
           VALUES (%s,%s,%s,%s)""",
        (command_id, actor_id, prepared["kind"], activated_at),
    )
    if prepared["kind"] == "suspended_animation":
        connection.execute(
            """INSERT INTO cmd_psi_suspended_animation_receipt
               VALUES (%s,%s+interval '7 days')""",
            (command_id, activated_at),
        )
    elif prepared["kind"] == "characteristic_enhancement":
        peak_ends = activated_at + timedelta(minutes=10)
        connection.execute(
            """INSERT INTO cmd_psi_characteristic_enhancement_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                command_id, prepared["characteristic_rule_id"],
                prepared["wounded_value"], prepared["racial_maximum"],
                prepared["awareness_level"], prepared["points"], peak_ends,
                peak_ends + timedelta(minutes=prepared["points"]),
            ),
        )
    else:
        connection.execute(
            """INSERT INTO cmd_psi_regeneration_receipt
               VALUES (%s,%s,%s)""",
            (command_id, prepared["points"], prepared["psi_maximum"]),
        )
        for allocation in prepared["allocations"]:
            connection.execute(
                """INSERT INTO cmd_psi_regeneration_allocation
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (command_id, *allocation),
            )
            connection.execute(
                """UPDATE actor_characteristic SET current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=%s""",
                (allocation[4], actor_id, allocation[1]),
            )
        connection.execute(
            """INSERT INTO camp_psi_regeneration_recovery_lock
               VALUES (%s,%s,%s)""",
            (actor_id, command_id, prepared["psi_maximum"]),
        )


def _refresh_awareness_effect_snapshots(connection, actor_id, prepared):
    if prepared is None:
        return
    if prepared["kind"] == "characteristic_enhancement":
        prepared["wounded_value"] = connection.execute(
            """SELECT current_value FROM actor_characteristic
               WHERE actor_id=%s AND characteristic_rule_id=%s""",
            (actor_id, prepared["characteristic_rule_id"]),
        ).fetchone()[0]
    elif prepared["kind"] == "regeneration":
        refreshed = []
        for order, (code, points) in enumerate(prepared["requests"], 1):
            rule_id, before, maximum = connection.execute(
                """SELECT state.characteristic_rule_id,state.current_value,
                          state.maximum_value
                   FROM actor_characteristic state
                   JOIN rule_rule rule
                     ON rule.rule_id=state.characteristic_rule_id
                   WHERE state.actor_id=%s AND rule.rule_code=%s""",
                (actor_id, code),
            ).fetchone()
            if before + points > maximum:
                raise ValueError(
                    "Regeneration cannot exceed the post-expenditure maximum")
            refreshed.append(
                (order, rule_id, points, before, before + points, maximum))
        prepared["allocations"] = refreshed


def _prepare_telekinetic_manipulation(
    connection, actor_id, power_rule_id, item_public_id,
    creature_public_id, creature_mass_grams, duration_rounds,
):
    profile = connection.execute(
        """SELECT maximum_mass_grams
           FROM rule_psi_telekinesis_mass_profile
           WHERE power_rule_id=%s""",
        (power_rule_id,),
    ).fetchone()
    supplied = sum(value is not None for value in (
        item_public_id, creature_public_id))
    if profile is None:
        if supplied or creature_mass_grams is not None or duration_rounds is not None:
            raise ValueError("Only Telekinesis accepts manipulation targets")
        return None
    if supplied != 1:
        raise ValueError("Telekinesis requires exactly one item or creature")
    if duration_rounds is None or duration_rounds <= 0:
        raise ValueError("Telekinesis requires positive resolved duration")
    if item_public_id is not None:
        row = connection.execute(
            """SELECT item.item_instance_id,definition.mass_grams,
                      item.campaign_id
               FROM inv_item_instance item
               JOIN inv_item_definition definition
                 ON definition.rule_id=item.item_rule_id
               JOIN actor_actor actor
                 ON actor.actor_id=%s
                AND actor.campaign_id=item.campaign_id
               WHERE item.public_id=%s AND item.item_status='active'""",
            (actor_id, item_public_id),
        ).fetchone()
        if row is None or row[1] is None or row[1] <= 0:
            raise ValueError("Telekinetic item requires exact known mass")
        target_kind, target_id, mass, campaign_id = (
            "item", row[0], row[1], row[2])
    else:
        row = connection.execute(
            """SELECT target.actor_id,target.campaign_id
               FROM actor_actor target JOIN actor_actor source
                 ON source.actor_id=%s
                AND source.campaign_id=target.campaign_id
               WHERE target.public_id=%s""",
            (actor_id, creature_public_id),
        ).fetchone()
        if row is None or creature_mass_grams is None or creature_mass_grams <= 0:
            raise ValueError(
                "Telekinetic creature requires an explicit positive mass")
        target_kind, target_id, mass, campaign_id = (
            "creature", row[0], creature_mass_grams, row[1])
    if mass > profile[0]:
        raise ValueError("Target exceeds the Telekinesis mass ceiling")
    return {
        "kind": target_kind,
        "target_id": target_id,
        "mass": mass,
        "maximum_mass": profile[0],
        "duration_rounds": duration_rounds,
        "campaign_id": campaign_id,
    }


def _prepare_telekinetic_throw(
    connection, actor_id, power_rule_id, manipulation,
    target_actor_public_id, psion_to_target_metres,
    object_origin_to_target_metres, range_rule_code,
    circumstance_modifiers,
):
    supplied = (
        target_actor_public_id, psion_to_target_metres,
        object_origin_to_target_metres, range_rule_code,
    )
    if all(value is None for value in supplied):
        if circumstance_modifiers:
            raise ValueError(
                "Telekinetic throw modifiers require a throw target")
        return None
    if manipulation is None or any(value is None for value in supplied):
        raise ValueError(
            "A telekinetic throw requires a manipulated object, target, "
            "both distances, and combat range")
    if psion_to_target_metres < 0 or object_origin_to_target_metres < 0:
        raise ValueError("Telekinetic throw distances cannot be negative")
    row = connection.execute(
        """SELECT target.actor_id,range_band.rule_id,difficulty.modifier,
                  skill.skill_level,modifier.modifier,
                  profile.throwing_damage_dice_count,
                  profile.throwing_damage_die_sides,
                  profile.throwing_damage_flat,
                  profile.can_inflict_throwing_damage
           FROM actor_actor source
           JOIN actor_actor target
             ON target.public_id=%s
            AND target.campaign_id=source.campaign_id
           JOIN rule_rule range_rule ON range_rule.rule_code=%s
           JOIN combat_range_band range_band
             ON range_band.rule_id=range_rule.rule_id
           JOIN combat_attack_profile_difficulty profile_difficulty
             ON profile_difficulty.attack_profile_code='thrown'
            AND profile_difficulty.range_band_rule_id=range_band.rule_id
            AND profile_difficulty.permitted
           JOIN rule_difficulty difficulty
             ON difficulty.rule_id=profile_difficulty.difficulty_rule_id
           JOIN rule_psi_telekinesis_system system
             ON system.talent_rule_id=(
                  SELECT talent_rule_id FROM psi_power
                  WHERE power_rule_id=%s
                )
           JOIN actor_skill skill
             ON skill.actor_id=source.actor_id
            AND skill.skill_rule_id=system.throwing_skill_rule_id
           JOIN actor_characteristic dexterity
             ON dexterity.actor_id=source.actor_id
            AND dexterity.characteristic_rule_id=(
                  SELECT rule_id FROM rule_rule
                  WHERE rule_code='characteristic.dexterity'
                )
           JOIN rule_characteristic_modifier_band modifier
             ON (modifier.characteristic_rule_id IS NULL
                 OR modifier.characteristic_rule_id=
                    dexterity.characteristic_rule_id)
            AND modifier.score_range @> dexterity.current_value::integer
           JOIN rule_psi_telekinesis_mass_profile profile
             ON profile.power_rule_id=%s
           WHERE source.actor_id=%s
           ORDER BY modifier.characteristic_rule_id NULLS LAST
           LIMIT 1""",
        (target_actor_public_id, range_rule_code, power_rule_id,
         power_rule_id, actor_id),
    ).fetchone()
    if row is None:
        raise ValueError(
            "No legal telekinetic thrown attack matches actor, target, or range")
    if not row[8]:
        raise ValueError("This Telekinesis mass cannot inflict throwing damage")
    if manipulation["kind"] == "creature" and manipulation["target_id"] == row[0]:
        raise ValueError("A thrown creature cannot be its own impact target")
    return {
        "target_actor_id": row[0],
        "range_band_rule_id": row[1],
        "difficulty_modifier": row[2],
        "skill_modifier": row[3],
        "characteristic_modifier": row[4],
        "damage_dice_count": row[5],
        "damage_die_sides": row[6],
        "damage_flat": row[7],
        "psion_to_target_metres": psion_to_target_metres,
        "object_origin_to_target_metres": object_origin_to_target_metres,
        "selected_distance_metres": max(
            psion_to_target_metres, object_origin_to_target_metres),
        "circumstance_modifier_total": sum(circumstance_modifiers),
    }


def _prepare_life_detection(
    connection, actor_id, power_code, area_reference, referee_summary,
    observations,
):
    supplied = (
        area_reference is not None or referee_summary is not None
        or bool(observations)
    )
    if power_code != "life-detection":
        if supplied:
            raise ValueError("Only Life Detection accepts detected minds")
        return None
    if not area_reference or not area_reference.strip():
        raise ValueError("Life Detection requires a search area reference")
    if not referee_summary or not referee_summary.strip():
        raise ValueError("Life Detection requires Referee observation evidence")
    campaign_id = connection.execute(
        "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
        (actor_id,),
    ).fetchone()[0]
    prepared = []
    for order, observation in enumerate(observations, 1):
        if (
            not observation.general_mind_type
            or not observation.general_mind_type.strip()
            or not observation.approximate_location
            or not observation.approximate_location.strip()
        ):
            raise ValueError(
                "Every detected mind requires general type and location")
        if observation.recognized_known_individual:
            if (
                observation.detected_actor_public_id is None
                or not observation.recognition_basis
                or not observation.recognition_basis.strip()
            ):
                raise ValueError(
                    "Recognized minds require an actor and recognition basis")
        elif observation.recognition_basis is not None:
            raise ValueError(
                "Unrecognized minds cannot carry recognition evidence")
        detected_actor_id = None
        if observation.detected_actor_public_id is not None:
            row = connection.execute(
                """SELECT target.actor_id,
                          EXISTS (
                            SELECT 1 FROM actor_skill skill
                            JOIN rule_rule rule
                              ON rule.rule_id=skill.skill_rule_id
                             AND rule.rule_code='skill.psionic-telepathy'
                            WHERE skill.actor_id=target.actor_id
                          ),
                          COALESCE(shield.shield_raised,true)
                   FROM actor_actor target
                   JOIN actor_actor source
                     ON source.actor_id=%s
                    AND source.campaign_id=target.campaign_id
                   LEFT JOIN actor_telepathic_shield_state shield
                     ON shield.actor_id=target.actor_id
                   WHERE target.public_id=%s""",
                (actor_id, observation.detected_actor_public_id),
            ).fetchone()
            if row is None:
                raise ValueError(
                    "Detected actor is outside the activation campaign")
            if row[1] and row[2]:
                raise ValueError("Shielded minds are undetectable")
            detected_actor_id = row[0]
        prepared.append(
            (
                order, detected_actor_id, campaign_id,
                observation.general_mind_type.strip(),
                observation.approximate_location.strip(), True,
                observation.recognized_known_individual,
                observation.recognition_basis.strip()
                if observation.recognition_basis else None,
            )
        )
    return {
        "campaign_id": campaign_id,
        "area_reference": area_reference.strip(),
        "referee_summary": referee_summary.strip(),
        "minds": tuple(prepared),
    }


def _prepare_telempathy(
    power_code, target_actor_id, target_is_telepath, operation,
    projected_emotion, perceived_emotions, referee_outcome,
):
    supplied = any(value is not None for value in (
        operation, projected_emotion, perceived_emotions, referee_outcome,
    ))
    if power_code != "telempathy":
        if supplied:
            raise ValueError("Only Telempathy accepts emotional evidence")
        return None
    if operation not in ("read", "project", "read_and_project"):
        raise ValueError("Telempathy requires a read or project operation")
    if not referee_outcome or not referee_outcome.strip():
        raise ValueError("Telempathy requires Referee outcome evidence")
    reads = operation in ("read", "read_and_project")
    projects = operation in ("project", "read_and_project")
    if reads != bool(perceived_emotions and perceived_emotions.strip()):
        raise ValueError(
            "Telempathy reading requires only perceived-emotion evidence")
    if projects != bool(projected_emotion and projected_emotion.strip()):
        raise ValueError(
            "Telempathy projection requires only a projected emotion")
    return {
        "target_actor_id": target_actor_id,
        "operation": operation,
        "projected_emotion": (
            projected_emotion.strip() if projected_emotion else None),
        "perceived_emotions": (
            perceived_emotions.strip() if perceived_emotions else None),
        "target_recognized": bool(target_is_telepath and projects),
        "referee_outcome": referee_outcome.strip(),
    }


def _prepare_surface_thoughts(
    power_code, target_actor_id, target_is_telepath, thoughts,
    clarity_evidence, consent_reference,
):
    supplied = any(value is not None for value in (
        thoughts, clarity_evidence, consent_reference,
    ))
    if power_code != "read-surface-thoughts":
        if supplied:
            raise ValueError(
                "Only Read Surface Thoughts accepts thought evidence")
        return None
    if not thoughts or not thoughts.strip():
        raise ValueError("Read Surface Thoughts requires current thoughts")
    if not clarity_evidence or not clarity_evidence.strip():
        raise ValueError("Read Surface Thoughts requires clarity evidence")
    if target_is_telepath:
        if not consent_reference or not consent_reference.strip():
            raise ValueError(
                "Reading a telepath requires willing shield-lowering evidence")
    elif consent_reference is not None:
        raise ValueError(
            "Nontelepath surface-thought reading has no shield consent")
    return {
        "target_actor_id": target_actor_id,
        "target_is_telepath": target_is_telepath,
        "target_unaware": not target_is_telepath,
        "consent_reference": (
            consent_reference.strip() if consent_reference else None),
        "thoughts": thoughts.strip(),
        "clarity_evidence": clarity_evidence.strip(),
    }


def _prepare_send_thoughts(
    power_code, target_actor_id, target_is_telepath, transmitted_thought,
):
    if power_code != "send-thoughts":
        if transmitted_thought is not None:
            raise ValueError("Only Send Thoughts accepts transmitted content")
        return None
    if not transmitted_thought or not transmitted_thought.strip():
        raise ValueError("Send Thoughts requires transmitted thought content")
    return {
        "target_actor_id": target_actor_id,
        "target_is_telepath": target_is_telepath,
        "transmitted_thought": transmitted_thought.strip(),
    }


def _prepare_probe(
    power_code, target_actor_id, innermost_thoughts, clarity_evidence,
    questions,
):
    supplied = any((
        innermost_thoughts is not None,
        clarity_evidence is not None,
        bool(questions),
    ))
    if power_code not in ("probe-deliberate", "probe-rapid"):
        if supplied:
            raise ValueError("Only Probe accepts Probe evidence")
        return None
    if not innermost_thoughts or not innermost_thoughts.strip():
        raise ValueError("Probe requires innermost-thought evidence")
    if not clarity_evidence or not clarity_evidence.strip():
        raise ValueError("Probe requires Effect-dependent clarity evidence")
    question_rows = []
    for order, question in enumerate(questions, 1):
        if not question.question_text or not question.question_text.strip():
            raise ValueError("Probe questions require question text")
        if (
            not question.divulged_information
            or not question.divulged_information.strip()
        ):
            raise ValueError("Probe questions require divulged information")
        question_rows.append((
            order, question.question_text.strip(),
            question.divulged_information.strip(),
            bool(question.deliberate_untruth_detected),
        ))
    return {
        "target_actor_id": target_actor_id,
        "mode": (
            "deliberate" if power_code == "probe-deliberate" else "rapid"
        ),
        "innermost_thoughts": innermost_thoughts.strip(),
        "clarity_evidence": clarity_evidence.strip(),
        "questions": tuple(question_rows),
    }


def _draws(connection, command_id, group):
    return tuple(row[0] for row in connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group=%s ORDER BY draw_order""",
        (command_id, group),
    ).fetchall())


def _load_activation(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,power_rule.rule_code,target.public_id,
                  receipt.check_total,
                  receipt.target_number,receipt.effect,receipt.succeeded,
                  receipt.psionic_cost,receipt.psionic_strength_before,
                  receipt.psionic_strength_after,receipt.overexertion_damage,
                  receipt.endurance_before,receipt.endurance_after,
                  receipt.timing_total,receipt.timing_unit
           FROM cmd_psionic_activation_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule power_rule
             ON power_rule.rule_id=receipt.power_rule_id
           LEFT JOIN actor_actor target
             ON target.actor_id=receipt.target_actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return PsionicActivationResult(
        str(public_id), str(row[0]), row[1],
        str(row[2]) if row[2] is not None else None,
        _draws(connection, command_id, "psionic_activation"),
        _draws(connection, command_id, "psionic_timing"),
        row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10],
        row[11], row[12], row[13], row[14], replayed,
    )


def activate_psionic_power_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, power_rule_code: str,
    range_rule_code: str | None = None, variable_points: int = 0,
    circumstance_modifiers: tuple[int, ...] = (),
    encounter_public_id: str | None = None, random_source=None,
    used_at: datetime | None = None,
    target_actor_public_id: str | None = None,
    regeneration_allocations: tuple[tuple[str, int], ...] = (),
    target_location_public_id: str | None = None,
    clairvoyant_observation: str | None = None,
    clairvoyant_maintained_rounds: int | None = None,
    telekinetic_item_public_id: str | None = None,
    telekinetic_creature_public_id: str | None = None,
    telekinetic_creature_mass_grams: int | None = None,
    telekinetic_duration_rounds: int | None = None,
    telekinetic_throw_target_actor_public_id: str | None = None,
    telekinetic_psion_to_target_metres=None,
    telekinetic_object_origin_to_target_metres=None,
    telekinetic_throw_range_rule_code: str | None = None,
    telekinetic_throw_circumstance_modifiers: tuple[int, ...] = (),
    life_detection_area_reference: str | None = None,
    life_detection_referee_summary: str | None = None,
    life_detection_observations: tuple[LifeDetectionObservation, ...] = (),
    telempathy_operation: str | None = None,
    telempathy_projected_emotion: str | None = None,
    telempathy_perceived_emotions: str | None = None,
    telempathy_referee_outcome: str | None = None,
    surface_thoughts_active_current: str | None = None,
    surface_thoughts_clarity_evidence: str | None = None,
    surface_thoughts_telepath_consent_reference: str | None = None,
    sent_thought_content: str | None = None,
    probe_innermost_thoughts: str | None = None,
    probe_clarity_evidence: str | None = None,
    probe_questions: tuple[ProbeQuestion, ...] = (),
    teleport_destination_location_public_id: str | None = None,
    teleport_destination_knowledge_kind: str | None = None,
    teleport_destination_knowledge_evidence: str | None = None,
    teleport_planetary_surface_jump: bool = True,
    teleport_altitude_change_metres=0,
    teleport_hourly_cumulative_altitude_metres=0,
    teleport_environmental_hazard_resolution: str | None = None,
    teleport_fast_vehicle_transition: bool = False,
    teleport_vehicle_ramming_resolution: str | None = None,
) -> PsionicActivationResult:
    if variable_points < 0:
        raise ValueError("Variable Psionic Strength points cannot be negative")
    rng = random_source or secrets.SystemRandom()
    use_time = used_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("activate_psionic_power", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_activation(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT actor.actor_id,power.power_rule_id,power.power_code,
                      power.base_cost,power.cost_per_point,
                      power.adds_range_cost,power.requires_check,
                      power.mechanics_complete,power.timing_dice_count,
                      power.timing_die_sides,power.timing_unit,
                      skill_state.skill_level,difficulty.modifier,
                      psi.current_value,psi.maximum_value,
                      endurance.current_value,
                      system.failed_activation_cost,
                      system.recovery_delay_hours,core.dice_count,
                      core.die_sides,core.target_number
               FROM actor_actor actor
               JOIN rule_rule power_rule ON power_rule.rule_code=%s
               JOIN psi_power power ON power.power_rule_id=power_rule.rule_id
               JOIN psi_talent talent
                 ON talent.talent_rule_id=power.talent_rule_id
               JOIN actor_skill skill_state
                 ON skill_state.actor_id=actor.actor_id
                AND skill_state.skill_rule_id=talent.skill_rule_id
               LEFT JOIN rule_difficulty difficulty
                 ON difficulty.rule_id=power.difficulty_rule_id
               CROSS JOIN psi_system system
               JOIN actor_characteristic psi
                 ON psi.actor_id=actor.actor_id
                AND psi.characteristic_rule_id=
                    system.characteristic_rule_id
               JOIN actor_characteristic endurance
                 ON endurance.actor_id=actor.actor_id
                AND endurance.characteristic_rule_id=
                    system.overexertion_characteristic_rule_id
               CROSS JOIN rule_check_system core
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor,skill_state,psi,endurance""",
            (power_rule_code, actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError(
                "Actor lacks the trained talent or required characteristics")
        anti_psionic = connection.execute(
            """SELECT EXISTS (
                   SELECT 1
                   FROM actor_current_species current_species
                   JOIN rule_species_trait_assignment assignment
                     ON assignment.species_rule_id=
                        current_species.species_rule_id
                   JOIN rule_species_trait trait
                     ON trait.species_trait_rule_id=
                        assignment.species_trait_rule_id
                   WHERE current_species.actor_id=%s
                     AND trait.trait_code='anti-psionic'
               )""",
            (state[0],),
        ).fetchone()[0]
        if anti_psionic:
            raise ValueError(
                "Anti-Psionic species cannot activate psionic powers")
        if not state[7]:
            raise ValueError("The governing sources do not complete this power")
        if not state[6] or state[3] is None or state[12] is None:
            raise ValueError("This power does not use the activation procedure")
        if state[13] <= 0:
            raise ValueError(
                "A character with no Psionic Strength cannot activate a power")
        if state[4] and variable_points <= 0:
            raise ValueError("This power requires a positive point expenditure")
        if not state[4] and variable_points != 0:
            raise ValueError("This power has no variable point expenditure")
        target_kind, talent_code = connection.execute(
            """SELECT targeting.target_kind,talent_rule.rule_code
               FROM psi_power_targeting targeting
               JOIN psi_power power
                 ON power.power_rule_id=targeting.power_rule_id
               JOIN rule_rule talent_rule
                 ON talent_rule.rule_id=power.talent_rule_id
               WHERE targeting.power_rule_id=%s""",
            (state[1],),
        ).fetchone()
        is_telepathy = talent_code == "psionics.talent.telepathy"
        if is_telepathy:
            own_shield = connection.execute(
                """SELECT COALESCE((
                       SELECT shield_raised
                       FROM actor_telepathic_shield_state
                       WHERE actor_id=%s
                   ),true)""",
                (state[0],),
            ).fetchone()[0]
            if own_shield:
                raise ValueError(
                    "A telepath must lower their shield before using Telepathy")
        target_actor_id = None
        target_is_telepath = False
        if target_kind == "actor":
            if target_actor_public_id is None:
                raise ValueError("This power requires a target actor")
            target = connection.execute(
                """SELECT target.actor_id,
                          EXISTS (
                              SELECT 1 FROM actor_skill skill_state
                              JOIN rule_rule skill_rule
                                ON skill_rule.rule_id=skill_state.skill_rule_id
                              WHERE skill_state.actor_id=target.actor_id
                                AND skill_rule.rule_code=
                                    'skill.psionic-telepathy'
                          ),
                          COALESCE(shield.shield_raised,true),
                          EXISTS (
                              SELECT 1
                              FROM actor_current_species current_species
                              JOIN rule_species_trait_assignment assignment
                                ON assignment.species_rule_id=
                                   current_species.species_rule_id
                              JOIN rule_species_trait trait
                                ON trait.species_trait_rule_id=
                                   assignment.species_trait_rule_id
                              WHERE current_species.actor_id=target.actor_id
                                AND trait.trait_code='anti-psionic'
                          ),
                          (SELECT skill_state.skill_level
                             FROM actor_skill skill_state
                             JOIN rule_rule skill_rule
                               ON skill_rule.rule_id=
                                  skill_state.skill_rule_id
                              AND skill_rule.rule_code=
                                  'skill.psionic-telepathy'
                            WHERE skill_state.actor_id=target.actor_id),
                          (SELECT characteristic.current_value
                             FROM actor_characteristic characteristic
                             JOIN rule_rule characteristic_rule
                               ON characteristic_rule.rule_id=
                                  characteristic.characteristic_rule_id
                              AND characteristic_rule.rule_code=
                                  'characteristic.psionic-strength'
                            WHERE characteristic.actor_id=target.actor_id)
                   FROM actor_actor target
                   JOIN actor_actor source
                     ON source.actor_id=%s
                    AND source.campaign_id=target.campaign_id
                   LEFT JOIN actor_telepathic_shield_state shield
                     ON shield.actor_id=target.actor_id
                   WHERE target.public_id=%s
                   FOR UPDATE OF target""",
                (state[0], target_actor_public_id),
            ).fetchone()
            if target is None or target[0] == state[0]:
                raise ValueError("Target actor is not a different campaign actor")
            if is_telepathy and target[3]:
                raise ValueError(
                    "Anti-Psionic target is immune to mental psionic effects")
            if (
                is_telepathy and target[1] and target[2]
                and state[2] != "assault"
            ):
                raise ValueError("Target's telepathic shield blocks the power")
            target_actor_id = target[0]
            target_is_telepath = target[1]
        elif target_actor_public_id is not None:
            raise ValueError("This power does not target a specific actor")
        assault_target = None
        if state[2] == "assault":
            condition = connection.execute(
                """SELECT unconscious FROM actor_personal_condition
                   WHERE actor_id=%s FOR UPDATE""",
                (target_actor_id,),
            ).fetchone()
            if condition and condition[0]:
                raise ValueError("Target is already unconscious")
            characteristic_rows = connection.execute(
                """SELECT rule.rule_code,state.characteristic_rule_id,
                          state.current_value
                   FROM actor_characteristic state
                   JOIN rule_rule rule
                     ON rule.rule_id=state.characteristic_rule_id
                   WHERE state.actor_id=%s
                     AND rule.rule_code=ANY(%s)
                   FOR UPDATE OF state""",
                (
                    target_actor_id,
                    [
                        "characteristic.psionic-strength",
                        "characteristic.intelligence",
                        "characteristic.endurance",
                    ],
                ),
            ).fetchall()
            characteristics = {
                row[0]: (row[1], row[2]) for row in characteristic_rows
            }
            if not {
                "characteristic.intelligence",
                "characteristic.endurance",
            }.issubset(characteristics):
                raise ValueError(
                    "Assault target requires Intelligence and Endurance")
            assault_target = {
                "shielded": bool(target[1] and target[2]),
                "skill": target[4],
                "psi": target[5],
                "characteristics": characteristics,
            }
            if assault_target["shielded"] and assault_target["psi"] is None:
                raise ValueError(
                    "Shielded Assault target requires Psionic Strength")
        target_location_id = None
        if target_kind == "location":
            if target_location_public_id is None:
                raise ValueError("This power requires a target location")
            if not clairvoyant_observation or not clairvoyant_observation.strip():
                raise ValueError(
                    "Successful remote perception requires Referee evidence")
            location = connection.execute(
                """SELECT location.location_id
                   FROM loc_location location
                   JOIN actor_actor actor
                     ON actor.actor_id=%s
                    AND actor.campaign_id=location.campaign_id
                   WHERE location.public_id=%s""",
                (state[0], target_location_public_id),
            ).fetchone()
            if location is None:
                raise ValueError("Target is not a location in the actor campaign")
            target_location_id = location[0]
        elif (
            target_location_public_id is not None
            or clairvoyant_observation is not None
            or clairvoyant_maintained_rounds is not None
        ):
            raise ValueError("This power does not create remote observations")
        awareness_effect = _prepare_awareness_effect(
            connection, state[0], state[2], variable_points,
            regeneration_allocations,
        )
        telekinetic_manipulation = _prepare_telekinetic_manipulation(
            connection, state[0], state[1], telekinetic_item_public_id,
            telekinetic_creature_public_id,
            telekinetic_creature_mass_grams, telekinetic_duration_rounds,
        )
        telekinetic_throw = _prepare_telekinetic_throw(
            connection, state[0], state[1], telekinetic_manipulation,
            telekinetic_throw_target_actor_public_id,
            telekinetic_psion_to_target_metres,
            telekinetic_object_origin_to_target_metres,
            telekinetic_throw_range_rule_code,
            telekinetic_throw_circumstance_modifiers,
        )
        life_detection = _prepare_life_detection(
            connection, state[0], state[2], life_detection_area_reference,
            life_detection_referee_summary, life_detection_observations,
        )
        telempathy = _prepare_telempathy(
            state[2], target_actor_id, target_is_telepath,
            telempathy_operation, telempathy_projected_emotion,
            telempathy_perceived_emotions, telempathy_referee_outcome,
        )
        surface_thoughts = _prepare_surface_thoughts(
            state[2], target_actor_id, target_is_telepath,
            surface_thoughts_active_current,
            surface_thoughts_clarity_evidence,
            surface_thoughts_telepath_consent_reference,
        )
        sent_thought = _prepare_send_thoughts(
            state[2], target_actor_id, target_is_telepath,
            sent_thought_content,
        )
        probe = _prepare_probe(
            state[2], target_actor_id, probe_innermost_thoughts,
            probe_clarity_evidence, probe_questions,
        )
        range_id = None
        range_cost = 0
        if state[5]:
            if range_rule_code is None:
                raise ValueError("This power requires a psionic range")
            range_row = connection.execute(
                """SELECT band.range_band_rule_id,cost.psionic_strength_cost
                   FROM rule_rule range_rule
                   JOIN psi_range_band band
                     ON band.range_band_rule_id=range_rule.rule_id
                   JOIN psi_talent_range_cost cost
                     ON cost.range_band_rule_id=band.range_band_rule_id
                    AND cost.talent_rule_id=(
                        SELECT talent_rule_id FROM psi_power
                        WHERE power_rule_id=%s
                    )
                   WHERE range_rule.rule_code=%s AND cost.permitted""",
                (state[1], range_rule_code),
            ).fetchone()
            if range_row is None:
                raise ValueError("Power is not permitted at that range")
            range_id, range_cost = range_row
        elif range_rule_code is not None:
            raise ValueError("This power does not use a range cost")
        teleport = None
        teleport_profile = connection.execute(
            """SELECT profile.load_kind
               FROM rule_psi_teleportation_power profile
               WHERE profile.power_rule_id=%s""",
            (state[1],),
        ).fetchone()
        teleport_arguments = (
            teleport_destination_location_public_id,
            teleport_destination_knowledge_kind,
            teleport_destination_knowledge_evidence,
            teleport_environmental_hazard_resolution,
            teleport_vehicle_ramming_resolution,
        )
        if teleport_profile is not None:
            if not teleport_destination_location_public_id:
                raise ValueError("Teleportation requires a destination location")
            if teleport_destination_knowledge_kind not in {
                "personal_visit", "distant_view", "telepathic_implant",
                "clairvoyance",
            }:
                raise ValueError(
                    "Teleportation requires permitted destination-image provenance")
            if not (
                teleport_destination_knowledge_evidence
                and teleport_destination_knowledge_evidence.strip()
            ):
                raise ValueError(
                    "Teleportation requires destination-image evidence")
            position = connection.execute(
                """SELECT position.actor_position_id,position.campaign_id,
                          position.location_id,actor.concurrency_version
                   FROM loc_actor_position position
                   JOIN actor_actor actor
                     ON actor.actor_id=position.actor_id
                    AND actor.campaign_id=position.campaign_id
                   WHERE position.actor_id=%s
                     AND position.position_status='current'
                   FOR UPDATE OF position""",
                (state[0],),
            ).fetchone()
            if position is None:
                raise ValueError(
                    "Teleporting actor requires an authoritative current position")
            destination = connection.execute(
                """SELECT location_id FROM loc_location
                   WHERE public_id=%s AND campaign_id=%s
                     AND location_status IN ('active','inaccessible')""",
                (teleport_destination_location_public_id, position[1]),
            ).fetchone()
            if destination is None:
                raise ValueError("Teleport destination is outside the campaign")
            altitude_change = float(teleport_altitude_change_metres)
            hourly_altitude = float(
                teleport_hourly_cumulative_altitude_metres)
            if hourly_altitude < abs(altitude_change):
                raise ValueError(
                    "Hourly altitude movement cannot be less than this jump")
            safe_single, safe_hourly = connection.execute(
                """SELECT abs(%s)<=maximum_safe_single_altitude_metres,
                          %s<=maximum_safe_hourly_altitude_metres
                   FROM rule_psi_teleportation_system""",
                (altitude_change, hourly_altitude),
            ).fetchone()
            if not (safe_single and safe_hourly) and not (
                teleport_environmental_hazard_resolution
                and teleport_environmental_hazard_resolution.strip()
            ):
                raise ValueError(
                    "Unsafe altitude change requires environmental hazard resolution")
            if teleport_fast_vehicle_transition and not (
                teleport_vehicle_ramming_resolution
                and teleport_vehicle_ramming_resolution.strip()
            ):
                raise ValueError(
                    "Fast-vehicle teleport requires ramming-damage resolution")
            selected_order, maximum_order, disorientation_dice, disorientation_sides = (
                connection.execute(
                    """SELECT selected.display_order,maximum.display_order,
                              disorientation.duration_dice_count,
                              disorientation.duration_die_sides
                       FROM psi_range_band selected
                       CROSS JOIN rule_psi_teleportation_system system
                       JOIN psi_range_band maximum ON maximum.range_band_rule_id=
                            system.planetary_maximum_range_rule_id
                       LEFT JOIN rule_psi_teleportation_disorientation disorientation
                         ON disorientation.range_band_rule_id=
                            selected.range_band_rule_id
                       WHERE selected.range_band_rule_id=%s""",
                    (range_id,),
                ).fetchone()
            )
            if teleport_planetary_surface_jump and selected_order > maximum_order:
                raise ValueError(
                    "Planetary Teleportation cannot exceed Very Distant range")
            teleport = {
                "load_kind": teleport_profile[0], "position": position,
                "destination_location_id": destination[0],
                "knowledge_kind": teleport_destination_knowledge_kind,
                "knowledge_evidence":
                    teleport_destination_knowledge_evidence.strip(),
                "planetary": teleport_planetary_surface_jump,
                "altitude_change": altitude_change,
                "hourly_altitude": hourly_altitude,
                "safe_single": safe_single, "safe_hourly": safe_hourly,
                "hazard": (
                    teleport_environmental_hazard_resolution.strip()
                    if teleport_environmental_hazard_resolution else None),
                "fast_vehicle": teleport_fast_vehicle_transition,
                "ramming": (
                    teleport_vehicle_ramming_resolution.strip()
                    if teleport_vehicle_ramming_resolution else None),
                "disorientation_dice": disorientation_dice or 0,
                "disorientation_sides": disorientation_sides,
            }
        elif any(value is not None for value in teleport_arguments) or (
            teleport_altitude_change_metres != 0
            or teleport_hourly_cumulative_altitude_metres != 0
            or teleport_fast_vehicle_transition
        ):
            raise ValueError("This power does not teleport the actor")
        psi_modifier = connection.execute(
            """SELECT modifier
               FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=(
                          SELECT rule_id FROM rule_rule
                          WHERE rule_code='characteristic.psionic-strength'
                      ))
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (state[13],),
        ).fetchone()[0]
        encounter_id = round_number = significant_before = significant_after = None
        if encounter_public_id is not None:
            combat = connection.execute(
                """SELECT pc.encounter_id,pc.current_round,
                          combatant.significant_actions_remaining
                   FROM enc_personal_combat pc
                   JOIN enc_encounter encounter
                     ON encounter.encounter_id=pc.encounter_id
                   JOIN enc_personal_combatant combatant
                     ON combatant.encounter_id=pc.encounter_id
                    AND combatant.actor_id=%s
                   WHERE encounter.public_id=%s
                     AND encounter.encounter_status='active'
                     AND pc.combat_status='active'
                     AND combatant.turn_started_this_round
                     AND NOT combatant.acted_this_round
                   FOR UPDATE OF pc,combatant""",
                (state[0], encounter_public_id),
            ).fetchone()
            if combat is None or combat[2] < 1:
                raise ValueError("No significant combat action remains")
            encounter_id, round_number, significant_before = combat
            significant_after = significant_before - 1
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('activate_psionic_power',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        activation_dice = tuple(
            rng.randint(1, state[19]) for _ in range(state[18]))
        timing_dice = tuple(
            rng.randint(1, state[9]) for _ in range(state[8] or 0))
        for group, dice, sides in (
            ("psionic_activation", activation_dice, state[19]),
            ("psionic_timing", timing_dice, state[9]),
        ):
            for order, value in enumerate(dice, 1):
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (command_id, group, order, sides, value))
        total = (
            sum(activation_dice) + state[11] + psi_modifier + state[12]
            + sum(circumstance_modifiers)
        )
        effect = total - state[20]
        succeeded = total >= state[20]
        base_cost = state[3]
        successful_power_cost = (
            base_cost * variable_points if state[4] else base_cost)
        psionic_cost = (
            successful_power_cost + range_cost if succeeded else state[16])
        psi_after = max(0, state[13] - psionic_cost)
        overexertion = max(0, psionic_cost - state[13])
        endurance_after = max(0, state[15] - overexertion)
        connection.execute(
            """UPDATE actor_characteristic SET current_value=%s
               WHERE actor_id=%s AND characteristic_rule_id=(
                   SELECT characteristic_rule_id FROM psi_system
               )""",
            (psi_after, state[0]),
        )
        if overexertion:
            connection.execute(
                """UPDATE actor_characteristic SET current_value=%s
                   WHERE actor_id=%s AND characteristic_rule_id=(
                       SELECT overexertion_characteristic_rule_id
                       FROM psi_system
                   )""",
                (endurance_after, state[0]),
            )
        connection.execute(
            """INSERT INTO actor_psionic_state
               (actor_id,last_talent_use_at,next_recovery_at)
               VALUES (%s,%s,%s+(%s * interval '1 hour'))
               ON CONFLICT (actor_id) DO UPDATE SET
                 last_talent_use_at=EXCLUDED.last_talent_use_at,
                 next_recovery_at=EXCLUDED.next_recovery_at""",
            (state[0], use_time, use_time, state[17]),
        )
        if encounter_id is not None:
            connection.execute(
                """UPDATE enc_personal_combatant
                   SET significant_actions_remaining=%s,
                       aim_target_actor_id=NULL,aim_modifier=0,
                       kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
                   WHERE encounter_id=%s AND actor_id=%s""",
                (significant_after, encounter_id, state[0]),
            )
        timing_total = sum(timing_dice) if timing_dice else None
        connection.execute(
            """INSERT INTO cmd_psionic_activation_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], range_id, encounter_id,
             round_number, state[11], psi_modifier, state[12],
             sum(circumstance_modifiers), total, state[20], effect, succeeded,
             variable_points, base_cost, range_cost, psionic_cost, state[13],
             psi_after, overexertion, state[15], endurance_after, timing_total,
             state[10], significant_before, significant_after,
             target_actor_id, target_location_id),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "psionic_power_activated" if succeeded
             else "psionic_power_failed"),
        )
        if succeeded:
            _refresh_awareness_effect_snapshots(
                connection, state[0], awareness_effect)
            _record_awareness_effect(
                connection, command_id, state[0], use_time, awareness_effect)
            if teleport is not None:
                disorientation_draws = tuple(
                    rng.randint(1, teleport["disorientation_sides"])
                    for _ in range(teleport["disorientation_dice"])
                )
                for order, value in enumerate(disorientation_draws, 1):
                    connection.execute(
                        """INSERT INTO cmd_random_draw
                           (command_id,draw_group,draw_order,die_sides,result)
                           VALUES (%s,'psionic_teleport_disorientation',%s,%s,%s)""",
                        (command_id, order,
                         teleport["disorientation_sides"], value),
                    )
                position = teleport["position"]
                connection.execute(
                    """UPDATE loc_actor_position
                       SET position_status='departed',ended_at=%s,
                           source_command_id=%s
                       WHERE actor_position_id=%s""",
                    (use_time, command_id, position[0]),
                )
                destination_position_id = connection.execute(
                    """INSERT INTO loc_actor_position
                       (campaign_id,actor_id,location_id,effective_at,
                        source_command_id)
                       VALUES (%s,%s,%s,%s,%s)
                       RETURNING actor_position_id""",
                    (position[1], state[0],
                     teleport["destination_location_id"], use_time,
                     command_id),
                ).fetchone()[0]
                connection.execute(
                    """UPDATE actor_actor
                       SET concurrency_version=concurrency_version+1
                       WHERE actor_id=%s""",
                    (state[0],),
                )
                connection.execute(
                    """INSERT INTO cmd_psi_teleportation_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                               %s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], position[1], position[0],
                        destination_position_id, position[2],
                        teleport["destination_location_id"],
                        teleport["knowledge_kind"],
                        teleport["knowledge_evidence"],
                        teleport["load_kind"], teleport["planetary"],
                        teleport["altitude_change"],
                        teleport["hourly_altitude"],
                        teleport["safe_single"], teleport["safe_hourly"],
                        -teleport["altitude_change"] * 2.5 / 1000,
                        teleport["hazard"], teleport["fast_vehicle"],
                        teleport["ramming"],
                        sum(disorientation_draws) * 10
                        if disorientation_draws else None,
                        position[3], position[3] + 1, use_time,
                    ),
                )
            if target_location_id is not None:
                mechanic = connection.execute(
                    """SELECT sensory_vision,sensory_hearing,snapshot_only
                       FROM rule_psi_clairvoyance_power
                       WHERE power_rule_id=%s""",
                    (state[1],),
                ).fetchone()
                if mechanic[2] and clairvoyant_maintained_rounds is not None:
                    raise ValueError("Sense is a snapshot, not maintained")
                if not mechanic[2] and (
                    clairvoyant_maintained_rounds is None
                    or clairvoyant_maintained_rounds <= 0
                ):
                    raise ValueError(
                        "Remote viewing requires positive maintained rounds")
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (state[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_psi_clairvoyant_observation_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], campaign_id, target_location_id,
                        effect, timing_total, mechanic[0], mechanic[1],
                        mechanic[2], clairvoyant_maintained_rounds,
                        clairvoyant_observation.strip(), use_time,
                    ),
                )
            if life_detection is not None:
                detection = life_detection
                connection.execute(
                    """INSERT INTO cmd_psi_life_detection_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], detection["campaign_id"], effect,
                        timing_total, detection["area_reference"],
                        detection["referee_summary"], len(detection["minds"]),
                        use_time,
                    ),
                )
                for mind in detection["minds"]:
                    connection.execute(
                        """INSERT INTO cmd_psi_life_detection_mind
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (command_id, *mind),
                    )
            if telempathy is not None:
                emotional = telempathy
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (state[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_psi_telempathy_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,%s)""",
                    (
                        command_id, state[0], emotional["target_actor_id"],
                        campaign_id, emotional["operation"], effect,
                        timing_total, emotional["projected_emotion"],
                        emotional["perceived_emotions"],
                        emotional["target_recognized"],
                        emotional["referee_outcome"], use_time,
                    ),
                )
            if surface_thoughts is not None:
                observed = surface_thoughts
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (state[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_psi_surface_thought_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], observed["target_actor_id"],
                        campaign_id, effect, timing_total,
                        observed["target_is_telepath"],
                        observed["target_unaware"],
                        observed["consent_reference"], observed["thoughts"],
                        observed["clarity_evidence"], use_time,
                    ),
                )
            if sent_thought is not None:
                sent = sent_thought
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (state[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_psi_sent_thought_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,true,%s)""",
                    (
                        command_id, state[0], sent["target_actor_id"],
                        campaign_id, timing_total, sent["target_is_telepath"],
                        sent["transmitted_thought"], use_time,
                    ),
                )
            if probe is not None:
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (state[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO cmd_psi_probe_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], probe["target_actor_id"],
                        campaign_id, probe["mode"], effect, timing_total,
                        state[10], probe["innermost_thoughts"],
                        probe["clarity_evidence"], len(probe["questions"]),
                        use_time,
                    ),
                )
                for question in probe["questions"]:
                    connection.execute(
                        """INSERT INTO cmd_psi_probe_question
                           VALUES (%s,%s,%s,%s,%s)""",
                        (command_id, *question),
                    )
            if assault_target is not None:
                defender_dice = ()
                attacker_opposed_total = defender_opposed_total = None
                penetrated = True
                if assault_target["shielded"]:
                    defender_dice = (
                        rng.randint(1, 6), rng.randint(1, 6))
                    defender_psi_modifier = connection.execute(
                        """SELECT modifier
                           FROM rule_characteristic_modifier_band
                           WHERE (characteristic_rule_id IS NULL
                                  OR characteristic_rule_id=(
                                    SELECT rule_id FROM rule_rule
                                    WHERE rule_code=
                                      'characteristic.psionic-strength'
                                  ))
                             AND score_range @> %s::integer
                           ORDER BY characteristic_rule_id NULLS LAST
                           LIMIT 1""",
                        (assault_target["psi"],),
                    ).fetchone()[0]
                    attacker_opposed_total = (
                        sum(activation_dice) + state[11] + psi_modifier
                        + sum(circumstance_modifiers)
                    )
                    defender_opposed_total = (
                        sum(defender_dice) + assault_target["skill"]
                        + defender_psi_modifier
                    )
                    penetrated = (
                        attacker_opposed_total > defender_opposed_total)
                damage_dice = (
                    (rng.randint(1, 6), rng.randint(1, 6))
                    if penetrated else ()
                )
                for group, dice in (
                    ("psionic_assault_defense", defender_dice),
                    ("psionic_assault_damage", damage_dice),
                ):
                    for order, value in enumerate(dice, 1):
                        connection.execute(
                            """INSERT INTO cmd_random_draw
                               (command_id,draw_group,draw_order,
                                die_sides,result)
                               VALUES (%s,%s,%s,6,%s)""",
                            (command_id, group, order, value),
                        )
                raw_damage = (
                    sum(damage_dice) + effect if penetrated else 0)
                remaining = raw_damage
                snapshots = {}
                for code in (
                    "characteristic.psionic-strength",
                    "characteristic.intelligence",
                    "characteristic.endurance",
                ):
                    characteristic = assault_target[
                        "characteristics"].get(code)
                    if characteristic is None:
                        snapshots[code] = (None, None, 0)
                        continue
                    rule_id, before = characteristic
                    damage = min(before, remaining)
                    after = before - damage
                    remaining -= damage
                    snapshots[code] = (before, after, damage)
                    if damage:
                        connection.execute(
                            """UPDATE actor_characteristic
                               SET current_value=%s
                               WHERE actor_id=%s
                                 AND characteristic_rule_id=%s""",
                            (after, target_actor_id, rule_id),
                        )
                campaign_id = connection.execute(
                    "SELECT campaign_id FROM actor_actor WHERE actor_id=%s",
                    (state[0],),
                ).fetchone()[0]
                psi_damage = snapshots[
                    "characteristic.psionic-strength"]
                int_damage = snapshots["characteristic.intelligence"]
                end_damage = snapshots["characteristic.endurance"]
                connection.execute(
                    """INSERT INTO cmd_psi_assault_receipt
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                               %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], target_actor_id, campaign_id,
                        effect, timing_total, assault_target["shielded"],
                        defender_dice[0] if defender_dice else None,
                        defender_dice[1] if defender_dice else None,
                        attacker_opposed_total, defender_opposed_total,
                        penetrated,
                        damage_dice[0] if damage_dice else None,
                        damage_dice[1] if damage_dice else None,
                        raw_damage, *psi_damage, *int_damage, *end_damage,
                        penetrated, use_time,
                    ),
                )
                if penetrated:
                    connection.execute(
                        """INSERT INTO actor_personal_condition (actor_id)
                           VALUES (%s) ON CONFLICT (actor_id) DO NOTHING""",
                        (target_actor_id,),
                    )
                    condition = connection.execute(
                        """SELECT fatigued,fatigue_sequence,
                                  fatigue_endurance_modifier,
                                  fatigue_rest_required_hours,unconscious,
                                  unconscious_recovery_failures,
                                  unconscious_minutes_elapsed,
                                  condition_version
                           FROM actor_personal_condition
                           WHERE actor_id=%s FOR UPDATE""",
                        (target_actor_id,),
                    ).fetchone()
                    connection.execute(
                        """INSERT INTO actor_personal_condition_transition
                           VALUES (%s,%s,'psi_assault_unconscious',
                                   %s,%s,%s,%s,%s,true,%s,0,%s,0)""",
                        (
                            command_id, target_actor_id,
                            condition[7], condition[7] + 1,
                            condition[0], condition[0], condition[4],
                            condition[5], condition[6],
                        ),
                    )
                    connection.execute(
                        """UPDATE actor_personal_condition
                           SET unconscious=true,
                               unconscious_cause='telepathic_assault',
                               unconscious_recovery_failures=0,
                               unconscious_minutes_elapsed=0,
                               condition_version=condition_version+1
                           WHERE actor_id=%s""",
                        (target_actor_id,),
                    )
            if telekinetic_manipulation is not None:
                manipulation = telekinetic_manipulation
                connection.execute(
                    """INSERT INTO cmd_psi_telekinetic_manipulation_receipt
                       (activation_command_id,actor_id,campaign_id,target_kind,
                        target_item_instance_id,target_actor_id,
                        mass_grams_snapshot,maximum_mass_grams_snapshot,
                        duration_rounds,manipulation_started_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (
                        command_id, state[0], manipulation["campaign_id"],
                        manipulation["kind"],
                        manipulation["target_id"]
                        if manipulation["kind"] == "item" else None,
                        manipulation["target_id"]
                        if manipulation["kind"] == "creature" else None,
                        manipulation["mass"], manipulation["maximum_mass"],
                        manipulation["duration_rounds"], use_time,
                    ),
                )
                if telekinetic_throw is not None:
                    throw = telekinetic_throw
                    attack_dice = tuple(rng.randint(1, 6) for _ in range(2))
                    attack_total = (
                        sum(attack_dice) + throw["skill_modifier"]
                        + throw["characteristic_modifier"]
                        + throw["difficulty_modifier"]
                        + throw["circumstance_modifier_total"]
                    )
                    attack_effect = attack_total - state[20]
                    hit = attack_total >= state[20]
                    damage_dice = tuple(
                        rng.randint(1, throw["damage_die_sides"])
                        for _ in range(
                            throw["damage_dice_count"] or 0
                            if hit else 0
                        )
                    )
                    for group, dice, sides in (
                        ("telekinetic_attack", attack_dice, 6),
                        (
                            "telekinetic_damage", damage_dice,
                            throw["damage_die_sides"],
                        ),
                    ):
                        for order, value in enumerate(dice, 1):
                            connection.execute(
                                """INSERT INTO cmd_random_draw
                                   (command_id,draw_group,draw_order,
                                    die_sides,result)
                                   VALUES (%s,%s,%s,%s,%s)""",
                                (command_id, group, order, sides, value),
                            )
                    rolled_damage = (
                        sum(damage_dice) + (throw["damage_flat"] or 0)
                        if hit else 0
                    )
                    effect_damage = max(attack_effect, 0) if hit else 0
                    raw_damage = rolled_damage + effect_damage
                    connection.execute(
                        """INSERT INTO cmd_psi_telekinetic_throw_receipt
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                   %s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            command_id, throw["target_actor_id"],
                            throw["psion_to_target_metres"],
                            throw["object_origin_to_target_metres"],
                            throw["selected_distance_metres"],
                            throw["range_band_rule_id"],
                            throw["skill_modifier"],
                            throw["characteristic_modifier"],
                            throw["difficulty_modifier"],
                            throw["circumstance_modifier_total"],
                            attack_total, state[20], attack_effect, hit,
                            throw["damage_dice_count"],
                            throw["damage_die_sides"], rolled_damage,
                            effect_damage, raw_damage,
                            raw_damage
                            if manipulation["kind"] == "creature" else None,
                        ),
                    )
        if teleport is None or not succeeded:
            connection.execute(
                """UPDATE actor_actor
                   SET concurrency_version=concurrency_version+1
                   WHERE actor_id=%s""",
                (state[0],),
            )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_activation(
            connection, command_id, public_id, False)


def _load_recovery(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.recovered_at,
                  receipt.points_available,receipt.points_recovered,
                  receipt.psionic_strength_before,
                  receipt.psionic_strength_after,receipt.next_recovery_at
           FROM cmd_psionic_recovery_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return PsionicRecoveryResult(
        str(public_id), str(row[0]), row[1], row[2], row[3], row[4], row[5],
        row[6], replayed,
    )


def recover_psionic_strength_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str,
    recovered_at: datetime | None = None,
) -> PsionicRecoveryResult:
    recovery_time = recovered_at or datetime.now(timezone.utc)
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("recover_psionic_strength", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_recovery(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT actor.actor_id,psi.current_value,psi.maximum_value,
                      psionic.next_recovery_at,
                      system.recovery_points_per_hour
               FROM actor_actor actor
               CROSS JOIN psi_system system
               JOIN actor_characteristic psi
                 ON psi.actor_id=actor.actor_id
                AND psi.characteristic_rule_id=
                    system.characteristic_rule_id
               LEFT JOIN actor_psionic_state psionic
                 ON psionic.actor_id=actor.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
               FOR UPDATE OF actor,psi""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Actor has no Psionic Strength")
        points_available = 0
        next_recovery = state[3]
        if next_recovery is not None and recovery_time >= next_recovery:
            elapsed_hours = int(
                (recovery_time - next_recovery).total_seconds() // 3600)
            recovery_ticks = elapsed_hours + 1
            points_available = recovery_ticks * state[4]
            next_recovery = state[3] + timedelta(hours=recovery_ticks)
        points_recovered = min(points_available, state[2] - state[1])
        psi_after = state[1] + points_recovered
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('recover_psionic_strength',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE actor_characteristic SET current_value=%s
               WHERE actor_id=%s AND characteristic_rule_id=(
                   SELECT characteristic_rule_id FROM psi_system
               )""",
            (psi_after, state[0]),
        )
        if state[3] is not None:
            connection.execute(
                """UPDATE actor_psionic_state SET next_recovery_at=%s
                   WHERE actor_id=%s""",
                (next_recovery, state[0]),
            )
        connection.execute(
            """INSERT INTO cmd_psionic_recovery_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], recovery_time, state[1], points_available,
             points_recovered, psi_after, next_recovery),
        )
        lock = connection.execute(
            """SELECT activation_command_id,psionic_maximum_snapshot
               FROM camp_psi_regeneration_recovery_lock
               WHERE actor_id=%s AND psionic_maximum_snapshot=%s""",
            (state[0], psi_after),
        ).fetchone()
        if lock:
            connection.execute(
                """INSERT INTO cmd_psi_regeneration_release_receipt
                   VALUES (%s,%s,%s,%s,%s)""",
                (command_id, state[0], lock[0], psi_after, lock[1]),
            )
            connection.execute(
                """DELETE FROM camp_psi_regeneration_recovery_lock
                   WHERE actor_id=%s""",
                (state[0],),
            )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "psionic_strength_recovered" if points_recovered
             else "psionic_strength_unchanged"),
        )
        if points_recovered:
            connection.execute(
                """UPDATE actor_actor
                   SET concurrency_version=concurrency_version+1
                   WHERE actor_id=%s""",
                (state[0],),
            )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_recovery(
            connection, command_id, public_id, False)


def _load_shield(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT actor.public_id,receipt.shield_before,receipt.shield_after
           FROM cmd_telepathic_shield_receipt receipt
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return TelepathicShieldResult(
        str(public_id), str(row[0]), row[1], row[2], replayed)


def set_telepathic_shield_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, shield_raised: bool,
) -> TelepathicShieldResult:
    """Raise or lower the trained telepath's source-defined free shield."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("set_telepathic_shield", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_shield(
                connection, existing[0], existing[1], True)
        actor = connection.execute(
            """SELECT actor.actor_id,actor.campaign_id,
                      actor.concurrency_version,
                      COALESCE(shield.shield_raised,true)
               FROM actor_actor actor
               JOIN actor_skill skill_state
                 ON skill_state.actor_id=actor.actor_id
               JOIN rule_rule skill_rule
                 ON skill_rule.rule_id=skill_state.skill_rule_id
                AND skill_rule.rule_code='skill.psionic-telepathy'
               LEFT JOIN actor_telepathic_shield_state shield
                 ON shield.actor_id=actor.actor_id
               WHERE actor.public_id=%s
                 AND actor.controller_reference=%s
                 AND NOT EXISTS (
                     SELECT 1
                     FROM actor_current_species current_species
                     JOIN rule_species_trait_assignment assignment
                       ON assignment.species_rule_id=
                          current_species.species_rule_id
                     JOIN rule_species_trait trait
                       ON trait.species_trait_rule_id=
                          assignment.species_trait_rule_id
                     WHERE current_species.actor_id=actor.actor_id
                       AND trait.trait_code='anti-psionic'
                 )
               FOR UPDATE OF actor""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Only a trained telepath controls a natural shield")
        before = actor[3]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('set_telepathic_shield',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        changed_at = connection.execute(
            """INSERT INTO actor_telepathic_shield_state
               (actor_id,shield_raised,changed_at)
               VALUES (%s,%s,clock_timestamp())
               ON CONFLICT (actor_id) DO UPDATE SET
                 shield_raised=EXCLUDED.shield_raised,
                 changed_at=EXCLUDED.changed_at
               RETURNING changed_at""",
            (actor[0], shield_raised),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "telepathic_shield_raised" if shield_raised
             else "telepathic_shield_lowered"),
        )
        if before != shield_raised:
            connection.execute(
                """UPDATE actor_actor
                   SET concurrency_version=concurrency_version+1
                   WHERE actor_id=%s""",
                (actor[0],),
            )
        connection.execute(
            """INSERT INTO cmd_telepathic_shield_receipt
               (command_id,actor_id,shield_before,shield_after,campaign_id,
                state_changed,actor_version_before,actor_version_after,
                changed_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                command_id, actor[0], before, shield_raised, actor[1],
                before != shield_raised, actor[2],
                actor[2] + (1 if before != shield_raised else 0), changed_at,
            ),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_shield(
            connection, command_id, public_id, False)
