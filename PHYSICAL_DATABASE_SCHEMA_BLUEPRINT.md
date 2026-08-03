# Relational Cepheus Engine Physical Database Schema Blueprint

## Status

Planning blueprint for the complete relational Cepheus engine.

This document translates the accepted constitution, inheritance assessment,
responsibility map, relational domain model, gameplay contracts, vessel
encounter pattern, and Cepheus rule decisions into physical relational
boundaries.

It is not yet a migration. No production table should be created until the open
database-engine and identifier decisions at the end of this document are
approved.

## Goals

The physical schema must:

- keep the relational database authoritative;
- distinguish source definitions from campaign instances;
- distinguish current state from immutable history;
- enforce campaign isolation;
- support player manual edits without bypassing integrity;
- record every material mutation;
- preserve the Cepheus rule and content versions used by resolutions;
- support personal and ship combat as separate mechanical scales;
- connect boarding operations to personal encounters;
- prevent rejected narration from becoming current context;
- avoid persistent JSON domain structures;
- migrate reproducibly from its first release.

## Proposed Database Areas

Table names use prefixes to make ownership visible even when the chosen database
does not support schemas.

| Prefix | Ownership | Purpose |
|---|---|---|
| `sys_` | Shared Foundation | migrations, packages, operations |
| `iam_` | Shared Foundation | accounts, roles, campaign authority |
| `cmd_` | Shared Foundation | commands, events, receipts, randomness |
| `nar_` | Shared Foundation | scene packets, narration, revisions |
| `can_` | Shared Foundation | campaign facts and decisions |
| `src_` | Cepheus Engine/tooling | sources, licenses, imports, review |
| `rule_` | Cepheus Engine | versioned Cepheus rule definitions |
| `cg_` | Cepheus Engine | chargen definitions and sessions |
| `camp_` | Cepheus Engine | campaign, clock, membership-facing state |
| `actor_` | Cepheus Engine | characters, NPCs, skills, relationships |
| `loc_` | Cepheus Engine | locations, containment, connections |
| `inv_` | Cepheus Engine | items, containers, possession |
| `fin_` | Cepheus Engine | accounts and balanced financial entries |
| `mkt_` | Cepheus Engine | markets, stock, quotes, executions |
| `journey_` | Cepheus Engine | travel, legs, jumps, refueling |
| `ship_` | Cepheus Engine | ship definitions and campaign vessels |
| `enc_` | Cepheus Engine | personal encounters and combat |
| `senc_` | Cepheus Engine | ship encounters and combat |
| `ability_` | Cepheus Engine | mind powers, costs, effects |
| `health_` | Cepheus Engine | damage, conditions, treatment |

Prefixes indicate module responsibility, not permission for cross-module direct
writes.

## Naming and Column Conventions

### Table Names

- singular nouns;
- explicit domain prefix;
- no misleading genre-neutral euphemisms for native Cepheus concepts;
- join tables name both related concepts;
- history and current-state tables are visibly distinct.

### Standard Identity Columns

Every authoritative entity requires:

- internal primary key;
- stable public identifier;
- creation timestamp;
- appropriate version or concurrency token.

The exact key types remain an open technology decision. Foreign keys always use
internal keys; external APIs expose public identifiers.

### Campaign Ownership

Every mutable game-state table either:

- carries `campaign_id` directly; or
- has an unavoidable foreign-key path to one campaign and is not queried without
  that parent.

High-risk mutable tables should carry `campaign_id` directly even when
derivable, permitting composite foreign keys that prevent cross-campaign
references.

### Time

Separate:

- system timestamps, stored in an unambiguous UTC representation;
- campaign time, stored in product calendar fields;
- round and phase counters, stored in encounter tables;
- source publication dates, which are not gameplay time.

### Money and Quantities

- monetary values use integer minor units when currency supports them;
- no floating-point money;
- quantities and capacities use explicit units;
- unit conversion is rule/application behavior, not an unlabeled number;
- ordinary stock and account mutations cannot silently underflow.

### Text

Structured state does not hide in text. Text columns are appropriate for:

- names;
- descriptions;
- source excerpts within license limits;
- player notes;
- narration;
- decision rationale;
- error and audit messages.

