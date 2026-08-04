"""Initialization of source-governed personal combat round state."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class InitializedCombatant:
    actor_public_id: str
    aware_at_start: bool
    initiative_method: str
    initiative_dice: tuple[int, ...]
    dexterity_value: int
    dexterity_modifier: int
    species_initiative_modifier: int
    initiative: int
    significant_actions: int
    minor_actions: int


@dataclass(frozen=True)
class InitializedPersonalCombat:
    command_public_id: str
    encounter_public_id: str
    round_number: int
    starting_context_code: str
    light_condition: str
    starting_range_rule_code: str
    starting_range_selection_basis: str
    combatants: tuple[InitializedCombatant, ...]
    replayed: bool


@dataclass(frozen=True)
class PersonalActionResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    operation: str
    significant_before: int
    significant_after: int
    minor_before: int
    minor_after: int
    replayed: bool


@dataclass(frozen=True)
class WeaponReloadResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    weapon_rule_code: str
    ammunition_rule_code: str
    round_number: int
    reload_procedure: str
    progress_before: int
    progress_after: int
    completed: bool
    rounds_loaded_after: int
    reload_units_available_after: int
    replayed: bool


@dataclass(frozen=True)
class PersonalReactionResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    attack_trigger_reference: str
    reaction_kind: str
    reactions_before: int
    reactions_after: int
    initiative_before: int
    initiative_after: int
    check_modifier_before: int
    check_modifier_after: int
    attack_modifier: int | None
    initiative_timing: str
    next_round_adjustment_before: int
    next_round_adjustment_after: int
    replayed: bool


@dataclass(frozen=True)
class PersonalTurnResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    significant_actions_unspent: int
    minor_actions_unspent: int
    replayed: bool


@dataclass(frozen=True)
class AdvancedCombatant:
    actor_public_id: str
    initiative_before: int
    pending_adjustment: int
    initiative_after: int


@dataclass(frozen=True)
class PersonalRoundResult:
    command_public_id: str
    encounter_public_id: str
    round_before: int
    round_after: int
    combatants: tuple[AdvancedCombatant, ...]
    replayed: bool


@dataclass(frozen=True)
class SpeciesFlyerMoveResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    operation: str
    metres_moved: float
    altitude_change_metres: float
    flight_status: str
    altitude_metres: float
    minor_actions_after: int
    replayed: bool


@dataclass(frozen=True)
class DeclaredPersonalAttack:
    command_public_id: str
    personal_attack_public_id: str
    encounter_public_id: str
    round_number: int
    attacker_actor_public_id: str
    target_actor_public_id: str
    item_rule_code: str
    attack_profile_code: str
    range_rule_code: str
    characteristic_rule_code: str
    aim_modifier: int
    target_has_cover: bool
    cover_modifier: int
    stance_modifier: int
    target_movement_modifier: int
    kill_aim_damage_bonus: int
    burst_size_rounds: int | None
    burst_option: str | None
    burst_attack_modifier: int
    burst_extra_damage_dice: int
    burst_extra_damage_flat: int
    suppression_fire: bool
    suppression_attack_modifier: int
    panic_fire: bool
    panic_attack_modifier: int
    panic_damage_burst_size_rounds: int | None
    panic_extra_damage_dice: int
    panic_extra_damage_flat: int
    shotgun_spread: bool
    shotgun_spread_attack_modifier: int
    shotgun_spread_damage_dice: int | None
    shotgun_spread_target_actor_public_ids: tuple[str, ...]
    blind_fire: bool
    blind_fire_eligible_actor_public_ids: tuple[str, ...]
    extreme_range: bool
    extreme_range_rest_reference: str | None
    extreme_range_skill_level: int | None
    extreme_range_attack_modifier: int
    extreme_range_energy_weapon: bool
    extreme_range_vehicle_public_id: str | None
    firing_into_combat: bool
    firing_into_combat_actor_public_ids: tuple[str, ...]
    thrown_delivery_type: str | None
    thrown_target_point_reference: str | None
    fatigue_attack_modifier: int
    significant_before: int
    significant_after: int
    replayed: bool


@dataclass(frozen=True)
class BegunPersonalTurn:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    initiative: int
    dexterity: int
    simultaneous_group_size: int
    replayed: bool


@dataclass(frozen=True)
class HastenedCombatant:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    initiative_before: int
    initiative_after: int
    check_modifier: int
    replayed: bool


@dataclass(frozen=True)
class DelayedPersonalTurn:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    initiative_when_delayed: int
    replayed: bool


@dataclass(frozen=True)
class ResumedPersonalTurn:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    initiative_before: int
    initiative_after: int
    interrupted_actor_public_id: str | None
    replayed: bool


@dataclass(frozen=True)
class ForfeitedDelayedTurn:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    initiative_forfeited: int
    significant_actions_forfeited: int
    minor_actions_forfeited: int
    replayed: bool


@dataclass(frozen=True)
class AimedPersonalAttack:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    target_actor_public_id: str
    round_number: int
    minor_actions_before: int
    minor_actions_after: int
    aim_modifier_before: int
    aim_modifier_after: int
    replayed: bool


@dataclass(frozen=True)
class PersonalStanceResult:
    command_public_id: str
    stance_before: str
    stance_after: str
    minor_actions_after: int
    replayed: bool


@dataclass(frozen=True)
class PersonalCoverResult:
    command_public_id: str
    cover_before: str | None
    cover_after: str | None
    replayed: bool


@dataclass(frozen=True)
class MovedPersonalCombatant:
    command_public_id: str
    metres_moved: float
    round_metres_after: float
    minor_actions_after: int
    replayed: bool


@dataclass(frozen=True)
class SpeciesGreatLeapResult:
    command_public_id: str
    encounter_public_id: str
    actor_public_id: str
    round_number: int
    characteristic_rule_code: str
    difficulty_rule_code: str
    dice: tuple[int, ...]
    athletics_skill_level: int
    characteristic_modifier: int
    difficulty_modifier: int
    check_total: int
    target_number: int
    effect: int
    succeeded: bool
    squares_jumped: int
    metres_jumped: float
    significant_after: int
    replayed: bool


@dataclass(frozen=True)
class KillAimedPersonalAttack:
    command_public_id: str
    target_actor_public_id: str
    damage_bonus_before: int
    damage_bonus_after: int
    minor_actions_after: int
    replayed: bool


def _load_initialized(connection, command_id, public_id, replayed):
    rows = connection.execute(
        """SELECT a.public_id,c.aware_at_start,c.initiative_method,
                  c.dexterity_value,c.dexterity_modifier,
                  receipt.species_initiative_modifier,c.initiative_base,
                  c.significant_actions_remaining,c.minor_actions_remaining,
                  receipt.first_draw_order,receipt.draw_count
           FROM cmd_combat_initialization_receipt command_receipt
           JOIN enc_personal_combatant c
             ON c.encounter_id=command_receipt.encounter_id
           JOIN actor_actor a ON a.actor_id=c.actor_id
           JOIN cmd_combat_initialization_combatant receipt
             ON receipt.command_id=command_receipt.command_id
            AND receipt.actor_id=c.actor_id
           WHERE command_receipt.command_id=%s
           ORDER BY c.initiative_current DESC,c.dexterity_value DESC,a.actor_id""",
        (command_id,),
    ).fetchall()
    draws = dict(connection.execute(
        """SELECT draw_order,result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group='initiative'""", (command_id,)
    ).fetchall())
    combatants = []
    for row in rows:
        dice = tuple(
            draws[index] for index in range(row[9], row[9] + row[10])
        ) if row[9] is not None else ()
        combatants.append(InitializedCombatant(
            str(row[0]), row[1], row[2], dice, row[3], row[4], row[5],
            row[6], row[7], row[8]))
    initialization = connection.execute(
        """SELECT e.public_id,r.round_number,starting.context_code,
                  starting.light_condition,range_rule.rule_code,
                  starting.selection_basis
           FROM cmd_combat_initialization_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN enc_personal_combat_starting_range starting
             ON starting.encounter_id=r.encounter_id
           JOIN rule_rule range_rule
             ON range_rule.rule_id=starting.range_rule_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return InitializedPersonalCombat(
        str(public_id), str(initialization[0]), initialization[1],
        initialization[2], initialization[3], initialization[4],
        initialization[5],
        tuple(combatants), replayed)


