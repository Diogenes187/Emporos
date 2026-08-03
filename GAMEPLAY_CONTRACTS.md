# Relational Cepheus Engine Gameplay Contracts

## Status

Planning contracts for the complete relational Cepheus engine.

### Rules-Package Notice

The command, transaction, audit, player-authority, and AI-boundary portions of
these contracts remain governing architecture.

Some detailed personal-combat, ship-combat, and boarding assumptions were
written while Cepheus Universal was being treated as the engine's rules
source. The Cepheus Engine website/GitHub corpus has since been selected as the
governing package. Those mechanical details must be re-derived from Cepheus
Engine before implementation. Universal-specific mechanics remain useful for a
separate Universal package and are not silently carried into the Engine
package.

These contracts sit between the logical domain model and the future physical
schema. They define observable behavior without prescribing route names, user
interface technology, or final SQL.

## Contract Vocabulary

### Query

A read-only request. It cannot advance time, consume randomness, change state,
or create a mechanical receipt.

### Command

A request to change authoritative state. A command is validated and completed
inside one transaction. It has an initiator, authority, idempotency key, and
result status.

### Intention

A desired action proposed by a player, human referee, or AI-controlled actor.
An intention is not yet a mechanical result.

### Resolution

The deterministic interpretation of a valid command using rules, current state,
and recorded random inputs.

### Domain Event

An immutable statement of what the completed command changed.

### Mechanical Receipt

An auditable explanation of how a mechanical result was obtained.

### Projection

A generated read model for a player, referee, browser screen, export, or AI
scene packet. It is disposable and not authoritative.

## Universal Command Contract

Every state-changing gameplay operation follows this sequence:

1. Authenticate the initiator.
2. Establish campaign and actor authority.
3. Check the idempotency key.
4. Load authoritative definitions and current state.
5. Validate prerequisites and legal targets.
6. Reserve or verify required resources.
7. Obtain random values only through the recorded-randomness service.
8. Resolve the applicable versioned rules.
9. Apply all state changes in one transaction.
10. Write domain events and mechanical receipts.
11. Commit.
12. Publish updated projections.
13. Optionally request narration from the committed result.

If any required step fails, no partial gameplay mutation is committed.

AI narration occurs after mechanical commitment. Failure to obtain narration
does not undo a valid mechanical action.

## Contract 1: Player Manual Editing

### Purpose

Allow a player or authorized referee to directly change appropriate campaign
state without bypassing integrity, history, or ownership rules.

### Commands

- `SetCharacteristic`
- `SetSkillLevel`
- `GrantOrRemoveAbility`
- `AddOrRemovePossession`
- `SetInventoryQuantity`
- `AdjustAccountBalance`
- `SetExperienceOrAdvancement`
- `SetCondition`
- `SetLocation`
- `EditCharacterIdentity`
- product-specific manual overrides added deliberately

### Preconditions

- the initiator controls the subject or has referee authority;
- the target record belongs to the campaign;
- the referenced definition exists in the installed content version;
- the requested state satisfies structural constraints;
- dependent changes are either included or explicitly acknowledged.

### Behavior

The system may display a warning when an edit conflicts with ordinary game
rules. The player may confirm the override. Rules illegality is not the same as
database invalidity.

For example, a player may grant themselves credits. They may not create a
negative inventory quantity, reference a nonexistent item definition, or place
an item in two containers simultaneously.

### Outputs

- updated authoritative state;
- one manual-override event;
- appropriate financial, inventory, character, or condition events;
- a receipt identifying the before and after values;
- refreshed projections.

### Reversal

A later manual command may restore a prior value. The earlier command and
receipt remain. Reversal must not delete intervening history.

### AI Boundary

AI may explain an edit or narrate its fictional consequences if asked. It may
not initiate a player manual override or shame the player for using one.

## Contract 1A: Characteristic Generation

### Player Flow

The engine rolls one complete set of six characteristic values and presents
the whole set before any value is committed to a characteristic.

The player may then:

- immediately reroll the entire six-value set; or
- freely assign the six displayed values among Strength, Dexterity, Endurance,
  Intelligence, Education, and Social Standing.

Rerolling is not a one-time concession. The product permits another immediate
whole-set reroll whenever the player rejects the current set. Individual dice
or individual values are not rerolled separately by this procedure.

### Persistence and Replay