Text is not appropriate for skills, inventory, cargo, crew, effects,
relationships, choices, or event links.

## Shared Foundation Tables

### System and Versioning

#### `sys_schema_migration`

Primary key: migration version.

Required fields:

- version;
- name;
- checksum;
- applied timestamp;
- application build identity.

Constraints:

- version unique and ordered;
- checksum cannot change after application.

#### `sys_content_package`

One known package release.

Required relationships:

- package identity;
- semantic or declared version;
- installation state;
- content checksum;
- source package where applicable.

Unique key: package identity plus version.

#### `sys_product_seed`

Records foundation and Product Seed ancestry.

Required fields:

- seed identity;
- adopted version;
- adopted timestamp;
- status: tracking, detached, or omitted;
- detachment rationale where applicable.

### Identity and Authority

#### `iam_account`

Human account identity and security state. Password material, if locally
managed, uses a dedicated credential table and approved password hashing.

#### `iam_role`

Product roles such as player, referee, and administrator.

#### `iam_campaign_membership`

Composite uniqueness: campaign plus account plus role.

#### `iam_character_controller`

Relates account, character, authority level, and effective period.

Constraint: account and character must belong to the same campaign context.

### Commands

#### `cmd_command`

Required fields:

- campaign;
- public command identifier;
- command type;
- command contract version;
- initiator type;
- optional initiating account;
- idempotency scope and key;
- status;
- submitted, begun, and completed timestamps;
- optional command being compensated;
- rejection/failure category and explanation.

Unique key: campaign plus idempotency scope plus idempotency key.

The command's domain arguments live in typed command-detail tables when they
must be retained. An optional diagnostic payload may exist only under an
architectural exemption and is never authoritative state.

#### `cmd_event`

Required fields:

- campaign;
- command;
- sequence number within campaign;
- event type;
- event contract version;
- occurred campaign time;
- recorded system time.

Unique key: campaign plus sequence.

Events are immutable after command completion.

#### Typed Event Details

Important events have typed detail tables sharing the event primary key:

- `cmd_event_actor_moved`;
- `cmd_event_item_transferred`;
- `cmd_event_funds_posted`;
- `cmd_event_damage_applied`;
- `cmd_event_condition_changed`;
- `cmd_event_encounter_transition`;
- `cmd_event_manual_override`;
- additional event types added through migrations.

This avoids a permanent `detail_json` authority column.

#### `cmd_receipt`

Required fields:

- campaign;
- command;
- receipt sequence within command;
- mechanical operation;
- rules implementation version;
- summary;
- status;
- optional receipt being corrected.

Unique key: command plus receipt sequence.

Receipts are immutable. Corrections create relationships rather than updates.

#### `cmd_random_result`

Required fields:

- receipt;
- use sequence;
- expression or named procedure;
- raw result;
- random-service version;
- seed/reference metadata required by policy.

Unique key: receipt plus use sequence.

#### `cmd_receipt_rule`

Links a receipt to one or more versioned `rule_rule` records and source
locators.

#### `cmd_event_reversal`

Links a compensating command/event to an earlier event.

### Narration

#### `nar_scene_packet`

Stores packet identity, campaign, assembling command/event boundary, projection
version, audience/authority scope, and creation time.

The provider payload is a disposable projection. The durable packet is
represented through relations below.

#### `nar_scene_actor`

Links visible/relevant actors to the packet and records disclosure scope.

#### `nar_scene_location`

Links permitted locations, connections, and features.

#### `nar_scene_fact`

Links established facts visible to the audience.

#### `nar_scene_event`

Links committed events the AI may describe.

#### `nar_scene_item`

Links permitted item/inventory facts.

#### `nar_scene_intention`

Links legal NPC intentions available for selection.

#### `nar_attempt`

Immutable provider response with:

- scene packet;
- provider/model identity;
- product prompt version;
- response text;
- validation status;
- provider timing and usage metadata.

#### `nar_validation_issue`

One structured validation failure tied to an attempt and, where possible, a
claimed entity or event.

#### `nar_decision`

Acceptance or rejection by an authorized account, reason, category, and time.

Constraint: only a validated attempt may become accepted unless an authorized
human explicitly overrides validation.

