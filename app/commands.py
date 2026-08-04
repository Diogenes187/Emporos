"""Emporos application commands delegated to the Base Cepheus engine."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import psycopg

from app.database import database_url


def _foundation_root() -> Path:
    configured = os.environ.get("BASE_CEPHEUS_ROOT")
    if configured:
        return Path(configured).resolve()
    product_root = Path(__file__).resolve().parents[1]
    if not (product_root / "engine" / "campaigns.py").exists():
        raise RuntimeError("Emporos engine is missing from the product directory")
    return product_root


foundation = _foundation_root()
if foundation.exists() and str(foundation) not in sys.path:
    sys.path.insert(0, str(foundation))

from engine.campaigns import create_campaign_command  # noqa: E402
from engine.character_creation import initialize_character_command  # noqa: E402
from engine.ships import acquire_ship_command  # noqa: E402
from engine.sectors import import_sector_command  # noqa: E402
from engine.travel_planning import place_ship_command, plan_jump_journey_command  # noqa: E402
from engine.navigation import resolve_navigation_command  # noqa: E402
from engine.jump_attempts import resolve_jump_attempt_command  # noqa: E402
from engine.spacecraft_journeys import start_spacecraft_journey_leg_command, complete_spacecraft_journey_leg_command  # noqa: E402
from engine.markets import open_trade_market_command  # noqa: E402
from engine.broker_carousing import resolve_broker_operation_command, resolve_carousing_influence_command  # noqa: E402
from engine.commerce_setup import prepare_trading_command  # noqa: E402
from engine.purchases import purchase_trade_goods_command  # noqa: E402
from engine.sales import sell_trade_goods_command  # noqa: E402
from engine.refueling import refuel_ship_command  # noqa: E402
from engine.ship_expenses import pay_ship_operating_expense_command  # noqa: E402
from engine.crew_assignments import assign_ship_crew_command  # noqa: E402
from engine.journal import add_campaign_note_command, archive_play_session_command  # noqa: E402
from engine.crew_payroll import pay_ship_crew_command  # noqa: E402
from engine.route_revenue import open_route_revenue_command  # noqa: E402
from engine.freight_contracts import accept_freight_contract_command  # noqa: E402
from engine.freight_delivery import deliver_freight_contract_command  # noqa: E402
from engine.passenger_booking import book_route_passengers_command  # noqa: E402
from engine.passenger_boarding import board_route_passengers_command  # noqa: E402
from engine.low_passage_revival import revive_low_passenger_command  # noqa: E402
from engine.passenger_manifest import finalize_passenger_manifest_command  # noqa: E402
from engine.postal_contracts import accept_postal_contract_command, deliver_postal_contract_command  # noqa: E402
from engine.starship_charters import quote_starship_charter_command, accept_starship_charter_command, complete_starship_charter_command  # noqa: E402
from engine.ship_mortgages import open_ship_mortgage_command, pay_ship_mortgage_command  # noqa: E402
from engine.source_library import ingest_campaign_source_command  # noqa: E402
from ai.source_reviewer import review_document_text_queue  # noqa: E402
from ai.referee import submit_referee_turn  # noqa: E402
from engine.referee_tools import confirm_referee_tool_request  # noqa: E402
from engine.encounters import create_encounter_command,add_encounter_participant_command,transition_encounter_mode_command,set_encounter_attitude_command,attempt_attitude_influence_command  # noqa: E402
from engine.combat_runtime import initialize_personal_combat_command,begin_personal_turn_command,move_personal_combatant_command,aim_personal_attack_command,complete_personal_turn_command,advance_personal_combat_round_command,advance_weapon_reload_command,hasten_personal_combatant_command,delay_personal_turn_command,resume_delayed_personal_turn_command,forfeit_delayed_personal_turn_command,change_personal_stance_command,set_personal_cover_command,spend_personal_action_command,aim_personal_attack_for_kill_command,move_species_flyer_command,resolve_species_great_leap_command  # noqa: E402
from engine.comms_runtime import set_battlefield_communication_command,apply_personal_initiative_support_command  # noqa: E402
from engine.combat_runtime import declare_personal_attack_command,declare_personal_reaction_command  # noqa: E402
from engine.commands import resolve_personal_attack_command,apply_personal_damage_command  # noqa: E402
from engine.combat_resolution_runtime import resolve_personal_combat_command  # noqa: E402
from engine.armor_runtime import equip_personal_armor_command,unequip_personal_armor_command  # noqa: E402
from engine.weapon_ready_runtime import advance_personal_weapon_ready_command  # noqa: E402
from engine.grappling_runtime import apply_personal_grapple_option_command, resolve_personal_grapple_check_command  # noqa: E402
from engine.coup_de_grace_runtime import resolve_personal_coup_de_grace_command  # noqa: E402
from engine.free_actions_runtime import perform_personal_free_action_command  # noqa: E402
from engine.extended_actions_runtime import abandon_personal_extended_action_command, advance_personal_extended_action_command, start_personal_extended_action_command  # noqa: E402
from engine.psionics import activate_psionic_power_command, recover_psionic_strength_command, set_telepathic_shield_command  # noqa: E402
from engine.streetwise import resolve_streetwise_command  # noqa: E402
from engine.bribery import attempt_bribery_command, resolve_bribery_consequence_command  # noqa: E402
from engine.gambling import resolve_house_gambling_command  # noqa: E402
from engine.recon import resolve_recon_command  # noqa: E402
from engine.survival import resolve_survival_task_command  # noqa: E402
from engine.animal_skills import resolve_animal_skill_operation_command  # noqa: E402
from engine.animals import set_animal_reaction_context_command,resolve_animal_reaction_command  # noqa: E402
from engine.environment import advance_species_environmental_exposure_command  # noqa: E402
from engine.competitive_gambling import resolve_competitive_gambling_command  # noqa: E402
from engine.liaison import resolve_liaison_negotiation_command  # noqa: E402
from engine.steward import resolve_steward_service_command  # noqa: E402
from engine.conditions_runtime import set_personal_battlefield_conditions_command  # noqa: E402
from engine.explosions_runtime import declare_personal_explosion_command,declare_personal_explosion_reaction_command,resolve_personal_explosion_command  # noqa: E402
from engine.extended_actions_runtime import resolve_personal_extended_action_interruption_command  # noqa: E402
from engine.scenes import SceneFact,create_scene_snapshot_command  # noqa: E402
from engine.tasks import resolve_species_hive_mentality_command,resolve_species_naturally_curious_command,evaluate_species_low_light_visibility_command  # noqa: E402
from engine.ground_starship_runtime import resolve_ground_starship_volley_attacks_command,finalize_ground_starship_volley_command  # noqa: E402
from engine.transport import resolve_transport_operation_command  # noqa: E402
from engine.regulatory import resolve_regulatory_task_command  # noqa: E402
from engine.computer import perform_computer_basic_operation_command  # noqa: E402
from engine.devices import resolve_device_operation_command  # noqa: E402
from engine.leadership import begin_leadership_coordination_command, allocate_leadership_coordination_command  # noqa: E402
from engine.linguistics import assign_actor_language_command, decipher_preserved_language_command  # noqa: E402
from engine.skill_training import allocate_skill_training_week_command  # noqa: E402
from engine.characters import assign_actor_species_command  # noqa: E402
from engine.starships import check_starship_encounter_command  # noqa: E402
from engine.trade_work import start_trade_work_week_command, complete_trade_work_week_command  # noqa: E402
from engine.equipment_purchases import purchase_personal_equipment_command  # noqa: E402
from engine.ammunition_purchases import purchase_personal_ammunition_command  # noqa: E402
from engine.characters import update_character_final_details_command  # noqa: E402
from engine.health_runtime import apply_personal_fatigue_command, complete_personal_fatigue_rest_command, resolve_personal_unconscious_recovery_command  # noqa: E402
from engine.mental_healing import resolve_personal_mental_healing_command  # noqa: E402
from engine.injury_runtime import apply_determined_personal_natural_healing_command, determine_personal_natural_healing_command  # noqa: E402
from engine.medical_runtime import apply_determined_personal_first_aid_command, apply_determined_personal_medical_care_command, apply_determined_personal_surgery_command, determine_personal_first_aid_command, determine_personal_medical_care_command, determine_personal_surgery_command  # noqa: E402
from engine.careers import apply_career_aging_command, apply_career_basic_training_command, apply_career_injury_command, apply_career_rank_zero_award_command, apply_career_term_training_command, attempt_career_entry_command, attempt_career_survival_command, complete_career_term_command, declare_career_anagathics_command, decide_career_reenlistment_command, determine_aging_crisis_cost_command, determine_anagathic_stopping_shock_command, determine_career_aging_command, determine_career_injury_command, determine_career_reenlistment_command, determine_injury_crisis_cost_command, finish_character_creation_command, initialize_career_muster_command, resolve_aging_crisis_command, resolve_career_medical_care_command, resolve_career_rank_attempt_command, resolve_career_weapon_benefit_command, resolve_failed_career_entry_command, resolve_injury_crisis_command, resolve_survival_mishap_command, roll_career_benefit_command  # noqa: E402


def create_campaign(
    *, name: str, play_mode: str, idempotency_key: str
):
    url = database_url()
    if not url:
        raise RuntimeError("No Emporos database URL is configured")
    authority = os.environ.get(
        "EMPOROS_AUTHORITY_REFERENCE", "emporos-local-player"
    )
    with psycopg.connect(url) as connection:
        return create_campaign_command(
            connection,
            initiator_reference=authority,
            idempotency_key=idempotency_key,
            name=name,
            play_mode=play_mode,
        )


def initialize_character(
    *, campaign_public_id: str, name: str, idempotency_key: str
):
    url = database_url()
    if not url:
        raise RuntimeError("No Emporos database URL is configured")
    authority = os.environ.get(
        "EMPOROS_AUTHORITY_REFERENCE", "emporos-local-player"
    )
    with psycopg.connect(url) as connection:
        return initialize_character_command(
            connection,
            initiator_reference=authority,
            idempotency_key=idempotency_key,
            campaign_public_id=campaign_public_id,
            character_name=name,
        )


def acquire_ship(*,campaign_public_id: str,owner_actor_public_id: str,
                 class_code: str,name: str,registration_identifier: str,
                 idempotency_key: str):
    url=database_url()
    if not url: raise RuntimeError("No Emporos database URL is configured")
    authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:
        return acquire_ship_command(
            connection,initiator_reference=authority,idempotency_key=idempotency_key,
            campaign_public_id=campaign_public_id,
            owner_actor_public_id=owner_actor_public_id,class_code=class_code,
            ship_name=name,registration_identifier=registration_identifier,
        )


def import_sector(*,campaign_public_id: str,sector_name: str,sector_x: int,
                  sector_y: int,source_filename: str,content: bytes,
                  idempotency_key: str):
    url=database_url()
    if not url: raise RuntimeError("No Emporos database URL is configured")
    authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:
        return import_sector_command(
            connection,initiator_reference=authority,idempotency_key=idempotency_key,
            campaign_public_id=campaign_public_id,sector_name=sector_name,
            sector_x=sector_x,sector_y=sector_y,source_filename=source_filename,
            content=content,
        )

def place_ship(*,campaign_public_id:str,ship_public_id:str,system_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return place_ship_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,ship_public_id=ship_public_id,system_public_id=system_public_id)

def plan_jump(*,campaign_public_id:str,ship_public_id:str,destination_system_public_id:str,journey_name:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return plan_jump_journey_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,ship_public_id=ship_public_id,destination_system_public_id=destination_system_public_id,journey_name=journey_name)

def plot_jump(*,journey_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_navigation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id,leg_order=1,actor_public_id=actor_public_id,operation_kind='jump_route',characteristic_rule_code='characteristic.education',difficulty_rule_code='difficulty.average')

def resolve_jump(*,journey_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_jump_attempt_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id,engineer_actor_public_id=actor_public_id)

def run_jump(*,journey_public_id:str,idempotency_key:str,complete:bool):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:
        command=complete_spacecraft_journey_leg_command if complete else start_spacecraft_journey_leg_command
        result=command(connection,referee_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id,leg_order=1)
        destination=connection.execute("SELECT location.public_id::text FROM journey_journey journey JOIN journey_leg leg USING(journey_id) JOIN loc_location location ON location.location_id=leg.destination_location_id WHERE journey.public_id=%s AND leg.leg_order=1",(journey_public_id,)).fetchone()[0] if complete and result.journey_completed else None
        return result,destination

def open_market(*,campaign_public_id:str,system_public_id:str,market_name:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return open_trade_market_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,system_public_id=system_public_id,market_name=market_name)

def roll_purchase_price(*,actor_public_id:str,market_session_id:int,trade_good_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_broker_operation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,market_session_id=market_session_id,operation_code='determine-purchase-price',objective_reference='Purchase '+trade_good_code,characteristic_rule_code='characteristic.intelligence',trade_good_code=trade_good_code)

def prepare_trading(*,campaign_public_id:str,actor_public_id:str,ship_public_id:str,opening_balance:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return prepare_trading_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,opening_balance=opening_balance)

def purchase_goods(*,campaign_public_id:str,actor_public_id:str,ship_public_id:str,stock_id:int,broker_command_public_id:str,quantity_tons:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return purchase_trade_goods_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,stock_id=stock_id,broker_command_public_id=broker_command_public_id,quantity_tons=quantity_tons)

def roll_sale_price(*,actor_public_id:str,market_session_id:int,trade_good_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_broker_operation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,market_session_id=market_session_id,operation_code='determine-sale-price',objective_reference='Sell '+trade_good_code,characteristic_rule_code='characteristic.intelligence',trade_good_code=trade_good_code)

def sell_goods(*,campaign_public_id:str,actor_public_id:str,ship_public_id:str,lot_id:int,market_session_id:int,broker_command_public_id:str,quantity_tons:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return sell_trade_goods_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,lot_id=lot_id,market_session_id=market_session_id,broker_command_public_id=broker_command_public_id,quantity_tons=quantity_tons)

def refuel_ship(*,campaign_public_id:str,actor_public_id:str,ship_public_id:str,fuel_type_code:str,tons:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return refuel_ship_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,fuel_type_code=fuel_type_code,tons=tons)

def pay_ship_expense(*,campaign_public_id:str,actor_public_id:str,ship_public_id:str,operating_cost_code:str,quantity:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return pay_ship_operating_expense_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,operating_cost_code=operating_cost_code,quantity=quantity)

def assign_ship_crew(*,campaign_public_id:str,actor_public_id:str,ship_public_id:str,ship_crew_position_id:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return assign_ship_crew_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,ship_crew_position_id=ship_crew_position_id)

def add_campaign_note(*,campaign_public_id:str,title:str,note_kind:str,note_text:str,ai_memory_enabled:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return add_campaign_note_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,title=title,note_kind=note_kind,note_text=note_text,ai_memory_enabled=ai_memory_enabled)

def archive_play_session(*,campaign_public_id:str,title:str,transcript_text:str,ai_memory_enabled:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return archive_play_session_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,title=title,transcript_text=transcript_text,ai_memory_enabled=ai_memory_enabled)

def pay_ship_crew(*,campaign_public_id:str,payer_actor_public_id:str,ship_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return pay_ship_crew_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,payer_actor_public_id=payer_actor_public_id,ship_public_id=ship_public_id)

def open_route_revenue(*,campaign_public_id:str,ship_public_id:str,destination_system_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return open_route_revenue_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,ship_public_id=ship_public_id,destination_system_public_id=destination_system_public_id)

def accept_freight_contract(*,cycle_public_id:str,journey_public_id:str,accepted_tons:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return accept_freight_contract_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,cycle_public_id=cycle_public_id,journey_public_id=journey_public_id,accepted_tons=accepted_tons)

def deliver_freight_contract(*,contract_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return deliver_freight_contract_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,contract_public_id=contract_public_id,actor_public_id=actor_public_id)

def book_route_passengers(*,cycle_public_id:str,journey_public_id:str,passage_class:str,passenger_count:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return book_route_passengers_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,cycle_public_id=cycle_public_id,journey_public_id=journey_public_id,passage_class=passage_class,passenger_count=passenger_count)

def board_route_passengers(*,journey_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return board_route_passengers_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id,actor_public_id=actor_public_id)

def revive_low_passenger(*,journey_passage_id:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return revive_low_passenger_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_passage_id=journey_passage_id)

def finalize_passenger_manifest(*,journey_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return finalize_passenger_manifest_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id)

def accept_postal_contract(*,journey_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return accept_postal_contract_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id)

def deliver_postal_contract(*,contract_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return deliver_postal_contract_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,contract_public_id=contract_public_id,actor_public_id=actor_public_id)

def quote_starship_charter(*,campaign_public_id:str,ship_public_id:str,billing_blocks:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return quote_starship_charter_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,ship_public_id=ship_public_id,billing_blocks=billing_blocks)
def accept_starship_charter(*,quote_public_id:str,journey_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return accept_starship_charter_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,quote_public_id=quote_public_id,journey_public_id=journey_public_id)
def complete_starship_charter(*,contract_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return complete_starship_charter_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,contract_public_id=contract_public_id,actor_public_id=actor_public_id)
def open_ship_mortgage(*,campaign_public_id:str,ship_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return open_ship_mortgage_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,ship_public_id=ship_public_id,actor_public_id=actor_public_id)
def pay_ship_mortgage(*,ship_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return pay_ship_mortgage_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,ship_public_id=ship_public_id,actor_public_id=actor_public_id)
def ingest_campaign_source(*,campaign_public_id:str,title:str,source_kind:str,original_filename:str,media_type:str,content:bytes,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    storage_root=Path(os.environ.get("EMPOROS_UPLOAD_ROOT",foundation/"uploads"))/"sources"
    with psycopg.connect(url) as connection:return ingest_campaign_source_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,title=title,source_kind=source_kind,original_filename=original_filename,media_type=media_type,content=content,storage_root=storage_root)

def review_campaign_source(*,document_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return review_document_text_queue(connection,initiator_reference=authority,document_public_id=document_public_id,idempotency_key=idempotency_key)

def send_referee_message(*,campaign_public_id:str,player_text:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return submit_referee_turn(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,player_text=player_text)

def confirm_referee_action(*,request_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not url:raise RuntimeError("No Emporos database URL is configured")
    with psycopg.connect(url) as connection:return confirm_referee_tool_request(connection,initiator_reference=authority,idempotency_key=idempotency_key,request_public_id=request_public_id)

def create_encounter(*,campaign_public_id:str,encounter_type_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return create_encounter_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,encounter_type_code=encounter_type_code)

def add_encounter_participant(*,encounter_public_id:str,actor_public_id:str,participant_role:str,side_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return add_encounter_participant_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,participant_role=participant_role,side_code=side_code)

def begin_personal_combat(*,encounter_public_id:str,reason:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return transition_encounter_mode_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,to_mode='personal_combat',reason=reason)

def initialize_personal_combat(*,encounter_public_id:str,aware_actor_public_ids:tuple[str,...],starting_context_code:str,light_condition:str,starting_range_rule_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return initialize_personal_combat_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,aware_actor_public_ids=aware_actor_public_ids,starting_context_code=starting_context_code,light_condition=light_condition,starting_range_rule_code=starting_range_rule_code or None)

def begin_combat_turn(*,encounter_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return begin_personal_turn_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def hasten_combatant(*,encounter_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return hasten_personal_combatant_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def delay_combat_turn(*,encounter_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return delay_personal_turn_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def resume_combat_turn(*,encounter_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resume_delayed_personal_turn_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def forfeit_combat_turn(*,encounter_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return forfeit_delayed_personal_turn_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def change_combat_stance(*,encounter_public_id:str,actor_public_id:str,stance_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return change_personal_stance_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,stance_code=stance_code)

def set_combat_cover(*,encounter_public_id:str,actor_public_id:str,cover_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return set_personal_cover_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,cover_code=cover_code or None)

def move_combatant(*,encounter_public_id:str,actor_public_id:str,metres:float,difficult_terrain:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return move_personal_combatant_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,metres=metres,difficult_terrain=difficult_terrain)

def aim_combatant(*,encounter_public_id:str,actor_public_id:str,target_actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return aim_personal_attack_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,target_actor_public_id=target_actor_public_id)

def spend_combat_action(*,encounter_public_id:str,actor_public_id:str,operation:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return spend_personal_action_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,operation=operation)

def aim_combatant_for_kill(*,encounter_public_id:str,actor_public_id:str,target_actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return aim_personal_attack_for_kill_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,target_actor_public_id=target_actor_public_id)

def resolve_combat_grapple(*,encounter_public_id:str,challenger_actor_public_id:str,opponent_actor_public_id:str,challenger_characteristic_rule_code:str,opponent_characteristic_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_personal_grapple_check_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,challenger_actor_public_id=challenger_actor_public_id,opponent_actor_public_id=opponent_actor_public_id,challenger_characteristic_rule_code=challenger_characteristic_rule_code,opponent_characteristic_rule_code=opponent_characteristic_rule_code,personal_range_confirmed=True)

def apply_combat_grapple_option(*,grapple_public_id:str,option_code:str,continue_grapple:bool,displacement_metres:float,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_personal_grapple_option_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,grapple_public_id=grapple_public_id,option_code=option_code,continue_grapple=continue_grapple,displacement_metres=displacement_metres)

def perform_combat_free_action(*,encounter_public_id:str,actor_public_id:str,action_reference:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return perform_personal_free_action_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,action_reference=action_reference,assessed_cost="free")

def resolve_combat_coup_de_grace(*,encounter_public_id:str,actor_public_id:str,target_actor_public_id:str,weapon_rule_code:str,delivery_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    relationship="close-quarters" if delivery_kind=="melee" else "adjacent"
    with psycopg.connect(url) as connection:return resolve_personal_coup_de_grace_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,target_actor_public_id=target_actor_public_id,weapon_rule_code=weapon_rule_code,delivery_kind=delivery_kind,range_relationship=relationship,helpless_basis="unconscious",helpless_evidence="Authoritative actor_personal_condition.unconscious state")

def start_combat_extended_action(*,encounter_public_id:str,actor_public_id:str,task_reference:str,characteristic_rule_code:str,skill_rule_code:str,time_frame_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return start_personal_extended_action_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,task_reference=task_reference,characteristic_rule_code=characteristic_rule_code,skill_rule_code=skill_rule_code,time_frame_rule_code=time_frame_rule_code)

def progress_combat_extended_action(*,encounter_public_id:str,actor_public_id:str,operation:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    command=advance_personal_extended_action_command if operation=="advance" else abandon_personal_extended_action_command
    with psycopg.connect(url) as connection:return command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def activate_self_psionic_power(*,actor_public_id:str,power_rule_code:str,variable_points:int,idempotency_key:str):
    allowed={"psionics.power.suspended-animation","psionics.power.enhanced-strength","psionics.power.enhanced-endurance"}
    if power_rule_code not in allowed:raise ValueError("This power requires a dedicated activation form")
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return activate_psionic_power_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,power_rule_code=power_rule_code,variable_points=variable_points)

def send_psionic_thought(*,actor_public_id:str,target_actor_public_id:str,range_rule_code:str,sent_thought_content:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return activate_psionic_power_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,power_rule_code="psionics.power.send-thoughts",target_actor_public_id=target_actor_public_id,range_rule_code=range_rule_code,sent_thought_content=sent_thought_content)

def perform_streetwise_operation(*,actor_public_id:str,operation_code:str,objective_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_streetwise_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,objective_reference=objective_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code)

def attempt_bribe(*,actor_public_id:str,target_reference:str,incident_reference:str,offense_code:str,law_level:int,characteristic_rule_code:str,offer_credits:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return attempt_bribery_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,target_reference=target_reference,incident_reference=incident_reference,offense_code=offense_code,law_level=law_level,characteristic_rule_code=characteristic_rule_code,offer_credits=offer_credits)

def resolve_bribe_consequence(*,actor_public_id:str,target_reference:str,incident_reference:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_bribery_consequence_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,target_reference=target_reference,incident_reference=incident_reference)

def perform_carousing_influence(*,encounter_public_id:str,acting_actor_public_id:str,target_actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_carousing_influence_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,acting_actor_public_id=acting_actor_public_id,target_actor_public_id=target_actor_public_id)

def gamble_against_house(*,actor_public_id:str,characteristic_rule_code:str,odds_code:str,venue_reference:str,game_reference:str,bet_credits:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_house_gambling_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,odds_code=odds_code,venue_reference=venue_reference,game_reference=game_reference,bet_credits=bet_credits)

def perform_recon_operation(*,actor_public_id:str,operation_code:str,subject_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_recon_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,subject_reference=subject_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code)

def perform_survival_operation(*,actor_public_id:str,operation_code:str,objective_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,opportunity_available:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_survival_task_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,objective_reference=objective_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,opportunity_available=opportunity_available)

def perform_animal_skill_operation(*,actor_public_id:str,operation_code:str,objective_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,subject_animal_public_id:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_animal_skill_operation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,objective_reference=objective_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,subject_animal_public_id=subject_animal_public_id or None)

def set_animal_reaction_context(*,encounter_public_id:str,animal_actor_public_id:str,animals_outnumber_characters:bool,animal_has_surprise:bool,animal_is_surprised:bool,animal_bigger_than_character:bool,attack_possible:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return set_animal_reaction_context_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,animal_actor_public_id=animal_actor_public_id,animals_outnumber_characters=animals_outnumber_characters,animal_has_surprise=animal_has_surprise,animal_is_surprised=animal_is_surprised,animal_bigger_than_character=animal_bigger_than_character,attack_possible=attack_possible)

def resolve_animal_reaction(*,encounter_public_id:str,animal_actor_public_id:str,provocation_number:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_animal_reaction_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,animal_actor_public_id=animal_actor_public_id,provocation_number=provocation_number)

def advance_environmental_exposure(*,actor_public_id:str,environment_kind:str,elapsed_minutes:int,protective_equipment_active:bool,exposure_public_id:str|None,end_exposure:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return advance_species_environmental_exposure_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,environment_kind=environment_kind,elapsed_minutes=elapsed_minutes,protective_equipment_active=protective_equipment_active,exposure_public_id=exposure_public_id or None,end_exposure=end_exposure)

def resolve_competitive_gambling(*,venue_reference:str,game_reference:str,pot_reference:str,first_actor_public_id:str,first_characteristic_rule_code:str,first_cheating:bool,second_actor_public_id:str,second_characteristic_rule_code:str,second_cheating:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    participants=[{"actor_public_id":first_actor_public_id,"characteristic_rule_code":first_characteristic_rule_code,"cheating":first_cheating},{"actor_public_id":second_actor_public_id,"characteristic_rule_code":second_characteristic_rule_code,"cheating":second_cheating}]
    with psycopg.connect(url) as connection:return resolve_competitive_gambling_command(connection,referee_reference=authority,idempotency_key=idempotency_key,venue_reference=venue_reference,game_reference=game_reference,pot_reference=pot_reference,participants=participants)

def resolve_liaison_negotiation(*,scene_reference:str,subject_reference:str,first_actor_public_id:str,first_characteristic_rule_code:str,second_actor_public_id:str,second_characteristic_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    participants=[{"actor_public_id":first_actor_public_id,"characteristic_rule_code":first_characteristic_rule_code},{"actor_public_id":second_actor_public_id,"characteristic_rule_code":second_characteristic_rule_code}]
    with psycopg.connect(url) as connection:return resolve_liaison_negotiation_command(connection,referee_reference=authority,idempotency_key=idempotency_key,scene_reference=scene_reference,subject_reference=subject_reference,participants=participants)

def resolve_steward_service(*,journey_public_id:str,steward_actor_public_id:str,passenger_actor_public_id:str,service_code:str,service_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_steward_service_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id,steward_actor_public_id=steward_actor_public_id,passenger_actor_public_id=passenger_actor_public_id,service_code=service_code,service_reference=service_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code)

def set_battlefield_conditions(*,encounter_public_id:str,light_code:str,obscurant_code:str,extreme_weather:bool,gravity_code:str,expected_version:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return set_personal_battlefield_conditions_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,light_code=light_code,obscurant_code=obscurant_code,extreme_weather=extreme_weather,gravity_code=gravity_code,expected_version=expected_version)

def declare_combat_explosion(*,encounter_public_id:str,source_reference:str,damage_dice:int,damage_die_sides:int,flat_damage:int,target_actor_public_ids:tuple[str,...],idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:
        targets=[]
        for actor_public_id in target_actor_public_ids:
            armor=connection.execute("""SELECT rule.rule_code FROM actor_actor actor LEFT JOIN inv_actor_armor_layer layer ON layer.actor_id=actor.actor_id AND layer.campaign_id=actor.campaign_id LEFT JOIN inv_item_instance item ON item.item_instance_id=layer.item_instance_id AND item.campaign_id=layer.campaign_id LEFT JOIN rule_rule rule ON rule.rule_id=item.item_rule_id WHERE actor.public_id=%s ORDER BY layer.layer_order LIMIT 1""",(actor_public_id,)).fetchone()
            targets.append((actor_public_id,armor[0] if armor and armor[0] else "combat.armor.unarmored"))
        return declare_personal_explosion_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,source_reference=source_reference,damage_dice=damage_dice,damage_die_sides=damage_die_sides,flat_damage=flat_damage,targets=tuple(targets))

def react_to_combat_explosion(*,explosion_public_id:str,actor_public_id:str,reaction_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return declare_personal_explosion_reaction_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,explosion_public_id=explosion_public_id,actor_public_id=actor_public_id,reaction_kind=reaction_kind)

def resolve_combat_explosion(*,explosion_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_personal_explosion_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,explosion_public_id=explosion_public_id)

def create_scene_snapshot(*,campaign_public_id:str,template_code:str,scene_reference:str,slot_codes:tuple[str,...],fact_values:tuple[str,...],source_references:tuple[str,...],idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    if not (len(slot_codes)==len(fact_values)==len(source_references)):raise ValueError("Scene fact fields do not align")
    facts=tuple(SceneFact(code,value,source or None) for code,value,source in zip(slot_codes,fact_values,source_references) if value.strip())
    with psycopg.connect(url) as connection:return create_scene_snapshot_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,template_code=template_code,scene_reference=scene_reference,facts=facts)

def resolve_species_hive_mentality(*,actor_public_id:str,family_group_reference:str,perceived_benefit:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_species_hive_mentality_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,family_group_reference=family_group_reference,perceived_benefit=perceived_benefit,difficulty_rule_code=difficulty_rule_code)

def resolve_species_naturally_curious(*,actor_public_id:str,mystery_reference:str,perceived_mystery:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_species_naturally_curious_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,mystery_reference=mystery_reference,perceived_mystery=perceived_mystery,difficulty_rule_code=difficulty_rule_code)

def evaluate_species_low_light(*,actor_public_id:str,illumination_context:str,human_visibility_metres:float,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return evaluate_species_low_light_visibility_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,illumination_context=illumination_context,human_visibility_metres=human_visibility_metres)

def resolve_ground_starship_volley(*,target_ship_public_id:str,target_range_code:str,battery_public_id:str,battery_quantity:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_ground_starship_volley_attacks_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,target_ship_public_id=target_ship_public_id,target_range_code=target_range_code,batteries=((battery_public_id,battery_quantity),))

def finalize_ground_starship_volley(*,volley_command_public_id:str,primary_attack_order:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return finalize_ground_starship_volley_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,volley_command_public_id=volley_command_public_id,primary_attack_order=primary_attack_order)

def perform_ship_transport_operation(*,actor_public_id:str,ship_public_id:str,operation_kind:str,operation_reference:str,challenging_conditions:bool,characteristic_rule_code:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_transport_operation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,target_public_id=ship_public_id,target_kind="ship",operation_kind=operation_kind,operation_reference=operation_reference,challenging_conditions=challenging_conditions,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code)

def perform_regulatory_operation(*,actor_public_id:str,operation_code:str,skill_rule_code:str,case_reference:str,authority_reference:str,law_level:int,characteristic_rule_code:str,illegal_material_present:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_regulatory_task_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,skill_rule_code=skill_rule_code,case_reference=case_reference,authority_reference=authority_reference,law_level=law_level,characteristic_rule_code=characteristic_rule_code,illegal_material_present=illegal_material_present)

def perform_basic_computer_operation(*,actor_public_id:str,operation_code:str,target_reference:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return perform_computer_basic_operation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,target_reference=target_reference)

def perform_device_operation(*,actor_public_id:str,operation_code:str,device_reference:str,characteristic_rule_code:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_device_operation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,operation_code=operation_code,device_reference=device_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code)

def begin_leadership_coordination(*,leader_actor_public_id:str,goal_reference:str,characteristic_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return begin_leadership_coordination_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,leader_actor_public_id=leader_actor_public_id,goal_reference=goal_reference,characteristic_rule_code=characteristic_rule_code)

def allocate_leadership_coordination(*,coordination_public_id:str,recipient_actor_public_id:str,points:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return allocate_leadership_coordination_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,coordination_public_id=coordination_public_id,recipient_actor_public_id=recipient_actor_public_id,points=points)

def assign_actor_language(*,actor_public_id:str,language_code:str,proficiency_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return assign_actor_language_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,language_code=language_code,proficiency_kind=proficiency_kind)

def decipher_language_specimen(*,actor_public_id:str,specimen_reference:str,specimen_medium:str,characteristic_rule_code:str,difficulty_rule_code:str,language_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return decipher_preserved_language_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,specimen_reference=specimen_reference,specimen_medium=specimen_medium,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,language_code=language_code or None)

def train_actor_skill_week(*,actor_public_id:str,skill_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return allocate_skill_training_week_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,skill_rule_code=skill_rule_code)

def assign_actor_species(*,actor_public_id:str,species_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return assign_actor_species_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,species_code=species_code,assignment_kind="player_edit")

def check_for_starship_encounter(*,campaign_public_id:str,region_context:str,target_transponder_active:bool,target_stealth_modifier:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return check_starship_encounter_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,region_context=region_context,target_transponder_active=target_transponder_active,target_stealth_modifier=target_stealth_modifier)

def start_trade_work_week(*,actor_public_id:str,skill_rule_code:str,employer_account_public_id:str,worker_account_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return start_trade_work_week_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,skill_rule_code=skill_rule_code,employer_account_public_id=employer_account_public_id,worker_account_public_id=worker_account_public_id)

def complete_trade_work_week(*,work_week_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return complete_trade_work_week_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,work_week_public_id=work_week_public_id)

def consume_actor_armor_resources(*,actor_public_id:str,item_public_id:str,laser_hits:int,life_support_seconds_used:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_personal_armor_usage_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,item_public_id=item_public_id,laser_hits=laser_hits,life_support_seconds_used=life_support_seconds_used)

def set_battlefield_communication(*,encounter_public_id:str,commander_actor_public_id:str,member_actor_public_id:str,method_code:str,jammed:bool,blocked:bool,line_of_sight:bool,smoke_or_aerosols:bool,member_moving:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return set_battlefield_communication_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,commander_actor_public_id=commander_actor_public_id,member_actor_public_id=member_actor_public_id,method_code=method_code,jammed=jammed,blocked=blocked,line_of_sight=line_of_sight,smoke_or_aerosols=smoke_or_aerosols,member_moving=member_moving)

def set_social_attitude(*,encounter_public_id:str,actor_public_id:str,attitude_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return set_encounter_attitude_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,attitude_code=attitude_code)

def attempt_social_influence(*,encounter_public_id:str,acting_actor_public_id:str,target_actor_public_id:str,skill_rule_code:str,characteristic_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:
        values=connection.execute("""SELECT COALESCE(skill.skill_level,-3),band.modifier FROM actor_actor actor JOIN actor_characteristic characteristic ON characteristic.actor_id=actor.actor_id JOIN rule_rule characteristic_rule ON characteristic_rule.rule_id=characteristic.characteristic_rule_id AND characteristic_rule.rule_code=%s JOIN rule_characteristic_modifier_band band ON (band.characteristic_rule_id IS NULL OR band.characteristic_rule_id=characteristic.characteristic_rule_id) AND band.score_range @> characteristic.current_value LEFT JOIN rule_rule skill_rule ON skill_rule.rule_code=%s LEFT JOIN actor_skill skill ON skill.actor_id=actor.actor_id AND skill.skill_rule_id=skill_rule.rule_id WHERE actor.public_id=%s ORDER BY band.characteristic_rule_id NULLS LAST LIMIT 1""",(characteristic_rule_code,skill_rule_code,acting_actor_public_id)).fetchone()
        if values is None:raise ValueError("Influence requires a valid actor characteristic")
        return attempt_attitude_influence_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,acting_actor_public_id=acting_actor_public_id,target_actor_public_id=target_actor_public_id,skill_modifier=values[0],characteristic_modifier=values[1])

def apply_combat_initiative_support(*,encounter_public_id:str,commander_actor_public_id:str,support_code:str,characteristic_rule_code:str,target_actor_public_id:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_personal_initiative_support_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,commander_actor_public_id=commander_actor_public_id,support_code=support_code,characteristic_rule_code=characteristic_rule_code,target_actor_public_id=target_actor_public_id or None)

def move_combatant_in_flight(*,encounter_public_id:str,actor_public_id:str,metres:float,altitude_change_metres:float,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return move_species_flyer_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,metres=metres,altitude_change_metres=altitude_change_metres)

def resolve_combatant_great_leap(*,encounter_public_id:str,actor_public_id:str,characteristic_rule_code:str,difficulty_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_species_great_leap_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code)

def recover_actor_psionic_strength(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return recover_psionic_strength_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def set_actor_telepathic_shield(*,actor_public_id:str,shield_raised:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return set_telepathic_shield_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,shield_raised=shield_raised)

def complete_combat_turn(*,encounter_public_id:str,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return complete_personal_turn_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id)

def advance_combat_round(*,encounter_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return advance_personal_combat_round_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id)

def ready_combat_weapon(*,encounter_public_id:str,actor_public_id:str,weapon_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return advance_personal_weapon_ready_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,weapon_rule_code=weapon_rule_code)

def reload_combat_weapon(*,encounter_public_id:str,actor_public_id:str,weapon_rule_code:str,ammunition_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return advance_weapon_reload_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,weapon_rule_code=weapon_rule_code,ammunition_rule_code=ammunition_rule_code,require_actor_holding=True)

def declare_combat_attack(*,encounter_public_id:str,attacker_actor_public_id:str,target_actor_public_id:str,item_rule_code:str,attack_profile_code:str,range_rule_code:str,target_has_cover:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return declare_personal_attack_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,attacker_actor_public_id=attacker_actor_public_id,target_actor_public_id=target_actor_public_id,item_rule_code=item_rule_code,attack_profile_code=attack_profile_code,range_rule_code=range_rule_code,target_has_cover=target_has_cover,require_actor_holding=True)

def resolve_combat_attack(*,personal_attack_public_id:str,item_rule_code:str,attack_profile_code:str,range_rule_code:str,target_actor_public_id:str,armor_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_personal_attack_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,personal_attack_public_id=personal_attack_public_id,item_rule_code=item_rule_code,attack_profile_code=attack_profile_code,range_rule_code=range_rule_code,target_actor_public_id=target_actor_public_id,armor_rule_code=armor_rule_code,use_equipped_armor=True)

def apply_combat_damage(*,damage_instance_public_id:str,strength_damage:int,dexterity_damage:int,endurance_damage:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    allocations=tuple((code,value) for code,value in (("characteristic.endurance",endurance_damage),("characteristic.strength",strength_damage),("characteristic.dexterity",dexterity_damage)) if value>0)
    with psycopg.connect(url) as connection:
        result=apply_personal_damage_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,damage_instance_public_id=damage_instance_public_id,allocations=allocations)
        damage=connection.execute("""SELECT damage.damage_instance_id,EXISTS(SELECT 1 FROM enc_personal_extended_action action WHERE action.actor_id=damage.target_actor_id AND action.action_status='active') FROM health_damage_instance damage WHERE damage.public_id=%s""",(damage_instance_public_id,)).fetchone()
        if damage and damage[1]:resolve_personal_extended_action_interruption_command(connection,initiator_reference=authority,idempotency_key=f"{idempotency_key}:extended-interruption",damage_instance_id=damage[0])
        return result

def react_to_combat_attack(*,encounter_public_id:str,actor_public_id:str,attack_trigger_reference:str,reaction_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return declare_personal_reaction_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,actor_public_id=actor_public_id,attack_trigger_reference=attack_trigger_reference,reaction_kind=reaction_kind)

def end_personal_combat(*,encounter_public_id:str,outcome_kind:str,resolution_summary:str,winning_side_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_personal_combat_command(connection,initiator_reference=authority,referee_reference=authority,idempotency_key=idempotency_key,encounter_public_id=encounter_public_id,outcome_kind=outcome_kind,resolution_summary=resolution_summary,winning_side_code=winning_side_code or None)

def equip_actor_armor(*,actor_public_id:str,item_public_id:str,layer_order:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return equip_personal_armor_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,item_public_id=item_public_id,layer_order=layer_order)

def unequip_actor_armor(*,actor_public_id:str,item_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return unequip_personal_armor_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,item_public_id=item_public_id)

def purchase_personal_equipment(*,campaign_public_id:str,actor_public_id:str,item_rule_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return purchase_personal_equipment_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,item_rule_code=item_rule_code)

def purchase_personal_ammunition(*,campaign_public_id:str,actor_public_id:str,ammunition_rule_code:str,reload_units:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return purchase_personal_ammunition_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,campaign_public_id=campaign_public_id,actor_public_id=actor_public_id,ammunition_rule_code=ammunition_rule_code,reload_units=reload_units)

def attempt_career_entry(*,actor_public_id:str,career_code:str,assignment_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return attempt_career_entry_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,career_code=career_code,assignment_code=assignment_code)

def resolve_career_entry_failure(*,attempt_command_public_id:str,fallback_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_failed_career_entry_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,attempt_command_public_id=attempt_command_public_id,fallback_kind=fallback_kind)

def apply_career_basic_training(*,actor_public_id:str,selected_roll_value:int|None,cascade_specializations:dict[str,str],idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_career_basic_training_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,selected_roll_value=selected_roll_value,cascade_specializations=cascade_specializations)

def apply_career_rank_zero_award(*,actor_public_id:str,cascade_specialization:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_career_rank_zero_award_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,cascade_specialization=cascade_specialization)

def declare_career_anagathics(*,actor_public_id:str,uses_anagathics:bool,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return declare_career_anagathics_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,uses_anagathics=uses_anagathics)

def attempt_career_survival(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return attempt_career_survival_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def resolve_career_rank_attempt(*,actor_public_id:str,attempt_kind:str,decision:str,cascade_specialization:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_career_rank_attempt_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,attempt_kind=attempt_kind,decision=decision,cascade_specialization=cascade_specialization)

def apply_career_term_training(*,actor_public_id:str,training_table_code:str,cascade_specializations:dict[str,str],idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_career_term_training_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,training_table_code=training_table_code,cascade_specializations=cascade_specializations)

def complete_career_term(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return complete_career_term_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def determine_career_reenlistment(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_career_reenlistment_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def decide_career_reenlistment(*,actor_public_id:str,decision:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return decide_career_reenlistment_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,decision=decision)

def resolve_survival_mishap(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_survival_mishap_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def determine_career_injury(*,actor_public_id:str,result_two_choice:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_career_injury_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,result_two_choice=result_two_choice)

def apply_career_injury(*,actor_public_id:str,primary_characteristic_code:str,other_reduction_mode:str|None,other_characteristic_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_career_injury_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,primary_characteristic_code=primary_characteristic_code,other_reduction_mode=other_reduction_mode,other_characteristic_code=other_characteristic_code)

def resolve_career_medical_care(*,actor_public_id:str,decision:str,restoration_points:dict[str,int],idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_career_medical_care_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,decision=decision,restoration_points=restoration_points)

def initialize_career_muster(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return initialize_career_muster_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def roll_career_benefit(*,actor_public_id:str,benefit_table_code:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return roll_career_benefit_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,benefit_table_code=benefit_table_code)

def resolve_career_weapon_benefit(*,actor_public_id:str,weapon_rule_code:str,resolution_kind:str,skill_rule_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_career_weapon_benefit_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,weapon_rule_code=weapon_rule_code,resolution_kind=resolution_kind,skill_rule_code=skill_rule_code or None)

def determine_career_aging(*,actor_public_id:str,aging_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    command=determine_anagathic_stopping_shock_command if aging_kind=="anagathic_stopping_shock" else determine_career_aging_command
    with psycopg.connect(url) as connection:return command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def apply_career_aging(*,actor_public_id:str,physical_characteristic_codes:tuple[str,...],mental_characteristic_code:str|None,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_career_aging_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,physical_characteristic_codes=physical_characteristic_codes,mental_characteristic_code=mental_characteristic_code or None)

def determine_aging_crisis_cost(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_aging_crisis_cost_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def resolve_aging_crisis(*,actor_public_id:str,resolution_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_aging_crisis_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,resolution_kind=resolution_kind)

def update_character_final_details(*,actor_public_id:str,character_name:str,gender_identity:str|None,appearance:str|None,personal_goals:tuple[str,...],idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return update_character_final_details_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,character_name=character_name,gender_identity=gender_identity or None,appearance=appearance or None,personal_goals=personal_goals)

def finish_character_creation(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return finish_character_creation_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def apply_personal_fatigue(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return apply_personal_fatigue_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def complete_personal_fatigue_rest(*,actor_public_id:str,completed_hours:float,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return complete_personal_fatigue_rest_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,completed_hours=completed_hours)

def resolve_personal_unconscious_recovery(*,actor_public_id:str,minutes_elapsed:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_personal_unconscious_recovery_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,minutes_elapsed=minutes_elapsed)

def resolve_personal_mental_healing(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_personal_mental_healing_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def determine_personal_first_aid(*,patient_actor_public_id:str,doctor_actor_public_id:str,damage_instance_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_personal_first_aid_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,patient_actor_public_id=patient_actor_public_id,doctor_actor_public_id=doctor_actor_public_id,damage_instance_public_id=damage_instance_public_id)

def apply_determined_personal_first_aid(*,determination_command_public_id:str,strength_points:int,dexterity_points:int,endurance_points:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    allocations=tuple((code,value) for code,value in (("characteristic.strength",strength_points),("characteristic.dexterity",dexterity_points),("characteristic.endurance",endurance_points)) if value>0)
    with psycopg.connect(url) as connection:return apply_determined_personal_first_aid_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,determination_command_public_id=determination_command_public_id,allocations=allocations)

def determine_personal_surgery(*,patient_actor_public_id:str,doctor_actor_public_id:str,first_aid_command_public_id:str,medical_facility_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_personal_surgery_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,patient_actor_public_id=patient_actor_public_id,doctor_actor_public_id=doctor_actor_public_id,first_aid_command_public_id=first_aid_command_public_id,medical_facility_public_id=medical_facility_public_id)

def apply_determined_personal_surgery(*,determination_command_public_id:str,strength_points:int,dexterity_points:int,endurance_points:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    allocations=tuple((code,value) for code,value in (("characteristic.strength",strength_points),("characteristic.dexterity",dexterity_points),("characteristic.endurance",endurance_points)) if value>0)
    with psycopg.connect(url) as connection:return apply_determined_personal_surgery_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,determination_command_public_id=determination_command_public_id,allocations=allocations)

def determine_personal_medical_care(*,patient_actor_public_id:str,doctor_actor_public_id:str,medical_facility_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_personal_medical_care_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,patient_actor_public_id=patient_actor_public_id,doctor_actor_public_id=doctor_actor_public_id,medical_facility_public_id=medical_facility_public_id)

def apply_determined_personal_medical_care(*,determination_command_public_id:str,strength_points:int,dexterity_points:int,endurance_points:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    allocations=tuple((code,value) for code,value in (("characteristic.strength",strength_points),("characteristic.dexterity",dexterity_points),("characteristic.endurance",endurance_points)) if value>0)
    with psycopg.connect(url) as connection:return apply_determined_personal_medical_care_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,determination_command_public_id=determination_command_public_id,allocations=allocations)

def determine_personal_natural_healing(*,actor_public_id:str,lifestyle:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_personal_natural_healing_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,lifestyle=lifestyle)

def apply_determined_personal_natural_healing(*,determination_command_public_id:str,strength_points:int,dexterity_points:int,endurance_points:int,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    allocations=tuple((code,value) for code,value in (("characteristic.strength",strength_points),("characteristic.dexterity",dexterity_points),("characteristic.endurance",endurance_points)) if value>0)
    with psycopg.connect(url) as connection:return apply_determined_personal_natural_healing_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,determination_command_public_id=determination_command_public_id,allocations=allocations)

def determine_injury_crisis_cost(*,actor_public_id:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return determine_injury_crisis_cost_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id)

def resolve_injury_crisis(*,actor_public_id:str,resolution_kind:str,idempotency_key:str):
    url=database_url();authority=os.environ.get("EMPOROS_AUTHORITY_REFERENCE","emporos-local-player")
    with psycopg.connect(url) as connection:return resolve_injury_crisis_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,actor_public_id=actor_public_id,resolution_kind=resolution_kind)
