import os
import unittest

import psycopg

from engine.characters import assign_actor_species_command
from engine.commands import (
    apply_personal_damage_command, resolve_personal_attack_command,
)
from engine.comms_runtime import (
    apply_personal_initiative_support_command,
    set_battlefield_communication_command,
)
from engine.conditions_runtime import (
    set_personal_battlefield_conditions_command,
)
from engine.psionics import activate_psionic_power_command
from engine.combat_runtime import (
    advance_personal_combat_round_command, aim_personal_attack_command,
    aim_personal_attack_for_kill_command,
    begin_personal_turn_command,
    change_personal_stance_command, complete_personal_turn_command,
    declare_personal_attack_command,
    declare_personal_reaction_command, delay_personal_turn_command,
    forfeit_delayed_personal_turn_command,
    hasten_personal_combatant_command, initialize_personal_combat_command,
    move_personal_combatant_command, resume_delayed_personal_turn_command,
    move_species_flyer_command, resolve_species_great_leap_command,
    spend_personal_action_command, advance_weapon_reload_command,
    set_personal_cover_command,
)
from engine.encounters import (
    add_encounter_participant_command, create_encounter_command,
    transition_encounter_mode_command,
)
from engine.explosions_runtime import (
    declare_personal_explosion_command,
    declare_personal_explosion_reaction_command,
    resolve_personal_explosion_command,
)
from engine.extreme_range_runtime import authorize_extreme_range_command
from engine.grappling_runtime import (
    apply_personal_grapple_option_command,
    resolve_personal_grapple_check_command,
)
from engine.health_runtime import (
    apply_personal_fatigue_command,
    complete_personal_fatigue_rest_command,
    resolve_personal_unconscious_recovery_command,
)
from engine.tasks import resolve_actor_task_command
from engine.injury_runtime import resolve_personal_natural_healing_command
from engine.medical_runtime import (
    apply_personal_first_aid_command,
    apply_personal_medical_care_command,
    resolve_personal_surgery_command,
)
from engine.mental_healing import resolve_personal_mental_healing_command


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class PersonalCombatRuntimeIntegrationTests(unittest.TestCase):
    def _initialized_combat(self, connection, species_codes=None):
        campaign_id, campaign_public = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Combat Actions','referee')
               RETURNING campaign_id,public_id"""
        ).fetchone()
        actors = []
        for name, controller in (
            ("Player", "player"), ("NPC", "referee"), ("NPC 2", "referee")
        ):
            actor_id, actor_public = connection.execute(
                """INSERT INTO actor_actor
                   (campaign_id,name,controller_reference)
                   VALUES (%s,%s,%s) RETURNING actor_id,public_id""",
                (campaign_id, name, controller),
            ).fetchone()
            connection.execute(
                """INSERT INTO actor_characteristic
                   (actor_id,characteristic_rule_id,maximum_value,current_value)
                   SELECT %s,rule_id,7,7 FROM rule_rule
                   WHERE rule_code IN (
                       'characteristic.dexterity',
                       'characteristic.endurance'
                   )""",
                (actor_id,))
            connection.execute(
                """INSERT INTO actor_skill (actor_id,skill_rule_id,skill_level)
                   SELECT %s,rule_id,0 FROM rule_rule
                   WHERE rule_code='skill.athletics'""", (actor_id,))
            actors.append(str(actor_public))
        if species_codes:
            controllers = ("player", "referee", "referee")
            for index, species_code in enumerate(species_codes):
                if species_code is None:
                    continue
                assign_actor_species_command(
                    connection,
                    initiator_reference=controllers[index],
                    idempotency_key=f"actions-species-{index}",
                    actor_public_id=actors[index],
                    species_code=species_code,
                    assignment_kind="import",
                )
        encounter = create_encounter_command(
            connection, initiator_reference="referee",
            idempotency_key="actions-create",
            campaign_public_id=str(campaign_public),
            encounter_type_code="routine")
        for index, (actor, role, side) in enumerate((
            (actors[0], "player_character", "party"),
            (actors[1], "non_player_character", "opposition"),
            (actors[2], "non_player_character", "opposition"),
        )):
            add_encounter_participant_command(
                connection, initiator_reference="referee",
                idempotency_key=f"actions-add-{index}",
                encounter_public_id=encounter.encounter_public_id,
                actor_public_id=actor, participant_role=role, side_code=side)
        transition_encounter_mode_command(
            connection, initiator_reference="referee",
            idempotency_key="actions-transition",
            encounter_public_id=encounter.encounter_public_id,
            to_mode="personal_combat", reason="NPC attacks.")
        initialize_personal_combat_command(
            connection, initiator_reference="referee",
            idempotency_key="actions-initialize",
            encounter_public_id=encounter.encounter_public_id,
            aware_actor_public_ids=(actors[0],),
            random_source=FixedRandom((2, 3, 3, 4)))
        return encounter.encounter_public_id, actors

    def test_metabolism_modifier_is_separate_in_combat_initiative(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                connection.execute(
                    """INSERT INTO rule_species_trait_assignment
                       (species_rule_id,species_trait_rule_id,
                        assignment_order)
                       SELECT species.species_rule_id,
                              trait.species_trait_rule_id,8
                       FROM rule_species species
                       CROSS JOIN rule_species_trait trait
                       WHERE species.species_code='insectan'
                         AND trait.trait_code='fast-metabolism'""")
                _, actors = self._initialized_combat(
                    connection, ("insectan", "human", "human"))
                state = connection.execute(
                    """SELECT combatant.initiative_base,
                              receipt.species_initiative_modifier
                       FROM enc_personal_combatant combatant
                       JOIN cmd_combat_initialization_combatant receipt
                         ON receipt.actor_id=combatant.actor_id
                       JOIN cmd_combat_initialization_receipt command_receipt
                         ON command_receipt.command_id=receipt.command_id
                        AND command_receipt.encounter_id=
                            combatant.encounter_id
                       JOIN actor_actor actor
                         ON actor.actor_id=combatant.actor_id
                       WHERE actor.public_id=%s""",
                    (actors[0],),
                ).fetchone()
                self.assertEqual(state, (14, 2))

    def test_player_attack_requires_a_held_weapon_when_enforced(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter,actors=self._initialized_combat(connection)
                begin_personal_turn_command(
                    connection,initiator_reference="player",
                    idempotency_key="held-begin",encounter_public_id=encounter,
                    actor_public_id=actors[0])
                arguments=dict(
                    initiator_reference="player",encounter_public_id=encounter,
                    attacker_actor_public_id=actors[0],target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal",require_actor_holding=True)
                with self.assertRaisesRegex(ValueError,"does not hold"):
                    declare_personal_attack_command(
                        connection,idempotency_key="held-rejected",**arguments)
                connection.execute(
                    """INSERT INTO actor_item_holding(actor_id,item_rule_id,quantity)
                       SELECT actor.actor_id,weapon.rule_id,1
                       FROM actor_actor actor CROSS JOIN rule_rule weapon
                       WHERE actor.public_id=%s
                         AND weapon.rule_code='equipment.weapon.dagger'""",
                    (actors[0],))
                with self.assertRaisesRegex(ValueError,"not ready"):
                    declare_personal_attack_command(
                        connection,idempotency_key="held-unready",**arguments)
                connection.execute(
                    """INSERT INTO actor_weapon_state(actor_id,weapon_rule_id,ready)
                       SELECT actor.actor_id,weapon.rule_id,true
                       FROM actor_actor actor CROSS JOIN rule_rule weapon
                       WHERE actor.public_id=%s
                         AND weapon.rule_code='equipment.weapon.dagger'""",
                    (actors[0],))
                declared=declare_personal_attack_command(
                    connection,idempotency_key="held-accepted",**arguments)
                self.assertEqual(declared.item_rule_code,"equipment.weapon.dagger")

    def test_slow_metabolism_penalty_uses_relational_trait_assignment(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                connection.execute(
                    """INSERT INTO rule_species_trait_assignment
                       (species_rule_id,species_trait_rule_id,
                        assignment_order)
                       SELECT species.species_rule_id,
                              trait.species_trait_rule_id,1
                       FROM rule_species species
                       CROSS JOIN rule_species_trait trait
                       WHERE species.species_code='human'
                         AND trait.trait_code='slow-metabolism'""")
                _, actors = self._initialized_combat(
                    connection, ("human", None, None))
                state = connection.execute(
                    """SELECT combatant.initiative_base,
                              receipt.species_initiative_modifier
                       FROM enc_personal_combatant combatant
                       JOIN cmd_combat_initialization_combatant receipt
                         ON receipt.actor_id=combatant.actor_id
                       JOIN cmd_combat_initialization_receipt command_receipt
                         ON command_receipt.command_id=receipt.command_id
                        AND command_receipt.encounter_id=
                            combatant.encounter_id
                       JOIN actor_actor actor
                         ON actor.actor_id=combatant.actor_id
                       WHERE actor.public_id=%s""",
                    (actors[0],),
                ).fetchone()
                self.assertEqual(state, (10, -2))

    def test_species_ground_speed_replaces_standard_move_allowance(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-movement-species",
                    actor_public_id=actors[0],
                    species_code="avian",
                    assignment_kind="import",
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-movement-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                with self.assertRaisesRegex(ValueError, "exceeds"):
                    move_personal_combatant_command(
                        connection, initiator_reference="player",
                        idempotency_key="avian-movement-too-far",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=5,
                    )
                moved = move_personal_combatant_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-movement-legal",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=4.5,
                )
                self.assertEqual(moved.metres_moved, 4.5)

    def test_flyer_takeoff_airborne_movement_and_landing_are_audited(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-species",
                    actor_public_id=actors[0], species_code="avian",
                    assignment_kind="import",
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                spend_personal_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-convert",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    operation="convert_significant",
                )
                with self.assertRaisesRegex(ValueError, "allowance"):
                    move_species_flyer_command(
                        connection, initiator_reference="player",
                        idempotency_key="avian-flight-too-far",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=9.1,
                        altitude_change_metres=1.5,
                    )
                takeoff = move_species_flyer_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-takeoff",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=3,
                    altitude_change_metres=1.5,
                )
                self.assertEqual(
                    (takeoff.operation, takeoff.flight_status,
                     takeoff.altitude_metres, takeoff.minor_actions_after),
                    ("takeoff", "aloft", 1.5, 2),
                )
                with self.assertRaisesRegex(ValueError, "grounded"):
                    move_personal_combatant_command(
                        connection, initiator_reference="player",
                        idempotency_key="avian-ground-move-aloft",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=1.5,
                    )
                replay = move_species_flyer_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-takeoff",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=1,
                    altitude_change_metres=0,
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.altitude_metres, 1.5)
                moved = move_species_flyer_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-move",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=4.5,
                    altitude_change_metres=1.5,
                )
                self.assertEqual(
                    (moved.operation, moved.altitude_metres),
                    ("airborne_movement", 3.0),
                )
                landed = move_species_flyer_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-flight-land",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=3,
                    altitude_change_metres=-3,
                )
                self.assertEqual(
                    (landed.operation, landed.flight_status,
                     landed.altitude_metres, landed.minor_actions_after),
                    ("landing", "grounded", 0.0, 0),
                )
                receipt_count = connection.execute(
                    """SELECT count(*) FROM cmd_species_flyer_move_receipt
                       WHERE actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                       )""",
                    (actors[0],),
                ).fetchone()[0]
                self.assertEqual(receipt_count, 3)

    def test_aloft_flyer_missing_round_movement_transitions_to_falling(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-stall-species",
                    actor_public_id=actors[0], species_code="avian",
                    assignment_kind="import",
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-stall-begin-one",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                move_species_flyer_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-stall-takeoff",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=1.5,
                    altitude_change_metres=1.5,
                )
                complete_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-stall-complete-one",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET acted_this_round=true
                       WHERE encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       )""",
                    (encounter_public,),
                )
                advance_personal_combat_round_command(
                    connection, initiator_reference="referee",
                    idempotency_key="avian-stall-round-two",
                    encounter_public_id=encounter_public,
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-stall-begin-two",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                complete_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="avian-stall-complete-two",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                flight = connection.execute(
                    """SELECT flight_status,altitude_metres
                       FROM enc_personal_combatant
                       WHERE encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       ) AND actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                       )""",
                    (encounter_public, actors[0]),
                ).fetchone()
                self.assertEqual((flight[0], float(flight[1])),
                                 ("falling", 1.5))
                transition = connection.execute(
                    """SELECT transition_reason,status_before,status_after
                       FROM cmd_species_flyer_transition_receipt
                       WHERE actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                       )""",
                    (actors[0],),
                ).fetchone()
                self.assertEqual(
                    transition,
                    ("missed_movement_upkeep", "aloft", "falling"),
                )

    def test_non_flyer_cannot_use_flight_movement(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="non-flyer-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                with self.assertRaisesRegex(ValueError, "not legal"):
                    move_species_flyer_command(
                        connection, initiator_reference="player",
                        idempotency_key="non-flyer-move",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=1.5,
                        altitude_change_metres=1.5,
                    )

    def test_species_natural_weapon_is_actor_bound_and_deals_flat_damage(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="reptilian-natural-weapon-species",
                    actor_public_id=actors[0],
                    species_code="reptilian",
                    assignment_kind="character_creation",
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="natural-weapon-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="natural-weapon-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code=(
                        "equipment.weapon.species-natural-weapon"),
                    attack_profile_code="natural-weapon",
                    range_rule_code="combat.range.personal",
                    characteristic_rule_code="characteristic.dexterity",
                )
                result = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="natural-weapon-resolve",
                    item_rule_code=(
                        "equipment.weapon.species-natural-weapon"),
                    attack_profile_code="natural-weapon",
                    range_rule_code="combat.range.personal",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=(
                        declared.personal_attack_public_id),
                    random_source=FixedRandom((4, 4)),
                )
                self.assertTrue(result.receipt.hit)
                self.assertEqual(result.receipt.damage_dice, ())
                self.assertEqual(result.receipt.weapon_flat_damage_bonus, 1)
                self.assertEqual(result.receipt.raw_damage, 1)

    def test_great_leaper_uses_selected_task_context_and_effect_distance(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                assign_actor_species_command(
                    connection, initiator_reference="player",
                    idempotency_key="insectan-leaper-species",
                    actor_public_id=actors[0],
                    species_code="insectan",
                    assignment_kind="character_creation",
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="great-leap-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                result = resolve_species_great_leap_command(
                    connection, initiator_reference="player",
                    idempotency_key="great-leap-resolve",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    characteristic_rule_code="characteristic.dexterity",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((5, 4)),
                )
                self.assertTrue(result.succeeded)
                self.assertEqual(result.effect, 1)
                self.assertEqual(result.squares_jumped, 5)
                self.assertEqual(result.metres_jumped, 7.5)
                self.assertEqual(result.significant_after, 0)
                replay = resolve_species_great_leap_command(
                    connection, initiator_reference="player",
                    idempotency_key="great-leap-resolve",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    characteristic_rule_code="characteristic.strength",
                    difficulty_rule_code="difficulty.formidable",
                    random_source=FixedRandom((1, 1)),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.dice, (5, 4))

    def test_source_defined_reload_and_attack_consume_ammunition(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.slug-pistol'""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready)
                       SELECT %s,rule_id,true FROM rule_rule
                       WHERE rule_code='equipment.weapon.auto-pistol'""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_item_holding(actor_id,item_rule_id,quantity)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='equipment.weapon.auto-pistol'""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_ammunition_supply
                       (actor_id,ammunition_rule_id,reload_units_available)
                       SELECT %s,rule_id,2 FROM rule_rule
                       WHERE rule_code=
                         'equipment.ammunition.auto-pistol.standard'""",
                    (actor_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="ammo-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                reloaded = advance_weapon_reload_command(
                    connection, initiator_reference="player",
                    idempotency_key="ammo-reload",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    weapon_rule_code="equipment.weapon.auto-pistol",
                    ammunition_rule_code=(
                        "equipment.ammunition.auto-pistol.standard"),
                    require_actor_holding=True,
                )
                self.assertTrue(reloaded.completed)
                self.assertEqual(
                    (reloaded.rounds_loaded_after,
                     reloaded.reload_units_available_after),
                    (15, 1),
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="ammo-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                )
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="ammo-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((4, 4, 4, 4)),
                )
                self.assertEqual(resolved.receipt.skill_modifier, 1)
                rounds = connection.execute(
                    """SELECT rounds_loaded FROM actor_weapon_state
                       WHERE actor_id=%s""",
                    (actor_id,),
                ).fetchone()[0]
                self.assertEqual(rounds, 14)

    def test_grouped_burst_freezes_damage_bonus_and_consumes_full_burst(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.slug-rifle'""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,20
                       FROM rule_rule weapon
                       CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.auto-rifle'
                         AND ammunition.rule_code=
                           'equipment.ammunition.auto-rifle.standard'""",
                    (actor_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="burst-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="burst-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.short",
                    burst_size_rounds=4,
                    burst_option="grouped",
                )
                self.assertEqual(
                    (declared.burst_size_rounds, declared.burst_option,
                     declared.burst_attack_modifier,
                     declared.burst_extra_damage_dice,
                     declared.burst_extra_damage_flat),
                    (4, "grouped", 0, 1, 0),
                )
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="burst-resolve",
                    item_rule_code="equipment.weapon.auto-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6, 6, 1, 2, 3, 4)),
                )
                self.assertEqual(resolved.receipt.burst_extra_damage_dice, 1)
                self.assertEqual(resolved.receipt.rolled_damage, 10)
                state = connection.execute(
                    """SELECT rounds_loaded FROM actor_weapon_state
                       WHERE actor_id=%s""",
                    (actor_id,),
                ).fetchone()[0]
                self.assertEqual(state, 16)

    def test_burst_fire_rejects_weapon_without_published_burst_rate(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,15
                       FROM rule_rule weapon
                       CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.auto-pistol'
                         AND ammunition.rule_code=
                           'equipment.ammunition.auto-pistol.standard'""",
                    (actor_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="no-burst-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                with self.assertRaisesRegex(
                    ValueError, "does not support selected burst"
                ):
                    declare_personal_attack_command(
                        connection, initiator_reference="player",
                        idempotency_key="no-burst-declare",
                        encounter_public_id=encounter_public,
                        attacker_actor_public_id=actors[0],
                        target_actor_public_id=actors[1],
                        item_rule_code="equipment.weapon.auto-pistol",
                        attack_profile_code="pistol",
                        range_rule_code="combat.range.short",
                        burst_size_rounds=4,
                        burst_option="spray",
                    )

    def test_suppression_fire_applies_effect_without_damage_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                attacker_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.slug-rifle'""",
                    (attacker_id,),
                )
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,20
                       FROM rule_rule weapon
                       CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.auto-rifle'
                         AND ammunition.rule_code=
                           'equipment.ammunition.auto-rifle.standard'""",
                    (attacker_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="suppression-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                target_before = connection.execute(
                    """SELECT initiative_current FROM enc_personal_combatant
                       WHERE encounter_id=(
                         SELECT encounter_id FROM enc_encounter
                         WHERE public_id=%s)
                         AND actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                         )""",
                    (encounter_public, actors[1]),
                ).fetchone()[0]
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="suppression-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.short",
                    burst_size_rounds=4,
                    burst_option="spray",
                    suppression_fire=True,
                )
                self.assertTrue(declared.suppression_fire)
                self.assertEqual(declared.suppression_attack_modifier, -2)
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="suppression-resolve",
                    item_rule_code="equipment.weapon.auto-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(resolved.receipt.hit)
                self.assertEqual(resolved.receipt.raw_damage, 0)
                self.assertIsNone(resolved.damage_instance_public_id)
                state = connection.execute(
                    """SELECT weapon.rounds_loaded,target.initiative_current,
                              target.suppression_check_modifier,
                              target.suppression_expires_after_round,
                              target.suppression_action_required
                       FROM actor_weapon_state weapon
                       JOIN actor_actor attacker
                         ON attacker.actor_id=weapon.actor_id
                       JOIN enc_encounter encounter ON encounter.public_id=%s
                       JOIN actor_actor target_actor
                         ON target_actor.public_id=%s
                       JOIN enc_personal_combatant target
                         ON target.encounter_id=encounter.encounter_id
                        AND target.actor_id=target_actor.actor_id
                       JOIN rule_rule weapon_rule
                         ON weapon_rule.rule_id=weapon.weapon_rule_id
                       WHERE attacker.public_id=%s
                         AND weapon_rule.rule_code=
                           'equipment.weapon.auto-rifle'""",
                    (encounter_public, actors[1], actors[0]),
                ).fetchone()
                self.assertEqual(state[0], 12)
                self.assertEqual(state[1], target_before - resolved.receipt.effect)
                self.assertEqual(state[2:], (-1, 2, True))
                suppression_receipt = connection.execute(
                    """SELECT immune,applied,effect,initiative_before,
                              initiative_after,check_modifier_after
                       FROM cmd_personal_suppression_receipt"""
                ).fetchone()
                self.assertEqual(
                    suppression_receipt,
                    (False, True, resolved.receipt.effect, target_before,
                     target_before - resolved.receipt.effect, -1),
                )
                replay = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="suppression-resolve",
                    item_rule_code="equipment.weapon.auto-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.receipt.attack_dice, (6, 6))
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException, "receipts are immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_personal_suppression_receipt
                               SET applied=false"""
                        )
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET minor_actions_remaining=minor_actions_remaining-1
                       WHERE encounter_id=(
                         SELECT encounter_id FROM enc_encounter
                         WHERE public_id=%s)
                         AND actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                         )""",
                    (encounter_public, actors[1]),
                )
                action_required = connection.execute(
                    """SELECT suppression_action_required
                       FROM enc_personal_combatant
                       WHERE encounter_id=(
                         SELECT encounter_id FROM enc_encounter
                         WHERE public_id=%s)
                         AND actor_id=(
                           SELECT actor_id FROM actor_actor WHERE public_id=%s
                         )""",
                    (encounter_public, actors[1]),
                ).fetchone()[0]
                self.assertFalse(action_required)

    def test_panic_fire_consumes_all_rounds_and_uses_agreed_damage_tier(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                attacker_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.slug-pistol'""",
                    (attacker_id,),
                )
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,15
                       FROM rule_rule weapon
                       CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.auto-pistol'
                         AND ammunition.rule_code=
                           'equipment.ammunition.auto-pistol.standard'""",
                    (attacker_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="panic-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="panic-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    panic_fire=True,
                )
                self.assertEqual(
                    (declared.panic_fire, declared.panic_attack_modifier,
                     declared.panic_damage_burst_size_rounds,
                     declared.panic_extra_damage_dice,
                     declared.panic_extra_damage_flat),
                    (True, -2, 10, 2, 0),
                )
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="panic-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6, 6, 1, 2, 3, 4)),
                )
                self.assertTrue(resolved.receipt.hit)
                self.assertEqual(resolved.receipt.panic_extra_damage_dice, 2)
                panic_state = connection.execute(
                    """SELECT weapon.rounds_loaded,
                              receipt.ammunition_consumed,
                              size.rounds_consumed,
                              receipt.extra_damage_dice,
                              receipt.extra_damage_flat
                       FROM actor_weapon_state weapon
                       JOIN rule_rule weapon_rule
                         ON weapon_rule.rule_id=weapon.weapon_rule_id
                       JOIN cmd_personal_panic_fire_receipt receipt ON true
                       LEFT JOIN rule_personal_burst_size size
                         ON size.rule_id=receipt.damage_burst_size_rule_id
                       WHERE weapon.actor_id=%s
                         AND weapon_rule.rule_code=
                           'equipment.weapon.auto-pistol'""",
                    (attacker_id,),
                ).fetchone()
                self.assertEqual(panic_state, (0, 15, 10, 2, 0))
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException, "receipts are immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            """UPDATE cmd_personal_panic_fire_receipt
                               SET ammunition_consumed=14"""
                        )

    def test_shotgun_spread_shares_rolls_and_records_each_target(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                attacker_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.shotgun'""", (attacker_id,))
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,10
                       FROM rule_rule weapon
                       CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.shotgun'
                         AND ammunition.rule_code=
                           'equipment.ammunition.shotgun.flechette-shell'""",
                    (attacker_id,))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="spread-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="spread-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.shotgun",
                    attack_profile_code="shotgun",
                    range_rule_code="combat.range.medium",
                    shotgun_spread=True,
                    shotgun_spread_target_actor_public_ids=(actors[2],))
                self.assertEqual(
                    (declared.shotgun_spread,
                     declared.shotgun_spread_attack_modifier,
                     declared.shotgun_spread_damage_dice,
                     declared.shotgun_spread_target_actor_public_ids),
                    (True, 1, 2, (actors[1], actors[2])))
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="spread-resolve",
                    item_rule_code="equipment.weapon.shotgun",
                    attack_profile_code="shotgun",
                    range_rule_code="combat.range.medium",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    shotgun_spread_armor_rule_codes=(
                        (actors[2], "equipment.armor.jack"),),
                    random_source=FixedRandom((6, 6, 3, 4)))
                self.assertEqual(resolved.receipt.damage_dice, (3, 4))
                target_receipts = connection.execute(
                    """SELECT target_order,is_primary,raw_damage,
                              penetrating_damage
                       FROM cmd_personal_shotgun_spread_target_receipt
                       ORDER BY target_order"""
                ).fetchall()
                self.assertEqual(len(target_receipts), 2)
                self.assertEqual(target_receipts[0][2:], target_receipts[1][2:])
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException, "receipts are immutable"
                ):
                    with connection.transaction():
                        connection.execute(
                            """DELETE FROM
                               cmd_personal_shotgun_spread_target_receipt""")

    def test_psionic_activation_consumes_significant_combat_action(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                for code in (
                    "characteristic.psionic-strength",
                    "characteristic.endurance",
                ):
                    connection.execute(
                        """INSERT INTO actor_characteristic
                           (actor_id,characteristic_rule_id,
                           maximum_value,current_value)
                           SELECT %s,rule_id,5,5 FROM rule_rule
                           WHERE rule_code=%s
                           ON CONFLICT (
                               actor_id,characteristic_rule_id
                           ) DO UPDATE SET maximum_value=5,current_value=5""",
                        (actor_id, code),
                    )
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.psionic-awareness'""",
                    (actor_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-combat-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                result = activate_psionic_power_command(
                    connection, initiator_reference="player",
                    idempotency_key="psi-combat-activate",
                    actor_public_id=actors[0],
                    power_rule_code="psionics.power.suspended-animation",
                    encounter_public_id=encounter_public,
                    random_source=FixedRandom((6, 6, 3)),
                )
                self.assertTrue(result.succeeded)
                actions, psi = connection.execute(
                    """SELECT combatant.significant_actions_remaining,
                              characteristic.current_value
                       FROM enc_personal_combatant combatant
                       JOIN actor_characteristic characteristic
                         ON characteristic.actor_id=combatant.actor_id
                       JOIN rule_rule rule
                         ON rule.rule_id=
                            characteristic.characteristic_rule_id
                       WHERE combatant.encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       )
                         AND combatant.actor_id=%s
                         AND rule.rule_code=
                             'characteristic.psionic-strength'""",
                    (encounter_public, actor_id),
                ).fetchone()
                self.assertEqual((actions, psi), (0, 2))

    def test_mixed_awareness_initializes_round_one_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign_id, campaign_public = connection.execute(
                    """INSERT INTO camp_campaign (name,owner_reference)
                       VALUES ('Combat Runtime','referee')
                       RETURNING campaign_id,public_id"""
                ).fetchone()
                actors = []
                for name, controller in (("Player", "player"), ("NPC", "referee")):
                    actor_id, actor_public = connection.execute(
                        """INSERT INTO actor_actor
                           (campaign_id,name,controller_reference)
                           VALUES (%s,%s,%s) RETURNING actor_id,public_id""",
                        (campaign_id, name, controller),
                    ).fetchone()
                    connection.execute(
                        """INSERT INTO actor_characteristic
                           (actor_id,characteristic_rule_id,
                            maximum_value,current_value)
                           SELECT %s,rule_id,7,7 FROM rule_rule
                           WHERE rule_code='characteristic.dexterity'""",
                        (actor_id,))
                    actors.append(str(actor_public))
                encounter = create_encounter_command(
                    connection, initiator_reference="referee",
                    idempotency_key="combat-create",
                    campaign_public_id=str(campaign_public),
                    encounter_type_code="routine")
                for index, (actor, role, side) in enumerate((
                    (actors[0], "player_character", "party"),
                    (actors[1], "non_player_character", "opposition"),
                )):
                    add_encounter_participant_command(
                        connection, initiator_reference="referee",
                        idempotency_key=f"combat-add-{index}",
                        encounter_public_id=encounter.encounter_public_id,
                        actor_public_id=actor, participant_role=role,
                        side_code=side)
                transition_encounter_mode_command(
                    connection, initiator_reference="referee",
                    idempotency_key="combat-transition",
                    encounter_public_id=encounter.encounter_public_id,
                    to_mode="personal_combat", reason="NPC attacks.")
                initialized = initialize_personal_combat_command(
                    connection, initiator_reference="referee",
                    idempotency_key="combat-initialize",
                    encounter_public_id=encounter.encounter_public_id,
                    aware_actor_public_ids=(actors[0],),
                    random_source=FixedRandom((2, 3)))
                replay = initialize_personal_combat_command(
                    connection, initiator_reference="referee",
                    idempotency_key="combat-initialize",
                    encounter_public_id=encounter.encounter_public_id,
                    aware_actor_public_ids=(),
                    random_source=FixedRandom((6, 6, 6, 6)))
                by_actor = {
                    combatant.actor_public_id: combatant
                    for combatant in initialized.combatants
                }
                self.assertEqual(
                    by_actor[actors[0]].initiative_method, "automatic_12")
                self.assertEqual(by_actor[actors[0]].initiative, 12)
                self.assertEqual(by_actor[actors[1]].initiative_dice, (2, 3))
                self.assertEqual(
                    (by_actor[actors[0]].significant_actions,
                     by_actor[actors[0]].minor_actions), (1, 1))
                self.assertTrue(replay.replayed)
                self.assertEqual(
                    initialized.command_public_id, replay.command_public_id)

    def test_action_conversion_and_reaction_penalties_are_transactional(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                with self.assertRaises(ValueError):
                    begin_personal_turn_command(
                        connection, initiator_reference="referee",
                        idempotency_key="npc-out-of-order",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[1])
                hastened = hasten_personal_combatant_command(
                    connection, initiator_reference="referee",
                    idempotency_key="hasten-npc-one",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[1])
                self.assertEqual(
                    (hastened.initiative_before, hastened.initiative_after),
                    (5, 7))
                begun = begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="begin-player",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                self.assertEqual(begun.initiative, 12)
                with self.assertRaises(ValueError):
                    hasten_personal_combatant_command(
                        connection, initiator_reference="referee",
                        idempotency_key="late-hasten",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[2])
                converted = spend_personal_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="convert-action",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    operation="convert_significant")
                spent = spend_personal_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="spend-minor",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], operation="spend_minor")
                replay = spend_personal_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="spend-minor",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], operation="spend_significant")
                self.assertEqual(
                    (converted.significant_after, converted.minor_after), (0, 3))
                self.assertEqual(
                    (spent.significant_after, spent.minor_after), (0, 2))
                self.assertTrue(replay.replayed)
                complete_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="finish-player-round-one",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                delayed = delay_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="delay-npc-two",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[2])
                self.assertEqual(delayed.initiative_when_delayed, 7)
                begin_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="begin-npc-one",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[1])
                resumed = resume_delayed_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="resume-npc-two",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[2])
                self.assertEqual(resumed.initiative_after, 7)
                self.assertEqual(
                    resumed.interrupted_actor_public_id, actors[1])
                reactions = []
                for index, attacker_index in enumerate((2, 1), 1):
                    declared = declare_personal_attack_command(
                        connection, initiator_reference="referee",
                        idempotency_key=f"declare-attack-{index}",
                        encounter_public_id=encounter_public,
                        attacker_actor_public_id=actors[attacker_index],
                        target_actor_public_id=actors[0],
                        item_rule_code="equipment.weapon.dagger",
                        attack_profile_code="thrown",
                        range_rule_code="combat.range.short",
                        target_has_cover=index == 1)
                    reaction = declare_personal_reaction_command(
                        connection, initiator_reference="player",
                        idempotency_key=f"dodge-{index}",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0],
                        attack_trigger_reference=(
                            declared.personal_attack_public_id),
                        reaction_kind="dodge")
                    reactions.append(reaction)
                    if index == 1:
                        with self.assertRaises(ValueError):
                            declare_personal_reaction_command(
                                connection, initiator_reference="player",
                                idempotency_key="second-dodge-same-attack",
                                encounter_public_id=encounter_public,
                                actor_public_id=actors[0],
                                attack_trigger_reference=(
                                    declared.personal_attack_public_id),
                                reaction_kind="dodge_with_cover")
                    resolved = resolve_personal_attack_command(
                        connection, initiator_reference="referee",
                        idempotency_key=f"resolve-declared-{index}",
                        item_rule_code="equipment.weapon.dagger",
                        attack_profile_code="thrown",
                        range_rule_code="combat.range.short",
                        armor_rule_code="equipment.armor.jack",
                        target_actor_public_id=actors[0],
                        personal_attack_public_id=(
                            declared.personal_attack_public_id),
                        random_source=FixedRandom((5, 4, 4)))
                    self.assertIn(-1, resolved.receipt.circumstance_modifiers)
                    self.assertEqual(resolved.receipt.skill_modifier, 0)
                    self.assertEqual(
                        resolved.receipt.characteristic_modifier, 0)
                    if attacker_index == 1:
                        self.assertEqual(
                            resolved.receipt.circumstance_modifiers.count(-1),
                            2)
                    complete_personal_turn_command(
                        connection, initiator_reference="referee",
                        idempotency_key=f"finish-npc-{index}",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[attacker_index])
                self.assertEqual(
                    [reaction.initiative_timing for reaction in reactions],
                    ["following_round", "following_round"])
                self.assertEqual(
                    reactions[-1].next_round_adjustment_after, -4)
                advanced = advance_personal_combat_round_command(
                    connection, initiator_reference="referee",
                    idempotency_key="advance-round-two",
                    encounter_public_id=encounter_public)
                advanced_by_actor = {
                    combatant.actor_public_id: combatant
                    for combatant in advanced.combatants
                }
                self.assertEqual(
                    (advanced.round_before, advanced.round_after), (1, 2))
                self.assertEqual(
                    advanced_by_actor[actors[0]].initiative_after, 8)
                state = connection.execute(
                    """SELECT significant_actions_remaining,
                              minor_actions_remaining,reactions_this_round,
                              reaction_check_modifier,acted_this_round
                       FROM enc_personal_combatant c
                       JOIN actor_actor a ON a.actor_id=c.actor_id
                       WHERE c.encounter_id=(
                           SELECT encounter_id FROM enc_encounter
                           WHERE public_id=%s
                       ) AND a.public_id=%s""",
                    (encounter_public, actors[0]),
                ).fetchone()
                self.assertEqual(tuple(state), (1, 1, 0, 0, False))

    def test_delayed_turn_may_be_forfeited_for_first_next_round(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                for actor, controller, key in (
                    (actors[0], "player", "carry-player"),
                    (actors[2], "referee", "carry-npc-two"),
                ):
                    begin_personal_turn_command(
                        connection, initiator_reference=controller,
                        idempotency_key=f"begin-{key}",
                        encounter_public_id=encounter_public,
                        actor_public_id=actor)
                    complete_personal_turn_command(
                        connection, initiator_reference=controller,
                        idempotency_key=f"finish-{key}",
                        encounter_public_id=encounter_public,
                        actor_public_id=actor)
                delay_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="carry-delay",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[1])
                forfeited = forfeit_delayed_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="carry-forfeit",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[1])
                self.assertEqual(forfeited.initiative_forfeited, 5)
                advanced = advance_personal_combat_round_command(
                    connection, initiator_reference="referee",
                    idempotency_key="carry-advance",
                    encounter_public_id=encounter_public)
                by_actor = {
                    combatant.actor_public_id: combatant
                    for combatant in advanced.combatants
                }
                self.assertEqual(by_actor[actors[1]].initiative_after, 13)
                begun = begin_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="carry-begin-round-two",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[1])
                self.assertEqual(begun.initiative, 13)

    def test_aim_is_frozen_into_the_declared_attack(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="aim-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                aimed = aim_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="aim-step",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    target_actor_public_id=actors[1])
                self.assertEqual(
                    (aimed.minor_actions_after, aimed.aim_modifier_after),
                    (0, 1))
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="aim-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    target_has_cover=False)
                self.assertEqual(declared.aim_modifier, 1)
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="aim-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=(
                        declared.personal_attack_public_id),
                    random_source=FixedRandom((4, 4, 4)))
                self.assertIn(1, resolved.receipt.circumstance_modifiers)

    def test_stance_improves_stored_cover_and_controls_dodge(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                cover = set_personal_cover_command(
                    connection, initiator_reference="player",
                    idempotency_key="cover-half",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], cover_code="one_half")
                self.assertEqual(cover.cover_after, "one_half")
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="stance-begin-player",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                stance = change_personal_stance_command(
                    connection, initiator_reference="player",
                    idempotency_key="stance-crouch",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], stance_code="crouched")
                self.assertEqual(
                    (stance.stance_after, stance.minor_actions_after),
                    ("crouched", 0))
                complete_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="stance-finish-player",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                begin_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="stance-begin-attacker",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[2])
                declared = declare_personal_attack_command(
                    connection, initiator_reference="referee",
                    idempotency_key="stance-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[2],
                    target_actor_public_id=actors[0],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    target_has_cover=False)
                self.assertTrue(declared.target_has_cover)
                self.assertEqual(declared.cover_modifier, -2)
                declare_personal_reaction_command(
                    connection, initiator_reference="player",
                    idempotency_key="stance-cover-dodge",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    attack_trigger_reference=declared.personal_attack_public_id,
                    reaction_kind="dodge_with_cover")
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="referee",
                    idempotency_key="stance-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[0],
                    personal_attack_public_id=(
                        declared.personal_attack_public_id),
                    random_source=FixedRandom((6, 6, 4)))
                self.assertEqual(
                    resolved.receipt.circumstance_modifiers.count(-2), 2)

    def test_target_movement_modifier_is_derived_from_round_distance(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="move-begin-player",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                spend_personal_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="move-convert",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    operation="convert_significant")
                for index in range(2):
                    move_personal_combatant_command(
                        connection, initiator_reference="player",
                        idempotency_key=f"move-step-{index}",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=6)
                complete_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="move-finish-player",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                begin_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="move-begin-attacker",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[2])
                declared = declare_personal_attack_command(
                    connection, initiator_reference="referee",
                    idempotency_key="move-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[2],
                    target_actor_public_id=actors[0],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short")
                self.assertEqual(declared.target_movement_modifier, -1)

    def test_kill_aim_adds_damage_not_attack_dm(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="kill-aim-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                aimed = aim_personal_attack_for_kill_command(
                    connection, initiator_reference="player",
                    idempotency_key="kill-aim-step",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    target_actor_public_id=actors[1])
                self.assertEqual(aimed.damage_bonus_after, 2)
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="kill-aim-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short")
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="kill-aim-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=(
                        declared.personal_attack_public_id),
                    random_source=FixedRandom((6, 6, 4)))
                self.assertEqual(resolved.receipt.kill_aim_damage_bonus, 2)
                self.assertNotIn(2, resolved.receipt.circumstance_modifiers)

    def test_battlefield_comms_suspend_and_restore_tactics(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT actor.actor_id,rule.rule_id,0
                       FROM actor_actor actor
                       CROSS JOIN rule_rule rule
                       WHERE actor.public_id IN (%s,%s)
                         AND rule.rule_code IN ('skill.tactics','skill.leadership')
                       ON CONFLICT DO NOTHING""", (actors[1], actors[2]))
                linked = set_battlefield_communication_command(
                    connection, initiator_reference="referee",
                    idempotency_key="comms-link",
                    encounter_public_id=encounter_public,
                    commander_actor_public_id=actors[1],
                    member_actor_public_id=actors[2], method_code="radio")
                self.assertTrue(linked.active)
                tactics = apply_personal_initiative_support_command(
                    connection, initiator_reference="referee",
                    idempotency_key="comms-tactics",
                    encounter_public_id=encounter_public,
                    commander_actor_public_id=actors[1],
                    support_code="tactics",
                    characteristic_rule_code="characteristic.dexterity",
                    random_source=FixedRandom((6, 6)))
                self.assertEqual(tactics.applied_bonus, 4)
                self.assertEqual(
                    [(target.communicated,
                      target.initiative_after-target.initiative_before)
                     for target in tactics.targets],
                    [(True, 4), (True, 4)])
                jammed = set_battlefield_communication_command(
                    connection, initiator_reference="referee",
                    idempotency_key="comms-jam",
                    encounter_public_id=encounter_public,
                    commander_actor_public_id=actors[1],
                    member_actor_public_id=actors[2], method_code="radio",
                    jammed=True)
                self.assertFalse(jammed.active)
                self.assertTrue(jammed.tactics_suspended)
                restored = set_battlefield_communication_command(
                    connection, initiator_reference="referee",
                    idempotency_key="comms-restore",
                    encounter_public_id=encounter_public,
                    commander_actor_public_id=actors[1],
                    member_actor_public_id=actors[2], method_code="radio")
                self.assertEqual(
                    restored.initiative, jammed.initiative + tactics.applied_bonus)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="comms-player-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                complete_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="comms-player-complete",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                begin_personal_turn_command(
                    connection, initiator_reference="referee",
                    idempotency_key="comms-leader-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[2])
                leadership = apply_personal_initiative_support_command(
                    connection, initiator_reference="referee",
                    idempotency_key="comms-leadership",
                    encounter_public_id=encounter_public,
                    commander_actor_public_id=actors[2],
                    target_actor_public_id=actors[1],
                    support_code="leadership",
                    characteristic_rule_code="characteristic.dexterity",
                    random_source=FixedRandom((6, 6)))
                self.assertEqual(leadership.applied_bonus, 4)
                self.assertEqual(
                    leadership.targets[0].initiative_after,
                    leadership.targets[0].initiative_before + 4)

    def test_battlefield_sensor_avoids_named_environmental_penalties(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id, campaign_id = connection.execute(
                    """SELECT actor_id,campaign_id FROM actor_actor
                       WHERE public_id=%s""", (actors[0],)).fetchone()
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,1 FROM rule_rule
                       WHERE rule_code='skill.energy-pistol'""", (actor_id,))
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,10
                       FROM rule_rule weapon CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.laser-pistol'
                         AND ammunition.rule_code=
                           'equipment.ammunition.laser-pistol.power-pack'""",
                    (actor_id,))
                connection.execute(
                    """INSERT INTO actor_personal_battlefield_sensor
                       (actor_id,campaign_id,sensor_rule_id)
                       SELECT %s,%s,rule_id
                       FROM rule_personal_battlefield_sensor
                       WHERE sensor_code='light-intensification'""",
                    (actor_id, campaign_id))
                conditions = set_personal_battlefield_conditions_command(
                    connection, initiator_reference="referee",
                    idempotency_key="conditions-set",
                    encounter_public_id=encounter_public,
                    light_code="complete-darkness",
                    obscurant_code="thick-smoke",
                    extreme_weather=True, expected_version=0)
                self.assertEqual(conditions.concurrency_version, 1)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="conditions-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="conditions-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.laser-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    battlefield_sensor_code="light-intensification")
                snapshot = connection.execute(
                    """SELECT battlefield_light_code,
                              battlefield_obscurant_code,
                              battlefield_extreme_weather,
                              environmental_attack_modifier
                       FROM enc_personal_attack WHERE public_id=%s""",
                    (declared.personal_attack_public_id,)).fetchone()
                self.assertEqual(
                    snapshot,
                    ("complete-darkness", "thick-smoke", True, -5))
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="conditions-resolve",
                    item_rule_code="equipment.weapon.laser-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6, 6, 3, 3, 3, 3)))
                self.assertIn(-5, resolved.receipt.circumstance_modifiers)

    def test_blind_fire_discards_highest_and_selects_success_target(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],)).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,4 FROM rule_rule
                       WHERE rule_code='skill.slug-pistol'""", (actor_id,))
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,10
                       FROM rule_rule weapon CROSS JOIN rule_rule ammunition
                       WHERE weapon.rule_code='equipment.weapon.auto-pistol'
                         AND ammunition.rule_code=
                           'equipment.ammunition.auto-pistol.standard'""",
                    (actor_id,))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="blind-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="blind-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    blind_fire=True,
                    blind_fire_eligible_actor_public_ids=(
                        actors[1], actors[2]))
                self.assertTrue(declared.blind_fire)
                self.assertEqual(
                    declared.blind_fire_eligible_actor_public_ids,
                    (actors[1], actors[2]))
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="blind-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    blind_fire_armor_rule_codes=(
                        (actors[1], "equipment.armor.jack"),
                        (actors[2], "equipment.armor.jack")),
                    random_source=FixedRandom((6, 6, 6, 2, 3, 3, 3)))
                self.assertTrue(resolved.receipt.hit)
                self.assertEqual(resolved.receipt.skill_modifier, 0)
                self.assertEqual(resolved.receipt.attack_dice, (6, 6))
                self.assertEqual(connection.execute(
                    """SELECT count(*) FROM cmd_random_draw
                       WHERE draw_group='attack'""").fetchone()[0], 3)
                blind = connection.execute(
                    """SELECT receipt.discarded_attack_die,
                              receipt.eligible_target_count,
                              receipt.selection_draw,actor.public_id
                       FROM cmd_personal_blind_fire_receipt receipt
                       JOIN actor_actor actor
                         ON actor.actor_id=receipt.selected_target_actor_id"""
                ).fetchone()
                self.assertEqual(
                    (blind[0], blind[1], blind[2], str(blind[3])),
                    (6, 2, 2, actors[2]))

    def test_explosion_uses_shared_damage_and_independent_reactions(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                connection.execute(
                    """UPDATE enc_personal_combatant SET aware_at_start=true
                       WHERE encounter_id=(
                         SELECT encounter_id FROM enc_encounter
                          WHERE public_id=%s)""",
                    (encounter_public,),
                )
                declared = declare_personal_explosion_command(
                    connection, initiator_reference="referee",
                    idempotency_key="explosion-declare",
                    encounter_public_id=encounter_public,
                    source_reference="grenade-impact-1",
                    damage_dice=3, damage_die_sides=6,
                    targets=tuple(
                        (actor, "equipment.armor.jack") for actor in actors),
                )
                self.assertEqual(declared.status, "awaiting_reactions")
                self.assertEqual(len(declared.targets), 3)
                declare_personal_explosion_reaction_command(
                    connection, initiator_reference="player",
                    idempotency_key="explosion-dive",
                    explosion_public_id=declared.explosion_public_id,
                    actor_public_id=actors[0], reaction_kind="dive",
                )
                declare_personal_explosion_reaction_command(
                    connection, initiator_reference="referee",
                    idempotency_key="explosion-dodge",
                    explosion_public_id=declared.explosion_public_id,
                    actor_public_id=actors[1], reaction_kind="dodge",
                )
                declare_personal_explosion_reaction_command(
                    connection, initiator_reference="referee",
                    idempotency_key="explosion-none",
                    explosion_public_id=declared.explosion_public_id,
                    actor_public_id=actors[2], reaction_kind="none",
                )
                resolved = resolve_personal_explosion_command(
                    connection, initiator_reference="referee",
                    idempotency_key="explosion-resolve",
                    explosion_public_id=declared.explosion_public_id,
                    random_source=FixedRandom((6, 5, 4, 4)),
                )
                self.assertEqual(resolved.shared_rolled_damage, 15)
                self.assertEqual(
                    tuple(
                        (target.reaction_kind, target.dodge_reduction,
                         target.damage_after_reaction,
                         target.penetrating_damage)
                        for target in resolved.targets),
                    (("dive", 0, 7, 4),
                     ("dodge", 4, 11, 8),
                     ("none", 0, 15, 12)),
                )
                dive_state = connection.execute(
                    """SELECT stance.rule_code,
                              combatant.significant_actions_remaining,
                              combatant.significant_action_losses_pending
                         FROM enc_personal_combatant combatant
                         JOIN rule_rule stance
                           ON stance.rule_id=combatant.stance_rule_id
                         JOIN actor_actor actor
                           ON actor.actor_id=combatant.actor_id
                        WHERE actor.public_id=%s""",
                    (actors[0],),
                ).fetchone()
                self.assertEqual(
                    dive_state, ("combat.stance.prone", 0, 0))
                self.assertEqual(connection.execute(
                    """SELECT count(DISTINCT shared_rolled_damage)
                         FROM cmd_personal_explosion_resolution_receipt"""
                ).fetchone()[0], 1)
                self.assertTrue(all(
                    target.damage_instance_public_id
                    for target in resolved.targets))

    def test_extreme_range_is_referee_authorized_and_halves_energy_damage(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,3 FROM rule_rule
                        WHERE rule_code='skill.energy-rifle'""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,weapon.rule_id,true,ammunition.rule_id,100
                         FROM rule_rule weapon CROSS JOIN rule_rule ammunition
                        WHERE weapon.rule_code='equipment.weapon.laser-rifle'
                          AND ammunition.rule_code=
                            'equipment.ammunition.laser-rifle.power-pack'""",
                    (actor_id,),
                )
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="extreme-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                aim_personal_attack_for_kill_command(
                    connection, initiator_reference="player",
                    idempotency_key="extreme-kill-aim",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                )
                authorization = authorize_extreme_range_command(
                    connection, initiator_reference="referee",
                    idempotency_key="extreme-authorize",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.laser-rifle",
                    attack_profile_code="rifle",
                    rest_reference="tripod",
                    line_of_sight=True,
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="extreme-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.laser-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.distant",
                    extreme_range_authorization_public_id=
                        authorization.authorization_public_id,
                )
                self.assertTrue(declared.extreme_range)
                self.assertEqual(declared.extreme_range_rest_reference, "tripod")
                self.assertEqual(declared.extreme_range_attack_modifier, -2)
                self.assertTrue(declared.extreme_range_energy_weapon)
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="extreme-resolve",
                    item_rule_code="equipment.weapon.laser-rifle",
                    attack_profile_code="rifle",
                    range_rule_code="combat.range.distant",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6, 6, 2, 1, 1, 1, 1)),
                )
                self.assertEqual(resolved.receipt.kill_aim_damage_bonus, 2)
                self.assertEqual(resolved.receipt.raw_damage, 5)
                self.assertEqual(resolved.receipt.penetrating_damage, 2)
                receipt = connection.execute(
                    """SELECT energy_reduction_applied,
                              damage_before_energy_reduction,
                              damage_after_energy_reduction
                         FROM cmd_personal_extreme_range_receipt"""
                ).fetchone()
                self.assertEqual(receipt, (True, 9, 5))

    def test_zero_gravity_caps_skill_and_applies_recoil(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],)).fetchone()[0]
                for code, level in (("skill.slug-pistol", 2), ("skill.zero-g", 0)):
                    connection.execute(
                        """INSERT INTO actor_skill
                           (actor_id,skill_rule_id,skill_level)
                           SELECT %s,rule_id,%s FROM rule_rule
                            WHERE rule_code=%s""", (actor_id,level,code))
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,w.rule_id,true,a.rule_id,10
                       FROM rule_rule w CROSS JOIN rule_rule a
                       WHERE w.rule_code='equipment.weapon.auto-pistol'
                         AND a.rule_code=
                           'equipment.ammunition.auto-pistol.standard'""",
                    (actor_id,))
                set_personal_battlefield_conditions_command(
                    connection,initiator_reference="referee",
                    idempotency_key="zero-gravity-state",
                    encounter_public_id=encounter_public,light_code="normal",
                    obscurant_code="none",extreme_weather=False,
                    expected_version=0,gravity_code="zero-gravity")
                begin_personal_turn_command(
                    connection,initiator_reference="player",
                    idempotency_key="zero-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                declared=declare_personal_attack_command(
                    connection,initiator_reference="player",
                    idempotency_key="zero-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short")
                resolve_personal_attack_command(
                    connection,initiator_reference="player",
                    idempotency_key="zero-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6,6,3,3,3)))
                receipt=connection.execute(
                    """SELECT weapon_skill_level,zero_g_trained,
                              zero_g_skill_level,effective_skill_level,
                              weapon_has_recoil,recoil_modifier
                       FROM cmd_personal_zero_gravity_receipt""").fetchone()
                self.assertEqual(receipt,(2,True,0,0,True,-2))

    def test_zero_gravity_without_training_uses_untrained_modifier(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public,actors=self._initialized_combat(connection)
                actor_id=connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],)).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       SELECT %s,rule_id,2 FROM rule_rule
                       WHERE rule_code='skill.slug-pistol'""",(actor_id,))
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,w.rule_id,true,a.rule_id,10
                       FROM rule_rule w CROSS JOIN rule_rule a
                       WHERE w.rule_code='equipment.weapon.auto-pistol'
                         AND a.rule_code=
                           'equipment.ammunition.auto-pistol.standard'""",
                    (actor_id,))
                set_personal_battlefield_conditions_command(
                    connection,initiator_reference="referee",
                    idempotency_key="zero-untrained-state",
                    encounter_public_id=encounter_public,light_code="normal",
                    obscurant_code="none",extreme_weather=False,
                    expected_version=0,gravity_code="zero-gravity")
                begin_personal_turn_command(
                    connection,initiator_reference="player",
                    idempotency_key="zero-untrained-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                declared=declare_personal_attack_command(
                    connection,initiator_reference="player",
                    idempotency_key="zero-untrained-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short")
                resolve_personal_attack_command(
                    connection,initiator_reference="player",
                    idempotency_key="zero-untrained-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6,6)))
                receipt=connection.execute(
                    """SELECT zero_g_trained,zero_g_skill_level,
                              effective_skill_level,recoil_modifier
                       FROM cmd_personal_zero_gravity_receipt""").fetchone()
                self.assertEqual(receipt,(False,None,-3,-2))

    def test_firing_into_combat_redirects_to_nearest_with_original_effect(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    "SELECT actor_id FROM actor_actor WHERE public_id=%s",
                    (actors[0],)).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       SELECT %s,rule_id,0 FROM rule_rule
                       WHERE rule_code='skill.slug-pistol'""", (actor_id,))
                connection.execute(
                    """INSERT INTO actor_weapon_state
                       (actor_id,weapon_rule_id,ready,
                        loaded_ammunition_rule_id,rounds_loaded)
                       SELECT %s,w.rule_id,true,a.rule_id,10
                       FROM rule_rule w CROSS JOIN rule_rule a
                       WHERE w.rule_code='equipment.weapon.auto-pistol'
                         AND a.rule_code=
                           'equipment.ammunition.auto-pistol.standard'""",
                    (actor_id,))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="combat-fire-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                aim_personal_attack_for_kill_command(
                    connection, initiator_reference="player",
                    idempotency_key="combat-fire-kill-aim",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    target_actor_public_id=actors[1])
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="combat-fire-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    firing_into_combat_targets=((actors[2], 1),))
                self.assertTrue(declared.firing_into_combat)
                self.assertEqual(
                    declared.firing_into_combat_actor_public_ids, (actors[2],))
                resolved = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="combat-fire-resolve",
                    item_rule_code="equipment.weapon.auto-pistol",
                    attack_profile_code="pistol",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    firing_into_combat_armor_rule_codes=(
                        (actors[2], "equipment.armor.jack"),),
                    random_source=FixedRandom((1, 1, 4, 6, 6)))
                self.assertTrue(resolved.receipt.hit)
                self.assertEqual(resolved.receipt.effect, -8)
                self.assertEqual(resolved.receipt.kill_aim_damage_bonus, 0)
                self.assertEqual(resolved.receipt.raw_damage, 4)
                self.assertEqual(resolved.receipt.penetrating_damage, 1)
                receipt = connection.execute(
                    """SELECT original_attack_hit,scatter_roll,redirected,
                              selected.public_id,original_effect,
                              kill_aim_damage_excluded
                       FROM cmd_personal_firing_into_combat_receipt combat
                       JOIN actor_actor selected
                         ON selected.actor_id=combat.selected_target_actor_id"""
                ).fetchone()
                self.assertEqual(
                    (receipt[0], receipt[1], receipt[2], str(receipt[3]),
                     receipt[4], receipt[5]),
                    (False, 4, True, actors[2], -8, 2))
                damage_target = connection.execute(
                    """SELECT target.public_id
                       FROM health_damage_instance damage
                       JOIN actor_actor target
                         ON target.actor_id=damage.target_actor_id
                       WHERE damage.attack_command_id=(
                         SELECT command_id
                         FROM cmd_personal_firing_into_combat_receipt)"""
                ).fetchone()[0]
                self.assertEqual(str(damage_target), actors[2])

    def test_thrown_weapon_miss_freezes_target_and_records_polar_scatter(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="thrown-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="thrown-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    thrown_target_point_reference="cargo-crate-north-corner",
                )
                result = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="thrown-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="thrown",
                    range_rule_code="combat.range.short",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((3, 3, 123)),
                )
                self.assertFalse(result.receipt.hit)
                receipt = connection.execute(
                    """SELECT delivery_type,attack_hit,original_effect,
                              target_point_reference,
                              scatter_direction_draw,
                              scatter_bearing_degrees,
                              scatter_distance_metres,
                              payload_delivery_required,
                              direct_damage_permitted
                       FROM cmd_personal_thrown_weapon_receipt"""
                ).fetchone()
                self.assertEqual(
                    receipt,
                    (
                        "impact", False, -4, "cargo-crate-north-corner",
                        123, 122, 2, False, False,
                    ),
                )
                draw = connection.execute(
                    """SELECT draw_order,die_sides,result
                       FROM cmd_random_draw
                       WHERE draw_group='thrown_scatter_direction'"""
                ).fetchone()
                self.assertEqual(draw, (1, 360, 123))
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "Thrown-weapon delivery history is immutable",
                ):
                    connection.execute(
                        """UPDATE cmd_personal_thrown_weapon_receipt
                           SET scatter_distance_metres=3"""
                    )

    def test_fatigue_penalty_repeated_exposure_recovery_and_rest(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                fatigue = apply_personal_fatigue_command(
                    connection, initiator_reference="player",
                    idempotency_key="fatigue-first",
                    actor_public_id=actors[0],
                )
                self.assertEqual(fatigue.check_modifier, -2)
                self.assertEqual(fatigue.rest_required_hours, 3)
                self.assertFalse(fatigue.became_unconscious)
                task = resolve_actor_task_command(
                    connection, initiator_reference="player",
                    idempotency_key="fatigue-task",
                    actor_public_id=actors[0],
                    characteristic_rule_code="characteristic.dexterity",
                    skill_rule_code="skill.athletics",
                    difficulty_rule_code="difficulty.average",
                    random_source=FixedRandom((4, 4)),
                )
                self.assertEqual(task.circumstance_modifier, 0)
                self.assertEqual(task.fatigue_modifier, -2)
                self.assertEqual(task.fatigue_modifier, -2)
                self.assertEqual(task.total, 6)
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="fatigue-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="fatigue-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal",
                )
                self.assertEqual(declared.fatigue_attack_modifier, -2)
                attack = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="fatigue-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((4, 4)),
                )
                self.assertIn(-2, attack.receipt.circumstance_modifiers)
                apply_personal_fatigue_command(
                    connection, initiator_reference="referee",
                    idempotency_key="npc-fatigue-first",
                    actor_public_id=actors[1],
                )
                repeated = apply_personal_fatigue_command(
                    connection, initiator_reference="referee",
                    idempotency_key="npc-fatigue-second",
                    actor_public_id=actors[1],
                )
                self.assertTrue(repeated.became_unconscious)
                failed = resolve_personal_unconscious_recovery_command(
                    connection, initiator_reference="referee",
                    idempotency_key="npc-recovery-failed",
                    actor_public_id=actors[1], minutes_elapsed=1,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertFalse(failed.succeeded)
                self.assertEqual(failed.prior_failure_modifier, 0)
                recovered = resolve_personal_unconscious_recovery_command(
                    connection, initiator_reference="referee",
                    idempotency_key="npc-recovery-succeeded",
                    actor_public_id=actors[1], minutes_elapsed=2,
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(recovered.succeeded)
                self.assertEqual(recovered.prior_failure_modifier, 1)
                self.assertTrue(recovered.remains_fatigued)
                rested = complete_personal_fatigue_rest_command(
                    connection, initiator_reference="referee",
                    idempotency_key="npc-fatigue-rest",
                    actor_public_id=actors[1], completed_hours=3,
                )
                self.assertTrue(rested.fatigue_cleared)
                state = connection.execute(
                    """SELECT fatigued,unconscious,condition_version
                       FROM actor_personal_condition
                       JOIN actor_actor USING (actor_id)
                       WHERE public_id=%s""", (actors[1],)).fetchone()
                self.assertEqual(state, (False, False, 6))
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "Personal-condition history is immutable",
                ):
                    connection.execute(
                        """UPDATE cmd_personal_fatigue_receipt
                           SET rest_required_hours=4"""
                    )

    def test_serious_wound_restrictions_and_signed_natural_healing(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_ids = dict(connection.execute(
                    """SELECT public_id::text,actor_id FROM actor_actor
                       WHERE public_id=ANY(%s::uuid[])""",
                    (actors,)).fetchall())
                for actor in actors[:2]:
                    connection.execute(
                        """INSERT INTO actor_characteristic
                           (actor_id,characteristic_rule_id,
                            maximum_value,current_value)
                           SELECT %s,rule_id,7,7 FROM rule_rule
                           WHERE rule_code='characteristic.strength'""",
                        (actor_ids[actor],))
                connection.execute(
                    """UPDATE actor_characteristic state
                       SET current_value=5
                       FROM rule_rule rule
                       WHERE state.characteristic_rule_id=rule.rule_id
                         AND state.actor_id=%s
                         AND rule.rule_code IN (
                           'characteristic.strength',
                           'characteristic.dexterity',
                           'characteristic.endurance')""",
                    (actor_ids[actors[0]],))
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET seriously_wounded=true,
                           minor_actions_remaining=0
                       WHERE actor_id=%s""", (actor_ids[actors[0]],))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="serious-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                spend_personal_action_command(
                    connection, initiator_reference="player",
                    idempotency_key="serious-convert",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                    operation="convert_significant",
                )
                moved = move_personal_combatant_command(
                    connection, initiator_reference="player",
                    idempotency_key="serious-move",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0], metres=1.5,
                )
                self.assertEqual(moved.round_metres_after, 1.5)
                with self.assertRaisesRegex(
                    ValueError, "exceeds the source allowance"
                ):
                    move_personal_combatant_command(
                        connection, initiator_reference="player",
                        idempotency_key="serious-move-too-far",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=0.5,
                    )
                degraded = resolve_personal_natural_healing_command(
                    connection, initiator_reference="player",
                    idempotency_key="serious-natural-degradation",
                    actor_public_id=actors[0], lifestyle="full_rest",
                    allocations=(("characteristic.strength", 1),),
                )
                self.assertEqual(degraded.injury_status_before,
                                 "seriously_wounded")
                self.assertEqual(degraded.signed_points, -1)
                self.assertEqual(
                    degraded.allocations,
                    (("characteristic.strength", -1, 5, 4),))
                with self.assertRaisesRegex(
                    ValueError, "already resolved"
                ):
                    resolve_personal_natural_healing_command(
                        connection, initiator_reference="player",
                        idempotency_key="serious-duplicate-day",
                        actor_public_id=actors[0], lifestyle="full_rest",
                        allocations=(("characteristic.strength", 1),),
                    )
                connection.execute(
                    """UPDATE actor_characteristic state SET current_value=5
                       FROM rule_rule rule
                       WHERE state.characteristic_rule_id=rule.rule_id
                         AND state.actor_id=%s
                         AND rule.rule_code='characteristic.dexterity'""",
                    (actor_ids[actors[1]],))
                healed = resolve_personal_natural_healing_command(
                    connection, initiator_reference="referee",
                    idempotency_key="wounded-natural-healing",
                    actor_public_id=actors[1], lifestyle="full_rest",
                    allocations=(("characteristic.dexterity", 2),),
                    random_source=FixedRandom((2,)),
                )
                self.assertEqual(healed.healing_die_result, 2)
                self.assertEqual(healed.signed_points, 2)
                self.assertEqual(healed.injury_status_after, "uninjured")
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "Natural-healing history is immutable",
                ):
                    connection.execute(
                        """UPDATE cmd_personal_natural_healing_receipt
                           SET lifestyle='active'""")

    def test_daily_mental_healing_excludes_psionic_strength(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _encounter_public, actors = self._initialized_combat(connection)
                actor_id = connection.execute(
                    """SELECT actor_id FROM actor_actor WHERE public_id=%s""",
                    (actors[0],)).fetchone()[0]
                for code, current in (
                    ("characteristic.intelligence", 5),
                    ("characteristic.education", 6),
                    ("characteristic.psionic-strength", 1),
                ):
                    connection.execute(
                        """INSERT INTO actor_characteristic
                           (actor_id,characteristic_rule_id,
                            maximum_value,current_value)
                           SELECT %s,rule_id,7,%s FROM rule_rule
                           WHERE rule_code=%s""",
                        (actor_id, current, code))
                result = resolve_personal_mental_healing_command(
                    connection, initiator_reference="player",
                    idempotency_key="mental-healing-day",
                    actor_public_id=actors[0],
                )
                self.assertEqual(
                    result.allocations,
                    (
                        ("characteristic.intelligence", 1, 5, 6),
                        ("characteristic.education", 1, 6, 7),
                    ))
                psionic = connection.execute(
                    """SELECT state.current_value
                       FROM actor_characteristic state
                       JOIN rule_rule rule
                         ON rule.rule_id=state.characteristic_rule_id
                       WHERE state.actor_id=%s
                         AND rule.rule_code=
                             'characteristic.psionic-strength'""",
                    (actor_id,)).fetchone()[0]
                self.assertEqual(psionic, 1)
                replay = resolve_personal_mental_healing_command(
                    connection, initiator_reference="player",
                    idempotency_key="mental-healing-day",
                    actor_public_id=actors[0],
                )
                self.assertTrue(replay.replayed)
                with self.assertRaisesRegex(ValueError, "already resolved"):
                    resolve_personal_mental_healing_command(
                        connection, initiator_reference="player",
                        idempotency_key="mental-healing-second-command",
                        actor_public_id=actors[0],
                    )
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "Mental-healing history is immutable",
                ):
                    connection.execute(
                        """UPDATE cmd_personal_mental_healing_receipt
                           SET applied_point_count=1""")

    def test_first_aid_failed_surgery_and_even_daily_medical_care(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_ids = dict(connection.execute(
                    """SELECT public_id::text,actor_id FROM actor_actor
                       WHERE public_id=ANY(%s::uuid[])""",
                    (actors,)).fetchall())
                for actor in actors:
                    connection.execute(
                        """INSERT INTO actor_characteristic
                           (actor_id,characteristic_rule_id,
                            maximum_value,current_value)
                           SELECT %s,rule_id,7,7 FROM rule_rule
                           WHERE rule_code='characteristic.strength'""",
                        (actor_ids[actor],))
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       SELECT %s,rule_id,2 FROM rule_rule
                       WHERE rule_code='skill.medicine'""",
                    (actor_ids[actors[2]],))
                campaign_id = connection.execute(
                    """SELECT campaign_id FROM actor_actor
                       WHERE actor_id=%s""",
                    (actor_ids[actors[1]],)).fetchone()[0]
                facility_public = connection.execute(
                    """INSERT INTO health_medical_facility
                       (campaign_id,facility_reference,facility_type)
                       VALUES (%s,'Port Sickbay','sickbay')
                       RETURNING public_id""", (campaign_id,)).fetchone()[0]
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-attack-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0],
                )
                declared = declare_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-attack-declare",
                    encounter_public_id=encounter_public,
                    attacker_actor_public_id=actors[0],
                    target_actor_public_id=actors[1],
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal",
                )
                attack = resolve_personal_attack_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-attack-resolve",
                    item_rule_code="equipment.weapon.dagger",
                    attack_profile_code="close-quarters",
                    range_rule_code="combat.range.personal",
                    armor_rule_code="equipment.armor.jack",
                    target_actor_public_id=actors[1],
                    personal_attack_public_id=declared.personal_attack_public_id,
                    random_source=FixedRandom((6, 6, 3)),
                )
                endurance_damage = min(
                    7, attack.receipt.penetrating_damage)
                strength_damage = (
                    attack.receipt.penetrating_damage - endurance_damage)
                damage_allocations = (
                    (("characteristic.endurance", endurance_damage),)
                    + ((("characteristic.strength", strength_damage),)
                       if strength_damage else ())
                )
                damage = apply_personal_damage_command(
                    connection, initiator_reference="referee",
                    idempotency_key="medical-damage-apply",
                    damage_instance_public_id=attack.damage_instance_public_id,
                    allocations=damage_allocations,
                )
                first_aid = apply_personal_first_aid_command(
                    connection, initiator_reference="referee",
                    idempotency_key="medical-first-aid",
                    patient_actor_public_id=actors[1],
                    doctor_actor_public_id=actors[2],
                    damage_instance_public_id=damage.damage_instance_public_id,
                    allocations=damage_allocations,
                    random_source=FixedRandom((6, 6)),
                )
                self.assertEqual(first_aid.effect, 6)
                self.assertEqual(first_aid.signed_points, 12)
                self.assertEqual(first_aid.injury_status_after, "uninjured")
                connection.execute(
                    """UPDATE actor_characteristic state SET current_value=5
                       FROM rule_rule rule
                       WHERE state.characteristic_rule_id=rule.rule_id
                         AND state.actor_id=%s
                         AND rule.rule_code=ANY(%s)""",
                    (actor_ids[actors[1]], list((
                        "characteristic.strength",
                        "characteristic.dexterity",
                        "characteristic.endurance",
                    ))))
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET seriously_wounded=true,
                           minor_actions_remaining=0
                       WHERE actor_id=%s""", (actor_ids[actors[1]],))
                surgery = resolve_personal_surgery_command(
                    connection, initiator_reference="referee",
                    idempotency_key="medical-surgery",
                    patient_actor_public_id=actors[1],
                    doctor_actor_public_id=actors[2],
                    first_aid_command_public_id=first_aid.command_public_id,
                    medical_facility_public_id=str(facility_public),
                    allocations=(("characteristic.strength", 4),),
                    random_source=FixedRandom((1, 1)),
                )
                self.assertEqual(surgery.effect, -4)
                self.assertEqual(surgery.signed_points, -4)
                self.assertEqual(
                    surgery.allocations,
                    (("characteristic.strength", -4, 5, 1),))
                connection.execute(
                    """UPDATE actor_characteristic state SET current_value=7
                       FROM rule_rule rule
                       WHERE state.characteristic_rule_id=rule.rule_id
                         AND state.actor_id=%s
                         AND rule.rule_code='characteristic.dexterity'""",
                    (actor_ids[actors[1]],))
                connection.execute(
                    """UPDATE enc_personal_combatant
                       SET seriously_wounded=false
                       WHERE actor_id=%s""", (actor_ids[actors[1]],))
                care = apply_personal_medical_care_command(
                    connection, initiator_reference="referee",
                    idempotency_key="medical-daily-care",
                    patient_actor_public_id=actors[1],
                    doctor_actor_public_id=actors[2],
                    medical_facility_public_id=str(facility_public),
                    allocations=(
                        ("characteristic.strength", 2),
                        ("characteristic.endurance", 1),
                    ),
                )
                self.assertEqual(care.signed_points, 3)
                self.assertEqual(
                    [item[1] for item in care.allocations], [2, 1])
                with self.assertRaisesRegex(
                    psycopg.errors.RaiseException,
                    "Medical-treatment history is immutable",
                ):
                    connection.execute(
                        """UPDATE cmd_personal_medical_treatment_receipt
                           SET signed_points=0""")

    def test_grapple_opposed_check_damage_and_movement_lock(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_rows = connection.execute(
                    """SELECT actor_id,public_id FROM actor_actor
                       WHERE public_id IN (%s,%s)""",
                    (actors[0], actors[1])).fetchall()
                actor_ids = {str(public_id): actor_id
                             for actor_id, public_id in actor_rows}
                for actor_public, level in ((actors[0], 1), (actors[1], 0)):
                    connection.execute(
                        """INSERT INTO actor_skill
                           SELECT %s,rule_id,%s FROM rule_rule
                           WHERE rule_code='skill.natural-weapons'""",
                        (actor_ids[actor_public], level))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="grapple-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                checked = resolve_personal_grapple_check_command(
                    connection, initiator_reference="player",
                    idempotency_key="grapple-check",
                    encounter_public_id=encounter_public,
                    challenger_actor_public_id=actors[0],
                    opponent_actor_public_id=actors[1],
                    challenger_characteristic_rule_code=
                        "characteristic.dexterity",
                    opponent_characteristic_rule_code=
                        "characteristic.dexterity",
                    personal_range_confirmed=True,
                    random_source=FixedRandom((6, 6, 1, 1)))
                self.assertEqual(checked.winner_actor_public_id, actors[0])
                self.assertEqual(checked.effect, 11)
                self.assertEqual(checked.grapple_status, "pending_option")
                applied = apply_personal_grapple_option_command(
                    connection, initiator_reference="player",
                    idempotency_key="grapple-damage",
                    grapple_public_id=checked.grapple_public_id,
                    option_code="damage", continue_grapple=True)
                self.assertEqual(applied.raw_damage, 13)
                self.assertEqual(applied.grapple_status, "active")
                self.assertIsNotNone(applied.damage_instance_public_id)
                with self.assertRaisesRegex(ValueError, "cannot move"):
                    move_personal_combatant_command(
                        connection, initiator_reference="player",
                        idempotency_key="grapple-illegal-move",
                        encounter_public_id=encounter_public,
                        actor_public_id=actors[0], metres=1)
                receipt = connection.execute(
                    """SELECT check_receipt.challenger_total,
                              check_receipt.opponent_total,
                              option_receipt.effect,
                              option_receipt.raw_damage,
                              count(active.actor_id)
                       FROM cmd_personal_grapple_check_receipt check_receipt
                       JOIN cmd_personal_grapple_option_receipt option_receipt
                         ON option_receipt.check_command_id=
                            check_receipt.command_id
                       JOIN enc_personal_grapple_active_actor active
                         ON active.grapple_id=check_receipt.grapple_id
                       GROUP BY check_receipt.challenger_total,
                                check_receipt.opponent_total,
                                option_receipt.effect,
                                option_receipt.raw_damage"""
                ).fetchone()
                self.assertEqual(receipt, (13, 2, 11, 13, 2))

    def test_grapple_defender_can_win_and_throw_ends_state(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                encounter_public, actors = self._initialized_combat(connection)
                actor_ids = {
                    str(public_id): actor_id
                    for actor_id, public_id in connection.execute(
                        """SELECT actor_id,public_id FROM actor_actor
                           WHERE public_id IN (%s,%s)""",
                        (actors[0], actors[1])).fetchall()
                }
                for actor_public in actors[:2]:
                    connection.execute(
                        """INSERT INTO actor_skill
                           SELECT %s,rule_id,0 FROM rule_rule
                           WHERE rule_code='skill.natural-weapons'""",
                        (actor_ids[actor_public],))
                begin_personal_turn_command(
                    connection, initiator_reference="player",
                    idempotency_key="grapple-throw-begin",
                    encounter_public_id=encounter_public,
                    actor_public_id=actors[0])
                checked = resolve_personal_grapple_check_command(
                    connection, initiator_reference="player",
                    idempotency_key="grapple-throw-check",
                    encounter_public_id=encounter_public,
                    challenger_actor_public_id=actors[0],
                    opponent_actor_public_id=actors[1],
                    challenger_characteristic_rule_code=
                        "characteristic.dexterity",
                    opponent_characteristic_rule_code=
                        "characteristic.dexterity",
                    personal_range_confirmed=True,
                    random_source=FixedRandom((1, 1, 6, 6)))
                self.assertEqual(checked.winner_actor_public_id, actors[1])
                thrown = apply_personal_grapple_option_command(
                    connection, initiator_reference="referee",
                    idempotency_key="grapple-throw-option",
                    grapple_public_id=checked.grapple_public_id,
                    option_code="throw", continue_grapple=True,
                    displacement_metres=3,
                    random_source=FixedRandom((5,)))
                self.assertEqual(thrown.raw_damage, 5)
                self.assertFalse(thrown.continue_grapple)
                self.assertEqual(thrown.grapple_status, "ended")
                self.assertEqual(connection.execute(
                    "SELECT count(*) FROM enc_personal_grapple_active_actor"
                ).fetchone()[0], 0)
