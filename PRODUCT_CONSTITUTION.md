# Base Cepheus Product Constitution

## Purpose

Base Cepheus is a database-first relational implementation of the Cepheus
Engine and the production ancestor of distinct, independently shipped
role-playing games.

The engine includes Cepheus's native science-fiction and space rules; those are
part of Cepheus rather than a separate product layer. Base Cepheus is not a
runtime genre selector. Purpose-built games—Space, Norse, Roman, historical,
fantastic, licensed, or otherwise—are derived from the completed relational
engine and then developed and shipped independently.

Each finished game should feel authored for its own world. Shared ancestry is an
implementation concern, not part of the player's experience.

## 1. The Database Is the Authority

Persistent rules, content, and campaign state belong in appropriately structured
database tables.

JSON may be used for API responses, imports, exports, caches, generated scene
packets, and other temporary projections. It must not become an alternate
canonical store for data that has a natural relational structure. A disposable
JSON representation should be reproducible from authoritative data.

Rules definitions and mutable campaign state must be distinguishable. Source,
edition, version, licensing, and import provenance must be retained for
published rules and content.

## 2. The Engine Resolves the Game

Deterministic application code owns mechanical truth, including:

- dice and task resolution;
- character creation and advancement;
- money, prices, trade, and transactions;
- possessions, equipment, cargo, and resources;
- travel, time, routes, fuel, and supplies;
- combat, damage, healing, and conditions;
- abilities, spells, powers, and psionics;
- vessel and vehicle operation;
- encounter state and other persistent consequences.

Random results must be rolled once, recorded, and reused. Reloading a page or
rewriting narration must not silently reroll or alter a mechanical outcome.

## 3. AI Is a Performer and Bounded Decision-Maker

AI may:

- narrate established facts and resolved events;
- portray dialogue, personality, mood, and sensory detail;
- produce prose or poetry appropriate to the product;
- select an NPC's intention from actions that the engine determines are legal;
- make bounded judgment calls when several legal NPC choices exist;
- propose new fiction for player or referee approval.

AI may not:

- resolve mechanics or modify authoritative state directly;
- invent possessions, money, abilities, exits, locations, or relationships and
  present them as established facts;
- silently create campaign canon;
- declare thoughts, speech, or actions for a player character;
- substitute remembered prose for a database lookup;
- change a resolved result while rewriting its presentation.

AI receives a deliberately assembled view of the current scene, not unrestricted
authority over the database or campaign history. Mechanical mutations pass
through validated engine commands.

## 4. Players Own Their Game

The player may directly edit their characters, possessions, money, experience,
and other appropriate campaign state.

The application may warn, explain, and preserve an audit trail, but it does not
police a solo player's preferred style of play. If a player chooses to give
themselves an advantage, that is their choice.

Manual changes use the same safe transaction and event mechanisms as automated
changes so that the resulting state remains consistent, visible, and, where
practical, reversible.

## 5. Narration Is Rejectable

Every consequential AI narration must support rejection.

The player may mark narration with an X, give a reason, and require a rewrite.
The rejected text remains available for audit but is not the current canonical
presentation of events.

A rewrite changes wording, interpretation, tone, or permitted fictional detail.
It does not change recorded dice, transactions, damage, movement, or other
mechanical results unless the player separately edits or reverses those results.

Corrections and AI apologies belong outside the fiction. A revised passage
should read as though the rejected mistake never occurred.

## 6. Canon Must Be Explicit

Campaign facts are either established, proposed, superseded, or rejected.
Narrative text is not automatically authoritative merely because an AI wrote it.

Important facts—people, locations, connections, possessions, factions,
relationships, promises, discoveries, and persistent scene conditions—must be
represented structurally when the game needs to remember or reason about them.

Approved prose may describe canonical facts; it must not be the only place those
facts exist.

## 7. Complete Engine, Derived Products

Base Cepheus first provides a complete relational Cepheus rules and state
engine. Games derived from it are independent products, not runtime genre
skins. Each may have its own:

