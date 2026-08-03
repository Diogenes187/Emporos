"""Allowlisted AI-facing dispatch over authoritative gameplay commands."""
from __future__ import annotations
from dataclasses import dataclass
import inspect
from types import MappingProxyType
from typing import Any,Callable,Mapping
import psycopg
from engine.animal_skills import resolve_animal_skill_operation_command
from engine.broker_carousing import resolve_broker_operation_command,resolve_carousing_influence_command
from engine.devices import resolve_device_operation_command
from engine.navigation import resolve_navigation_command
from engine.recon import resolve_recon_command
from engine.regulatory import resolve_regulatory_task_command
from engine.spacecraft_journeys import start_spacecraft_journey_leg_command,complete_spacecraft_journey_leg_command
from engine.steward import resolve_steward_service_command
from engine.streetwise import resolve_streetwise_command
from engine.survival import resolve_survival_task_command
from engine.transport import resolve_transport_operation_command
from engine.travel_planning import plan_jump_journey_command
from engine.jump_attempts import resolve_jump_attempt_command
from engine.markets import open_trade_market_command
from engine.commerce_setup import prepare_trading_command
from engine.purchases import purchase_trade_goods_command
from engine.sales import sell_trade_goods_command
from engine.refueling import refuel_ship_command
from engine.ship_expenses import pay_ship_operating_expense_command
from engine.route_revenue import open_route_revenue_command
from engine.freight_contracts import accept_freight_contract_command
from engine.freight_delivery import deliver_freight_contract_command
from engine.passenger_booking import book_route_passengers_command
from engine.passenger_boarding import board_route_passengers_command
from engine.passenger_manifest import finalize_passenger_manifest_command
from engine.low_passage_revival import revive_low_passenger_command
from engine.postal_contracts import accept_postal_contract_command,deliver_postal_contract_command

@dataclass(frozen=True)
class ToolSpec:
 name:str;description:str;authority_kind:str;required_arguments:tuple[str,...];optional_arguments:tuple[str,...]
@dataclass(frozen=True)
class ToolOutcome:
 tool_name:str;command_public_id:str|None;replayed:bool|None;result:object
@dataclass(frozen=True)
class _RegisteredTool:
 spec:ToolSpec;handler:Callable[...,object];authority_parameter:str

