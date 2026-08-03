# Emporos Inheritance Assessment

## Purpose and Scope

Emporos is the successful prototype and evidence base for Base Cepheus. It is
not the codebase from which the new foundation will simply be renamed and
continued.

This assessment identifies what should be preserved, what should be adapted
through deliberate redesign, and what should be left behind. It evaluates both
product ideas and their present implementations. A strong idea in Emporos does
not automatically imply that its current code or schema should be copied.

The existing `cepheus` project remains read-only reference material. Work based
on this assessment belongs in `baseCepheus`.

## Executive Finding

Emporos has already demonstrated the central product thesis:

> An AI-assisted role-playing game becomes more dependable and enjoyable when
> software owns mechanics and persistent state while AI concentrates on
> language, character portrayal, and bounded judgment.

Its strongest innovations are the event history, mechanical receipts, held
market state, resumable character creation, persistent battles, lore approval,
and narration rejection. These should shape the new foundation.

Its principal structural weakness is divided authority. The application says
the database is authoritative, but important data still resides in JSON
columns, authored JSON files, narrative history, large prompts, browser logic,
and several oversized application modules. The result works, but correctness
depends on many parts agreeing by convention rather than by enforced
boundaries.

The recommended strategy is therefore:

- preserve the proven product principles;
- selectively salvage small, well-tested algorithms;
- redesign state, boundaries, and application structure;
- do not fork the whole application as the new base.

## Preserve

“Preserve” means the idea belongs in the constitution or shared foundation.
Specific code may still be rewritten.

### 1. The Mechanical Receipt Tape

Emporos numbers and retains records of mechanical acts. It can detect gaps and
void a receipt without pretending it never existed.

This is one of the project's most valuable ideas. The new foundation should
retain append-only mechanical accountability, while strengthening receipts to
record command identity, initiator, inputs, rule version, random inputs,
resulting events, and reversal relationships.

**Disposition:** Preserve as foundational infrastructure. Redesign the schema
and transaction boundary before reusing code.

### 2. An Event Spine for Campaign History

Emporos records meaningful campaign activity in an event stream. This provides
a basis for timelines, synchronization, audit, recovery, and narration.

Events should remain an ordered record of things that happened. They should not
be used as a substitute for queryable current state, nor should arbitrary JSON
event detail become the only surviving representation of an important fact.

**Disposition:** Preserve the pattern. Separate domain events, mechanical
receipts, current state, and narrative presentation more explicitly.

### 3. Held Markets and Atomic Trade

Emporos correctly recognizes that a market must not reroll because a user
reloads a page. Daily stock and negotiated prices are stored, and stock is
drained through database operations rather than conversational memory.

This is an excellent example of the engine doing what AI should not do.

**Disposition:** Preserve the behavior and relational direction. Generalize the
transaction pattern so products can implement bazaars, ports, caravan markets,
auction houses, or interstellar exchanges without inheriting space terminology.

### 4. Player-Approved Lore

Emporos distinguishes proposed lore from approved canon and rejected material.
That distinction is essential for an AI-assisted world.

**Disposition:** Preserve. Expand it into structured campaign facts with
provenance, scope, status, supersession, and relationships. Prose descriptions
can accompany facts but should not be their only representation.

### 5. Narration Rejection

The X-and-reason interaction is a signature feature. It gives the player a
direct, low-friction way to correct tone, agency, continuity, or interpretation
without replaying mechanics.

**Disposition:** Preserve the user experience. Redesign storage so the original,
the rejection reason, and each revision remain auditable while only the accepted
revision is supplied as current narration.

### 6. Deterministic, Resumable Character Creation

Emporos treats character creation as a sequence of choices with a seed rather
than as one opaque AI-generated character. A player can stop and resume without
silently changing earlier results.

**Disposition:** Preserve the workflow and reproducibility contract. Redesign
the choice state relationally and make character-creation procedures
product-specific strategies built on shared workflow infrastructure.

### 7. Persistent Encounter and Battle State

Emporos stores battles and combatants rather than asking narration to remember
initiative, damage, or whose turn it is.

**Disposition:** Preserve. Replace combat-specific coupling with a clean
encounter state machine that a product's combat rules can extend.

### 8. Audited Randomness and Narration Validation

Dice-producing tools leave receipts, and the narration validator attempts to
detect numerical claims unsupported by the current turn's mechanics.

**Disposition:** Preserve both goals. Evolve from checking numbers in prose to
validating structured narration claims against a deliberately assembled scene
packet and event results.

### 9. Multiple Referee Modes

AI, assisted, and human-referee play can share one authoritative campaign
engine. This expands the market without requiring separate rules
implementations.

