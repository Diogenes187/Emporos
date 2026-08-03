# Relational Cepheus Engine Domain Model

## Status

Planning model for the complete relational Cepheus engine.

This is a logical relational model, not yet a physical SQL schema. It identifies
authoritative records, ownership boundaries, important relationships, and table
families. Column types, indexes, database-specific features, and migration syntax
will follow after the gameplay contracts are settled.

## Engine Scope

Base Cepheus implements the complete science-fiction role-playing engine
governed by the Cepheus Engine SRD published through the Open Gaming Network
website and its related GitHub source repository.

The Cepheus Universal material available in `books` remains a separate rules
package and comparison source. Universal rules are not mixed into this product
without an explicit, recorded product decision.

It is not a runtime genre selector and does not embed Norse, Roman, or other
future product content in the core schema. Cepheus's own worlds, spacecraft,
travel, trade, and space-combat concepts are native engine domains and use clear
science-fiction vocabulary. Later products derive from this engine.

## Modeling Rules

### Database Authority

Persistent rules, content, and campaign state are relational records.

JSON is permitted only for:

- temporary import staging;
- API and UI projections;
- export packages;
- provider-specific AI payloads;
- explicitly unstructured diagnostic metadata.

An entity does not become unstructured merely because its fields vary. Skills,
career terms, inventory, cargo, crew, effects, tables, choices, and event
relationships all have natural relational representations.

### Definition Versus Instance

The model distinguishes reusable definitions from campaign instances.

Examples:

- `weapon_definition` describes a laser carbine.
- `item_instance` is the particular laser carbine carried by a character.
- `ship_class` describes a Free Trader.
- `ship` is the named vessel operating in a campaign.
- `npc_template` describes a type of customs officer.
- `character` is the officer currently questioning the crew.

Definitions belong to versioned content packages. Instances belong to campaigns.

### Current State Versus History

Current state remains directly queryable. Events and receipts explain how it
became current.

The application must not reconstruct a character's inventory, current location,
or wounds by replaying prose. Event replay may support audit and recovery, but it
is not the ordinary query path.

### Commands Own Mutations

Every material state change is produced by an application command inside one
transaction. Domain tables do not write event or receipt rows for themselves.
The shared command kernel coordinates state changes, events, receipts, and
real-time publication.

### Provenance Is Required

Imported definitions retain source, license, location, import, and review
information. Product identity and open content must remain distinguishable.

## Model Overview

```text
Source and Content Packages
        |
Rules Catalogue ---- Character-Creation Catalogue
        |                        |
        +----------+-------------+
                   |
             Campaign Actors
                   |
      +------------+-------------+
      |            |             |
 Possessions    Locations    Relationships
      |            |             |
   Economy      Journeys       Factions
      |            |
   Vessels ---- Star Systems
      |
 Encounters and Combat
      |
 Effects, Damage, and Conditions

All state-changing paths -> Commands -> Events and Receipts
All AI presentation paths -> Scene Packets -> Narration Attempts/Revisions
```

## Foundation-Owned Tables

These tables implement shared infrastructure. Names are provisional but their
responsibilities belong to Base Cepheus.

### Identity and Access

#### `account`

An authenticated human identity.

#### `product_role`

A role recognized by this product, such as player, referee, or administrator.

#### `campaign_membership`

Relates an account to a campaign and role. Character control is recorded
separately because one account may control several characters.

#### `character_controller`

Relates an account to a character with an authority level and effective dates.

### Commands, Events, and Receipts

#### `game_command`

One requested state-changing operation.

Important relationships:

- belongs to one campaign;
- has one initiator classification and optional account;
- has a stable idempotency key;
- names its command type and implementation version;
- records requested, accepted, rejected, completed, or failed status;
- may reverse or compensate for another command.

#### `domain_event`

An immutable fact emitted by a successful command.

Examples include `CharacterMoved`, `CreditsTransferred`, `DamageApplied`, and
`CargoLoaded`. Event payload fields that are important to the domain should use
typed event-detail tables or references, not one opaque permanent JSON object.

#### `mechanical_receipt`

An auditable account of a mechanical resolution. A command may generate
multiple receipts when it contains multiple explicitly visible mechanical
steps. Receipt ordering is stable.

#### `receipt_random_result`

Records each consumed random expression and its raw result.

#### `receipt_rule_reference`

Links a receipt to the versioned rule definitions used to interpret it.

#### `command_reversal`

Relates a corrective command to the earlier command or events it compensates
for. History is retained.

### Narration and Canon