#### `nar_revision`

Links a revision attempt to the attempt it revises.

No narration text is overwritten.

### Canon

#### `can_fact`

Required fields:

- campaign;
- fact type;
- subject type and typed subject relation;
- status;
- visibility;
- effective campaign time;
- provenance type;
- proposing command/account;
- deciding account and time where applicable;
- human-readable statement.

Important fact types should receive typed fact-detail tables rather than relying
on polymorphic text.

#### `can_fact_relation`

Relates facts with typed relationships such as supports, contradicts,
supersedes, or depends upon.

#### `can_actor_knowledge`

Separates an established fact from an actor knowing that fact.

## Source, License, and Import Tables

### `src_work`

Publication identity, edition, publisher, publication date, and classification.

### `src_license`

License identity, version, reference text or location, and obligations.

### `src_work_license`

Scope-specific relation between source work and license.

### `src_locator`

Required fields:

- source work;
- locator type;
- heading path;
- printed/PDF page where stable;
- paragraph/table/import anchor;
- normalized display citation.

### `src_import_batch`

Source file identity, checksum, importer version, execution time, and status.

### `src_import_candidate`

Temporary candidate type, source locator, staging value, validation status, and
review status.

Staging content may use JSON because it is temporary and nonauthoritative.
Approved candidates are materialized into typed rule tables.

### `src_review`

Reviewer, decision, corrections, rationale, and time.

### `src_record_provenance`

Relates each approved rules/content record to package, source locator, import
candidate, classification, and review.

## Rules Catalogue Tables

### Common Rule Identity

#### `rule_rule`

A stable, versioned identity for an executable or referential rule.

Required fields:

- content package;
- rule code;
- name;
- rule category;
- status;
- effective package version.

Unique key: content package plus rule code.

#### `rule_interpretation`

Records whether implementation follows explicit source, source option, agreed
interpretation, or agreed addition.

Required relationship to the Cepheus Rule Decision Register entry when not a
direct source rule.

### Characteristics and Skills

- `rule_characteristic`
- `rule_characteristic_modifier_band`
- `rule_skill`
- `rule_skill_specialty`
- `rule_skill_prerequisite`

Key constraints:

- characteristic and skill codes unique per package;
- specialty unique within its parent skill;
- prerequisites cannot reference removed package records.

### Difficulties and Tasks

- `rule_difficulty`
- `rule_task`
- `rule_task_skill_option`
- `rule_task_characteristic_option`
- `rule_task_modifier`
- `rule_opposed_task`
- `rule_extended_task`

Modifiers have typed conditions and numeric values. They are not embedded in
description text.

### Random Tables

- `rule_random_table`
- `rule_random_table_entry`
- `rule_random_entry_effect`
- `rule_random_entry_text`

Constraints:

- result ranges do not overlap within one table unless source behavior
  explicitly requires it;
- dice expression is versioned;
- structured results reference definitions/effects;
- player and referee visibility are explicit.

## Character-Creation Definition Tables

- `cg_method`
- `cg_step`
- `cg_step_transition`
- `cg_choice`
- `cg_career`
- `cg_assignment`
- `cg_rank`
- `cg_qualification_rule`
- `cg_survival_rule`
- `cg_advancement_rule`
- `cg_skill_table`
- `cg_skill_result`
- `cg_event`
- `cg_mishap`
- `cg_benefit_table`
- `cg_benefit_result`
- `cg_connection_option`

Every definition belongs to a content package and has provenance.

Random table results link to typed skill, characteristic, money, possession,
relationship, or status effects.

## Campaign and Actor Tables

### Campaign

#### `camp_campaign`

Campaign identity, title, play mode, status, created time, and installed product
configuration.

#### `camp_clock`

Exactly one current clock per campaign.

Fields must support the Cepheus calendar selected for the engine without
using a prose date as authority.

### Actors

#### `actor_character`

Required fields:

- campaign;
- name;
- actor kind;
- player/NPC origin;
- lifecycle status;
- template/procedure origin where applicable;
- current concurrency version.

#### `actor_characteristic`

Composite primary/unique key: character plus characteristic definition.