def initialize_personal_combat_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    aware_actor_public_ids: tuple[str, ...], random_source=None,
    starting_context_code: str = "outdoors",
    light_condition: str = "normal",
    starting_range_rule_code: str | None = None,
    referee_override_reason: str | None = None,
) -> InitializedPersonalCombat:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("initialize_personal_combat", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_initialized(
                connection, existing[0], existing[1], replayed=True)
        encounter = connection.execute(
            """SELECT e.encounter_id,c.owner_reference
               FROM enc_encounter e JOIN camp_campaign c
                 ON c.campaign_id=e.campaign_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND e.current_mode='personal_combat' FOR UPDATE OF e""",
            (encounter_public_id,),
        ).fetchone()
        if encounter is None:
            raise ValueError("Encounter is not in active personal combat mode")
        if encounter[1] != initiator_reference:
            raise PermissionError("Initiator does not own this campaign")
        if connection.execute(
            "SELECT 1 FROM enc_personal_combat WHERE encounter_id=%s",
            (encounter[0],),
        ).fetchone():
            raise ValueError("Personal combat is already initialized")
        participants = connection.execute(
            """SELECT p.actor_id,a.public_id,c.current_value,
                      COALESCE((
                          SELECT sum(modifier.initiative_modifier)
                          FROM actor_current_species current_species
                          JOIN rule_species_trait_assignment assignment
                            ON assignment.species_rule_id=
                               current_species.species_rule_id
                          JOIN rule_species_trait_combat_modifier modifier
                            ON modifier.species_trait_rule_id=
                               assignment.species_trait_rule_id
                          WHERE current_species.actor_id=a.actor_id
                      ),0) AS species_initiative_modifier,
                      COALESCE((
                        SELECT injury.injury_status='seriously_wounded'
                        FROM health_actor_injury_status injury
                        WHERE injury.actor_id=a.actor_id
                      ),false) AS seriously_wounded
               FROM enc_participant p
               JOIN actor_actor a ON a.actor_id=p.actor_id
               JOIN actor_characteristic c ON c.actor_id=a.actor_id
               JOIN rule_rule r ON r.rule_id=c.characteristic_rule_id
               WHERE p.encounter_id=%s
                 AND r.rule_code='characteristic.dexterity'
               ORDER BY p.actor_id""", (encounter[0],)
        ).fetchall()
        if len(participants) < 2:
            raise ValueError("Personal combat requires at least two participants")
        participant_publics = {str(row[1]) for row in participants}
        aware = set(aware_actor_public_ids)
        if not aware <= participant_publics:
            raise ValueError("Awareness references a nonparticipant")
        procedure = connection.execute(
            """SELECT initiative_dice_count,initiative_die_sides,
                      aware_unopposed_base
               FROM rule_personal_combat_procedure""").fetchone()
        economy = connection.execute(
            """SELECT significant_actions,minor_actions_with_significant
               FROM rule_personal_action_economy""").fetchone()
        standing_stance = connection.execute(
            """SELECT rule_id FROM rule_personal_stance
               WHERE stance_code='standing'""").fetchone()[0]
        context = connection.execute(
            """SELECT source_default_range_rule_id,
                      referee_decides_between_options
               FROM rule_personal_starting_range_context
               WHERE context_code=%s""", (starting_context_code,)).fetchone()
        light = connection.execute(
            """SELECT maximum_range_rule_id
               FROM rule_personal_starting_range_light_cap
               WHERE light_condition=%s""", (light_condition,)).fetchone()
        if context is None or light is None:
            raise ValueError("Unknown Starting Range context or light condition")
        if starting_range_rule_code is None:
            if context[0] is None:
                raise ValueError(
                    "Open-area Starting Range requires Long or Very Long selection")
            range_rule_id = context[0]
        else:
            selected = connection.execute(
                """SELECT band.rule_id,band.display_order
                   FROM rule_rule rule JOIN combat_range_band band
                     ON band.rule_id=rule.rule_id
                   WHERE rule.rule_code=%s""",
                (starting_range_rule_code,)).fetchone()
            if selected is None:
                raise ValueError("Unknown personal-combat Starting Range")
            range_rule_id = selected[0]
        source_option = connection.execute(
            """SELECT 1 FROM rule_personal_starting_range_option
               WHERE context_code=%s AND range_rule_id=%s""",
            (starting_context_code, range_rule_id)).fetchone()
        override = bool(referee_override_reason and referee_override_reason.strip())
        if source_option is None and not override:
            raise ValueError(
                "Starting Range outside source context requires referee reason")
        selected_order = connection.execute(
            "SELECT display_order FROM combat_range_band WHERE rule_id=%s",
            (range_rule_id,)).fetchone()[0]
        if light[0] is not None:
            cap_order = connection.execute(
                "SELECT display_order FROM combat_range_band WHERE rule_id=%s",
                (light[0],)).fetchone()[0]
            if selected_order > cap_order:
                raise ValueError("Starting Range exceeds the source light cap")
        selection_basis = (
            "referee_override" if override else
            "source_default" if range_rule_id == context[0] else
            "source_option")
        mixed_awareness = 0 < len(aware) < len(participants)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('initialize_personal_combat',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            "INSERT INTO enc_personal_combat (encounter_id) VALUES (%s)",
            (encounter[0],))
        connection.execute(
            """INSERT INTO enc_personal_combat_starting_range
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (encounter[0], starting_context_code, light_condition,
             range_rule_id, selection_basis,
             referee_override_reason.strip() if override else None,
             command_id))
        connection.execute(
            """INSERT INTO cmd_combat_initialization_receipt
               VALUES (%s,%s,1,%s)""",
            (command_id, encounter[0], len(participants)))
        draw_order = 1
        for (
            actor_id, actor_public, dexterity, species_modifier,
            seriously_wounded,
        ) in participants:
            modifier = connection.execute(
                """SELECT modifier
                   FROM rule_characteristic_modifier_band
                   WHERE characteristic_rule_id IS NULL
                     AND score_range @> %s::integer""", (dexterity,)
            ).fetchone()[0]
            is_aware = str(actor_public) in aware
            automatic = mixed_awareness and is_aware
            if automatic:
                method, dice, first_draw = "automatic_12", (), None
                initiative = procedure[2] + modifier + species_modifier
            else:
                method, first_draw = "rolled", draw_order
                dice = tuple(
                    rng.randint(1, procedure[1])
                    for _ in range(procedure[0]))
                initiative = sum(dice) + modifier + species_modifier
                for value in dice:
                    connection.execute(
                        """INSERT INTO cmd_random_draw
                           (command_id,draw_group,draw_order,die_sides,result)
                           VALUES (%s,'initiative',%s,%s,%s)""",
                        (command_id, draw_order, procedure[1], value))
                    draw_order += 1
            connection.execute(
                """INSERT INTO enc_personal_combatant
                   (encounter_id,actor_id,aware_at_start,initiative_method,
                    dexterity_value,dexterity_modifier,initiative_base,
                    initiative_current,significant_actions_remaining,
                    minor_actions_remaining,stance_rule_id,
                    seriously_wounded)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (encounter[0], actor_id, is_aware, method, dexterity, modifier,
                 initiative, initiative, economy[0],
                 max(0, economy[1] - (1 if seriously_wounded else 0)),
                 standing_stance, seriously_wounded))
            connection.execute(
                """INSERT INTO cmd_combat_initialization_combatant
                   (command_id,actor_id,initiative_method,first_draw_order,
                    draw_count,initiative_base,species_initiative_modifier)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (command_id, actor_id, method, first_draw, len(dice),
                 initiative, species_modifier))
            connection.execute(
                """UPDATE enc_participant SET aware=%s
                   WHERE encounter_id=%s AND actor_id=%s""",
                (is_aware, encounter[0], actor_id))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_combat_initialized')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_initialized(
            connection, command_id, public_id, replayed=False)


def _load_action_result(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,r.action_operation,
                  r.significant_before,r.significant_after,
                  r.minor_before,r.minor_after
           FROM cmd_personal_action_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return PersonalActionResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3],
        row[4], row[5], row[6], row[7], replayed)


def spend_personal_action_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    operation: str,
) -> PersonalActionResult:
    allowed = {"spend_significant", "spend_minor", "convert_significant"}
    if operation not in allowed:
        raise ValueError("Unknown personal action operation")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("spend_personal_action", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_action_result(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,a.actor_id,pc.current_round,
                      c.significant_actions_remaining,c.minor_actions_remaining,
                      c.significant_converted
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round
                 AND NOT EXISTS (
                   SELECT 1 FROM enc_personal_extended_action extended
                   WHERE extended.encounter_id=pc.encounter_id
                     AND extended.actor_id=a.actor_id
                     AND extended.action_status='active')
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control an active combatant")
        significant_before, minor_before = state[3], state[4]
        significant_after, minor_after = significant_before, minor_before
        if operation == "spend_significant":
            if significant_before < 1:
                raise ValueError("No significant action remains")
            significant_after -= 1
        elif operation == "spend_minor":
            if minor_before < 1:
                raise ValueError("No minor action remains")
            minor_after -= 1
        else:
            if significant_before < 1 or state[5]:
                raise ValueError("Significant action cannot be converted")
            converted = connection.execute(
                "SELECT minor_actions_from_significant FROM rule_personal_action_economy"
            ).fetchone()[0]
            significant_after -= 1
            minor_after += converted
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('spend_personal_action',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=%s,
                   minor_actions_remaining=%s,
                   significant_converted=(
                       significant_converted OR %s
                   ),
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (significant_after, minor_after,
             operation == "convert_significant", state[0], state[1]))
        connection.execute(
            """INSERT INTO cmd_personal_action_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[2], operation,
             significant_before, significant_after, minor_before, minor_after))
        event_type = (
            "personal_action_converted"
            if operation == "convert_significant"
            else "personal_action_spent")
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event_type))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_action_result(
            connection, command_id, public_id, False)