Every generated set, every reroll decision, and the final one-to-one assignment
is recorded. Reloading or reconnecting presents the current recorded set and
does not consume another roll. Replaying the command history reproduces all
sets and the final assignment exactly.

The interface may provide convenient swapping, dragging, or reassignment before
confirmation. No characteristic value becomes authoritative until the player
confirms the complete assignment.

### Player Authority

After confirmation, ordinary manual-editing contracts still permit the player
to change characteristic values. Such edits are audited manual overrides, not
retroactive changes to the recorded generation rolls.

## Contract 1B: Existing Character Entry

### Purpose

Allow a player to bring an existing character into the product without
recreating that character through the generation procedure. Valid sources
include tabletop sheets, another online campaign, a legacy EMPOROS character,
an exported file, or the player's own written record.

### Entry Modes

The product supports:

- direct manual entry through a complete editable character form;
- structured import from a supported export format;
- review and correction of imported values before final commitment.

Import is optional convenience. Manual entry remains available even when no
compatible file or prior application exists.

### Behavior

The player may enter characteristics, skills and levels, career history and
ranks, age, money and debt, possessions, benefits, injuries, conditions,
abilities, identity, and other supported character state.

The engine validates structural integrity and resolves entered names against
installed rule definitions. It may warn about values that ordinary generation
could not produce, but the controlling player may confirm those values as
authorized external state or manual overrides.

The product does not require generation rolls, reconstruct missing dice, invent
a career history, or force the character through qualification, survival,
aging, or mustering-out again.

### Provenance and Audit

The resulting actor is marked as externally entered, with optional source
label and player notes. Imported source data, field mappings, warnings, player
corrections, and the final committed values remain auditable.

Unknown or unsupported entries are not silently discarded. They remain visible
for player mapping, free-text retention, or later content installation.

### AI Boundary

AI may help explain an import warning or suggest a likely mapping when the
player asks. It cannot silently alter, normalize, complete, or reject the
player's character. Final mappings and values require player confirmation.

## Contract 2: Tasks and Recorded Randomness

### Purpose

Resolve a declared uncertain action exactly once and retain enough information
to explain the outcome.

### Commands

- `AttemptTask`
- `AttemptOpposedTask`
- `AttemptExtendedTask`
- `ContinueExtendedTask`
- `CancelExtendedTask`

### Preconditions

- a task definition or explicit referee-created task specification exists;
- the acting character is authorized and currently able to act;
- characteristic, skill, difficulty, modifiers, time cost, and stakes are known;
- the action is genuinely uncertain and consequential;
- required tools, abilities, or resources are present.

### Trivial Actions

The engine must support a `NoCheckRequired` result. Routine actions do not become
random simply because AI requested a roll.

A referee or product rule may require a check, but the reason and stakes must be
recorded before randomness is consumed.

### Resolution

- freeze the declared task inputs;
- request recorded random values;
- calculate total, effect, degree, and consequences;
- consume time or resources only as defined;
- apply structured consequences;
- record the rule and modifiers used.

### Outputs

- task result;
- raw dice and calculation receipt;
- time/resource events;
- structured consequences;
- narration-ready result projection.

### Repetition

Reloading, reconnecting, retrying an HTTP request, or rewriting narration returns
the recorded result. A new attempt requires a new command and must be legal in
the changed situation.

### AI Boundary

AI may propose that a task is appropriate. The engine or authorized referee
decides whether a check is required and supplies legal parameters. AI may
narrate only the committed result.

## Contract 3: Inventory, Containers, and Money

### Purpose

Make possessions and finances directly manageable, transactionally correct, and
independent of narration.

### Commands

- `TransferItem`
- `TransferInventoryQuantity`
- `EquipItem`
- `UnequipItem`
- `LoadContainer`
- `UnloadContainer`
- `ConsumeItem`
- `SplitInventoryLot`
- `MergeInventoryLots`
- `TransferFunds`
- `PostManualFinancialAdjustment`

### Preconditions

- initiator has authority over the source or explicit permission;
- source contains the stated item or quantity;
- destination exists and is accessible;
- capacity, compatibility, and containment rules pass or an authorized override
  is confirmed;
- financial accounts use compatible currency or an explicit exchange exists;
- ordinary transfers cannot create negative quantities or balances where the
  product prohibits them.

### Atomicity