Stores current and permitted maximum/minimum values where rules require.

#### `actor_skill`

Composite unique key: character plus skill plus nullable specialty, with a
database-specific uniqueness strategy that treats “no specialty” correctly.

#### `actor_career_term`

One completed term with career, assignment, rank, sequence, and campaign/chargen
time.

#### `actor_career_event`

Links experienced event or mishap and resulting effects.

#### `actor_benefit`

Links a benefit definition and its realized structured award.

#### `actor_note`

Authored note with author and visibility. Notes are not canonical mechanics.

### NPC Definitions

- `actor_npc_template`
- `actor_npc_template_characteristic`
- `actor_npc_template_skill`
- `actor_npc_template_item`
- `actor_npc_behavior`
- `actor_npc_objective`
- `actor_template_instantiation`

Named NPCs become ordinary `actor_character` rows. Abstract background units use
the encounter-unit tables and do not masquerade as full characters.

### Relationships

- `actor_relationship_type`
- `actor_relationship`
- `actor_faction`
- `actor_faction_membership`
- `actor_faction_relationship`
- `actor_reputation`

Directed relationships store source, status, strength where defined, and
effective time.

## Location and Map Tables

### `loc_location`

Campaign location identity, type, name, visibility, and current status.

### `loc_containment`

Parent/child location relationship.

Constraints:

- one current direct parent;
- no self-parent;
- no containment cycles.

Cycle prevention may require application validation plus a database trigger or
recursive constraint strategy.

### `loc_connection`

From/to locations, directionality, traversal state, access rule, distance, and
visibility.

### `loc_feature`

Structured feature definition/instance such as airlock, hatch, console, cover,
or breach.

### `loc_actor_position`

Current actor location plus optional mapped coordinates and stance.

Only one current position per actor.

### `loc_item_position`

Used only when an item is directly located rather than inside a container.

### Space Map

- `loc_sector`
- `loc_subsector`
- `loc_star_system`
- `loc_celestial_body`
- `loc_world_profile`
- `loc_trade_code`
- `loc_world_trade_code`
- `loc_star_route`

Coordinates and route distances use explicit constraints and units.

## Inventory and Equipment Tables

### Definitions

- `inv_item_definition`
- `inv_item_category`
- `inv_weapon_definition`
- `inv_weapon_range`
- `inv_ammunition_definition`
- `inv_armor_definition`
- `inv_equipment_effect`
- `inv_modification_definition`

### Instances and Lots

#### `inv_item_instance`

One individually tracked object with definition, campaign, condition, owner, and
provenance.

#### `inv_lot`

One fungible quantity with definition, campaign, owner, condition, and
provenance.

#### `inv_container`

A storage context owned by an actor, vessel, location, or item.

The owner relationship should use typed association tables rather than one
unconstrained polymorphic identifier:

- `inv_actor_container`;
- `inv_ship_container`;
- `inv_location_container`;
- `inv_item_container`.

#### `inv_container_item`

Places an item instance in one container.

#### `inv_container_lot`

Places a lot and quantity in one container.

Constraints:

- one immediate container per item;
- lot quantity positive;
- capacity checked transactionally;
- containment cycle prohibited;
- ownership and location remain separate.

### Equipment State

- `inv_item_condition`
- `inv_item_modification`
- `inv_weapon_ammunition`
- `inv_equipped_item`

No character or ship carries a `gear_json`, `cargo_json`, or `crew_json` field.

## Finance and Market Tables

### Finance

#### `fin_currency`

Currency code, precision, and package.

#### `fin_account`

Campaign, owner through typed association, currency, account kind, and status.

#### `fin_transaction`

Command, description, campaign time, and transaction status.

#### `fin_entry`

Transaction, account, signed integer amount, and sequence.

Constraint: completed transactions balance to zero per currency unless a
documented product accounting boundary uses an explicit external account.

Account balances are derived from entries or maintained as a transactionally
verified cache, never mutated without entries.

### Markets

- `mkt_market`
- `mkt_session`
- `mkt_trade_good`
- `mkt_trade_modifier`
- `mkt_stock`
- `mkt_quote`
- `mkt_quote_modifier`
- `mkt_order`
- `mkt_execution`