- database schema and content;
- rules and terminology;
- interface and workflows;
- artwork, tone, and narrative instructions;
- deployment, branding, licensing, and commercial identity.

Common code should be retained where shared behavior has lasting value, such as
database transactions, event ledgers, audit records, AI boundaries, validation,
authentication, and narration rejection.

Systems may be copied and adapted when a product needs meaningful independence.
Copied ancestry must remain traceable so that important corrections can be
evaluated across descendant products. A product may deliberately detach from a
shared component rather than accumulating accidental incompatibility.

## 8. Authored Content Beats Improvised Substitution

NPCs, creatures, vessels, vehicles, equipment, encounters, locations, markets,
and other reusable game elements should be drawn from curated database content
or generated by deterministic procedures whose results are stored.

AI improvisation may enrich presentation, but it is not a substitute for the
content and state required to operate the game reliably.

## 9. Every Material Change Is Accountable

Mechanical actions and manual edits should produce durable events or receipts
that answer:

- what changed;
- why it changed;
- who or what initiated it;
- which rule, command, or manual override was used;
- what random result was consumed;
- what the prior and resulting states were, when material.

The event history is a record of the game, not a dumping ground for unstructured
state.

## 10. The Interface Exposes Truth

Players should be able to see and manage the state the engine uses: inventory,
money, time, location, conditions, abilities, cargo, market information, and
mechanical results.

The browser or client may format and preview rules, but it must not independently
implement authoritative calculations. The server-side engine and database
remain the source of resolved truth.

## 11. Licensing and Provenance Are Design Requirements

Open content, original content, product identity, licensed material, and private
campaign material must remain distinguishable.

No protected setting or commercial text is incorporated merely because the
foundation is technically capable of representing it. A licensed product can
be created when the necessary rights and agreement exist.

The foundation should make legitimate collaboration with publishers easier by
keeping content ownership, sources, and product boundaries visible.

## 12. Relational Completeness Precedes Product Breadth

The first construction milestone is the complete relational Cepheus database:
all rule definitions, campaign-state families, provenance, constraints, and
extension boundaries required by the engine.

After that schema exists, gameplay commands should prove complete vertical
paths through engine resolution, event records, AI presentation, validation,
and rejection behavior. Downstream products are not developed in parallel with
an incomplete engine database.

## 13. Cepheus Rules Govern the Engine

While designing and building Base Cepheus, the selected Cepheus source package
is the default authority for rules, procedures, tables, definitions, and
mechanical interpretation. Native space rules remain part of that engine.

Before implementing a game rule, the relevant Cepheus material must be queried
and its source recorded. The implementation must distinguish:

- a rule stated by the source;
- an interpretation required to implement that rule;
- an omission or ambiguity in the source;
- an optional rule supplied by the source;
- a deliberate house rule or product addition.

No mechanic, modifier, restriction, table result, item property, encounter
procedure, or setting assumption may be invented merely to fill a gap, simplify
implementation, or satisfy an AI-generated design.

When the source is silent or ambiguous, implementation pauses at that decision
point. A proposed interpretation or addition must be presented for explicit
agreement. Once agreed, it is recorded as a product decision with its rationale
and relationship to the source.

Refactoring may change code structure without changing rule behavior. Any
intentional rules departure requires the same explicit agreement even when the
departure appears minor or beneficial.

## Decision Test

A proposed feature or shortcut belongs in the foundation only if it can answer
these questions satisfactorily:

1. What is the authoritative data?
2. Where is that data stored?
3. Which code is allowed to change it?
4. What is the player's authority over it?
5. What may the AI say or choose, and what may it not change?
6. How is the action validated, recorded, and, when appropriate, reversed?
7. Is this truly common infrastructure, or should it belong to one finished
   product?
8. Can a second product reuse the underlying idea without inheriting irrelevant
   terminology or rules?
9. What Cepheus source governs this behavior, and is any part an interpretation,
   omission, optional rule, or agreed departure?

If those answers are unclear, the feature is not ready for implementation.