Ownership, location, quantity, capacity, and financial entries change together.
There is no successful payment without the corresponding transfer, or successful
item transfer without its required payment.

### Outputs

- inventory/location/ownership events;
- balanced financial entries where money is involved;
- capacity changes;
- one command record and relevant receipts;
- refreshed character, cargo, and account views.

### AI Boundary

AI may mention only possessions present in the supplied scene packet. Flavor
details cannot silently become new item instances. An AI-controlled NPC uses
ordinary commands to give, take, consume, equip, or trade items.

## Contract 4: Markets and Trade

### Purpose

Provide stable, inspectable markets whose stock, prices, negotiations, money,
and cargo agree.

### Commands

- `OpenMarketSession`
- `GenerateMarketStock`
- `RequestMarketQuote`
- `NegotiateMarketQuote`
- `BuyTradeGood`
- `SellTradeGood`
- `CloseOrExpireMarketSession`
- `CreateSpecialTradeOffer`

### Market Session Contract

A market session represents one defined availability period. Generating it is a
command because it may consume randomness and create stock. Viewing it is a
query.

An empty generated market is distinct from a market not yet generated.

### Quote Contract

A quote records:

- market session;
- good;
- buy or sell side;
- negotiator and relevant skill state;
- quantity or quantity band where required;
- all price modifiers;
- random results;
- unit price;
- expiry and usage rules.

Reloading does not generate a new quote. A new negotiation requires a legal new
command.

### Trade Execution

In one transaction:

- verify quote and stock;
- verify account funds and cargo capacity;
- reduce source stock or inventory;
- increase destination inventory;
- post balanced financial entries;
- mark or reduce quote availability where required;
- create transaction, inventory, and market events.

Concurrent buyers cannot purchase the same final stock.

### Player Freedom

Authorized players may manually edit money, stock, or cargo separately using
manual override commands. The market does not pretend those changes resulted
from ordinary trade.

### AI Boundary

AI may portray a merchant, explain a quote, or choose whether an NPC accepts a
legal discretionary offer. It cannot invent stock, alter a held price, debit an
account, or transfer cargo through prose.

## Contract 5: Travel, Time, and Space Jumps

### Purpose

Move characters and vessels through known locations while accounting for time,
routes, access, resources, interruption, and arrival.

### Commands

- `PlanJourney`
- `BeginJourney`
- `AdvanceJourney`
- `InterruptJourney`
- `ResumeJourney`
- `CancelJourney`
- `CompleteJourney`
- `PrepareJump`
- `ExecuteJump`
- `RefuelVessel`

### Journey Planning

Planning is initially non-mutating. A confirmed plan records origin,
destination, ordered legs, participants, transport, expected time, resource
commitments, and known risks.

### Beginning Travel

The command verifies:

- participants remain at the origin;
- route and transport remain available;
- required fuel, fare, supplies, capacity, and crew are present;
- no conflicting active journey exists.

It reserves or consumes resources according to product rules and advances time
only when the journey actually begins.

### Progress and Interruption

Long journeys advance through explicit legs or intervals. Each advancement may
create a stored encounter or hazard. An interruption records current transit
position and remaining commitments; it does not teleport participants back to
the origin.

### Arrival

Arrival updates participant and vessel locations, releases reservations,
records elapsed time, and applies arrival effects atomically.

### Space Jump

Jump preparation and execution are distinct where the rules make preparation
meaningful.

The jump contract must account for:

- legal origin and destination;
- route or calculated distance;
- drive capability;
- fuel requirement;
- astrogation or equivalent task;
- engineering or operational task where applicable;
- jump time;
- misjump or failure consequences;
- vessel and passenger location during transit.

Fuel is not spent twice when a request is retried.

### AI Boundary

AI may describe travel and portray events selected by the engine. It cannot
change location, advance time, consume fuel, discover an exit, or declare
arrival.

## Contract 6: Personal Encounters and Combat

### Purpose

Operate persistent character-scale encounters, including social tension,
stealth, hazards, pursuit, negotiation, and combat.

### Commands

- `CreatePersonalEncounter`
- `AddPersonalParticipant`
- `EstablishPersonalPosition`
- `BeginPersonalCombat`
- `GeneratePersonalIntentions`
- `DeclarePersonalIntention`
- `ResolvePersonalAction`
- `AdvancePersonalPhase`
- `WithdrawPersonalParticipant`
- `SurrenderPersonalParticipant`
- `EndPersonalEncounter`