#### `scene_packet`

The stored identity and version of the authoritative projection assembled for
an AI interaction.

#### `scene_packet_fact`

Links the packet to approved campaign facts or current state projections.

#### `scene_packet_event`

Links the packet to mechanical events the narration may describe.

#### `scene_packet_actor`

Identifies visible or narratively relevant actors and their permitted
information scope.

#### `scene_available_intention`

Lists the bounded choices an AI-controlled actor may select.

#### `narration_attempt`

One immutable AI response to a scene packet.

#### `narration_decision`

Records acceptance or rejection, the deciding player/referee, and the reason.

#### `narration_revision`

Relates a new attempt to the rejected attempt it revises. Accepted narration is
selected by relationship rather than overwriting earlier text.

#### `campaign_fact`

One identifiable persistent fact with status, scope, provenance, and effective
time.

#### `fact_relationship`

Relates facts or their subjects without burying connections in prose.

### Operational Versioning

#### `schema_migration`

Records applied database migrations.

#### `content_package_installation`

Records installed content package and version.

#### `product_seed_ancestry`

Records the seed versions from which the product was created and whether each
has detached.

## Product Source and Provenance

### `source_work`

A source publication or original authored collection.

Examples:

- Cepheus Universal SRD;
- Cepheus Universal Player's Book;
- original Cepheus Engine content.

Important attributes include title, publisher, edition, publication date, and
source classification.

### `source_license`

A license or rights basis under which material is used.

### `source_work_license`

Relates a work, or a defined portion of a work, to its license and any required
attribution.

### `source_locator`

A stable citation within a work: heading path, page, table, paragraph range, or
import anchor.

### `content_package`

A versioned collection of released definitions.

### `content_record_provenance`

Relates a rules/content record to its package, source locator, classification,
import batch, and human review status.

### `import_batch`

One ingestion attempt from a source file or dataset.

### `import_candidate`

Temporary normalized candidate awaiting validation and approval. This is an
appropriate place for temporary source fragments or JSON staging data.

### `import_review`

Records approval, correction, rejection, and reviewer notes for an import
candidate.

## Core Rules Catalogue

### Characteristics and Skills

#### `characteristic_definition`

Defines characteristics such as Strength, Dexterity, Endurance, Intellect,
Education, and Social Standing.

#### `characteristic_scale`

Defines interpretation, display, and modifiers for characteristic values where
the product requires them.

#### `skill_definition`

Defines one skill, its description, training rules, and whether it permits
specialties.

#### `skill_specialty`

Defines a recognized specialty belonging to a skill.

#### `skill_prerequisite`

Represents prerequisites without encoding them in descriptive text.

### Tasks and Difficulties

#### `difficulty_definition`

Names a task difficulty and target number or rule behavior.

#### `task_rule`

Defines a reusable task pattern, relevant characteristic/skill choices, time
unit, difficulty, and effect interpretation.

#### `task_modifier_rule`

A structured conditional modifier linked to a task or rule category.

#### `opposed_task_rule`

Defines how opposed results, ties, and effect comparisons work.

### Tables and Random Procedures

Many Cepheus procedures are naturally tabular, but a generic “all game tables”
blob would sacrifice meaning. Tables should have identities and typed entries.

#### `random_table`

Identifies a table, roll expression, purpose, and package.

#### `random_table_entry`

Stores an inclusive result range and links to a result definition or typed
effect.

#### `table_entry_text`

Holds player-facing or referee-facing descriptive text when the outcome is
genuinely prose rather than another entity.

#### `table_entry_effect`

Links the result to structured mechanical effects.

## Character-Creation Catalogue

### `chargen_method`

Defines an available creation method: designed, random, term-by-term, or
lifepath.

### `chargen_step_definition`

An ordered, versioned step within a method.

### `chargen_choice_definition`

A legal choice offered by a step.

### `career_definition`

A career available during character creation or advancement.

### `career_assignment`

A branch, service, or assignment within a career.

### `career_rank`

An ordered rank and title within a career or assignment.

### `career_qualification_rule`

Structured entry or qualification requirements.

### `career_survival_rule`

Structured term survival rules.

### `career_advancement_rule`

Structured advancement and promotion rules.

### `career_skill_table`

Identifies a skill table associated with a career or assignment.

### `career_skill_result`

Maps a roll range to skill training or another structured benefit.

### `career_event`

One event definition available during a term.

### `career_mishap`

One mishap definition and its structured consequences.

### `career_benefit_table`

Identifies cash or material mustering-out benefits.

