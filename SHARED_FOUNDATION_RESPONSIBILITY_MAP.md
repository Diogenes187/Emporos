# Shared Foundation Responsibility Map

## Purpose

Base Cepheus is the complete relational Cepheus engine and the ancestor of
distinct, independently shipped role-playing games. This document determines
which responsibilities remain engine-owned, which may be copied into a derived
product and adapted, and which belong exclusively to that product.

The objective is not to eliminate duplication. It is to make duplication
intentional, traceable, and safer than accidental coupling.

## The Three Ownership Classes

Every component must have one—and only one—primary ownership class.

### Class A: Cepheus Engine Core

Engine Core components are maintained centrally. They include both stable
engineering infrastructure and the complete source-governed Cepheus rules,
content structures, and campaign-state model—including Cepheus's native space
domains.

A product should not casually fork these components. Product variation is
provided through explicit configuration, interfaces, or replaceable adapters.

### Class B: Product Seed

Product Seed components are maintained as good starting implementations. When a
new product is created, they are copied into that product and become
product-owned.

After copying, the product may modify them freely. Their origin and seed version
remain recorded so later fixes can be evaluated and selectively applied.

This class is appropriate when games share a recognizable workflow or algorithm
but are likely to diverge in rules, terminology, or presentation.

### Class C: Product-Specific

Product-Specific components belong only to one shipped game. They are not forced
through generic abstractions merely because another game contains something
similar.

If two or more products later reveal a genuinely stable common pattern, that
pattern may be extracted deliberately. Similarity alone is not sufficient.

## Responsibility Matrix

| Responsibility | Owner | Reason |
|---|---|---|
| Database connection and transaction management | Shared Foundation | Atomicity and reliability do not depend on genre |
| Migration runner and schema-version tracking | Shared Foundation | Every product needs reproducible database evolution |
| Content-package version tracking | Shared Foundation | Imported rules and content must be identifiable |
| Event and receipt infrastructure | Shared Foundation | All products need accountable state changes |
| Command identity and idempotency | Shared Foundation | Prevents duplicated actions and unsafe retries |
| Random-number service and recorded random inputs | Shared Foundation | Reproducibility is universal |
| Authentication primitives | Shared Foundation | Security behavior should receive fixes centrally |
| Authorization framework | Shared Foundation | Products define permissions but share enforcement |
| Audit logging | Shared Foundation | Operational accountability is common |
| Backup and restore mechanisms | Shared Foundation | Data safety should not be reinvented per game |
| AI provider interface | Shared Foundation | Provider transport is not game logic |
| AI scene-packet envelope | Shared Foundation | Establishes the universal AI boundary |
| AI command gateway | Shared Foundation | AI must never mutate state outside validated commands |
| Narration attempts, rejection, and revision records | Shared Foundation | The X workflow is a product-wide invariant |
| Canon proposal and approval workflow | Shared Foundation | Status and provenance behavior are common |
| Web error, session, and request infrastructure | Shared Foundation | Stable application plumbing |
| Real-time update transport | Shared Foundation | Delivery mechanism is independent of game rules |
| Test harnesses and architectural checks | Shared Foundation | Boundaries should be verified consistently |
| Observability and health checks | Shared Foundation | Required for every deployed product |
| Cepheus character creation and careers | Cepheus Engine Core | Required source-governed engine behavior |
| Actors, possessions, and advancement | Cepheus Engine Core | Required authoritative Cepheus state |
| Cepheus task resolution | Cepheus Engine Core | Governing reusable resolution system |
| Personal and ship encounters | Cepheus Engine Core | Both scales are native Cepheus domains |
| Cepheus markets and trade | Cepheus Engine Core | Native rules and campaign state |
| Cepheus travel, worlds, and journeys | Cepheus Engine Core | Native rules and campaign state |
| Cepheus vehicles and starships | Cepheus Engine Core | Spacecraft are part of Cepheus itself |
| Manual state-edit workflow | Product Seed | Common player freedom with product-specific fields |
| Standard campaign screens | Product Seed | Useful starting UX that should become product-authored |
| Standard administrator screens | Product Seed | Common needs, product deployment may vary |
| Cepheus rules tables and calculations | Cepheus Engine Core | The relational engine is the first goal |
| Cepheus characteristics, skills, careers, and advancement | Cepheus Engine Core | Source-governed engine content |
| Cepheus combat and damage rules | Cepheus Engine Core | Source-governed engine behavior |
| Cepheus psionics and abilities | Cepheus Engine Core | Native engine domain with extension points |
| Faction, relationship, and location structures | Cepheus Engine Core | Required reusable campaign-state relationships |
| Authored setting, factions, locations, history, and lore | Product-Specific | Constitutes the authored world |
| Cepheus NPC, creature, equipment, and vessel catalogues | Cepheus Engine Core | Source-governed engine content |
| Cepheus trade goods and economic rules | Cepheus Engine Core | Source-governed engine content |
| Product terminology | Product-Specific | Each game should speak its own language |
| Visual design, artwork, and sound | Product-Specific | Each shipped game needs a distinct identity |
| Product system prompt and narrative voice | Product-Specific | Tone and portrayal are authored content |
| Product licensing and legal notices | Product-Specific | Rights and attributions differ |
| Product onboarding and help | Product-Specific | Must explain the actual game, not the factory |