**Disposition:** Preserve as a product capability. Authorization and available
commands should be explicit rather than implemented mainly through prompt
instructions.

### 10. Player Freedom

Emporos increasingly exposes money, possessions, records, and reversals to the
player. This agrees with the product constitution: the application assists the
player and maintains consistency but does not police how a private game “ought”
to be played.

**Disposition:** Preserve and make systematic through safe manual-edit commands.

## Adapt

“Adapt” means the existing work contains valuable domain knowledge or algorithms
but should enter Base Cepheus only through a new contract.

### 1. Dice, Tasks, Travel, Trade, Combat, and World Algorithms

The `engine` modules contain useful Cepheus behavior and testable calculations.
They are the most plausible source of directly reusable code.

Before reuse, each candidate should be checked for:

- independence from SQLite rows and JSON fields;
- explicit inputs and outputs;
- deterministic behavior when supplied random inputs;
- absence of web, prompt, and persistence concerns;
- rule-source and edition provenance;
- sufficient unit tests;
- product-specific terminology.

**Disposition:** Review algorithm by algorithm. Port only code that can operate
as a small, pure rule component.

### 2. Repository and Transaction Logic

The repository contains valuable lessons about atomic stock changes, ledgers,
receipts, lore, and battle persistence. It also combines many unrelated domains
in one large class and performs JSON serialization throughout.

**Disposition:** Use it as a behavioral reference. Replace it with domain-focused
repositories or services under a single unit-of-work transaction boundary.

### 3. API Workflows

The FastAPI application proves useful workflows for campaigns, characters,
character creation, ships, markets, transfers, combat, lore, receipts, travel,
and narration rejection.

The application module is nearly two thousand lines and mixes HTTP handling,
domain decisions, seeding, authentication, serialization, and orchestration.

**Disposition:** Preserve the endpoint use cases as requirements. Rebuild them
as thin route modules calling application services.

### 4. Referee Tools

The tool layer demonstrates an important capability model: AI asks the engine to
perform named operations rather than directly editing state.

At present, the tool module is also nearly two thousand lines and mixes schemas,
rule execution, persistence, formatting, and policy. A large tool surface gives
the model more authority and more opportunities to choose the wrong operation.

**Disposition:** Preserve command mediation. Replace the universal tool bag with
small, scene-specific command sets generated from current permissions and state.

### 5. The Referee Prompt

The prompt documents many valuable play lessons: respect database truth, avoid
fabricating mechanics, consult lore, preserve player agency, and call tools.

Its size is also evidence that application invariants are being enforced through
instructions. Repetition in a prompt does not create a reliable security or
transaction boundary.

**Disposition:** Mine it for requirements and test cases. Keep future system
prompts short; enforce important rules in scene assembly, command permissions,
validators, and database constraints.

### 6. The Browser Interface

The existing interface demonstrates which controls players actually need:
campaign selection, character state, market operations, battles, maps, lore,
receipts, and the narration veto.

The main page is large, and some domain values are decoded or calculated in the
browser. That creates another potential source of mechanical truth.

**Disposition:** Preserve the workflows and learn from actual use. Rebuild the
interface in product-focused screens fed by stable view models. Browser
calculations may preview but never resolve authoritative results.

### 7. Existing Cepheus Data Files

The authored JSON data provides a valuable inventory of required rule content
and may help verify imports.

**Disposition:** Treat it as migration input and a comparison corpus, not as the
canonical content system. Imported records must preserve source and license
provenance and pass human review.

### 8. Authentication, Campaign Ownership, and Live Operations

The existing application has already encountered real public-deployment
concerns: registration, login, campaign claiming, passwords, backups, and
multi-user updates.

**Disposition:** Preserve these as operational requirements. Reassess the
implementation separately from game mechanics, with explicit authorization
tests and versioned migrations.

## Discard

“Discard” means the pattern should not be copied into the new foundation even
when compatibility makes it tempting.

### 1. JSON as Persistent Domain Structure

Skills, careers, gear, cargo, crew, event detail, and character-creation choices
are examples of naturally structured data stored in JSON text columns.

This prevents dependable foreign keys, constraints, joins, partial updates,
provenance, and concurrent mutation. Creating auxiliary relational indexes while
retaining a JSON master produces two representations that must remain synchronized.

**Disposition:** Do not reproduce this pattern. Normalize persistent domain data
from the beginning.

### 2. Authored JSON as the Ultimate Rules Authority

Seeding tables from files while declaring the files the lasting source of truth
leaves the database as a cache rather than the authoritative content system.

**Disposition:** Imports are allowed, but reviewed database records become the
authority for a released product. Exports are generated from those records.

### 3. Narrative History as Working Memory