### `career_benefit_result`

Maps a roll to money, item definitions, characteristic changes, contacts,
shares, or other structured results.

### `career_connection_option`

Defines rules for relationships formed through careers.

## Campaigns, Time, and Actors

### `campaign`

The independent play world and top-level owner of mutable game state.

### `campaign_clock`

The current authoritative date and time, calendar reference, and time zone or
scale where needed.

### `character`

An individual person or person-like actor in a campaign. Player characters and
NPCs share essential physiology and skills; authority and generation source are
separate attributes.

### `character_characteristic`

One current characteristic value for one character.

### `character_skill`

One trained skill or specialty level for one character.

### `character_career_term`

A completed career term with dates, career, assignment, rank, and outcome.

### `character_career_event`

The actual event or mishap experienced during a term.

### `character_benefit`

A benefit awarded during creation or later service.

### `character_note`

Player- or referee-authored commentary. Notes are not automatically structured
canon or mechanical state.

### `character_status`

Active, retired, deceased, missing, or another product-defined lifecycle state.

### `npc_template`

A curated reusable NPC definition.

### `npc_template_skill`

Skills supplied by a template.

### `npc_template_item`

Equipment supplied by a template.

### `npc_template_behavior`

Structured motives, risk tolerance, preferred intentions, and prohibitions used
to assemble bounded AI choices.

### `character_template_origin`

Records which template or deterministic procedure created an NPC.

## Relationships, Contacts, and Factions

### `relationship_type`

Defines contact, ally, rival, enemy, patron, dependent, relative, crew mate, and
other product relationships.

### `character_relationship`

A directed relationship between two actors with status, strength, provenance,
and effective dates.

### `faction`

A persistent organization in the campaign.

### `faction_membership`

Relates a character to a faction, role, rank, standing, and dates.

### `faction_relationship`

Relates two factions with a typed, potentially asymmetric stance.

### `reputation`

A character's standing with a faction, community, or other scoped subject.

## Places, Star Systems, and Movement

### `location`

Any place at which an actor or object may be located: room, facility, settlement,
world region, orbital area, or abstract transit position.

### `location_containment`

Defines that a location is inside another location. This supports rooms within a
ship, facilities within a settlement, and settlements on a world.

### `location_connection`

A traversable connection between two locations with direction, status,
visibility, and access requirements.

### `location_feature`

A structured persistent feature such as an airlock, hazard, terminal, or
concealed entrance.

### `sector`

A mapped region containing subsectors and star systems.

### `subsector`

A mapped division within a sector.

### `star_system`

A system identity, coordinates, naming, and discovery status.

### `celestial_body`

A star, world, moon, belt, or other significant body.

### `world_profile`

The versioned physical and social profile for a principal world.

### `world_trade_code`

Relates a world to normalized trade classifications.

### `star_route`

A known connection between systems, including distance and navigational status.

### `character_location`

The current location of a character with effective time.

### `item_location`

The current direct location or container of an item instance.

## Journeys and Travel

### `journey`

A planned or active movement from origin to destination.

### `journey_leg`

An ordered portion of a journey using one travel mode or route.

### `journey_participant`

Characters and vessels committed to a journey.

### `journey_resource_commitment`

Fuel, life support, money, cargo capacity, or other reserved resources.

### `journey_event`

A structured interruption, encounter, delay, or arrival associated with a leg.

### `jump_attempt`

The specific preparation, calculation, fuel use, and outcome of a space jump.

### `refuel_operation`

Records source, method, time, cost, risk, and fuel transferred.

## Items, Containers, and Inventory

### `item_definition`

The common definition for a purchasable, transferable, or usable object.

### `item_category`

A classification hierarchy for presentation and rule lookup.

### `item_instance`

A particular owned or located object. Individually insignificant fungible goods
may instead use inventory lots.

### `inventory_lot`

A quantity of interchangeable items with one owner, location, condition, and
provenance.

### `container`

A capacity-bearing storage context associated with a character, item, location,
vehicle, or vessel.

### `container_content`

Relates an item instance or inventory lot to its immediate container.

### `item_condition`

Current damage, wear, charge, or another tracked item state.

### `item_modification_definition`

Defines a legal modification.

### `item_modification`

A modification installed on a particular item instance.

Ownership and physical location are separate. A character may own cargo stored
aboard a vessel they do not own.

## Weapons, Armor, and Personal Equipment

### `weapon_definition`

Extends an item definition with skill, range, damage, traits, ammunition, and
other weapon rules.