## Shared Foundation Responsibilities

### 1. Persistence Kernel

The foundation owns:

- opening and configuring database connections;
- beginning, committing, and rolling back transactions;
- migration discovery and execution;
- schema and content version records;
- optimistic concurrency or equivalent conflict detection;
- idempotency protection for retried commands;
- backup integrity checks;
- common identifier, timestamp, and provenance conventions.

The foundation does not own product tables merely because they reside in the
same database.

### 2. Command and Event Kernel

Every state-changing operation enters through a named application command.

The shared kernel provides:

- command identity;
- initiator identity and authority;
- validation result;
- transaction scope;
- generated domain events;
- mechanical receipts;
- reversal or compensating-command relationships;
- event ordering;
- safe publication to connected clients.

The product defines what a command means. The foundation guarantees how a
command is executed and recorded.

### 3. Recorded Randomness

The foundation supplies random values to product rules rather than allowing
rules, browser code, or AI to obtain hidden randomness independently.

Each meaningful random use records:

- the requesting command;
- the requested expression or distribution;
- raw result;
- interpreted result where appropriate;
- generator or seed metadata needed by the product's reproducibility policy.

A product decides whether it uses 2d6, cards, dice pools, tables, or another
method.

### 4. AI Boundary

The foundation owns the safe path between authoritative game state and an AI
provider.

It provides:

- a versioned scene-packet envelope;
- explicit separation of facts, resolved events, dialogue context, and style;
- a bounded list of commands or intentions available in the current situation;
- validation of AI-requested commands;
- storage of AI inputs and outputs according to product privacy policy;
- narration-attempt and revision lineage;
- exclusion of rejected narration from current context;
- provider abstraction, timeouts, retries, and failure handling.

The foundation does not decide the voice of a Roman senator, Viking skald, alien
broker, or anime rival.

### 5. Narration and Canon Workflows

The foundation implements states and transitions, not creative content.

Narration states may include:

- proposed;
- accepted;
- rejected;
- superseded.

Campaign-fact states may include:

- proposed;
- established;
- rejected;
- superseded.

A product may extend these states only through a deliberate migration and
contract change. It must not collapse mechanics, facts, and narration into one
record.

### 6. Identity, Access, and Player Authority

The foundation supplies authentication and general authorization mechanisms.
Products define their roles and policies.

The shared model must be able to distinguish:

- system activity;
- AI proposals;
- referee commands;
- player commands;
- player manual overrides;
- administrative operations.

Manual overrides are legitimate commands, not database corruption. They should
remain visible and mechanically consistent.

### 7. Operational Foundation

The foundation owns repeatable production capabilities:

- configuration and secret loading;
- structured logs;
- health and readiness checks;
- database backups and tested restoration;
- deployment build conventions;
- error reporting;
- basic performance instrumentation;
- data export and account deletion mechanisms where required;
- security updates to shared dependencies.

These are part of the product even though they are not game rules.

## Derived Product Seed Responsibilities

Derived product seeds are cut from a versioned, complete Cepheus engine. They
accelerate product creation without reducing Base Cepheus itself to examples or
partial workflows.

Each seed must include:

- a clearly stated contract;
- an origin name and semantic version;
- focused tests;
- extension and replacement points;
- a record of assumptions;
- sample—not mandatory—terminology;
- a changelog of fixes worth evaluating in descendants.