Important unique keys:

- market plus session period;
- session plus good for stock;
- session plus good plus side plus negotiator/party plus quote scope.

Execution links:

- quote;
- stock change;
- inventory transfer;
- financial transaction;
- originating command.

Stock reduction uses a guarded update or row lock appropriate to the selected
database. It cannot rely on application read-then-write alone.

## Journey Tables

- `journey_journey`
- `journey_leg`
- `journey_participant`
- `journey_resource_commitment`
- `journey_progress`
- `journey_event`
- `journey_jump_attempt`
- `journey_refuel_operation`

Constraints:

- ordered legs unique within journey;
- active actor/vessel cannot be committed to incompatible journeys;
- origin matches authoritative current location when beginning;
- completed legs are immutable;
- fuel consumption links to ship-resource movement and command receipt.

## Ship Tables

### Definitions

- `ship_class`
- `ship_class_characteristic`
- `ship_component_definition`
- `ship_class_component`
- `ship_weapon_definition`
- `ship_class_weapon`
- `ship_crew_position_definition`
- `ship_class_crew_position`

All definitions belong to content packages and retain provenance.

### Campaign Ships

#### `ship_ship`

Campaign, class, name, registration, lifecycle status, legal status, and current
concurrency version.

#### `ship_component`

Installed component instance, rating, operational status, and permanent damage.

#### `ship_resource`

Typed current resource quantity and capacity: fuel, power where rules track it,
life support, ammunition, and other Cepheus-defined resources.

#### `ship_crew_position`

The actual position available aboard a ship.

#### `ship_crew_assignment`

Character, position, duty status, and effective period.

#### `ship_deck_location`

Links a ship to `loc_location` compartments and features.

#### `ship_damage`

Persistent hull, structure, armor, component, or crew damage tied to its source
action and receipt.

#### `ship_temporary_restoration`

Battle-only damage-control restoration. It expires at combat end and does not
overwrite permanent component damage.

#### `ship_legal_interest`

Ownership, mortgage, lien, charter, or other legal relationship.

#### `ship_operational_control`

Current operational controller, basis, effective time, and originating command.

Legal interest and operational control are deliberately separate.

## Personal Encounter Tables

### `enc_encounter`

Campaign, location, encounter type, status, awareness stage, hostility state,
round, subphase, and source.

### `enc_participant`

Character, side, entry/exit state, awareness, surprise, and encounter status.

### `enc_abstract_unit`

Cepheus abstract friendly/background/enemy unit with side, unit size, Morale
where assigned, visibility/concealment, and status.

### `enc_unit_member_transition`

Records promotion from abstract unit presence to a named persistent actor.

### `enc_range_relation`

Authoritative theatre-of-the-mind relationship between participants or sides
using Cepheus range bands.

### `enc_map_position`

Mapped local coordinates/distance. Range band is derived under the agreed
positioning decision.

### `enc_round_resource`

Significant action, minor action, reaction/parry/counter state, and movement
used for one participant and round.

### `enc_intention`

Generated legal intention with:

- participant;
- action type;
- targets;
- weapon/ability/equipment;
- legal-from state version;
- selecting authority;
- status and expiry.

### `enc_action`

Resolved personal action, declared intention, acting participant, round,
resolution order, status, and receipt.

Resolution order enforces:

- player-character phase;
- player-chosen ordering within that phase;
- allied NPC phase;
- enemy phase;
- Cepheus Melee-before-Direct-Fire precedence.

### Personal Action Details

Typed one-to-one or one-to-many detail tables:

- `enc_action_move`;
- `enc_action_melee`;
- `enc_action_direct_fire`;
- `enc_action_area_fire`;
- `enc_action_parry`;
- `enc_action_counterattack`;
- `enc_action_reload`;
- `enc_action_extended`;
- `enc_action_surrender`;
- `enc_action_other_task`.

### `enc_objective`

Actor/side objective and completion status.

### `enc_outcome`

Encounter completion and structured result.

## Ship Encounter Tables

### `senc_encounter`

Campaign, status, six-minute round, current Cepheus phase, environment, and
source.

Constraint: the initial approved implementation has at most two active ship
combatants.