### `weapon_range_band`

Defines range-specific behavior for a weapon or weapon class.

### `ammunition_definition`

Defines ammunition compatibility and capacity.

### `weapon_ammunition_state`

Tracks loaded ammunition for a specific weapon instance when relevant.

### `armor_definition`

Extends an item definition with protection and usage rules.

### `equipment_effect`

Structured modifiers or capabilities granted by equipment.

## Money, Trade, and Markets

### `currency`

A product-recognized unit of account.

### `financial_account`

A purse, personal account, ship account, company account, escrow, or other
balance owner.

### `financial_entry`

An immutable debit or credit posted by a transaction.

### `financial_transaction`

Groups balanced entries and links them to the originating game command.

### `trade_good_definition`

A fungible good with base price, legality, category, and trade rules.

### `trade_code_modifier`

Relates world trade codes to purchase or sale modifiers for a good.

### `market`

A persistent market operating at a location.

### `market_session`

A market's availability period, such as one campaign day.

### `market_stock`

The quantity of a good available in one market session.

### `market_quote`

A held buy or sell quote scoped to market session, good, party or negotiator,
and relevant conditions.

### `trade_order`

A proposed purchase or sale.

### `trade_execution`

The completed atomic exchange linking financial entries, stock change, and
inventory movement.

## Vehicles and Spacecraft

### `vehicle_definition`

A reusable ground, air, water, gravitic, walker, or other vehicle design.

### `vehicle`

A campaign instance of a vehicle definition.

### `ship_class`

A reusable spacecraft design.

### `ship_class_component`

Components and quantities installed by the class design.

### `ship`

A named spacecraft instance with ownership, registration, and current state.

### `ship_component`

A component installed on a ship, including individual condition where required.

### `ship_deck_location`

Links the general location model to significant compartments aboard a ship.

### `ship_crew_position`

A required or optional role defined by a class or ship.

### `ship_crew_assignment`

A character assigned to a crew position with dates and duty status.

### `ship_resource`

Current fuel, power, life support, ammunition, or other quantified ship
resources.

### `ship_damage`

Current structural or component damage.

### `ship_ownership`

Characters, companies, factions, or financial agreements associated with ship
ownership.

### `ship_finance_agreement`

Mortgage, payment schedule, lien, or other ship obligation.

Cargo uses the ordinary container and inventory model; it is not a JSON field on
the ship.

## Abilities, Mind Powers, and Effects

### `ability_definition`

A learnable or granted active capability.

### `ability_category`

Classifies abilities, including mind powers where appropriate.

### `ability_cost`

A structured resource or condition cost.

### `ability_target_rule`

Defines legal targets, range, area, and consent or resistance behavior.

### `ability_resolution_rule`

Links an ability to tasks, difficulties, opposed checks, and effects.

### `effect_definition`

A reusable mechanical effect such as damage, healing, movement, modifier,
information, or condition application.

### `effect_component`

One ordered component of a compound effect.

### `character_ability`

An ability known or possessed by a character.

### `ability_use`

A resolved attempt to use an ability, linked to targets, receipts, costs, and
effects.

The AI may select a legal ability intention for an NPC. It does not determine
costs, targets, success, or effects.

## Health, Damage, and Conditions

### `damage_type`

A product damage classification.

### `damage_instance`

Damage produced by a resolved action before or during application.

### `damage_allocation`

The application of damage to a characteristic, body location, armor, component,
or other legal target.

### `condition_definition`

A reusable condition and its rule behavior.

### `actor_condition`

A condition currently affecting a character, with source, severity, duration,
and status.

### `treatment`

An attempted medical intervention and its result.

### `recovery_progress`

Tracked healing or recovery over campaign time.

## Encounters and Combat

The Cepheus engine requires two complete mechanical scales:

- **personal-scale encounters and combat**, involving characters, creatures,
  personal weapons, armor, movement, abilities, injury, and recovery;
- **ship-scale encounters and combat**, involving vessels, crews, range or
  position, sensors, maneuver, weapons, defenses, power or fuel, component
  damage, boarding, withdrawal, and surrender.

Both scales must operate in player-directed, human-refereed, AI-assisted, and
AI-refereed play. The engine remains authoritative in every mode. A human or AI
may choose legal intentions for actors under its control, but the selected
product rules resolve initiative, attacks, damage, resource use, movement, and
consequences.

An encounter is broader than combat at either scale. Personal encounters may be
social, exploratory, hazardous, stealth-oriented, or hostile. Ship encounters
may involve communication, inspection, pursuit, navigation hazards, rescue,
trade, piracy, boarding, or battle. Escalation into combat is a state transition,
not an assumption made when the encounter is created.