def _load_weapon_reload_result(
    connection, command_id, public_id, replayed,
) -> WeaponReloadResult:
    row = connection.execute(
        """SELECT encounter.public_id,actor.public_id,weapon.rule_code,
                  ammunition.rule_code,receipt.round_number,
                  receipt.reload_procedure,receipt.progress_before,
                  receipt.progress_after,receipt.completed,
                  receipt.rounds_loaded_after,
                  receipt.reload_units_available_after
           FROM cmd_weapon_reload_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule weapon ON weapon.rule_id=receipt.weapon_rule_id
           JOIN rule_rule ammunition
             ON ammunition.rule_id=receipt.ammunition_rule_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return WeaponReloadResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], row[6], row[7], row[8], row[9], row[10], replayed,
    )


def advance_weapon_reload_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    weapon_rule_code: str, ammunition_rule_code: str,
    require_actor_holding: bool = False,
) -> WeaponReloadResult:
    """Advance one source-defined combat reload unit."""
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("advance_weapon_reload", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_weapon_reload_result(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,actor.actor_id,pc.current_round,
                      combatant.significant_actions_remaining,
                      combatant.minor_actions_remaining,
                      combatant.acted_this_round,weapon.rule_id,
                      ammunition.rule_id,definition.capacity_rounds,
                      definition.reload_procedure,definition.reload_units,
                      weapon_state.reload_progress,
                      weapon_state.loaded_ammunition_rule_id,
                      supply.reload_units_available
               FROM enc_personal_combat pc
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=pc.encounter_id
               JOIN actor_actor actor ON actor.public_id=%s
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=pc.encounter_id
                AND combatant.actor_id=actor.actor_id
               JOIN rule_rule weapon ON weapon.rule_code=%s
               JOIN rule_rule ammunition ON ammunition.rule_code=%s
               JOIN inv_ammunition_definition definition
                 ON definition.ammunition_rule_id=ammunition.rule_id
                AND definition.weapon_rule_id=weapon.rule_id
               JOIN actor_weapon_state weapon_state
                 ON weapon_state.actor_id=actor.actor_id
                AND weapon_state.weapon_rule_id=weapon.rule_id
               JOIN actor_ammunition_supply supply
                 ON supply.actor_id=actor.actor_id
                AND supply.ammunition_rule_id=ammunition.rule_id
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND pc.combat_status='active'
                 AND actor.controller_reference=%s
                 AND combatant.turn_started_this_round
               FOR UPDATE OF pc,combatant,weapon_state,supply""",
            (actor_public_id, weapon_rule_code, ammunition_rule_code,
             encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Reload is not legal in this combat state")
        if require_actor_holding:
            held=connection.execute(
                """SELECT quantity FROM actor_item_holding
                   WHERE actor_id=%s AND item_rule_id=%s""",
                (state[1],state[6])).fetchone()
            if held is None or held[0]<1:
                raise ValueError("Actor does not hold the weapon being reloaded")
        procedure, required = state[9], state[10]
        if procedure == "recharge_hours":
            raise ValueError("This weapon must be recharged outside combat")
        if procedure == "unspecified":
            raise ValueError("The governing sources do not specify reload timing")
        if state[11] > 0 and state[12] != state[7]:
            raise ValueError("Cannot change ammunition during a reload")
        if state[13] < 1:
            raise ValueError("No reload unit of this ammunition remains")
        significant_after, minor_after = state[3], state[4]
        if procedure == "minor_actions":
            if minor_after < 1:
                raise ValueError("No minor action remains")
            minor_after -= 1
        elif procedure == "full_rounds":
            if state[5] or significant_after < 1 or minor_after < 1:
                raise ValueError("A full-round reload requires an unused turn")
            significant_after = 0
            minor_after = 0
        else:
            raise RuntimeError("Unknown stored reload procedure")
        progress_before = state[11]
        progress_after = progress_before + 1
        completed = progress_after >= required
        rounds_after = state[8] if completed else 0
        supply_after = state[13] - (1 if completed else 0)
        if completed:
            progress_after = 0
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('advance_weapon_reload',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=%s,
                   minor_actions_remaining=%s,
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (significant_after, minor_after, state[0], state[1]),
        )
        connection.execute(
            """UPDATE actor_weapon_state
               SET loaded_ammunition_rule_id=%s,rounds_loaded=%s,
                   reload_progress=%s
               WHERE actor_id=%s AND weapon_rule_id=%s""",
            (state[7], rounds_after, progress_after, state[1], state[6]),
        )
        if completed:
            connection.execute(
                """UPDATE actor_ammunition_supply
                   SET reload_units_available=%s
                   WHERE actor_id=%s AND ammunition_rule_id=%s""",
                (supply_after, state[1], state[7]),
            )
        connection.execute(
            """INSERT INTO cmd_weapon_reload_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[6], state[7], state[2],
             procedure, progress_before, progress_after, completed,
             rounds_after, supply_after),
        )
        event_type = "weapon_reloaded" if completed else "weapon_reload_advanced"
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event_type),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_weapon_reload_result(
            connection, command_id, public_id, False)


def _load_reaction_result(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.attack_trigger_reference,r.reaction_kind,
                  r.reactions_before,r.reactions_after,
                  r.initiative_before,r.initiative_after,
                  r.check_modifier_before,r.check_modifier_after,
                  CASE r.reaction_kind
                    WHEN 'dodge' THEN rules.dodge_attack_modifier
                    WHEN 'dodge_with_cover'
                      THEN rules.dodge_with_cover_attack_modifier
                  END,r.initiative_timing,
                  r.next_round_adjustment_before,
                  r.next_round_adjustment_after
           FROM cmd_personal_reaction_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           CROSS JOIN rule_personal_reaction_system rules
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return PersonalReactionResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], row[6], row[7], row[8], row[9], row[10], row[11],
        row[12], row[13], row[14], replayed)


def declare_personal_reaction_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    attack_trigger_reference: str, reaction_kind: str,
    parrying_weapon_rule_code: str | None = None,
    parrying_weapon_item_instance_public_id: str | None = None,
) -> PersonalReactionResult:
    if reaction_kind not in {"dodge", "dodge_with_cover", "parry"}:
        raise ValueError("Unknown personal reaction")
    if not attack_trigger_reference.strip():
        raise ValueError("Attack trigger reference is required")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("declare_personal_reaction", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_reaction_result(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,a.actor_id,pc.current_round,
                      c.aware_at_start,c.reactions_this_round,
                      c.initiative_current,c.reaction_check_modifier,
                      c.acted_this_round,c.next_round_initiative_adjustment
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round
                 AND NOT EXISTS (
                   SELECT 1 FROM enc_personal_extended_action extended
                   WHERE extended.encounter_id=pc.encounter_id
                     AND extended.actor_id=a.actor_id
                     AND extended.action_status='active')
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control an active combatant")
        attack = connection.execute(
            """SELECT personal_attack_id,target_actor_id,attack_profile_code,
                      target_has_cover,stance.may_dodge
               FROM enc_personal_attack attack
               JOIN enc_personal_combatant target
                 ON target.encounter_id=attack.encounter_id
                AND target.actor_id=attack.target_actor_id
               JOIN rule_personal_stance stance
                 ON stance.rule_id=target.stance_rule_id
               WHERE attack.public_id::text=%s AND attack.encounter_id=%s
                 AND attack.round_number=%s
                 AND attack.attack_status='awaiting_reactions'
               FOR UPDATE""",
            (attack_trigger_reference, state[0], state[2]),
        ).fetchone()
        if attack is None or attack[1] != state[1]:
            raise ValueError(
                "Reaction must target a pending attack against this combatant")
        if reaction_kind == "dodge_with_cover" and not attack[3]:
            raise ValueError("Dodge with cover requires declared cover")
        if reaction_kind in {"dodge", "dodge_with_cover"} and not attack[4]:
            raise ValueError("Current stance forbids dodging")
        kill_aiming = connection.execute(
            """SELECT kill_aim_damage_bonus FROM enc_personal_combatant
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[0], state[1]),
        ).fetchone()[0]
        if reaction_kind in {"dodge", "dodge_with_cover"} and kill_aiming:
            raise ValueError("Aiming for the Kill forbids dodging")
        if reaction_kind == "parry" and attack[2] != "close-quarters":
            raise ValueError("Only a close-quarters attack may be parried")
        parry = None
        if reaction_kind == "parry":
            if not parrying_weapon_rule_code:
                raise ValueError("Parry requires the defender's armed weapon")
            if parrying_weapon_rule_code == "equipment.weapon.species-natural-weapon":
                if parrying_weapon_item_instance_public_id is not None:
                    raise ValueError("An inherent natural weapon has no item instance")
                parry = connection.execute(
                    """SELECT weapon.rule_id,NULL::bigint,skill.rule_id,
                              GREATEST(COALESCE(actor_skill.skill_level,0),0)
                       FROM rule_rule weapon
                       JOIN rule_rule skill
                         ON skill.rule_code='skill.natural-weapons'
                       LEFT JOIN actor_skill ON actor_skill.actor_id=%s
                         AND actor_skill.skill_rule_id=skill.rule_id
                       WHERE weapon.rule_code=%s AND EXISTS (
                         SELECT 1 FROM actor_current_species current_species
                         JOIN rule_species_trait_assignment assignment
                           ON assignment.species_rule_id=current_species.species_rule_id
                         JOIN rule_species_trait trait
                           ON trait.species_trait_rule_id=assignment.species_trait_rule_id
                         WHERE current_species.actor_id=%s
                           AND trait.trait_code='natural-weapon')""",
                    (state[1], parrying_weapon_rule_code, state[1])).fetchone()
            else:
                if parrying_weapon_item_instance_public_id is None:
                    raise ValueError("Parry requires a held weapon instance")
                parry = connection.execute(
                    """SELECT weapon.rule_id,item.item_instance_id,skill.rule_id,
                              GREATEST(COALESCE(actor_skill.skill_level,0),0)
                       FROM rule_rule weapon
                       JOIN inv_item_instance item ON item.item_rule_id=weapon.rule_id
                       JOIN inv_container_item held USING(item_instance_id,campaign_id)
                       JOIN inv_actor_container owner USING(container_id,campaign_id)
                       JOIN actor_weapon_state ready
                         ON ready.actor_id=owner.actor_id
                        AND ready.weapon_rule_id=weapon.rule_id AND ready.ready
                       JOIN inv_weapon_attack_mode mode ON mode.item_rule_id=weapon.rule_id
                        AND mode.attack_profile_code IN ('close-quarters','extended-reach')
                       JOIN inv_weapon_damage_type damage ON damage.item_rule_id=weapon.rule_id
                        AND damage.damage_type_code IN ('bludgeoning','piercing','slashing')
                       JOIN rule_rule skill ON skill.rule_code='skill.'||damage.damage_type_code||'-weapons'
                       LEFT JOIN actor_skill ON actor_skill.actor_id=owner.actor_id
                        AND actor_skill.skill_rule_id=skill.rule_id
                       WHERE weapon.rule_code=%s AND item.public_id=%s
                         AND item.item_status='active' AND owner.actor_id=%s
                       ORDER BY GREATEST(COALESCE(actor_skill.skill_level,0),0) DESC,
                                skill.rule_code LIMIT 1""",
                    (parrying_weapon_rule_code,
                     parrying_weapon_item_instance_public_id,state[1])).fetchone()
            if parry is None:
                raise ValueError("Defender is not armed and ready with that melee weapon")
        elif (parrying_weapon_rule_code is not None
              or parrying_weapon_item_instance_public_id is not None):
            raise ValueError("Only Parry accepts a parrying weapon")
        rules = connection.execute(
            """SELECT initiative_cost_per_reaction,
                      check_modifier_per_reaction,maximum_per_round,
                      requires_awareness
               FROM rule_personal_reaction_system""").fetchone()
        if rules[3] and not state[3]:
            raise ValueError("Unaware combatant cannot react")
        if rules[2] is not None and state[4] >= rules[2]:
            raise ValueError("No reactions remain this round")
        if connection.execute(
            """SELECT 1 FROM cmd_personal_reaction_receipt
               WHERE encounter_id=%s AND actor_id=%s AND round_number=%s
                 AND attack_trigger_reference=%s""",
            (state[0], state[1], state[2], attack_trigger_reference),
        ).fetchone():
            raise ValueError("Combatant has already reacted to this attack")
        reactions_after = state[4] + 1
        applies_next_round = state[7]
        initiative_after = state[5] if applies_next_round else state[5] + rules[0]
        next_adjustment_after = (
            state[8] + rules[0] if applies_next_round else state[8])
        check_after = state[6] + rules[1]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('declare_personal_reaction',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET reactions_this_round=%s,initiative_current=%s,
                   reaction_check_modifier=%s,
                   next_round_initiative_adjustment=%s,
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (reactions_after, initiative_after, check_after,
             next_adjustment_after,
             state[0], state[1]))
        connection.execute(
            """INSERT INTO cmd_personal_reaction_receipt
               (command_id,encounter_id,actor_id,round_number,
                attack_trigger_reference,reaction_kind,reactions_before,
                reactions_after,initiative_before,initiative_after,
                check_modifier_before,check_modifier_after,initiative_timing,
                next_round_adjustment_before,next_round_adjustment_after,
                personal_attack_id,parrying_weapon_rule_id,
                parrying_weapon_item_instance_id,parry_skill_rule_id,
                parry_skill_modifier)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[2],
             attack_trigger_reference, reaction_kind, state[4],
             reactions_after, state[5], initiative_after, state[6],
             check_after,
             "following_round" if applies_next_round else "current_round",
             state[8], next_adjustment_after, attack[0],
             *(parry if parry else (None,None,None,None))))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_reaction_declared')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_reaction_result(
            connection, command_id, public_id, False)


def _load_turn_result(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.significant_actions_unspent,r.minor_actions_unspent
           FROM cmd_personal_turn_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return PersonalTurnResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        replayed)


def complete_personal_turn_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
) -> PersonalTurnResult:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("complete_personal_turn", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_turn_result(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,a.actor_id,pc.current_round,
                      c.significant_actions_remaining,c.minor_actions_remaining,
                      c.acted_this_round,c.flight_status,c.altitude_metres,
                      c.flight_upkeep_round
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control an active combatant")
        if state[5]:
            raise ValueError("Combatant has already completed this turn")
        if connection.execute(
            """SELECT 1 FROM enc_personal_extended_action
               WHERE encounter_id=%s AND actor_id=%s
                 AND action_status='active'""",
            (state[0], state[1]),
        ).fetchone():
            raise ValueError(
                "Active Extended Action must be advanced or abandoned")
        if connection.execute(
            """SELECT 1 FROM enc_personal_attack
               WHERE encounter_id=%s AND round_number=%s
                 AND attacker_actor_id=%s
                 AND attack_status='awaiting_reactions'""",
            (state[0], state[2], state[1]),
        ).fetchone():
            raise ValueError(
                "Combatant has an unresolved declared attack")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('complete_personal_turn',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant SET acted_this_round=true
               WHERE encounter_id=%s AND actor_id=%s""", (state[0], state[1]))
        if state[6] == "aloft" and state[8] != state[2]:
            connection.execute(
                """UPDATE enc_personal_combatant SET flight_status='falling'
                   WHERE encounter_id=%s AND actor_id=%s""",
                (state[0], state[1]),
            )
            connection.execute(
                """INSERT INTO cmd_species_flyer_transition_receipt
                   (command_id,actor_id,encounter_id,round_number,
                    transition_reason,status_before,status_after,
                    altitude_metres)
                   VALUES (%s,%s,%s,%s,'missed_movement_upkeep',
                           'aloft','falling',%s)""",
                (command_id, state[1], state[0], state[2], state[7]),
            )
        connection.execute(
            """INSERT INTO cmd_personal_turn_receipt
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[1], state[2], state[3], state[4]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_turn_completed')""", (command_id,))
        if state[6] == "aloft" and state[8] != state[2]:
            connection.execute(
                """INSERT INTO cmd_domain_event
                   (command_id,event_order,event_type)
                   VALUES (%s,2,'species_flyer_fell')""",
                (command_id,),
            )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_turn_result(
            connection, command_id, public_id, False)


def _load_round_result(connection, command_id, public_id, replayed):
    header = connection.execute(
        """SELECT e.public_id,r.round_before,r.round_after
           FROM cmd_personal_round_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    rows = connection.execute(
        """SELECT a.public_id,c.initiative_before,c.pending_adjustment,
                  c.initiative_after
           FROM cmd_personal_round_combatant c
           JOIN actor_actor a ON a.actor_id=c.actor_id
           WHERE c.command_id=%s
           ORDER BY c.initiative_after DESC,a.actor_id""", (command_id,)
    ).fetchall()
    return PersonalRoundResult(
        str(public_id), str(header[0]), header[1], header[2],
        tuple(AdvancedCombatant(str(row[0]), row[1], row[2], row[3])
              for row in rows), replayed)


def advance_personal_combat_round_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
) -> PersonalRoundResult:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("advance_personal_combat_round", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_round_result(
                connection, existing[0], existing[1], True)
        combat = connection.execute(
            """SELECT pc.encounter_id,pc.current_round
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN camp_campaign campaign
                 ON campaign.campaign_id=e.campaign_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND campaign.owner_reference=%s
               FOR UPDATE OF pc""",
            (encounter_public_id, initiator_reference),
        ).fetchone()
        if combat is None:
            raise PermissionError(
                "Initiator does not own this active personal combat")
        combatants = connection.execute(
            """SELECT actor_id,initiative_current,initiative_base,
                      next_round_initiative_adjustment,acted_this_round,
                      delayed_first_next_round
               FROM enc_personal_combatant
               WHERE encounter_id=%s FOR UPDATE""", (combat[0],)
        ).fetchall()
        if len(combatants) < 2:
            raise ValueError("Personal combat requires at least two combatants")
        if not all(row[4] for row in combatants):
            raise ValueError("Every combatant must complete the round")
        if connection.execute(
            """SELECT 1 FROM enc_personal_attack
               WHERE encounter_id=%s AND round_number=%s
                 AND attack_status='awaiting_reactions'""",
            (combat[0], combat[1]),
        ).fetchone():
            raise ValueError("Every declared attack must be resolved or cancelled")
        economy = connection.execute(
            """SELECT significant_actions,minor_actions_with_significant
               FROM rule_personal_action_economy""").fetchone()
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('advance_personal_combat_round',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        round_after = combat[1] + 1
        missed_upkeep = connection.execute(
            """SELECT actor_id,altitude_metres
               FROM enc_personal_combatant
               WHERE encounter_id=%s AND flight_status='aloft'
                 AND flight_upkeep_round IS DISTINCT FROM %s""",
            (combat[0], combat[1]),
        ).fetchall()
        connection.execute(
            """INSERT INTO cmd_personal_round_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, combat[0], combat[1], round_after, len(combatants)))
        ordinary_next_first = max(
            row[2] + row[3] for row in combatants)
        delayed_first_initiative = ordinary_next_first + connection.execute(
            """SELECT next_round_initiative_above_current_first
               FROM rule_personal_delay""").fetchone()[0]
        for actor_id, current, base, pending, _, delayed_first in combatants:
            initiative_after = (
                delayed_first_initiative
                if delayed_first else base + pending)
            connection.execute(
                """INSERT INTO cmd_personal_round_combatant
                   VALUES (%s,%s,%s,%s,%s)""",
                (command_id, actor_id, current, pending, initiative_after))
        for actor_id, altitude in missed_upkeep:
            connection.execute(
                """INSERT INTO cmd_species_flyer_transition_receipt
                   (command_id,actor_id,encounter_id,round_number,
                    transition_reason,status_before,status_after,
                    altitude_metres)
                   VALUES (%s,%s,%s,%s,'missed_movement_upkeep',
                           'aloft','falling',%s)""",
                (command_id, actor_id, combat[0], combat[1], altitude),
            )
        connection.execute(
            """UPDATE enc_personal_combatant SET flight_status='falling'
               WHERE encounter_id=%s AND flight_status='aloft'
                 AND flight_upkeep_round IS DISTINCT FROM %s""",
            (combat[0], combat[1]),
        )
        connection.execute(
            """UPDATE enc_personal_combatant
               SET initiative_current=CASE
                     WHEN delayed_first_next_round THEN %s
                     ELSE initiative_base + next_round_initiative_adjustment
                   END,
                   significant_actions_remaining=CASE WHEN EXISTS (
                     SELECT 1 FROM enc_personal_extended_action extended
                     WHERE extended.encounter_id=
                           enc_personal_combatant.encounter_id
                       AND extended.actor_id=enc_personal_combatant.actor_id
                       AND extended.action_status='active'
                   ) THEN 0 ELSE GREATEST(
                     %s-significant_action_losses_pending,0) END,
                   minor_actions_remaining=CASE WHEN EXISTS (
                     SELECT 1 FROM enc_personal_extended_action extended
                     WHERE extended.encounter_id=
                           enc_personal_combatant.encounter_id
                       AND extended.actor_id=enc_personal_combatant.actor_id
                       AND extended.action_status='active'
                   ) THEN 0 ELSE GREATEST(
                     %s-CASE WHEN EXISTS (
                       SELECT 1 FROM health_actor_injury_status injury
                       WHERE injury.actor_id=enc_personal_combatant.actor_id
                         AND injury.injury_status='seriously_wounded'
                     ) THEN 1 ELSE 0 END,0) END,
                   seriously_wounded=EXISTS (
                     SELECT 1 FROM health_actor_injury_status injury
                     WHERE injury.actor_id=enc_personal_combatant.actor_id
                       AND injury.injury_status='seriously_wounded'
                   ),
                   significant_action_losses_pending=GREATEST(
                     significant_action_losses_pending-%s,0),
                   significant_converted=false,reactions_this_round=0,
                   reaction_check_modifier=0,acted_this_round=false,
                   next_round_initiative_adjustment=0,
                   turn_started_this_round=false,
                   hastened_this_round=false,hasten_check_modifier=0,
                   delayed_this_round=false,
                   delayed_first_next_round=false,
                   metres_moved_this_round=0,
                   suppression_check_modifier=CASE
                     WHEN suppression_expires_after_round < %s THEN 0
                     ELSE suppression_check_modifier END,
                   suppression_expires_after_round=CASE
                     WHEN suppression_expires_after_round < %s THEN NULL
                     ELSE suppression_expires_after_round END
               WHERE encounter_id=%s""",
            (delayed_first_initiative, economy[0], economy[1], economy[0],
             round_after, round_after, combat[0]))
        connection.execute(
            """UPDATE enc_personal_combat SET current_round=%s,
                   round_started_at=clock_timestamp()
               WHERE encounter_id=%s""", (round_after, combat[0]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_combat_round_advanced')""", (command_id,))
        if missed_upkeep:
            connection.execute(
                """INSERT INTO cmd_domain_event
                   (command_id,event_order,event_type)
                   VALUES (%s,2,'species_flyer_fell')""",
                (command_id,),
            )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_round_result(
            connection, command_id, public_id, False)


def _load_declared_attack(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT attack.public_id,e.public_id,attack.round_number,
                  attacker.public_id,target.public_id,weapon.rule_code,
                  attack.attack_profile_code,range_rule.rule_code,
                  characteristic.rule_code,
                  attack.aim_modifier,attack.target_has_cover,
                  attack.cover_modifier,attack.stance_modifier,
                  attack.target_movement_modifier,
                  attack.kill_aim_damage_bonus,
                  burst_size.rounds_consumed,burst_option.option_code,
                  attack.burst_attack_modifier,
                  attack.burst_extra_damage_dice,
                  attack.burst_extra_damage_flat,
                  attack.suppression_fire,
                  attack.suppression_attack_modifier,
                  attack.panic_fire,attack.panic_attack_modifier,
                  panic_size.rounds_consumed,
                  attack.panic_extra_damage_dice,
                  attack.panic_extra_damage_flat,
                  attack.shotgun_spread,
                  attack.shotgun_spread_attack_modifier,
                  attack.shotgun_spread_damage_dice,
                  attack.blind_fire,
                  receipt.significant_before,
                  receipt.significant_after,
                  attack.extreme_range,
                  attack.extreme_range_rest_reference,
                  attack.extreme_range_skill_level,
                  attack.extreme_range_attack_modifier,
                  attack.extreme_range_energy_weapon,
                  firing_vehicle.public_id,
                  attack.firing_into_combat,
                  attack.thrown_delivery_type,
                  attack.thrown_target_point_reference,
                  attack.fatigue_attack_modifier
           FROM cmd_personal_attack_declaration_receipt receipt
           JOIN enc_personal_attack attack
             ON attack.personal_attack_id=receipt.personal_attack_id
           JOIN enc_encounter e ON e.encounter_id=attack.encounter_id
           JOIN actor_actor attacker
             ON attacker.actor_id=attack.attacker_actor_id
           JOIN actor_actor target ON target.actor_id=attack.target_actor_id
           JOIN rule_rule weapon ON weapon.rule_id=attack.weapon_rule_id
           JOIN rule_rule range_rule
             ON range_rule.rule_id=attack.range_band_rule_id
           JOIN rule_rule characteristic
             ON characteristic.rule_id=attack.characteristic_rule_id
           LEFT JOIN rule_personal_burst_size burst_size
             ON burst_size.rule_id=attack.burst_size_rule_id
           LEFT JOIN rule_personal_burst_option burst_option
             ON burst_option.rule_id=attack.burst_option_rule_id
           LEFT JOIN rule_personal_burst_size panic_size
             ON panic_size.rule_id=attack.panic_damage_burst_size_rule_id
           LEFT JOIN vehicle_vehicle firing_vehicle
             ON firing_vehicle.vehicle_id=attack.extreme_range_vehicle_id
           WHERE receipt.command_id=%s""", (command_id,)
    ).fetchone()
    spread_targets = tuple(str(value[0]) for value in connection.execute(
        """SELECT actor.public_id
           FROM enc_personal_shotgun_spread_target target
           JOIN actor_actor actor ON actor.actor_id=target.target_actor_id
           JOIN cmd_personal_attack_declaration_receipt receipt
             ON receipt.personal_attack_id=target.personal_attack_id
           WHERE receipt.command_id=%s ORDER BY target.target_order""",
        (command_id,),
    ).fetchall())
    blind_targets = tuple(str(value[0]) for value in connection.execute(
        """SELECT actor.public_id
           FROM enc_personal_blind_fire_target target
           JOIN actor_actor actor ON actor.actor_id=target.target_actor_id
           JOIN cmd_personal_attack_declaration_receipt receipt
             ON receipt.personal_attack_id=target.personal_attack_id
           WHERE receipt.command_id=%s ORDER BY target.target_order""",
        (command_id,),
    ).fetchall())
    combat_targets = tuple(str(value[0]) for value in connection.execute(
        """SELECT actor.public_id
           FROM enc_personal_firing_into_combat_target target
           JOIN actor_actor actor ON actor.actor_id=target.target_actor_id
           JOIN cmd_personal_attack_declaration_receipt receipt
             ON receipt.personal_attack_id=target.personal_attack_id
           WHERE receipt.command_id=%s ORDER BY target.target_order""",
        (command_id,),
    ).fetchall())
    return DeclaredPersonalAttack(
        str(public_id), str(row[0]), str(row[1]), row[2], str(row[3]),
        str(row[4]), row[5], row[6], row[7], row[8], row[9], row[10],
        row[11], row[12], row[13], row[14], row[15], row[16], row[17],
        row[18], row[19], row[20], row[21], row[22], row[23], row[24],
        row[25], row[26], row[27], row[28], row[29],
        spread_targets, row[30], blind_targets,
        row[33], row[34], row[35], row[36], row[37],
        str(row[38]) if row[38] else None,
        row[39], combat_targets,
        row[40], row[41], row[42],
        row[31], row[32], replayed)


def declare_personal_attack_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    attacker_actor_public_id: str, target_actor_public_id: str,
    item_rule_code: str, attack_profile_code: str, range_rule_code: str,
    target_has_cover: bool | None = None,
    characteristic_rule_code: str | None = None,
    burst_size_rounds: int | None = None,
    burst_option: str | None = None,
    suppression_fire: bool = False,
    panic_fire: bool = False,
    shotgun_spread: bool = False,
    shotgun_spread_target_actor_public_ids: tuple[str, ...] = (),
    battlefield_sensor_code: str | None = None,
    blind_fire: bool = False,
    blind_fire_eligible_actor_public_ids: tuple[str, ...] = (),
    extreme_range_authorization_public_id: str | None = None,
    firing_into_combat_targets: tuple[tuple[str, int], ...] = (),
    thrown_target_point_reference: str | None = None,
    weapon_item_instance_public_id: str | None = None,
    intelligent_weapon_suppressed: bool = False,
    intelligent_weapon_suppression_referee_reference: str | None = None,
    intelligent_weapon_suppression_reason: str | None = None,
    require_actor_holding: bool = False,
) -> DeclaredPersonalAttack:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("declare_personal_attack", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_declared_attack(
                connection, existing[0], existing[1], True)
        if attack_profile_code == "thrown":
            selected_characteristic = "characteristic.dexterity"
            if (characteristic_rule_code is not None
                    and characteristic_rule_code != selected_characteristic):
                raise ValueError("Thrown attacks use Dexterity")
        elif attack_profile_code in {"close-quarters", "natural-weapon"}:
            selected_characteristic = (
                characteristic_rule_code or "characteristic.dexterity")
            if selected_characteristic not in {
                "characteristic.strength", "characteristic.dexterity"
            }:
                raise ValueError(
                    "Melee and natural-weapon attacks use Strength or Dexterity")
        else:
            selected_characteristic = "characteristic.dexterity"
            if (characteristic_rule_code is not None
                    and characteristic_rule_code != selected_characteristic):
                raise ValueError("Ranged attacks use Dexterity")
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,attacker.actor_id,
                      target.actor_id,combatant.significant_actions_remaining,
                      combatant.acted_this_round,weapon.rule_id,
                      range_rule.rule_id,characteristic.rule_id,
                      combatant.aim_target_actor_id,combatant.aim_modifier,
                      combatant.kill_aim_target_actor_id,
                      combatant.kill_aim_damage_bonus,
                      target_combatant.metres_moved_this_round,
                      target_combatant.suppression_action_required,
                      combatant.metres_moved_this_round
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor attacker ON attacker.public_id=%s
               JOIN actor_actor target ON target.public_id=%s
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=pc.encounter_id
                AND combatant.actor_id=attacker.actor_id
               JOIN enc_personal_combatant target_combatant
                 ON target_combatant.encounter_id=pc.encounter_id
                AND target_combatant.actor_id=target.actor_id
               JOIN rule_rule weapon ON weapon.rule_code=%s
               JOIN inv_weapon_attack_mode mode
                 ON mode.item_rule_id=weapon.rule_id
                AND mode.attack_profile_code=%s
               JOIN rule_rule range_rule ON range_rule.rule_code=%s
               JOIN rule_rule characteristic
                 ON characteristic.rule_code=%s
               JOIN actor_characteristic characteristic_state
                 ON characteristic_state.actor_id=attacker.actor_id
                AND characteristic_state.characteristic_rule_id=
                    characteristic.rule_id
               JOIN combat_attack_profile_difficulty difficulty
                 ON difficulty.attack_profile_code=mode.attack_profile_code
                AND difficulty.range_band_rule_id=range_rule.rule_id
                AND difficulty.permitted
               CROSS JOIN rule_personal_attack_sequence sequence
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND attacker.controller_reference=%s
                 AND combatant.turn_started_this_round
                 AND sequence.consumes_significant_action
               FOR UPDATE OF pc,combatant""",
            (attacker_actor_public_id, target_actor_public_id, item_rule_code,
             attack_profile_code, range_rule_code, selected_characteristic,
             encounter_public_id,
             initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError(
                "Attack declaration is not legal in this combat state")
        condition = connection.execute(
            """SELECT fatigued,unconscious
               FROM actor_personal_condition WHERE actor_id=%s""",
            (state[2],)).fetchone()
        if condition and condition[1]:
            raise ValueError("An unconscious combatant cannot attack")
        fatigue_attack_modifier = -2 if condition and condition[0] else 0
        if state[2] == state[3]:
            raise ValueError("Combatant cannot attack itself")
        if connection.execute(
            """SELECT 1 FROM enc_personal_grapple_active_actor
               WHERE actor_id=%s""", (state[2],)).fetchone():
            raise ValueError(
                "A grappled combatant may only make opposed grapple checks")
        if state[5]:
            raise ValueError("Combatant has already completed its turn")
        if state[4] < 1:
            raise ValueError("No significant action remains")
        thrown_delivery_type = None
        frozen_thrown_target = None
        if attack_profile_code == "thrown":
            thrown = connection.execute(
                """SELECT delivery_type
                   FROM inv_thrown_delivery_capability
                   WHERE item_rule_id=%s
                     AND attack_profile_code='thrown'""",
                (state[6],)).fetchone()
            if thrown is None:
                raise ValueError(
                    "Thrown weapon lacks a normalized delivery classification")
            thrown_delivery_type = thrown[0]
            frozen_thrown_target = (
                thrown_target_point_reference or target_actor_public_id)
            if not frozen_thrown_target.strip():
                raise ValueError("Thrown attack target-point reference is required")
        elif thrown_target_point_reference is not None:
            raise ValueError(
                "Only thrown attacks accept a target-point reference")
        if suppression_fire and state[14]:
            raise ValueError(
                "Target must take an action before being suppressed again")
        if item_rule_code == "equipment.weapon.species-natural-weapon":
            eligible = connection.execute(
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
                         AND trait.trait_code='natural-weapon'
                   )""",
                (state[2],),
            ).fetchone()[0]
            if not eligible:
                raise ValueError(
                    "Actor's species has no source-defined natural weapon")
        elif require_actor_holding:
            held = connection.execute(
                """SELECT holding.quantity,weapon_state.ready
                   FROM actor_item_holding holding
                   LEFT JOIN actor_weapon_state weapon_state
                     ON weapon_state.actor_id=holding.actor_id
                    AND weapon_state.weapon_rule_id=holding.item_rule_id
                   WHERE holding.actor_id=%s AND holding.item_rule_id=%s""",
                (state[2],state[6])).fetchone()
            if held is None or held[0] < 1:
                raise ValueError("Actor does not hold the declared weapon")
            if held[1] is not True:
                raise ValueError("Actor's held weapon is not ready")
        if (burst_size_rounds is None) != (burst_option is None):
            raise ValueError("Burst size and burst option must be selected together")
        if panic_fire and (burst_size_rounds is not None or suppression_fire):
            raise ValueError(
                "Panic fire cannot be combined with burst or suppression fire")
        if shotgun_spread and (
            panic_fire or suppression_fire or burst_size_rounds is not None
        ):
            raise ValueError("Shotgun spread cannot combine with other fire modes")
        if blind_fire and shotgun_spread:
            raise ValueError("Blind fire cannot use the shotgun-spread procedure")
        if bool(blind_fire_eligible_actor_public_ids) != blind_fire:
            raise ValueError("Blind fire requires an eligible firing-line roster")
        if len(set(blind_fire_eligible_actor_public_ids)) != len(
            blind_fire_eligible_actor_public_ids
        ):
            raise ValueError("Blind-fire targets must be unique")
        if blind_fire and (
            target_actor_public_id not in blind_fire_eligible_actor_public_ids
        ):
            raise ValueError("Declared target must be in the blind-fire roster")
        if len(set(shotgun_spread_target_actor_public_ids)) != len(
            shotgun_spread_target_actor_public_ids
        ):
            raise ValueError("Shotgun spread targets must be unique")
        if target_actor_public_id in shotgun_spread_target_actor_public_ids:
            raise ValueError("Primary target cannot be repeated")
        firing_into_combat = bool(firing_into_combat_targets)
        if firing_into_combat:
            if attack_profile_code in {
                "close-quarters","natural-weapon","thrown",
            }:
                raise ValueError("Firing into Combat requires a shooting attack")
            if suppression_fire or blind_fire or shotgun_spread:
                raise ValueError(
                    "Firing into Combat cannot be combined with suppression, "
                    "blind fire, or shotgun spread")
            actors = [value[0] for value in firing_into_combat_targets]
            if len(set(actors)) != len(actors) or any(
                tier < 1 for _,tier in firing_into_combat_targets
            ):
                raise ValueError("Combat proximity roster is invalid")
        extreme = None
        if extreme_range_authorization_public_id is not None:
            if range_rule_code != "combat.range.distant":
                raise ValueError("Extreme-range fire uses the Distant range")
            if state[15] != 0:
                raise ValueError("Extreme-range attacker must remain stationary")
            extreme = connection.execute(
                """SELECT auth.authorization_id,
                          auth.rest_reference,
                          auth.line_of_sight,
                          auth.skill_level,
                          auth.attacker_metres_moved,
                          auth.energy_weapon,
                          auth.vehicle_id,
                          auth.vehicle_combat_round_id,
                          auth.venc_vehicle_id,
                          auth.vehicle_movement_status,
                          auth.vehicle_speed_kph
                     FROM enc_personal_extreme_range_authorization auth
                    WHERE auth.public_id=%s
                      AND auth.encounter_id=%s
                      AND auth.round_number=%s
                      AND auth.attacker_actor_id=%s
                      AND auth.target_actor_id=%s
                      AND auth.weapon_rule_id=%s
                      AND auth.attack_profile_code=%s
                      AND auth.authorization_status='available'
                    FOR UPDATE""",
                (extreme_range_authorization_public_id, state[0], state[1],
                 state[2], state[3], state[6], attack_profile_code),
            ).fetchone()
            if extreme is None:
                raise ValueError(
                    "Extreme-range authorization does not match this attack")
        burst_size_rule_id = None
        burst_option_rule_id = None
        burst_attack_modifier = 0
        burst_extra_damage_dice = 0
        burst_extra_damage_flat = 0
        ammunition_consumed = 1
        suppression_attack_modifier = 0
        panic_attack_modifier = 0
        panic_damage_burst_size_rule_id = None
        panic_extra_damage_dice = 0
        panic_extra_damage_flat = 0
        shotgun_spread_attack_modifier = 0
        shotgun_spread_damage_dice = None
        if burst_size_rounds is not None:
            burst = connection.execute(
                """SELECT size.rule_id,option_rule.rule_id,
                          CASE WHEN option_rule.applies_attack_modifier
                               THEN size.attack_modifier ELSE 0 END,
                          CASE WHEN option_rule.applies_extra_damage
                               THEN size.extra_damage_dice ELSE 0 END,
                          CASE WHEN option_rule.applies_extra_damage
                               THEN size.extra_damage_flat ELSE 0 END
                   FROM rule_personal_burst_size size
                   JOIN inv_weapon_burst_capability capability
                     ON capability.burst_size_rule_id=size.rule_id
                    AND capability.weapon_rule_id=%s
                   JOIN rule_personal_burst_option option_rule
                     ON option_rule.option_code=%s
                   WHERE size.rounds_consumed=%s""",
                (state[6], burst_option, burst_size_rounds),
            ).fetchone()
            if burst is None:
                raise ValueError("Weapon does not support selected burst fire")
            (burst_size_rule_id, burst_option_rule_id,
             burst_attack_modifier, burst_extra_damage_dice,
             burst_extra_damage_flat) = burst
            ammunition_consumed = burst_size_rounds
        if suppression_fire:
            if attack_profile_code in {
                "close-quarters", "natural-weapon", "thrown",
            }:
                raise ValueError("Suppression fire requires a shooting attack")
            if burst_option == "grouped":
                raise ValueError("Suppression fire cannot use grouped burst damage")
            suppression = connection.execute(
                """SELECT attack_modifier,ammunition_multiplier
                   FROM rule_personal_suppression_fire"""
            ).fetchone()
            suppression_attack_modifier = suppression[0]
            ammunition_consumed *= suppression[1]
        uses_ammunition = connection.execute(
            """SELECT EXISTS (
                   SELECT 1 FROM inv_ammunition_definition
                   WHERE weapon_rule_id=%s
               )""",
            (state[6],),
        ).fetchone()[0]
        if uses_ammunition:
            weapon_state = connection.execute(
                """SELECT ready,rounds_loaded
                   FROM actor_weapon_state
                   WHERE actor_id=%s AND weapon_rule_id=%s
                   FOR UPDATE""",
                (state[2], state[6]),
            ).fetchone()
            if weapon_state is None or not weapon_state[0]:
                raise ValueError("Weapon is not ready")
            if weapon_state[1] < ammunition_consumed:
                raise ValueError("Weapon lacks ammunition for the attack")
            if panic_fire:
                panic_rule = connection.execute(
                    """SELECT panic.attack_modifier
                       FROM rule_personal_panic_fire panic
                       JOIN inv_weapon_panic_fire_capability capability
                         ON capability.weapon_rule_id=%s""",
                    (state[6],),
                ).fetchone()
                if panic_rule is None:
                    raise ValueError(
                        "Panic fire requires a small-arms slug thrower")
                if weapon_state[1] < 1:
                    raise ValueError("Weapon has no ammunition for panic fire")
                ammunition_consumed = weapon_state[1]
                panic_attack_modifier = panic_rule[0]
                panic_tier = connection.execute(
                    """SELECT rule_id,extra_damage_dice,extra_damage_flat
                       FROM rule_personal_burst_size
                       WHERE rounds_consumed<=%s
                       ORDER BY rounds_consumed DESC LIMIT 1""",
                    (ammunition_consumed,),
                ).fetchone()
                if panic_tier is not None:
                    (panic_damage_burst_size_rule_id,
                     panic_extra_damage_dice,
                     panic_extra_damage_flat) = panic_tier
            if shotgun_spread:
                spread = connection.execute(
                    """SELECT rule.attack_modifier,rule.damage_dice
                       FROM rule_personal_shotgun_spread rule
                       JOIN inv_weapon_shotgun_spread_capability capability
                         ON capability.weapon_rule_id=%s
                        AND capability.ammunition_rule_id=%s""",
                    (state[6], connection.execute(
                        """SELECT loaded_ammunition_rule_id
                           FROM actor_weapon_state
                           WHERE actor_id=%s AND weapon_rule_id=%s""",
                        (state[2], state[6]),
                    ).fetchone()[0]),
                ).fetchone()
                if spread is None:
                    raise ValueError(
                        "Shotgun spread requires a shotgun loaded with flechette shells")
                shotgun_spread_attack_modifier = spread[0]
                shotgun_spread_damage_dice = spread[1]
        elif burst_size_rounds is not None:
            raise ValueError("Burst fire requires a weapon with ammunition state")
        battlefield = connection.execute(
            """SELECT attacker_stance.may_make_melee_attack,
                      target_stance.stance_code,
                      target_stance.cover_step_bonus,
                      target_stance.ranged_dm_personal,
                      target_stance.ranged_dm_medium_or_greater,
                      cover.display_order,range_band.display_order
               FROM enc_personal_combatant attacker
               JOIN rule_personal_stance attacker_stance
                 ON attacker_stance.rule_id=attacker.stance_rule_id
               JOIN enc_personal_combatant target
                 ON target.encounter_id=attacker.encounter_id
                AND target.actor_id=%s
               JOIN rule_personal_stance target_stance
                 ON target_stance.rule_id=target.stance_rule_id
               LEFT JOIN rule_personal_cover cover
                 ON cover.rule_id=target.cover_rule_id
               JOIN combat_range_band range_band ON range_band.rule_id=%s
               WHERE attacker.encounter_id=%s AND attacker.actor_id=%s""",
            (state[3], state[7], state[0], state[2]),
        ).fetchone()
        melee_attack = attack_profile_code in {
            "close-quarters", "natural-weapon",
        }
        if melee_attack and not battlefield[0]:
            raise ValueError("Current stance forbids melee attacks")
        cover_modifier = 0
        derived_has_cover = battlefield[5] is not None
        if derived_has_cover:
            effective_cover_order = battlefield[5] + battlefield[2]
            if effective_cover_order > 4:
                raise ValueError("Target is impossible to hit from full cover")
            cover_modifier = connection.execute(
                """SELECT attack_modifier FROM rule_personal_cover
                   WHERE display_order=%s""",
                (effective_cover_order,),
            ).fetchone()[0]
        stance_modifier = 0
        if not melee_attack and battlefield[1] == "prone":
            if battlefield[6] == 1:
                stance_modifier = battlefield[3]
            elif battlefield[6] >= 4:
                stance_modifier = battlefield[4]
        movement_rule = connection.execute(
            """SELECT target_modifier_metres,target_modifier_per_increment
               FROM rule_personal_movement""").fetchone()
        target_movement_modifier = (
            int(state[13] // movement_rule[0]) * movement_rule[1])
        assistance = None
        if weapon_item_instance_public_id is not None:
            assistance = connection.execute(
                """SELECT item.item_instance_id,
                          bool_or(option.option_code='laser-sights') FILTER (
                            WHERE option.option_code IS NOT NULL),
                          bool_or(option.option_code='intelligent-weapon') FILTER (
                            WHERE option.option_code IS NOT NULL),
                          campaign.owner_reference
                   FROM inv_item_instance item
                   JOIN inv_container_item held
                     ON held.item_instance_id=item.item_instance_id
                    AND held.campaign_id=item.campaign_id
                   JOIN inv_actor_container owner
                     ON owner.container_id=held.container_id
                    AND owner.campaign_id=held.campaign_id
                   JOIN actor_actor actor ON actor.actor_id=owner.actor_id
                   JOIN camp_campaign campaign
                     ON campaign.campaign_id=item.campaign_id
                   LEFT JOIN cmd_book1_ranged_weapon_option_receipt installed
                     ON installed.weapon_item_instance_id=item.item_instance_id
                   LEFT JOIN rule_book1_ranged_weapon_option option
                     ON option.rule_id=installed.option_rule_id
                   WHERE item.public_id=%s AND item.item_status='active'
                     AND item.item_rule_id=%s AND actor.actor_id=%s
                   GROUP BY item.item_instance_id,campaign.owner_reference""",
                (weapon_item_instance_public_id, state[6], state[2])).fetchone()
            if assistance is None:
                raise ValueError(
                    "Weapon instance is not an active held instance of this weapon")
        if intelligent_weapon_suppressed:
            if (assistance is None or not assistance[2]
                    or intelligent_weapon_suppression_referee_reference !=
                        assistance[3]
                    or not intelligent_weapon_suppression_reason
                    or not intelligent_weapon_suppression_reason.strip()):
                raise PermissionError(
                    "Intelligent Weapon suppression requires campaign referee reason")
        elif (intelligent_weapon_suppression_referee_reference is not None
              or intelligent_weapon_suppression_reason is not None):
            raise ValueError("Suppression authority is only valid when suppressed")
        kill_aim_damage_bonus = (
            state[12] if state[11] == state[3] else 0)
        conditions = connection.execute(
            """SELECT light_code,obscurant_code,extreme_weather,gravity_code
               FROM enc_personal_battlefield_condition
               WHERE encounter_id=%s""", (state[0],)).fetchone()
        sensor_rule_id = None
        sensor_jammed = None
        sensor = None
        if battlefield_sensor_code is not None:
            sensor = connection.execute(
                """SELECT sensor.rule_id,assignment.jammed,
                          sensor.qualifies_for_weather_visibility,
                          sensor.negates_darkness,
                          sensor.negates_smoke_concealment
                   FROM rule_personal_battlefield_sensor sensor
                   JOIN actor_personal_battlefield_sensor assignment
                     ON assignment.sensor_rule_id=sensor.rule_id
                    AND assignment.actor_id=%s
                   WHERE sensor.sensor_code=%s""",
                (state[2], battlefield_sensor_code)).fetchone()
            if sensor is None:
                raise ValueError("Actor does not possess the selected sensor")
            sensor_rule_id, sensor_jammed = sensor[0], sensor[1]
        sensor_active = sensor is not None and not sensor_jammed
        environmental_modifier = 0
        zero_gravity = conditions[3] == "zero-gravity"
        zero_weapon_skill = zero_trained = zero_level = zero_effective = None
        zero_recoil = None
        zero_recoil_modifier = 0
        if zero_gravity:
            zero_facts = connection.execute(
                """SELECT COALESCE(combat_skill.skill_level,
                                  required_skill.untrained_modifier),
                          zero_skill.skill_level IS NOT NULL,
                          zero_skill.skill_level,weapon.has_recoil,
                          required_skill.untrained_modifier
                   FROM inv_weapon_definition weapon
                   JOIN inv_weapon_attack_mode mode
                     ON mode.item_rule_id=weapon.item_rule_id
                    AND mode.attack_profile_code=%s
                   JOIN combat_attack_profile profile
                     ON profile.attack_profile_code=mode.attack_profile_code
                   JOIN rule_skill required_skill
                     ON required_skill.rule_id=COALESCE(
                        mode.required_skill_rule_id,profile.required_skill_rule_id)
                   LEFT JOIN actor_skill combat_skill
                     ON combat_skill.actor_id=%s
                    AND combat_skill.skill_rule_id=required_skill.rule_id
                   JOIN rule_rule zero_rule ON zero_rule.rule_code='skill.zero-g'
                   LEFT JOIN actor_skill zero_skill
                     ON zero_skill.actor_id=%s
                    AND zero_skill.skill_rule_id=zero_rule.rule_id
                   WHERE weapon.item_rule_id=%s""",
                (attack_profile_code,state[2],state[2],state[6])).fetchone()
            zero_weapon_skill,zero_trained,zero_level,zero_recoil,untrained = zero_facts
            zero_effective = (
                min(zero_weapon_skill,zero_level)
                if zero_trained else untrained)
            zero_recoil_modifier = -2 if zero_recoil else 0
        if not melee_attack:
            if conditions[0] != "normal" and not (
                sensor_active and sensor[3]
            ):
                environmental_modifier += connection.execute(
                    """SELECT ranged_attack_modifier
                       FROM rule_personal_battlefield_condition
                       WHERE condition_code=%s""",
                    (conditions[0],)).fetchone()[0]
            if conditions[1] != "none" and not (
                sensor_active and sensor[4]
            ):
                obscurant = connection.execute(
                    """SELECT ranged_attack_modifier,
                              doubled_for_laser_weapons
                       FROM rule_personal_battlefield_condition
                       WHERE condition_code=%s""",
                    (conditions[1],)).fetchone()
                environmental_modifier += obscurant[0] * (
                    2 if obscurant[1]
                    and item_rule_code.startswith("equipment.weapon.laser-")
                    else 1)
            if conditions[2]:
                if not (sensor_active and sensor[2]):
                    environmental_modifier -= 1
                environmental_modifier -= 1
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('declare_personal_attack',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        attack_id, attack_public = connection.execute(
            """INSERT INTO enc_personal_attack
               (encounter_id,round_number,attacker_actor_id,target_actor_id,
                weapon_rule_id,attack_profile_code,range_band_rule_id,
                target_has_cover,characteristic_rule_id,aim_modifier,
                cover_modifier,stance_modifier,target_movement_modifier,
                kill_aim_damage_bonus,ammunition_consumed,
                burst_size_rule_id,burst_option_rule_id,
                burst_attack_modifier,burst_extra_damage_dice,
                burst_extra_damage_flat,suppression_fire,
                suppression_attack_modifier,panic_fire,
                panic_attack_modifier,panic_damage_burst_size_rule_id,
                panic_extra_damage_dice,panic_extra_damage_flat,
                shotgun_spread,shotgun_spread_attack_modifier,
                shotgun_spread_damage_dice,battlefield_light_code,
                battlefield_obscurant_code,battlefield_extreme_weather,
                battlefield_sensor_rule_id,battlefield_sensor_jammed,
                environmental_attack_modifier,blind_fire,
                extreme_range,extreme_range_rest_reference,
                extreme_range_line_of_sight,extreme_range_skill_level,
                extreme_range_attacker_metres_moved,
                extreme_range_attack_modifier,extreme_range_energy_weapon,
                extreme_range_vehicle_id,
                extreme_range_vehicle_combat_round_id,
                extreme_range_venc_vehicle_id,
                extreme_range_vehicle_movement_status,
                extreme_range_vehicle_speed_kph,
                extreme_range_authorization_id,zero_gravity,
                zero_gravity_weapon_skill_level,zero_gravity_trained,
                zero_gravity_skill_level,zero_gravity_effective_skill_level,
                zero_gravity_weapon_has_recoil,zero_gravity_recoil_modifier,
                firing_into_combat,firing_into_combat_attack_modifier,
                thrown_delivery_type,thrown_target_point_reference,
                fatigue_attack_modifier)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s)
               RETURNING personal_attack_id,public_id""",
            (state[0], state[1], state[2], state[3], state[6],
             attack_profile_code, state[7], derived_has_cover, state[8],
             state[10] if state[9] == state[3] else 0, cover_modifier,
             stance_modifier, target_movement_modifier, kill_aim_damage_bonus,
             ammunition_consumed if uses_ammunition else 0,
             burst_size_rule_id, burst_option_rule_id,
             burst_attack_modifier, burst_extra_damage_dice,
             burst_extra_damage_flat, suppression_fire,
             suppression_attack_modifier,panic_fire,panic_attack_modifier,
             panic_damage_burst_size_rule_id,panic_extra_damage_dice,
             panic_extra_damage_flat,shotgun_spread,
             shotgun_spread_attack_modifier,shotgun_spread_damage_dice,
             conditions[0],conditions[1],conditions[2],sensor_rule_id,
             sensor_jammed,environmental_modifier,blind_fire,
             extreme is not None,
             extreme[1] if extreme else None,
             extreme[2] if extreme else None,
             extreme[3] if extreme else None,
             extreme[4] if extreme else None,
             -2 if extreme else 0,
             extreme[5] if extreme else False,
             extreme[6] if extreme else None,
             extreme[7] if extreme else None,
             extreme[8] if extreme else None,
             extreme[9] if extreme else None,
             extreme[10] if extreme else None,
             extreme[0] if extreme else None,zero_gravity,zero_weapon_skill,
             zero_trained,zero_level,zero_effective,zero_recoil,
             zero_recoil_modifier,firing_into_combat,
             -2 if firing_into_combat else 0,
             thrown_delivery_type,frozen_thrown_target,
             fatigue_attack_modifier),
        ).fetchone()
        if assistance is not None:
            aimed = state[9] == state[3] and state[10] > 0
            connection.execute(
                """INSERT INTO enc_personal_attack_weapon_assistance
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (attack_id, assistance[0], bool(assistance[1]),
                 1 if assistance[1] and aimed else 0,
                 bool(assistance[2]),
                 0 if intelligent_weapon_suppressed else
                    (1 if assistance[2] else 0),
                 intelligent_weapon_suppressed,
                 intelligent_weapon_suppression_referee_reference,
                 (intelligent_weapon_suppression_reason.strip()
                  if intelligent_weapon_suppression_reason else None)))
        if extreme:
            connection.execute(
                """UPDATE enc_personal_extreme_range_authorization
                      SET authorization_status='consumed'
                    WHERE authorization_id=%s""",
                (extreme[0],),
            )
        for order,(target_public,tier) in enumerate(
            firing_into_combat_targets,1
        ):
            target_row=connection.execute(
                """SELECT actor.actor_id FROM actor_actor actor
                   JOIN enc_personal_combatant combatant
                     ON combatant.actor_id=actor.actor_id
                    AND combatant.encounter_id=%s
                   WHERE actor.public_id=%s""",
                (state[0],target_public)).fetchone()
            if target_row is None or target_row[0] in (state[2],state[3]):
                raise ValueError("Combat proximity roster target is invalid")
            connection.execute(
                """INSERT INTO enc_personal_firing_into_combat_target
                   VALUES (%s,%s,%s,%s)""",
                (attack_id,target_row[0],tier,order))
        if blind_fire:
            for order, target_public in enumerate(
                blind_fire_eligible_actor_public_ids, 1
            ):
                target_row = connection.execute(
                    """SELECT actor.actor_id
                       FROM actor_actor actor
                       JOIN enc_personal_combatant combatant
                         ON combatant.actor_id=actor.actor_id
                        AND combatant.encounter_id=%s
                       WHERE actor.public_id=%s""",
                    (state[0], target_public)).fetchone()
                if target_row is None or target_row[0] == state[2]:
                    raise ValueError(
                        "Blind-fire roster includes an ineligible combatant")
                connection.execute(
                    """INSERT INTO enc_personal_blind_fire_target
                       VALUES (%s,%s,%s)""",
                    (attack_id, target_row[0], order))
        if shotgun_spread:
            target_rows = [(state[3], True)] + [
                (connection.execute(
                    """SELECT actor.actor_id FROM actor_actor actor
                       JOIN enc_personal_combatant combatant
                         ON combatant.actor_id=actor.actor_id
                        AND combatant.encounter_id=%s
                       WHERE actor.public_id=%s""",
                    (state[0], target_public),
                ).fetchone(), False)
                for target_public in shotgun_spread_target_actor_public_ids
            ]
            if any(row[0] is None for row in target_rows):
                raise ValueError("Shotgun spread includes a nonparticipant")
            for order, (actor_value, primary) in enumerate(target_rows, 1):
                actor_id = actor_value if primary else actor_value[0]
                connection.execute(
                    """INSERT INTO enc_personal_shotgun_spread_target
                       VALUES (%s,%s,%s,%s,%s)""",
                    (attack_id, actor_id, order, primary, not primary))
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=
                   significant_actions_remaining-1,
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_attack_declaration_receipt
               VALUES (%s,%s,%s,%s)""",
            (command_id, attack_id, state[4], state[4] - 1))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_attack_declared')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_declared_attack(
            connection, command_id, public_id, False)


def _load_begun_turn(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.initiative_at_start,r.dexterity_at_start,
                  r.simultaneous_group_size
           FROM cmd_personal_turn_begin_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return BegunPersonalTurn(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], replayed)


def begin_personal_turn_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
) -> BegunPersonalTurn:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("begin_personal_turn", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_begun_turn(
                connection, existing[0], existing[1], True)
        combat = connection.execute(
            """SELECT pc.encounter_id,pc.current_round
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
               FOR UPDATE OF pc""", (encounter_public_id,)
        ).fetchone()
        if combat is None:
            raise ValueError("Active personal combat does not exist")
        combatants = connection.execute(
            """SELECT c.actor_id,a.public_id,a.controller_reference,
                      c.initiative_current,c.dexterity_value,
                      c.acted_this_round,c.turn_started_this_round,
                      c.delayed_this_round
               FROM enc_personal_combatant c
               JOIN actor_actor a ON a.actor_id=c.actor_id
               WHERE c.encounter_id=%s FOR UPDATE OF c""", (combat[0],)
        ).fetchall()
        remaining = [
            row for row in combatants if not row[5] and not row[7]]
        candidate = next(
            (row for row in remaining if str(row[1]) == actor_public_id), None)
        if candidate is None or candidate[2] != initiator_reference:
            raise PermissionError(
                "Initiator does not control an awaiting combatant")
        if candidate[6]:
            raise ValueError("Combatant has already begun this turn")
        highest = max((row[3], row[4]) for row in remaining)
        if (candidate[3], candidate[4]) != highest:
            raise ValueError("A higher initiative combatant must act first")
        simultaneous = sum(
            (row[3], row[4]) == highest for row in remaining)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('begin_personal_turn',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET turn_started_this_round=true
               WHERE encounter_id=%s AND actor_id=%s""",
            (combat[0], candidate[0]))
        connection.execute(
            """INSERT INTO cmd_personal_turn_begin_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, combat[0], candidate[0], combat[1], candidate[3],
             candidate[4], simultaneous))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_turn_begun')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_begun_turn(
            connection, command_id, public_id, False)


def _load_hastened(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.initiative_before,r.initiative_after,r.check_modifier
           FROM cmd_personal_hasten_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return HastenedCombatant(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], replayed)


def hasten_personal_combatant_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
) -> HastenedCombatant:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("hasten_personal_combatant", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_hastened(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      c.initiative_current,c.hastened_this_round
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND NOT EXISTS (
                   SELECT 1 FROM enc_personal_extended_action extended
                   WHERE extended.encounter_id=pc.encounter_id
                     AND extended.actor_id=a.actor_id
                     AND extended.action_status='active')
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control an active combatant")
        if state[4]:
            raise ValueError("Combatant has already hastened this round")
        if connection.execute(
            """SELECT 1 FROM enc_personal_combatant
               WHERE encounter_id=%s AND turn_started_this_round""",
            (state[0],),
        ).fetchone():
            raise ValueError("The round-start hasten window has closed")
        rules = connection.execute(
            """SELECT initiative_modifier,check_modifier,
                      maximum_per_round,declared_at_round_start
               FROM rule_personal_hasten""").fetchone()
        if rules[2] != 1 or not rules[3]:
            raise RuntimeError("Unsupported stored hasten procedure")
        initiative_after = state[3] + rules[0]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('hasten_personal_combatant',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET initiative_current=%s,hastened_this_round=true,
                   hasten_check_modifier=%s
               WHERE encounter_id=%s AND actor_id=%s""",
            (initiative_after, rules[1], state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_hasten_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], state[3],
             initiative_after, rules[1]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_combatant_hastened')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_hastened(
            connection, command_id, public_id, False)


def _load_delayed(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.initiative_when_delayed
           FROM cmd_personal_delay_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return DelayedPersonalTurn(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], replayed)


def delay_personal_turn_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
) -> DelayedPersonalTurn:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("delay_personal_turn", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_delayed(
                connection, existing[0], existing[1], True)
        combat = connection.execute(
            """SELECT pc.encounter_id,pc.current_round
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
               FOR UPDATE OF pc""", (encounter_public_id,)
        ).fetchone()
        if combat is None:
            raise ValueError("Active personal combat does not exist")
        combatants = connection.execute(
            """SELECT c.actor_id,a.public_id,a.controller_reference,
                      c.initiative_current,c.dexterity_value,
                      c.acted_this_round,c.turn_started_this_round,
                      c.delayed_this_round
               FROM enc_personal_combatant c
               JOIN actor_actor a ON a.actor_id=c.actor_id
               WHERE c.encounter_id=%s FOR UPDATE OF c""", (combat[0],)
        ).fetchall()
        committed_actor_ids = {
            row[0] for row in connection.execute(
                """SELECT actor_id FROM enc_personal_extended_action
                   WHERE encounter_id=%s AND action_status='active'""",
                (combat[0],),
            ).fetchall()
        }
        available = [
            row for row in combatants
            if not row[5] and not row[6] and not row[7]
            and row[0] not in committed_actor_ids]
        candidate = next(
            (row for row in available if str(row[1]) == actor_public_id), None)
        if candidate is None or candidate[2] != initiator_reference:
            raise PermissionError(
                "Initiator does not control an eligible combatant")
        highest = max((row[3], row[4]) for row in available)
        if (candidate[3], candidate[4]) != highest:
            raise ValueError("A higher initiative combatant must act first")
        rules = connection.execute(
            """SELECT may_act_later_in_round,may_interrupt_action,
                      initiative_becomes_action_count
               FROM rule_personal_delay""").fetchone()
        if rules != (True, True, True):
            raise RuntimeError("Unsupported stored delay procedure")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('delay_personal_turn',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant SET delayed_this_round=true
               WHERE encounter_id=%s AND actor_id=%s""",
            (combat[0], candidate[0]))
        connection.execute(
            """INSERT INTO cmd_personal_delay_receipt
               VALUES (%s,%s,%s,%s,%s)""",
            (command_id, combat[0], candidate[0], combat[1], candidate[3]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_turn_delayed')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_delayed(
            connection, command_id, public_id, False)


def _load_resumed_turn(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.initiative_before,r.initiative_after,interrupted.public_id
           FROM cmd_personal_delay_resume_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           LEFT JOIN actor_actor interrupted
             ON interrupted.actor_id=r.interrupted_actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return ResumedPersonalTurn(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        str(row[5]) if row[5] else None, replayed)


def resume_delayed_personal_turn_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
) -> ResumedPersonalTurn:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resume_delayed_personal_turn", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_resumed_turn(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      c.initiative_current
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.delayed_this_round AND NOT c.acted_this_round
                 AND NOT c.turn_started_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control a delayed combatant")
        others = connection.execute(
            """SELECT c.actor_id,c.initiative_current,
                      c.turn_started_this_round,c.acted_this_round,
                      c.delayed_this_round
               FROM enc_personal_combatant c
               WHERE c.encounter_id=%s AND c.actor_id<>%s
               FOR UPDATE OF c""", (state[0], state[2])
        ).fetchall()
        active = [
            row for row in others if row[2] and not row[3]]
        interrupted = max(active, key=lambda row: row[1]) if active else None
        if interrupted:
            action_count = interrupted[1]
        else:
            awaiting = [
                row[1] for row in others
                if not row[3] and not row[4]]
            action_count = max(awaiting) if awaiting else min(
                [row[1] for row in others] + [state[3]])
        action_count = min(state[3], action_count)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resume_delayed_personal_turn',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET delayed_this_round=false,turn_started_this_round=true,
                   initiative_current=%s
               WHERE encounter_id=%s AND actor_id=%s""",
            (action_count, state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_delay_resume_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], state[3],
             action_count, interrupted[0] if interrupted else None))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'delayed_personal_turn_resumed')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_resumed_turn(
            connection, command_id, public_id, False)