_DEFINITIONS=(
 ('resolve_animal_skill_operation','Resolve a Farming, Riding, or Veterinary Medicine task.','actor','initiator_reference',resolve_animal_skill_operation_command),
 ('resolve_broker_operation','Search for a trade counterparty or determine a speculative price.','actor','initiator_reference',resolve_broker_operation_command),
 ('resolve_carousing_influence','Use stored Carousing and Social Standing to influence an NPC attitude.','actor','initiator_reference',resolve_carousing_influence_command),
 ('resolve_device_operation','Resolve a Demolitions, Electronics, or Mechanics device task.','actor','initiator_reference',resolve_device_operation_command),
 ('resolve_navigation','Create an audited normal-space course, Jump route, or post-Jump fix.','actor','initiator_reference',resolve_navigation_command),
 ('resolve_recon','Resolve a source-defined Recon operation.','actor','initiator_reference',resolve_recon_command),
 ('resolve_regulatory_action','Resolve an Admin or Advocate regulatory action.','actor','initiator_reference',resolve_regulatory_task_command),
 ('resolve_steward_service','Resolve journey-bound Steward service.','actor','initiator_reference',resolve_steward_service_command),
 ('resolve_streetwise','Resolve a source-defined Streetwise operation.','actor','initiator_reference',resolve_streetwise_command),
 ('resolve_survival_task','Resolve a source-defined Survival operation.','actor','initiator_reference',resolve_survival_task_command),
 ('resolve_transport_operation','Resolve spacecraft or vehicle operation using its canonical skill.','actor','initiator_reference',resolve_transport_operation_command),
 ('start_spacecraft_journey_leg','Depart on a ready spacecraft journey leg and consume reserved resources.','referee','referee_reference',start_spacecraft_journey_leg_command),
 ('complete_spacecraft_journey_leg','Arrive from an underway spacecraft leg and advance campaign state.','referee','referee_reference',complete_spacecraft_journey_leg_command),
 ('plan_jump_journey','Plan a legal Jump route and reserve its ship fuel.','actor','initiator_reference',plan_jump_journey_command),
 ('resolve_jump_attempt','Resolve the committed engineering Jump attempt.','actor','initiator_reference',resolve_jump_attempt_command),
 ('open_trade_market','Open the current system trade exchange and generate audited stock.','actor','initiator_reference',open_trade_market_command),
 ('prepare_trading','Create the trader account and ship cargo-hold custody boundary.','actor','initiator_reference',prepare_trading_command),
 ('purchase_trade_goods','Purchase quoted goods into the selected ship cargo hold.','actor','initiator_reference',purchase_trade_goods_command),
 ('sell_trade_goods','Sell owned cargo against an audited market quote.','actor','initiator_reference',sell_trade_goods_command),
 ('refuel_ship','Purchase refined or unrefined fuel for a ship.','actor','initiator_reference',refuel_ship_command),
 ('pay_ship_operating_expense','Pay a supported berthing, maintenance, or life-support expense.','actor','initiator_reference',pay_ship_operating_expense_command),
 ('open_route_revenue','Generate freight and passenger availability for a destination.','actor','initiator_reference',open_route_revenue_command),
 ('accept_freight_contract','Reserve available freight for a planned journey.','actor','initiator_reference',accept_freight_contract_command),
 ('deliver_freight_contract','Deliver arrived freight and collect its payment.','actor','initiator_reference',deliver_freight_contract_command),
 ('book_route_passengers','Book available passengers into journey accommodations.','actor','initiator_reference',book_route_passengers_command),
 ('board_route_passengers','Board booked passengers and collect their fares.','actor','initiator_reference',board_route_passengers_command),
 ('finalize_passenger_manifest','Validate accommodations and steward coverage before departure.','actor','initiator_reference',finalize_passenger_manifest_command),
 ('revive_low_passenger','Resolve an arrived low-passage revival check.','actor','initiator_reference',revive_low_passenger_command),
 ('accept_postal_contract','Attempt to secure a postal contract for an armed, crewed ship.','actor','initiator_reference',accept_postal_contract_command),
 ('deliver_postal_contract','Deliver carried mail and collect its payment.','actor','initiator_reference',deliver_postal_contract_command),
)
_HOST_ARGUMENTS=frozenset({'c','connection','idempotency_key','initiator_reference','referee_reference','random_source'})
def _register(definition)->_RegisteredTool:
 name,description,authority,authority_parameter,handler=definition;signature=inspect.signature(handler);required=[];optional=[]
 for parameter in signature.parameters.values():
  if parameter.name in _HOST_ARGUMENTS:continue
  (required if parameter.default is inspect.Parameter.empty else optional).append(parameter.name)
 return _RegisteredTool(ToolSpec(name,description,authority,tuple(required),tuple(optional)),handler,authority_parameter)
_REGISTRY=MappingProxyType({entry.spec.name:entry for entry in map(_register,_DEFINITIONS)})
def available_tools()->tuple[ToolSpec,...]:return tuple(entry.spec for entry in _REGISTRY.values())
class GameplayOrchestrator:
 def __init__(self,connection:psycopg.Connection,*,authority_reference:str,random_source=None):
  if not authority_reference.strip():raise ValueError('Authority reference is required')
  self._connection=connection;self._authority=authority_reference;self._random_source=random_source
 def invoke(self,tool_name:str,*,idempotency_key:str,arguments:Mapping[str,Any])->ToolOutcome:
  if not idempotency_key.strip():raise ValueError('Idempotency key is required')
  entry=_REGISTRY.get(tool_name)
  if entry is None:raise KeyError(f'Gameplay tool is not allowlisted: {tool_name}')
  supplied=set(arguments);allowed=set(entry.spec.required_arguments)|set(entry.spec.optional_arguments);unknown=supplied-allowed;missing=set(entry.spec.required_arguments)-supplied
  if unknown:raise TypeError('Unknown or host-controlled arguments: '+', '.join(sorted(unknown)))
  if missing:raise TypeError('Missing required arguments: '+', '.join(sorted(missing)))
  values=dict(arguments);values[entry.authority_parameter]=self._authority;values['idempotency_key']=idempotency_key
  if self._random_source is not None and 'random_source' in inspect.signature(entry.handler).parameters:values['random_source']=self._random_source
  result=entry.handler(self._connection,**values);return ToolOutcome(tool_name,getattr(result,'command_public_id',None),getattr(result,'replayed',None),result)
