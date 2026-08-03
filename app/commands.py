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
        return command(connection,referee_reference=authority,idempotency_key=idempotency_key,journey_public_id=journey_public_id,leg_order=1)

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