### Recommended Initial Seeds

#### Character Creation

The complete Cepheus workflow for ordered steps, choices, random results,
validation, preview, and final commitment. A derived product can retain it,
extend it, or deliberately replace terms and careers with its own lifepath.

#### Tasks

The complete deterministic Cepheus task implementation showing
characteristics, skills, difficulty, modifiers, random input, Effect, and a
recorded result. A descendant may fork it deliberately.

#### Encounters

The complete Cepheus state machines for participants, phases or turns, legal
intentions, resolved actions, conditions, and encounter completion.

#### Journeys

A workflow for departure, route selection, time and resource commitments,
intermediate events, arrival, interruption, and cancellation.

#### Markets

A workflow for stored availability, held quotes, atomic exchange, money,
inventory, and transaction receipts.

#### Vessels

A workflow for identity, ownership, capacity, crew assignments, cargo,
condition, movement, and damage. A descendant may become a starship system,
longship system, galley system, train system, or discard vessels entirely.

#### Vessel-to-Personal Encounters

A workflow connecting a vessel-scale approach, attachment, or breach to a
linked personal encounter, then returning structured personal outcomes to
vessel control and condition. Descendants supply their own mechanics: docking
and airlocks, grappling and crossing decks, ramming and boarding bridges, or
other product-specific procedures.

## Product-Specific Responsibilities

A derived product owns every choice that makes it distinct from Base Cepheus:

- rules and balance that depart from or extend Cepheus;
- database tables needed only by those extensions;
- downstream source content and its provenance;
- world model;
- terminology;
- gameplay screens;
- presentation and accessibility decisions;
- AI voice and portrayal guidance;
- legal text and branding;
- which seed systems it adopts, rewrites, or omits.

A product is permitted to become unlike its siblings. Independence is a feature.

The Cepheus engine must acquire native concepts such as `jump_drive_rating`.
It must not acquire downstream-only concepts such as `longship_oar_benches` or
`legion_rank` merely to avoid writing a product extension.

## Dependency Direction

Dependencies must flow toward stable infrastructure:

```text
Product presentation
        |
Product application commands
        |
Product domain rules and state
        |
Shared command, event, AI, and persistence contracts
        |
Shared technical infrastructure
```

The shared foundation may define interfaces implemented by a product. It must
not import product modules or branch on product names.

Forbidden patterns include:

- `if product == "norse"` inside shared code;
- shared database tables accumulating nullable columns for every product;
- AI provider code importing combat rules;
- browser routes performing authoritative rule calculations;
- product rules directly writing receipt or event tables;
- one product reading another product's content directory at runtime.

## Proposed Repository Shape

The exact programming language and packaging details will be chosen during
architecture design, but responsibility should be visible in the repository.

```text
baseCepheus/
  docs/
    constitution/
    architecture/
    product-method/

  foundation/
    persistence/
    commands/
    events/
    randomness/
    identity/
    ai/
    narration/
    canon/
    operations/
    testing/

  seeds/
    chargen/
    tasks/
    encounters/
    journeys/
    markets/
    vessels/
    web-shell/

  tooling/
    product-create/
    source-import/
    schema-check/
    descendant-audit/

  products/
    space/
      product-manifest
      application/
      domain/
      content/
      web/
      tests/

  books/
    [unaltered source material]
```

This is a responsibility sketch, not authorization to create all directories
before their contracts are understood.

## Creating a Product

A new product should be created through a recorded procedure:

1. Select a tagged Shared Foundation version.
2. Select Product Seeds individually.
3. Record every selected seed and version in a product manifest.
4. Copy selected seeds into product ownership.
5. Rename product vocabulary deliberately.
6. Remove irrelevant capabilities before adding content.
7. Define product rules and database extensions.
8. Establish source and license provenance.
9. Pass the foundation contract tests.
10. Begin product-specific development.

The product manifest might conceptually record:

```text
foundation: 1.2.0
seeds:
  chargen: 1.0.0
  tasks: 1.1.0
  journeys: detached-from-1.0.0
  markets: omitted
```

“Detached” means the product retains ancestry but no longer expects routine
compatibility updates from that seed.

## Propagating Fixes

Shared Foundation fixes and Product Seed fixes travel differently.