### Encounter Before Combat

Creating an encounter does not roll initiative or assume hostility. The
encounter records participants, visibility, location, objectives, awareness,
and current stance.

Escalation to combat is an explicit command triggered by a participant's
intention or referee decision.

### Legal Intentions

The engine generates intentions from:

- participant state and authority;
- known targets;
- position and range;
- equipped items and ammunition;
- learned abilities and available resources;
- conditions and impairments;
- encounter phase and action economy;
- product rules.

The intention list may include attack, move, defend, communicate, use equipment,
use an ability, assist, withdraw, surrender, or another defined action.

### Resolution

Resolving an action:

- verifies the intention is still legal;
- freezes actor, targets, weapon/ability, modifiers, and resource costs;
- obtains recorded randomness;
- resolves attack, defense, damage, effects, and movement;
- consumes ammunition, actions, or abilities;
- applies conditions, injury, incapacitation, or death;
- emits events and receipts;
- updates encounter completion conditions.

### Player Agency

The AI cannot declare a player character's intention. It may offer legal choices
or portray consequences after resolution.

### Human and AI Modes

The same intention and resolution commands serve player-directed,
human-refereed, AI-assisted, and AI-refereed play. Only the authorized chooser
changes.

### Narration

The narration packet distinguishes attempted action from result. It supplies
exact participants, equipment, positions, rolls, damage, and conditions. Prose
cannot add disarmament, movement, injury, death, surrender, or item destruction
unless present in the resolved effects.

## Contract 7: Ship Encounters and Combat

### Purpose

Operate persistent vessel-scale encounters, including detection,
communication, inspection, pursuit, rescue, hazards, piracy, boarding, and
combat.

### Commands

- `CreateShipEncounter`
- `AddShipParticipant`
- `EstablishDetectionState`
- `CommunicateBetweenShips`
- `AssignCombatCrew`
- `BeginShipCombat`
- `GenerateShipIntentions`
- `DeclareShipIntention`
- `ResolveShipAction`
- `AdvanceShipPhase`
- `LaunchBoardingOperation`
- `WithdrawShip`
- `SurrenderShip`
- `EndShipEncounter`

### Encounter State

The encounter records:

- participating vessels and sides;
- tactical range, zones, or relative position;
- detection and identification state;
- communication state;
- objectives;
- readiness;
- crew assignments;
- maneuver and pursuit state;
- environmental conditions.

The final spatial representation remains a product-rules decision, but it must
be authoritative and queryable.

### Crew Authority

A ship acts through crew positions where the rules require them. Legal
intentions depend on assigned characters, their condition and skills, ship
components, available power/fuel/ammunition, detection, position, and phase.

AI may choose for an NPC captain, crew member, or entire non-player ship only
within the authority assigned to it.

### Legal Intentions

May include:

- detect, identify, jam, or communicate;
- maneuver, pursue, evade, hold position, or withdraw;
- attack with a legal weapon and target;
- defend or operate countermeasures;
- repair or conduct damage control;
- redistribute product-defined resources;
- launch craft or boarding parties;
- surrender or accept surrender;
- perform a scenario-specific operation.

### Resolution

Resolving a ship action:

- verifies crew, component, target, range, and resource legality;
- freezes modifiers and commitments;
- obtains recorded randomness;
- resolves detection, maneuver, attack, defense, damage, or repair;
- consumes actions, power, fuel, ammunition, or other resources;
- applies hull, armor, crew, or component effects;
- emits events and receipts;
- updates pursuit, surrender, withdrawal, and completion conditions.

### Boarding

Boarding is a bridge between scales:

1. the ship encounter establishes a legal boarding opportunity;
2. `LaunchBoardingOperation` records vessels, access point, parties, and
   objective;
3. the engine creates or links a personal encounter in ship deck locations;
4. personal combat resolves characters and equipment;
5. structured personal outcomes update ship control, crew, and components;
6. both encounter histories remain linked.

Narration cannot skip the personal encounter and simply award control unless a
product rule explicitly resolves boarding abstractly.

### Human and AI Modes

As with personal combat, mode changes who chooses legal intentions—not who
resolves the mechanics.

### Narration

The packet supplies detection, range/position, maneuver, weapons, component
state, consumed resources, damage, crew effects, and objectives. AI cannot
invent destroyed systems, decompression, boarding, casualties, escape, or
surrender.