### `encounter`

A persistent bounded situation involving actors, locations, and potentially
hostile action. Not every encounter must become combat.

### `encounter_participant`

An actor or vessel participating in an encounter, including side, status, and
entry/exit time.

### `encounter_phase`

The current phase, round, or other product-defined temporal unit.

### `initiative_entry`

A participant's ordering information and relevant receipt.

### `available_intention`

An engine-generated legal choice for a participant. This is the list from which
AI may choose for an NPC.

### `declared_intention`

The participant's selected intention before resolution where the rules require
declaration.

### `combat_action`

A resolved action with actor, targets, rule, receipts, and status.

### `combat_action_effect`

Links a combat action to applied damage, conditions, movement, resource use, or
other effects.

### `encounter_position`

Product-defined relative or mapped position. The initial product must decide
whether it requires zones, exact distance, range bands, deck locations, or a
combination.

### `encounter_objective`

An actor or side's structured objective, useful for both AI intent selection and
encounter termination.

### `encounter_outcome`

Records completion, withdrawal, surrender, escape, victory, or another result.

Personal and spacecraft combat require different product rule modules while
using the same command, event, receipt, intention, authority, and narration
infrastructure. Shared infrastructure must not flatten the two scales into one
set of combat statistics.

### `ship_encounter_state`

The ship-scale state for an encounter, including tactical range or position,
detection, communication, pursuit, and engagement status.

### `ship_encounter_participant`

A participating vessel, its controlling side, readiness, current maneuver, and
entry or exit status.

### `ship_crew_combat_assignment`

Connects characters and NPCs to the bridge, engineering, sensors, weapons,
damage control, boarding, medical, or other duties that give them legal
ship-combat intentions.

### `ship_combat_action`

A resolved ship-scale action with acting vessel, responsible crew member where
applicable, targets, rule, receipts, and status.

### `ship_combat_action_effect`

Links a ship action to maneuver, detection, damage, component impairment,
resource expenditure, boarding state, or another structured consequence.

### `boarding_operation`

Connects ship-scale and personal-scale encounters. It records the vessels,
access point, participating actors, objective, and related personal encounter
without treating boarding combat as ordinary ship-weapon damage.

## Encounters, Creatures, and Reusable NPC Content

### `creature_definition`

A reusable non-human or animal type.

### `creature_characteristic`

Characteristic generation or fixed values.

### `creature_skill`

Skills or capabilities granted by the creature definition.

### `creature_attack`

A structured attack linked to weapon-like resolution and effects.

### `encounter_table`

A context-specific collection of encounter possibilities.

### `encounter_table_entry`

Links result ranges to creature groups, NPC templates, events, hazards, or other
encounter definitions.

### `encounter_group_definition`

Defines composition without creating campaign instances until selected.

When generated, encountered NPCs and creatures become stored campaign actors.
They are not regenerated from a prompt on each appearance.

## Computers, Robots, and Augments

### `computer_definition`

A computer or computing platform definition.

### `software_definition`

A program, expert package, or other installable capability.

### `software_installation`

Software installed on a particular item, vehicle, ship, or facility.

### `robot_definition`

A reusable robot design.

### `robot`

A campaign robot instance, linked to the actor model where it can act
independently.

### `augment_definition`

A biological or cybernetic augmentation definition.

### `character_augment`

An augmentation installed on a character with condition and provenance.

### `artificial_intelligence_definition`

A rules definition for an in-world artificial intelligence. This is distinct
from the external narration AI provider.

### `artificial_intelligence_instance`

An in-world AI associated with appropriate hardware, ownership, and actor
records.

The model must never confuse an in-fiction AI with the software provider used to
narrate the game.

## Character-Creation Session State

### `chargen_session`

A resumable creation attempt with method, content version, seed policy, and
status.

### `chargen_step_instance`

The actual occurrence of one step in a session.

### `chargen_choice_instance`

The option selected by the player at a step.

### `chargen_random_result`

The random values consumed at a step, linked to receipts.

### `chargen_provisional_change`

A structured proposed characteristic, skill, career, relationship, benefit, or
possession change prior to final commitment.

### `chargen_commit`

The command that converts the accepted provisional character into ordinary
campaign records.

There is no `choices_json` master record. The entire session is queryable and
can be resumed or audited.

## Important Integrity Constraints

The physical schema should enforce at least the following:

- every campaign-owned record belongs to exactly one campaign;
- a product definition references an installed content package;
- a skill specialty belongs to its declared skill;
- an inventory quantity cannot become negative through ordinary commands;
- a contained object has no more than one immediate physical container;
- container relationships cannot form cycles;
- an actor has no more than one current direct location;
- market stock cannot be oversold;
- financial transactions balance according to currency rules;
- a held quote belongs to one market session and expires explicitly;
- ship crew assignments reference legal positions;
- encounter actions reference current participants;
- an applied effect references the action or command that caused it;
- rejected narration is never selected as accepted narration;
- established facts retain their provenance;
- a command idempotency key cannot execute twice in the same scope;
- random results cannot be altered after their receipt is completed;
- manual overrides are attributed and receipted.

## Deliberately Separate Concepts

These pairs must not be collapsed:

| Concept A | Concept B |
|---|---|
| Definition | Campaign instance |
| Ownership | Physical location |
| Rule content | Mutable campaign state |
| Current state | Historical event |
| Mechanical receipt | Narrative description |
| Campaign fact | Prose mentioning that fact |
| AI provider | In-world artificial intelligence |
| NPC template | NPC campaign character |
| Market stock | Player inventory |
| Proposed trade | Completed transaction |
| Rejected narration | Accepted revision |
| Player manual override | Untracked database edit |
| Ship class | Individual ship |
| Encounter intention | Resolved action |

## Initial Read Models

The normalized write model should generate focused projections for the user
interface and AI. These are not alternate authorities.

### Character Sheet View

Combines identity, characteristics, skills, careers, conditions, abilities,
money, and carried possessions.

### Scene View

Combines current location, visible connections and features, present actors,
relevant facts, recent accepted narration, and available player commands.

### Market Board View

Combines current market session, stock, legal goods, held quotes, negotiator,
available accounts, and cargo capacity.

### Ship Console View

Combines ship identity, class, crew, location, resources, components, cargo,
finances, and current damage.

### Encounter Board View

Combines participants, positions, current phase, initiative, declared
intentions, conditions, and legal actions.

### Ship Encounter Board View

Combines vessels, tactical relationship, detection and communication state,
crew assignments, maneuvers, ship resources, weapons, defenses, component
condition, boarding state, and legal ship-scale actions.

### Referee View

Adds hidden actors, concealed features, pending facts, encounter objectives, and
other information permitted by referee authority.

### AI Scene Packet

Includes only the facts, accepted prose, resolved events, actor information, and
bounded intentions necessary for one interaction.

## Questions Deferred to Gameplay Contracts

The model intentionally does not yet decide:

- whether personal combat uses exact distance, zones, or only range bands;
- the precise initiative and action-economy rules;
- when a generated NPC becomes persistent;
- the scope and expiry rules for market quotes;
- how much jump preparation is one atomic command;
- how player edits reverse or supersede dependent later events;
- which campaign facts require explicit approval in human-referee mode;
- which rules records may be customized per campaign;
- whether all item quantities require individual instances;
- data-retention policy for complete AI inputs and outputs.

Those are workflow decisions and should be settled in gameplay contracts before
physical schema creation.

## First Vertical Slice

The initial implementation slice should exercise the model with:

- one campaign and campaign clock;
- one player account and controlled character;
- one curated NPC template and instantiated NPC;
- two connected locations;
- one character skill and task;
- one financial account;
- one market with one held stock item and quote;
- one completed trade transferring money and inventory atomically;
- one journey between the locations;
- one encounter with a legal NPC intention;
- one resolved mechanical action and receipt;
- one AI scene packet and narration attempt;
- one rejected narration and accepted revision;
- one player manual edit with an audit record.

This slice is complete only when database state, event history, receipt,
interface projection, and accepted narration all agree.

The first vertical slice proves personal-scale encounter infrastructure. A
second required slice must then prove ship-scale encounter infrastructure with
two vessels, crew assignments, detection or communication, maneuver, one
resolved ship action, component or resource consequences, and the same
human/AI intention boundary. Ship combat is not deferred as an optional future
genre feature.

## Next Design Step

The next planning document should define gameplay contracts for:

1. player manual editing;
2. tasks and recorded randomness;
3. inventory and financial transactions;
4. markets and trade;
5. travel and time;
6. encounters and combat;
7. abilities and mind powers;
8. NPC intention selection;
9. scene assembly, narration, rejection, and revision.

Those contracts will determine transaction boundaries and reveal which logical
entities require refinement before a physical schema is written.
