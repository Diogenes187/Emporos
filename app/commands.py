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
from engine.broker_carousing import resolve_broker_operation_command  # noqa: E402
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
from engine.encounters import create_encounter_command,add_encounter_participant_command,transition_encounter_mode_command  # noqa: E402
from engine.combat_runtime import initialize_personal_combat_command,begin_personal_turn_command,move_personal_combatant_command,aim_personal_attack_command,complete_personal_turn_command,advance_personal_combat_round_command,advance_weapon_reload_command,hasten_personal_combatant_command,delay_personal_turn_command,resume_delayed_personal_turn_command,forfeit_delayed_personal_turn_command,change_personal_stance_command,set_personal_cover_command  # noqa: E402
from engine.combat_runtime import declare_personal_attack_command,declare_personal_reaction_command  # noqa: E402
from engine.commands import resolve_personal_attack_command,apply_personal_damage_command  # noqa: E402
from engine.combat_resolution_runtime import resolve_personal_combat_command  # noqa: E402
from engine.armor_runtime import equip_personal_armor_command,unequip_personal_armor_command  # noqa: E402
from engine.weapon_ready_runtime import advance_personal_weapon_ready_command  # noqa: E402
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
    with psycopg.connect(url) as connection:return apply_personal_damage_command(connection,initiator_reference=authority,idempotency_key=idempotency_key,damage_instance_public_id=damage_instance_public_id,allocations=allocations)

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