## Contract 8: Abilities and Mind Powers

### Purpose

Resolve active abilities, including Cepheus mind powers, without allowing prose
to substitute for targeting, cost, resistance, duration, or effect rules.

### Commands

- `PrepareAbility`
- `UseAbility`
- `MaintainAbility`
- `EndAbility`
- `ResistAbility`

### Preconditions

- actor knows or possesses the ability;
- actor is conscious and legally able to use it;
- target, range, visibility, and other requirements pass;
- required resources or conditions are available;
- encounter timing permits the action.

### Resolution

- freeze ability version, actor, targets, and declared parameters;
- reserve or consume costs according to the rule;
- obtain recorded randomness;
- resolve success and resistance;
- apply structured effects and durations;
- create conditions or ongoing effect instances;
- record costs, receipts, and events.

### Failure and Cost

The contract must explicitly define when costs are paid: on declaration,
attempt, success, or maintenance. AI cannot waive or invent costs.

### AI Boundary

AI may select a legal power for an NPC and describe experienced sensations or
visible consequences. It cannot create new powers, expand targets, change
duration, or turn evocative language into additional mechanical effects.

## Contract 9: NPC Creation and Intention Selection

### Purpose

Use curated content and deterministic generation to produce persistent NPCs,
then allow bounded AI judgment without granting mechanical authority.

### Commands

- `InstantiateNpcFromTemplate`
- `GenerateNpcFromProcedure`
- `AssignNpcRelationship`
- `GenerateNpcIntentions`
- `SelectNpcIntention`
- `ResolveNpcAction`

### NPC Creation

An NPC originates from:

- a curated template;
- a deterministic generation procedure;
- an authorized referee-authored definition.

Creation records provenance, generated values, equipment, relationships, and
random receipts. Once created, the NPC is an ordinary persistent campaign actor.

AI may propose a name, personality phrasing, dialogue style, or other prose
within product rules. Required statistics, possessions, and abilities come from
structured content or referee commands.

### Intention Generation

The engine generates legal intentions using current state, rules, authority,
objectives, behavior profile, knowledge, and risk tolerance.

AI receives:

- only information the NPC is permitted to know;
- the NPC's relevant motives and portrayal guidance;
- a bounded list of intention identifiers and descriptions;
- no command for directly editing state.

### Selection

AI selects an intention identifier and may provide a concise reason or dialogue
cue. Invalid or invented identifiers are rejected. The engine revalidates the
choice immediately before resolution because state may have changed.

### Fallback

If AI is unavailable, invalid, or times out, the product applies a deterministic
fallback policy or yields the choice to a human referee. The encounter remains
playable.

## Contract 10: Scene Assembly, Narration, and Revision

### Purpose

Generate compelling prose from authoritative facts without allowing prose to
become an ungoverned state-changing channel.

### Commands and Queries

- `BuildSceneProjection` — query
- `RequestNarration` — records an AI operation but does not mutate mechanics
- `AcceptNarration`
- `RejectNarration`
- `RequestNarrationRevision`
- `ProposeCampaignFact`
- `DecideCampaignFact`

### Scene Assembly

A scene packet contains only:

- current authoritative location and time;
- visible actors and permitted actor facts;
- relevant possessions, conditions, and relationships;
- accepted campaign facts;
- resolved events the prose may describe;
- accepted recent dialogue or narration needed for continuity;
- product voice and safety instructions;
- bounded NPC intentions when selection is requested.

Hidden referee data, rejected prose, irrelevant transcript history, and
unauthorized player knowledge are excluded.

### Narration Claims

Where practical, AI output should separate prose from structured claims or
references. The validator checks claimed actors, items, locations, movement,
damage, money, abilities, relationships, and mechanical numbers against the
scene packet and resolved events.

An invalid attempt is not shown as accepted fiction. It may be automatically
retried within provider limits or presented as rejected diagnostic output to an
authorized referee.

### Acceptance

Accepted narration becomes the current presentation associated with the
resolved events. Acceptance does not create new mechanical state.

Potential new lasting facts are submitted separately as fact proposals.

### Rejection

The X action records:

- narration attempt;
- rejecting account;
- reason;
- categories such as agency, continuity, tone, factual error, or style;
- whether a revision is requested.

