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