def _load_forfeited_turn(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,r.round_number,
                  r.initiative_forfeited,r.significant_actions_forfeited,
                  r.minor_actions_forfeited
           FROM cmd_personal_delay_forfeit_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return ForfeitedDelayedTurn(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        row[5], replayed)


def forfeit_delayed_personal_turn_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
) -> ForfeitedDelayedTurn:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("forfeit_delayed_personal_turn", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_forfeited_turn(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      c.initiative_current,c.significant_actions_remaining,
                      c.minor_actions_remaining
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.delayed_this_round AND NOT c.acted_this_round
                 AND NOT c.turn_started_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control a delayed combatant")
        if connection.execute(
            """SELECT 1 FROM enc_personal_combatant
               WHERE encounter_id=%s AND actor_id<>%s
                 AND NOT acted_this_round AND NOT delayed_this_round""",
            (state[0], state[2]),
        ).fetchone():
            raise ValueError(
                "Delayed turn may be forfeited only at the end of the round")
        rules = connection.execute(
            """SELECT may_forfeit_for_first_next_round
               FROM rule_personal_delay""").fetchone()
        if rules != (True,):
            raise RuntimeError("Stored delay procedure forbids forfeiture")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('forfeit_delayed_personal_turn',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET delayed_this_round=false,acted_this_round=true,
                   delayed_first_next_round=true
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_delay_forfeit_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], state[3],
             state[4], state[5]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'delayed_personal_turn_forfeited')""",
            (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_forfeited_turn(
            connection, command_id, public_id, False)


def _load_aimed(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,a.public_id,target.public_id,r.round_number,
                  r.minor_actions_before,r.minor_actions_after,
                  r.aim_modifier_before,r.aim_modifier_after
           FROM cmd_personal_aim_receipt r
           JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           JOIN actor_actor a ON a.actor_id=r.actor_id
           JOIN actor_actor target ON target.actor_id=r.target_actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return AimedPersonalAttack(
        str(public_id), str(row[0]), str(row[1]), str(row[2]), row[3],
        row[4], row[5], row[6], row[7], replayed)


def aim_personal_attack_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    target_actor_public_id: str,
) -> AimedPersonalAttack:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("aim_personal_attack", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_aimed(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      target.actor_id,c.minor_actions_remaining,
                      c.aim_target_actor_id,c.aim_modifier
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN actor_actor target ON target.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               JOIN enc_personal_combatant target_combatant
                 ON target_combatant.encounter_id=pc.encounter_id
                AND target_combatant.actor_id=target.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round AND NOT c.acted_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, target_actor_public_id, encounter_public_id,
             initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Initiator does not control an active eligible combatant")
        if state[2] == state[3]:
            raise ValueError("Combatant cannot aim at itself")
        rules = connection.execute(
            """SELECT minor_actions_per_step,modifier_per_step,
                      maximum_modifier,requires_same_target
               FROM rule_personal_aim""").fetchone()
        if state[4] < rules[0]:
            raise ValueError("No minor action remains for aiming")
        before = state[6] if state[5] == state[3] else 0
        after = min(rules[2], before + rules[1])
        if after == before:
            raise ValueError("Maximum aiming modifier has been reached")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('aim_personal_attack',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET minor_actions_remaining=minor_actions_remaining-%s,
                   aim_target_actor_id=%s,aim_modifier=%s,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (rules[0], state[3], after, state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_aim_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[3], state[1], state[4],
             state[4] - rules[0], before, after))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_attack_aimed')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_aimed(
            connection, command_id, public_id, False)


def _load_stance(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT before.stance_code,after.stance_code,r.minor_actions_after
           FROM cmd_personal_stance_receipt r
           JOIN rule_personal_stance before
             ON before.rule_id=r.stance_before_rule_id
           JOIN rule_personal_stance after
             ON after.rule_id=r.stance_after_rule_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return PersonalStanceResult(
        str(public_id), row[0], row[1], row[2], replayed)


def change_personal_stance_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    stance_code: str,
) -> PersonalStanceResult:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("change_personal_stance", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_stance(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      c.stance_rule_id,c.minor_actions_remaining,
                      desired.rule_id,mechanic.minor_action_cost
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               JOIN rule_personal_stance desired
                 ON desired.stance_code=%s
               CROSS JOIN rule_personal_stance_change mechanic
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round AND NOT c.acted_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, stance_code, encounter_public_id,
             initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError("Stance change is not legal")
        if state[3] == state[5]:
            raise ValueError("Combatant already has that stance")
        if state[4] < state[6]:
            raise ValueError("No minor action remains")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('change_personal_stance',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET stance_rule_id=%s,minor_actions_remaining=
                   minor_actions_remaining-%s,
                   aim_target_actor_id=NULL,aim_modifier=0,
                   kill_aim_target_actor_id=NULL,kill_aim_damage_bonus=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[5], state[6], state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_stance_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], state[3], state[5],
             state[4], state[4] - state[6]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_stance_changed')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_stance(connection, command_id, public_id, False)


def _load_cover(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT before.cover_code,after.cover_code
           FROM cmd_personal_cover_receipt r
           LEFT JOIN rule_personal_cover before
             ON before.rule_id=r.cover_before_rule_id
           LEFT JOIN rule_personal_cover after
             ON after.rule_id=r.cover_after_rule_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return PersonalCoverResult(
        str(public_id), row[0], row[1], replayed)


def set_personal_cover_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    cover_code: str | None,
) -> PersonalCoverResult:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("set_personal_cover", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_cover(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      c.cover_rule_id,desired.rule_id
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               LEFT JOIN rule_personal_cover desired
                 ON desired.cover_code=%s
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
               FOR UPDATE OF pc,c""",
            (actor_public_id, cover_code, encounter_public_id,
             initiator_reference),
        ).fetchone()
        if state is None or (cover_code is not None and state[4] is None):
            raise ValueError("Cover context is not legal")
        if state[3] == state[4]:
            raise ValueError("Cover is unchanged")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('set_personal_cover',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant SET cover_rule_id=%s
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[4], state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_cover_receipt
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], state[3], state[4]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_cover_set')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_cover(connection, command_id, public_id, False)