Additional vessels may be related to the broader noncombat scene but cannot
become active ship-combat participants.

### `senc_participant`

Ship, side, detection state, identity state, readiness, entry/exit state, and
status.

### `senc_relative_range`

The authoritative Cepheus relative range band between the two active
combatants.

### `senc_detection`

Detection/tracking/identification attempts and current result.

### `senc_crew_assignment`

Encounter-specific duty assignment linked to persistent ship crew positions.

### `senc_weapon_commitment`

Weapon/bay/turret group committed, held in reserve, assigned to missile defense,
or unavailable for the round.

### `senc_advantage`

Both submitted values/receipts, winning participant, chosen range change, and
round.

### `senc_intention`

Engine-generated legal ship intention, selecting authority, targets, crew
operator, component/resource requirements, and state version.

### `senc_action`

Resolved action with phase, acting ship, responsible character/Crew Rating,
target, intention, receipt, and status.

### Ship Action Details

- `senc_action_attack`;
- `senc_action_maneuver`;
- `senc_action_detection`;
- `senc_action_screen`;
- `senc_action_damage_control`;
- `senc_action_communication`;
- `senc_action_escape`;
- `senc_action_surrender`;
- `senc_action_boarding`.

### `senc_missile_salvo`

Launching weapon group, target, launch round, arrival phase/round, missile
quantity, interception state, and result.

### `senc_screen_state`

Current rating, degradation, collapse, activation time, and recharge state.

### `senc_damage_result`

Raw damage, screen result, armor reduction, post-armor damage, Ship Damage table
result, hull/structure loss, and linked component effects.

Personal attack Effect is never added to this ship-damage record.

### Boarding

#### `senc_boarding_operation`

Required fields:

- ship encounter;
- attacking and defending ships;
- status;
- approach method;
- docking/attachment state;
- access point;
- boarding objective;
- linked personal encounter;
- operational-control result.

#### `senc_boarding_party`

Character membership, originating ship/location, equipment container, and
status.

#### `senc_boarding_access_attempt`

Source procedure used, acting character/ship, difficulty, time, receipt, and
result.

#### `senc_boarding_outcome`

Access secured/repelled, compartment effects, defender status, command-control
conditions, and linked control command.

Operational control may change only when the approved conditions are all
represented:

- surrender/abandonment/no capable resistance;
- physical access to usable command controls;
- capable operator assuming controls.

No row here transfers `ship_legal_interest`.

## Health and Ability Tables

### Health

- `health_damage_type`
- `health_damage_instance`
- `health_damage_allocation`
- `health_injury`
- `health_condition_definition`
- `health_actor_condition`
- `health_treatment`
- `health_recovery`

Personal damage allocations reference physical characteristics and preserve the
Cepheus sequence and player choices.

### Abilities

- `ability_definition`
- `ability_category`
- `ability_cost`
- `ability_target_rule`
- `ability_resolution_rule`
- `ability_effect_definition`
- `ability_effect_component`
- `ability_character`
- `ability_use`
- `ability_use_target`
- `ability_use_cost`
- `ability_use_effect`

Mind powers are populated from Cepheus definitions. No generic spell behavior
is invented for the Cepheus engine.

## Character-Creation Session Tables

- `cg_session`
- `cg_step_instance`
- `cg_choice_instance`
- `cg_random_result`
- `cg_provisional_characteristic`
- `cg_provisional_skill`
- `cg_provisional_career_term`
- `cg_provisional_relationship`
- `cg_provisional_benefit`
- `cg_provisional_item`
- `cg_commit`

Constraints:

- one current step per active session;
- choices reference legal definitions for the session's package version;
- completed steps are immutable;
- rerolls create new receipted random results without erasing earlier attempts;
- commit is idempotent;
- no `choices_json` authority column exists.

## Transaction Ownership

Only application services own multi-table transactions.

| Command family | Primary transaction owner |
|---|---|
| Manual character edit | Character application service |
| Item transfer | Inventory application service |
| Funds transfer | Finance application service |
| Market purchase/sale | Market application service coordinating inventory and finance |
| Journey progress | Journey application service coordinating clock, location, and resources |
| Personal action | Personal encounter service coordinating inventory, health, and effects |
| Ship action | Ship encounter service coordinating ship state, crew, resources, and damage |
| Boarding transition | Ship encounter service coordinating locations and personal encounter creation |
| Operational capture | Boarding service coordinating control without changing legal ownership |
| Ability use | Ability service coordinating costs, tasks, conditions, and effects |
| Narration decision | Narration service; never changes mechanics |