### Shared Foundation Fixes

Security, transaction, audit, migration, AI-boundary, and operational fixes are
released centrally. A product updates its foundation dependency and runs the
shared contract suite plus its own tests.

Breaking shared changes require a migration guide and a major version.

### Product Seed Fixes

A seed fix does not automatically overwrite descendant code.

The seed changelog should state:

- affected seed versions;
- severity;
- behavioral consequence;
- relevant commits or patch;
- tests that demonstrate the defect;
- whether detached products should evaluate the fix.

Each product then records one of:

- applied;
- already independently fixed;
- not applicable;
- deliberately declined;
- awaiting evaluation.

The goal is informed propagation, not permanent lockstep.

### Cross-Product Learning

A defect found in one product should be classified:

1. **Foundation defect:** fix centrally and release.
2. **Seed defect:** fix the seed and notify descendants.
3. **Product defect:** fix only that product.
4. **Emerging common pattern:** document it; do not extract until its stability
   is demonstrated.

## Change-Control Rules

### Promoting Code into the Shared Foundation

Code may be promoted only when:

- at least two real product needs support the abstraction, or it protects a
  constitutional invariant from the beginning;
- the behavior can be described without product vocabulary;
- the interface is smaller and more stable than the implementations it replaces;
- contract tests can verify it;
- central ownership will reduce total risk rather than merely reduce visible
  duplication.

### Moving Shared Code into a Product

A shared responsibility may be detached only when:

- the product has a legitimate incompatible requirement;
- the security, audit, and data-integrity consequences are understood;
- the product records the point of divergence;
- replacement contract tests exist;
- future shared fixes can still be evaluated.

### Avoiding Premature Abstraction

Two features that sound alike may still need different implementations.
Starship combat and naval combat can share design insight without sharing a
class hierarchy. Extraction should follow demonstrated common behavior.

## Emporos Extraction Targets

Emporos should supply requirements and tests before it supplies code.

### Evaluate for Shared-Foundation Lessons

- numbered mechanical receipts;
- gap detection and non-destructive voiding;
- event ordering;
- lore proposal and approval;
- narration rejection;
- provider-independent referee modes;
- real-time campaign updates;
- authentication and campaign ownership;
- backup needs observed in production.

### Evaluate as Product Seeds

- deterministic character-creation sessions;
- held daily markets and atomic stock reduction;
- personal and vessel combat workflows;
- travel and jump workflows;
- cargo and money transfers;
- battle persistence;
- task and dice calculations.

### Do Not Extract Whole

- `web/app.py`;
- `referee/tools.py`;
- `state/repo.py`;
- `referee/prompt.py`;
- `state/schema.sql`;
- the main static HTML page;
- JSON-shaped domain records;
- existing database snapshots as schema templates.

These remain behavioral references and sources of acceptance cases.

## Architectural Enforcement

The responsibility boundary should eventually be tested automatically.

Candidate checks include:

- shared modules cannot import from a product;
- product domain code cannot import an AI provider;
- browser code cannot write the database;
- AI callbacks can invoke only registered application commands;
- product rules cannot generate unrecorded randomness;
- every state-changing command creates an audit record;
- rejected narration cannot enter a current scene packet;
- JSON columns require an explicit architectural exemption;
- migrations must upgrade every supported prior schema fixture.

Written boundaries that are not tested will gradually become suggestions.

## Decision Test

When placing a new component, ask:

1. Is this a stable engineering invariant or a game-design choice?
2. Must a critical fix reach every product?
3. Is meaningful product divergence likely?
4. Can the responsibility be expressed without genre terminology?
5. Does sharing reduce risk, or merely reduce duplicated lines?
6. Would copying give the product valuable independence?
7. Who owns its tests and migration consequences?
8. How will descendants learn about later defects?

The default choices are:

- infrastructure and source-governed Cepheus behavior: **Cepheus Engine Core**;
- a versioned starting point copied from that engine: **Derived Product Seed**;
- downstream departures, setting, language, and identity: **Product-Specific**.

## Accepted Direction

Base Cepheus will first be a complete relational implementation of the Cepheus
engine, including its native science-fiction and space domains.

It will not become a runtime filled with genre switches. Derived products begin
from the complete engine, then may detach or evolve independently while
preserving ancestry and the ability to evaluate later engine corrections.