def _load_move(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT metres_moved,round_metres_after,minor_actions_after
           FROM cmd_personal_move_receipt WHERE command_id=%s""",
        (command_id,),
    ).fetchone()
    return MovedPersonalCombatant(
        str(public_id), float(row[0]), float(row[1]), row[2], replayed)


def _load_species_great_leap(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT encounter.public_id,actor.public_id,receipt.round_number,
                  characteristic.rule_code,difficulty.rule_code,
                  receipt.athletics_skill_level,
                  receipt.characteristic_modifier,
                  receipt.difficulty_modifier,receipt.check_total,
                  receipt.target_number,receipt.effect,receipt.succeeded,
                  receipt.squares_jumped,receipt.metres_jumped,
                  receipt.significant_after
           FROM cmd_species_great_leap_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           JOIN rule_rule characteristic
             ON characteristic.rule_id=receipt.characteristic_rule_id
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
    return SpeciesGreatLeapResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3], row[4],
        dice, row[5], row[6], row[7], row[8], row[9], row[10], row[11],
        row[12], float(row[13]), row[14], replayed,
    )


def _load_species_flyer_move(
    connection, command_id, public_id, replayed,
):
    row = connection.execute(
        """SELECT encounter.public_id,actor.public_id,receipt.round_number,
                  receipt.operation,receipt.metres_moved,
                  receipt.altitude_change_metres,receipt.status_after,
                  receipt.altitude_after,receipt.minor_after
           FROM cmd_species_flyer_move_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return SpeciesFlyerMoveResult(
        str(public_id), str(row[0]), str(row[1]), row[2], row[3],
        float(row[4]), float(row[5]), row[6], float(row[7]), row[8],
        replayed,
    )


def move_species_flyer_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    metres: float, altitude_change_metres: float = 0,
) -> SpeciesFlyerMoveResult:
    """Take off, move aloft, or land using the species Flyer speed."""
    if metres <= 0:
        raise ValueError("Flight movement distance must be positive")
    if abs(altitude_change_metres) > metres:
        raise ValueError("Altitude change cannot exceed flight movement")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("move_species_flyer", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_species_flyer_move(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,actor.actor_id,
                      combatant.minor_actions_remaining,
                      combatant.metres_moved_this_round,
                      combatant.flight_status,combatant.altitude_metres,
                      assignment.movement_metres,
                      combatant.kill_aim_damage_bonus
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor actor ON actor.public_id=%s
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=actor.actor_id
               JOIN actor_current_species current_species
                 ON current_species.actor_id=actor.actor_id
               JOIN rule_species_trait_assignment assignment
                 ON assignment.species_rule_id=current_species.species_rule_id
               JOIN rule_species_trait trait
                 ON trait.species_trait_rule_id=
                    assignment.species_trait_rule_id
                AND trait.trait_code='flyer'
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND actor.controller_reference=%s
                 AND combatant.turn_started_this_round
                 AND NOT combatant.acted_this_round
               FOR UPDATE OF combat,combatant,actor""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Flight movement is not legal for this actor and turn")
        if connection.execute(
            """SELECT seriously_wounded FROM enc_personal_combatant
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[0], state[2])).fetchone()[0]:
            raise ValueError(
                "A seriously wounded combatant cannot use flight movement")
        if state[5] == "falling":
            raise ValueError("A falling combatant cannot use controlled flight")
        if state[3] < 1:
            raise ValueError("No minor action remains")
        if state[8]:
            raise ValueError("Aiming for the Kill forbids movement")
        speed = float(state[7])
        if metres > speed:
            raise ValueError("Flight movement exceeds the species allowance")
        altitude_before = float(state[6])
        altitude_after = altitude_before + altitude_change_metres
        if altitude_after < 0:
            raise ValueError("Altitude cannot be negative")
        if state[5] == "grounded":
            if altitude_after <= 0:
                raise ValueError("Takeoff must end above ground")
            operation, status_after = "takeoff", "aloft"
        elif altitude_after == 0:
            operation, status_after = "landing", "grounded"
        else:
            operation, status_after = "airborne_movement", "aloft"
        minor_after = state[3] - 1
        round_metres_after = float(state[4]) + metres
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('move_species_flyer',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET minor_actions_remaining=%s,metres_moved_this_round=%s,
                   flight_status=%s,altitude_metres=%s,
                   flight_upkeep_round=CASE WHEN %s='aloft' THEN %s ELSE NULL END,
                   aim_target_actor_id=NULL,aim_modifier=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (minor_after, round_metres_after, status_after, altitude_after,
             status_after, state[1], state[0], state[2]),
        )
        connection.execute(
            """INSERT INTO cmd_species_flyer_move_receipt
               (command_id,encounter_id,actor_id,round_number,operation,
                flight_speed_metres,metres_moved,altitude_change_metres,
                status_before,status_after,altitude_before,altitude_after,
                minor_before,minor_after,round_metres_before,
                round_metres_after)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], operation, speed,
             metres, altitude_change_metres, state[5], status_after,
             altitude_before, altitude_after, state[3], minor_after,
             state[4], round_metres_after),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'species_flyer_moved')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (state[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_species_flyer_move(
            connection, command_id, command_public, False)


def resolve_species_great_leap_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    characteristic_rule_code: str, difficulty_rule_code: str,
    random_source=None,
) -> SpeciesGreatLeapResult:
    """Resolve the Great Leaper Athletics check and source jump distance."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("resolve_species_great_leap", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_species_great_leap(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,actor.actor_id,
                      combatant.significant_actions_remaining,
                      combatant.metres_moved_this_round,
                      characteristic.rule_id,characteristic_state.current_value,
                      athletics.skill_level,difficulty.rule_id,
                      difficulty_rule.modifier,core.dice_count,core.die_sides,
                      core.target_number,combatant.kill_aim_damage_bonus
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor actor ON actor.public_id=%s
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=actor.actor_id
               JOIN rule_rule characteristic
                 ON characteristic.rule_code=%s
               JOIN actor_characteristic characteristic_state
                 ON characteristic_state.actor_id=actor.actor_id
                AND characteristic_state.characteristic_rule_id=
                    characteristic.rule_id
               JOIN rule_rule athletics_rule
                 ON athletics_rule.rule_code='skill.athletics'
               JOIN actor_skill athletics
                 ON athletics.actor_id=actor.actor_id
                AND athletics.skill_rule_id=athletics_rule.rule_id
               JOIN rule_rule difficulty
                 ON difficulty.rule_code=%s
               JOIN rule_difficulty difficulty_rule
                 ON difficulty_rule.rule_id=difficulty.rule_id
               CROSS JOIN rule_check_system core
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND actor.controller_reference=%s
                 AND combatant.turn_started_this_round
                 AND NOT combatant.acted_this_round
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
                       AND trait.trait_code='great-leaper'
                 )
               FOR UPDATE OF combat,combatant,actor""",
            (actor_public_id, characteristic_rule_code,
             difficulty_rule_code, encounter_public_id,
             initiator_reference),
        ).fetchone()
        if state is None:
            raise ValueError("Great Leap is not legal for this actor and turn")
        if connection.execute(
            """SELECT seriously_wounded FROM enc_personal_combatant
               WHERE encounter_id=%s AND actor_id=%s""",
            (state[0], state[2])).fetchone()[0]:
            raise ValueError(
                "A seriously wounded combatant cannot use Great Leap")
        if state[3] < 1:
            raise ValueError("No significant action remains")
        if state[13]:
            raise ValueError("Aiming for the Kill forbids movement")
        characteristic_modifier = connection.execute(
            """SELECT modifier
               FROM rule_characteristic_modifier_band
               WHERE (characteristic_rule_id IS NULL
                      OR characteristic_rule_id=%s)
                 AND score_range @> %s::integer
               ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
            (state[5], state[6]),
        ).fetchone()[0]
        dice = tuple(
            rng.randint(1, state[11]) for _ in range(state[10]))
        total = (
            sum(dice) + state[7] + characteristic_modifier + state[9])
        effect = total - state[12]
        succeeded = total >= state[12]
        squares = 4 + effect if succeeded else 0
        metres = squares * 1.5
        significant_after = state[3] - 1
        metres_after = float(state[4]) + metres
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_species_great_leap',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, state[11], die),
            )
        connection.execute(
            """UPDATE enc_personal_combatant
               SET significant_actions_remaining=%s,
                   metres_moved_this_round=%s,
                   aim_target_actor_id=NULL,aim_modifier=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (significant_after, metres_after, state[0], state[2]),
        )
        connection.execute(
            """INSERT INTO cmd_species_great_leap_receipt
               (command_id,encounter_id,actor_id,round_number,
                characteristic_rule_id,characteristic_modifier,
                athletics_skill_level,difficulty_rule_id,
                difficulty_modifier,check_total,target_number,effect,
                succeeded,squares_jumped,metres_jumped,
                significant_before,significant_after,
                round_metres_before,round_metres_after)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], state[5],
             characteristic_modifier, state[7], state[8], state[9], total,
             state[12], effect, succeeded, squares, metres, state[3],
             significant_after, state[4], metres_after),
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'species_great_leap_resolved')""",
            (command_id,),
        )
        connection.execute(
            """UPDATE actor_actor SET concurrency_version=concurrency_version+1
               WHERE actor_id=%s""",
            (state[2],),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_species_great_leap(
            connection, command_id, command_public, False)


def move_personal_combatant_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    metres: float, difficult_terrain: bool = False,
) -> MovedPersonalCombatant:
    if metres <= 0:
        raise ValueError("Movement distance must be positive")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("move_personal_combatant", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_move(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      c.minor_actions_remaining,c.metres_moved_this_round,
                      stance.stance_code,c.kill_aim_damage_bonus,
                      (
                          SELECT assignment.movement_metres
                          FROM actor_current_species current_species
                          JOIN rule_species_trait_assignment assignment
                            ON assignment.species_rule_id=
                               current_species.species_rule_id
                          JOIN rule_species_trait trait
                            ON trait.species_trait_rule_id=
                               assignment.species_trait_rule_id
                          WHERE current_species.actor_id=c.actor_id
                            AND trait.trait_code IN (
                                'fast-speed','slow-speed'
                            )
                          LIMIT 1
                      ) AS species_ground_speed,
                      c.flight_status,c.seriously_wounded
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               JOIN rule_personal_stance stance
                 ON stance.rule_id=c.stance_rule_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round AND NOT c.acted_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError("Movement is not legal")
        if connection.execute(
            """SELECT 1 FROM enc_personal_grapple_active_actor
               WHERE actor_id=%s""", (state[2],)).fetchone():
            raise ValueError("A grappled combatant cannot move")
        if state[8] != "grounded":
            raise ValueError("Ordinary movement requires a grounded combatant")
        if state[6]:
            raise ValueError("Aiming for the Kill forbids movement")
        rules = connection.execute(
            """SELECT minor_actions_per_move,normal_metres,
                      difficult_terrain_divisor,crouched_divisor
               FROM rule_personal_movement""").fetchone()
        if state[3] < rules[0]:
            raise ValueError("No minor action remains")
        maximum = float(state[7]) if state[7] is not None else rules[1]
        if difficult_terrain:
            maximum /= rules[2]
        if state[5] == "crouched":
            maximum /= rules[3]
        if state[9]:
            maximum = min(maximum, 1.5 - float(state[4]))
        if metres > maximum:
            raise ValueError("Movement exceeds the source allowance")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('move_personal_combatant',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        after_metres = float(state[4]) + metres
        after_minor = state[3] - rules[0]
        connection.execute(
            """UPDATE enc_personal_combatant
               SET minor_actions_remaining=%s,metres_moved_this_round=%s,
                   aim_target_actor_id=NULL,aim_modifier=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (after_minor, after_metres, state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_move_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[1], difficult_terrain,
             state[5], metres, state[4], after_metres, state[3], after_minor))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_combatant_moved')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_move(connection, command_id, public_id, False)


def _load_kill_aim(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT target.public_id,r.damage_bonus_before,
                  r.damage_bonus_after,r.minor_actions_after
           FROM cmd_personal_kill_aim_receipt r
           JOIN actor_actor target ON target.actor_id=r.target_actor_id
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return KillAimedPersonalAttack(
        str(public_id), str(row[0]), row[1], row[2], row[3], replayed)


def aim_personal_attack_for_kill_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, actor_public_id: str,
    target_actor_public_id: str,
) -> KillAimedPersonalAttack:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("aim_personal_attack_for_kill", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_kill_aim(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT pc.encounter_id,pc.current_round,c.actor_id,
                      target.actor_id,c.minor_actions_remaining,
                      c.kill_aim_target_actor_id,c.kill_aim_damage_bonus
               FROM enc_personal_combat pc
               JOIN enc_encounter e ON e.encounter_id=pc.encounter_id
               JOIN actor_actor a ON a.public_id=%s
               JOIN actor_actor target ON target.public_id=%s
               JOIN enc_personal_combatant c
                 ON c.encounter_id=pc.encounter_id AND c.actor_id=a.actor_id
               JOIN enc_personal_combatant target_state
                 ON target_state.encounter_id=pc.encounter_id
                AND target_state.actor_id=target.actor_id
               WHERE e.public_id=%s AND e.encounter_status='active'
                 AND pc.combat_status='active'
                 AND a.controller_reference=%s
                 AND c.turn_started_this_round AND NOT c.acted_this_round
               FOR UPDATE OF pc,c""",
            (actor_public_id, target_actor_public_id, encounter_public_id,
             initiator_reference),
        ).fetchone()
        if state is None or state[2] == state[3]:
            raise ValueError("Kill aiming is not legal")
        rules = connection.execute(
            """SELECT minor_actions_per_step,damage_per_step,maximum_damage
               FROM rule_personal_kill_aim""").fetchone()
        if state[4] < rules[0]:
            raise ValueError("No minor action remains")
        before = state[6] if state[5] == state[3] else 0
        after = min(rules[2], before + rules[1])
        if after == before:
            raise ValueError("Maximum kill-aim bonus has been reached")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('aim_personal_attack_for_kill',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        connection.execute(
            """UPDATE enc_personal_combatant
               SET minor_actions_remaining=minor_actions_remaining-%s,
                   kill_aim_target_actor_id=%s,kill_aim_damage_bonus=%s,
                   aim_target_actor_id=NULL,aim_modifier=0
               WHERE encounter_id=%s AND actor_id=%s""",
            (rules[0], state[3], after, state[0], state[2]))
        connection.execute(
            """INSERT INTO cmd_personal_kill_aim_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[3], state[1], state[4],
             state[4] - rules[0], before, after))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type)
               VALUES (%s,1,'personal_attack_kill_aimed')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_kill_aim(connection, command_id, public_id, False)