The attempt remains immutable but is excluded from future current-scene
projections.

### Revision

A revision packet includes the same authoritative mechanics, accepted facts,
and rejection guidance. It does not include rejected prose as canonical
history. The revision must preserve mechanical outcomes.

The accepted revision is linked to both the resolved events and rejected
attempt. Corrections and apologies are not written into the fiction.

### AI Failure

The game remains usable if narration fails. The interface presents the
mechanical result plainly and permits retry, human narration, or continuation.

## Contract 11: Canon and Structured Discovery

### Purpose

Distinguish durable world knowledge from narration and support discovery without
silently rewriting the setting.

### Commands

- `ProposeCampaignFact`
- `ApproveCampaignFact`
- `RejectCampaignFact`
- `SupersedeCampaignFact`
- `RevealCampaignFact`
- `RelateCampaignFacts`

### Fact Status

A fact has explicit status and provenance. Approval rules depend on play mode:

- player-authored facts within player authority may become established
  immediately;
- AI-originated lasting facts are proposals;
- human-referee facts may be established according to campaign policy;
- imported product facts are established content, with visibility controlled
  separately.

### Discovery

A hidden fact and a character's knowledge of it are separate. Discovering a
fact changes visibility or knowledge relationships; it does not create the
underlying world fact at that moment unless the campaign uses generative
creation and explicitly approves the proposal.

## Cross-Contract Invariants

The following rules apply everywhere:

1. Queries never consume randomness or change state.
2. Retried commands do not execute twice.
3. Random results are recorded before being interpreted as completed mechanics.
4. No authoritative state depends solely on AI prose.
5. No AI response directly writes a domain table.
6. Legal intentions are generated from current state and revalidated at use.
7. Player-character intentions require player or authorized human selection.
8. Manual overrides are allowed but identified.
9. Mechanics commit before optional narration.
10. Rejected narration never becomes current context.
11. Current state is queryable without replaying prose.
12. Every material mutation has an initiator and command.
13. Product rule versions used by resolutions remain identifiable.
14. Personal and ship combat share infrastructure but not forced statistics.
15. Human and AI modes use the same mechanical commands.

## Failure Classes

Every command failure should belong to a stable category:

- authentication failure;
- authorization failure;
- stale state or concurrency conflict;
- invalid definition or target;
- illegal action;
- insufficient resource;
- structural integrity failure;
- rule-resolution failure;
- external provider failure;
- internal application failure.

Expected rule failures are ordinary game results, not application errors. A
failed attack is a completed command; an unavailable weapon is a rejected
command.

## Minimum Acceptance Scenarios

Before physical schema approval, these scenarios must be expressible without
JSON-owned domain state:

1. A player manually grants credits, sees the audit record, and later reverses
   the adjustment.
2. A trivial action proceeds without a roll.
3. A task roll survives page reload and narration rejection unchanged.
4. Two buyers contend for the final ton of market stock; only one succeeds.
5. Payment and cargo transfer either both occur or neither occurs.
6. A journey interruption retains participants at a valid transit position.
7. A retried jump request consumes fuel only once.
8. AI cannot choose an intention absent from the NPC's legal list.
9. Personal combat consumes ammunition and applies recorded damage.
10. AI narration cannot invent a weapon or move the player character.
11. A ship without detection cannot legally target an unidentified vessel.
12. A disabled ship component removes dependent legal actions.
13. Boarding creates a linked personal encounter.
14. A mind power pays its defined cost and applies only resolved effects.
15. Rejected narration remains auditable but absent from later scene context.
16. An AI-proposed relationship remains noncanonical until approved.
17. AI-provider failure leaves the resolved game state usable.
18. Human-refereed and AI-refereed versions of the same declared action call the
    same resolution command.

## Decisions Required Before Physical Schema

The contracts expose several product decisions still to be made:

- personal-combat positioning model;
- ship-combat positioning and range model;
- initiative and action economy at each scale;
- detailed damage allocation at each scale;
- character death and incapacitation policy;
- market-session and quote durations;
- account overdraft policy;
- item fungibility threshold;
- jump preparation and misjump procedure;
- NPC persistence threshold;
- campaign-fact approval defaults by referee mode;
- narration retention and privacy policy;
- rules customization allowed at campaign level.

These should be resolved from the Cepheus Universal source, Emporos experience,
and desired player experience before generating SQL migrations.