The live campaign demonstrates that important geography, equipment, intentions,
and discoveries are often reconstructed from prior prose or notes. This permits
continuity errors and confident invention.

**Disposition:** Never rely on transcript recovery for facts the game must know.
Store locations, connections, scene participants, possessions, relationships,
and persistent discoveries structurally.

### 4. Prompt-Enforced Mechanical Safety

Instructions such as “never contradict the database” are useful guidance but
cannot substitute for limiting what data and commands the model receives.

**Disposition:** Do not grant broad capability and then ask the model not to
misuse it. Enforce the boundary in code.

### 5. Destructive Narration Replacement

Overwriting rejected prose removes evidence needed to understand failures and
improve the product.

**Disposition:** Store immutable narration attempts and a pointer to the
currently accepted revision. Exclude rejected text from future AI context by
query, not by destroying it.

### 6. Mechanical Logic in the Client

Duplicating calculations in JavaScript invites disagreement with the server and
makes rule changes harder to audit.

**Disposition:** The client may display, explain, or preview. Only an
authoritative engine command resolves state.

### 7. Monolithic Application Modules

Large web, tool, repository, and page modules combine unrelated reasons to
change. Every new feature increases regression risk and makes extraction for a
new product harder.

**Disposition:** Do not copy these files wholesale. Organize the foundation
around domain modules and application use cases.

### 8. Database Snapshots as a Migration Strategy

Multiple database snapshots at different schema generations are useful backups
but do not constitute a repeatable schema history. Existing snapshots lack some
newer tables and behavior.

**Disposition:** Adopt numbered, tested, forward migrations immediately. Every
supported database must report its schema and content-package versions.

### 9. Corrections Inside the Fiction

Live narration sometimes includes apologies, record-checking commentary, or
explicit correction of earlier mistakes. This breaks immersion and allows the
mistake to keep influencing later context.

**Disposition:** Corrections belong to the interaction record. Accepted fiction
should read cleanly, as if the rejected version never happened.

### 10. AI Declaration of Player Actions

Narration occasionally attributes speech, deductions, or actions to the player
character that the player did not choose.

**Disposition:** Prohibit this at the scene-contract and validation levels, not
only in prose instructions.

### 11. One Shipped Universal Genre Application

The new objective is not a single runtime capable of switching between every
genre.

**Disposition:** Do not carry forward a design that forces every product to load
generic abstractions, irrelevant tables, or a genre-selection layer. Build
distinct products from common, traceable foundations.

## What Can Be Reused Directly?

Direct code reuse should be exceptional rather than assumed. A component is a
candidate only when all of the following are true:

1. Its behavior is wanted by the new product constitution.
2. Its inputs and outputs are explicit.
3. It does not depend on legacy JSON-shaped domain records.
4. It does not combine HTTP, AI, persistence, and rule resolution.
5. Its random inputs can be controlled and recorded.
6. It has focused tests that pass independently.
7. Its source and license are known.
8. Copying it is cheaper and safer than implementing the clarified contract.

Likely candidates are small dice, task, trade, world, and combat calculations.
Unlikely candidates are the primary web application, referee tool registry,
repository class, large prompt, main HTML page, and current schema as a whole.

## Recommended Inheritance Order

The foundation should inherit Emporos in this order:

1. **Product lessons:** incorporate proven behavior into specifications.
2. **Tests:** turn failures and successful workflows into acceptance scenarios.
3. **Data inventory:** identify every natural table implied by existing content.
4. **Algorithms:** port isolated, provenance-known rule calculations.
5. **Operational lessons:** reproduce deployment capabilities deliberately.
6. **Presentation:** design product-specific interfaces after authoritative
   workflows are stable.

The existing schema and application layout should not lead this process.

## Immediate Architectural Consequences

The following decisions should govern the next design deliverable:

- Base Cepheus is an internal production foundation.
- Finished games are independent products.
- The first relational model should be derived from gameplay facts and source
  material, not from the legacy schema.
- Rules content and mutable campaign state require separate ownership and
  versioning.
- All mutations enter through application commands and one transaction boundary.
- AI receives scene projections and bounded choices, never ambient authority.
- Accepted narration, rejected narration, mechanical events, and current state
  are distinct records.
- Emporos supplies acceptance tests and domain insight, not the starting
  directory tree.

## Final Disposition

Emporos should be treated with respect as a successful field prototype. It has
already answered the hardest question: whether the underlying experience is
worth building.

Base Cepheus should now answer the engineering question Emporos was never
structured to answer:

> How do we produce several reliable, distinctive role-playing games from the
> same accumulated knowledge without making AI, JSON, or copied prototype code
> the hidden source of truth?