Repositories do not commit independently. A command either commits all state,
events, and receipts or none.

## Immutability Policy

Immutable after completion:

- applied migrations;
- approved source import provenance;
- completed commands;
- domain events;
- mechanical receipts;
- random results;
- financial entries;
- completed trade executions;
- completed encounter actions;
- narration attempts;
- narration decisions.

Corrected through new records:

- financial mistakes;
- manual edits;
- event interpretations;
- narration;
- canon;
- operational control;
- inventory transfers.

Mutable current state with concurrency protection:

- character characteristics and skills;
- locations;
- inventory placement and quantities;
- market stock;
- account balance cache if used;
- ship resources and component status;
- encounter phase and participation;
- current conditions;
- accepted narration pointer/projection.

## Database-Level Integrity

The schema and database must enforce:

- foreign keys enabled in every environment;
- no cross-campaign mutable references;
- unique command idempotency keys;
- nonnegative ordinary quantities;
- balanced completed financial transactions;
- one immediate container per item;
- no containment cycles;
- one current direct actor location;
- no stock oversell;
- one accepted current narration per narrated event set;
- no rejected narration selected as current;
- no more than two active ship-combat participants initially;
- one active range relationship for those combatants;
- legal encounter phase transitions;
- immutable completed receipt/random rows;
- source provenance for released rules content;
- explicit architectural exemption for any persistent JSON column.

Some invariants require both database enforcement and application validation.
Application validation alone is insufficient for concurrency-sensitive money,
stock, identity, and containment constraints.

## JSON Exemption Process

Any proposed persistent JSON column requires a recorded architecture decision
that answers:

1. Why does the data have no stable relational structure?
2. Is it authoritative or diagnostic?
3. Which queries, constraints, and relationships are knowingly sacrificed?
4. How is it versioned?
5. How can it be migrated?
6. Why is a child table not appropriate?

Prohibited exemptions include skills, careers, gear, cargo, crew, choices,
effects, market boards, event relationships, or accepted campaign facts.

## Index Families

Exact indexes follow query prototypes, but the initial design requires:

- campaign plus public identifier for all exposed campaign entities;
- campaign event sequence;
- command idempotency;
- account campaign memberships;
- current actor and ship locations;
- character skill lookup;
- container contents;
- item/lot owner and location;
- financial entries by account and transaction;
- active market session and stock;
- active journey by participant;
- ship component and crew assignment;
- encounter participants and current intentions;
- ship encounter phase, salvo arrival, and active range;
- accepted narration and unresolved narration decisions;
- established visible facts by campaign and subject;
- content records by package and source locator.

Every index must correspond to a demonstrated query, uniqueness rule, or
referential need.

## Migration Order

Recommended initial migration families:

1. system migration and package metadata;
2. source, license, import, and provenance;
3. identity and campaign;
4. command, event, receipt, and randomness;
5. narration and canon;
6. core rules catalogue;
7. character-creation definitions;
8. actors, relationships, and factions;
9. locations and space map;
10. inventory and equipment;
11. finance and markets;
12. ships and crew;
13. journeys and jumps;
14. health and abilities;
15. personal encounters;
16. ship encounters and boarding;
17. chargen sessions;
18. read-model views and performance indexes.

Each migration family requires:

- forward migration;
- schema verification;
- representative fixture upgrade;
- rollback or documented compensating recovery strategy;
- compatibility statement;
- migration test from every supported prior release.

## Vertical-Slice Physical Subset

The first executable schema should not create every table above.

It should include only enough to prove:

- migration and package versioning;
- one source work, locator, rule, and provenance chain;
- account, campaign, membership, and controlled character;
- characteristics and one skill;
- two locations and one connection;
- item definition, lot/container, and possession;
- currency, accounts, and balanced entries;
- market, session, stock, held quote, and atomic trade;
- command, event, receipt, and random result;
- one personal encounter, intention, action, and damage/condition result;
- scene packet, narration attempt, rejection, and accepted revision;
- one manual override.

The second executable slice adds:

- two ships and their classes/components/crew;
- ship encounter phases, range, Advantage, attack, damage, and control;
- boarding approach/access;
- linked personal encounter on deck locations;
- operational capture under the approved conditions.

## Required Schema Tests

### Structural Tests

- every declared foreign key exists and is enabled;
- every campaign-owned table is isolated;
- prohibited JSON authority columns do not exist;
- migration checksums are stable;
- released rule records have provenance.

### Constraint Tests

- cross-campaign item transfer fails;
- duplicate command retry returns the original result;
- negative stock fails;
- two buyers cannot buy the final unit;
- unbalanced financial transaction cannot complete;
- one item cannot occupy two containers;
- containment cycles fail;
- rejected narration cannot become current;
- third active ship combatant fails under the initial decision;
- operational control cannot transfer without all approved conditions;
- legal ownership remains unchanged after capture.

### History Tests

- correction does not delete the original receipt;
- manual reversal produces new events;
- reroll retains the earlier roll;
- narration revision retains the rejected attempt;
- ship damage control does not erase permanent damage;
- content updates do not alter the rule version on old receipts.

## Open Technology Decisions

These are engineering choices rather than Cepheus rules and require agreement
before migrations:

### DB-OPEN-001 - Database Engine

**Decision:** PostgreSQL is the sole authoritative database engine for the
complete relational Cepheus engine.

Persistence integration tests use PostgreSQL behavior. Pure domain unit tests
may operate without a database, but SQLite is not used as a substitute
authoritative engine.

**Rationale:** PostgreSQL provides the concurrency, row locking, constraints,
recursive queries, transactional behavior, migrations, and operational tooling
needed for markets, inventories, balanced finance, encounter state, public
deployment, and future growth. Supporting two authoritative SQL engines would
weaken guarantees and multiply persistence testing.

**Status:** Approved by Raymond on 2026-07-27.

### DB-OPEN-002 - Identifier Strategy

**Decision:** Authoritative entities use:

- `BIGINT GENERATED ALWAYS AS IDENTITY` internal primary keys;
- PostgreSQL `UUID` public identifiers generated randomly;
- internal keys for database foreign-key relationships;
- public UUIDs for URLs, APIs, imports, exports, and external references.

Sequential internal keys are never exposed as public resource identities.

**Rationale:** This keeps joins, indexes, fixtures, and foreign keys efficient
while providing stable, non-enumerable public identities.

**Status:** Approved by Raymond on 2026-07-27.

### DB-OPEN-003 - Event Detail Representation

**Decision:**

- typed event-detail tables for domain-significant facts;
- narrow text summary for human audit;
- optional nonauthoritative diagnostic payload only under JSON exemption.

**Rationale:** Additional typed tables preserve relational authority,
constraints, queryability, provenance, and migrations. A generic event payload
must not become a second domain store.

**Status:** Approved by Raymond on 2026-07-27.

### DB-OPEN-004 - Financial Balance Strategy

**Decision:** Initial account balances are derived from immutable balanced
financial entries.

A transactionally verified balance cache or materialized projection may be
added only after production measurements demonstrate a need. Any cache remains
rebuildable and is verified against the ledger.

**Rationale:** Financial correctness must not depend on an independently
mutable cached value.

**Status:** Approved by Raymond on 2026-07-27.

### DB-OPEN-005 - Rules Customization

**Decision:** Released Cepheus rule and content records are immutable.

Campaign customization is provided through explicit, versioned house-rule
packages. A campaign records exactly which released and house-rule package
versions govern it. Ad hoc mutation of released source definitions is
prohibited.

**Rationale:** This preserves source fidelity and old mechanical receipts while
still allowing agreed customization to become a supported product feature.

**Status:** Approved by Raymond on 2026-07-27.

## Recommended Next Decision

The foundational schema policies are settled. The next planning step is the
Cepheus source-ingestion and normalization plan, which will define how the DOCX
and approved supporting sources become reviewed PostgreSQL records with
traceable provenance.
