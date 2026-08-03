# Relational Cepheus Schema Completion

## Controlling Goal

Base Cepheus is the complete relational implementation of the Cepheus Engine.
Its native science-fiction domains—including worlds, interstellar travel,
trade, spacecraft, and space combat—belong in the engine.

Space, Norse, Roman, and other later games are derived products. Their future
needs do not justify weakening, postponing, or prematurely generalizing the
Cepheus schema.

## Definition of Schema Complete

The first database milestone is complete only when:

1. Every source-governed Cepheus definition has a normalized relational home.
2. Every persistent campaign-state concept needed by those rules has a
   normalized relational home.
3. Definitions belong to versioned content packages and retain provenance.
4. Campaign rows cannot cross campaign boundaries through an invalid
   relationship.
5. Current state is distinguishable from immutable history and receipts.
6. Cardinality, lifecycle, ranges, uniqueness, and legal state transitions are
   enforced in PostgreSQL wherever practical.
7. JSON remains temporary import or projection data, never canonical domain
   state.
8. A new database can rebuild from migration 0001 and pass structural,
   catalogue, provenance, and integration verification.
9. Downstream products can identify the engine version and package ancestry
   from which they derive without being embedded in the core schema.

Application commands and user interfaces may remain incomplete at this
milestone. The schema itself may not omit a domain merely because its command
handler has not yet been written.

## Current Physical Coverage

Snapshot after migration 0190: 617 public tables and 17 public views.

| Family | State | Current coverage | Principal remaining work |
|---|---|---|---|
| `sys_` | Partial | migrations, content packages, legacy seed ancestry | explicit derived-engine ancestry and operational release metadata |
| `iam_` | Foundation | accounts, roles, campaign membership, character authority | credentials, sessions, invitations, administrative grants |
| `cmd_` | Substantial | commands, events, random draws, many typed receipts | campaign-scoped kernel records, generic receipt/rule links, reversals |
| `nar_` | Absent | — | scene packets, attempts, rejection, revision, current selection |
| `can_` | Absent | — | fact proposals, decisions, supersession, discovery |
| `src_` | Substantial | sources, locators, staging, review, provenance, and a typed issue register with exact evidence links, reviewer questions, priority, disposition, and resolution state | remaining source families and import-run coverage |
| `rule_` | Substantial | tasks, combat including the published burst-size and mutually exclusive spray/grouped-fire rules, careers, species, encounters, psionics, UWP vocabularies and qualification conditions, jump travel, passage, fuel, traffic, trade goods, trade modifiers, price bands, and spacecraft definitions | hazards, recovery, NPC content, and source-complete spacecraft catalogues |
| `cg_` | Partial under `actor_` | extensive career/lifepath state | explicit creation session, step, choice, preview, and import-batch families |
| `camp_` | Foundation | campaign, installed packages, clock, clock history | campaign configuration, structured time advancement, scenes |
| `actor_` | Substantial | actors, characteristics, skills, careers, species, relationships, factions, memberships, reputation, notes | NPC templates and objectives |
| `loc_` | Substantial | typed locations, acyclic containment, positions, sectors, subsectors, systems, celestial bodies, definition-bound revisioned world profiles, validated trade-code assignment, and routes | world-generation roll procedures, stellar details, and mapping procedures |
| `inv_` | Substantial | definitions, instances, lots, typed containers, custody, ownership, transfers, conditions, equipped state, capacity and cycle guards, and relational weapon-to-burst-size eligibility | modifications, source-complete equipment effects, cargo integration |
| `fin_` | Foundation | currencies, typed accounts, balanced immutable journals, reversals, obligations, payments, derived balances | migrate specialized career cash/debt state into ledger authority; recurring payments and interest |
| `mkt_` | Foundation | markets, sessions, typed suppliers, stock, scoped quotes, orders, financially and physically linked executions, and complete trade-code modifier catalogue | supplier-search attempts and broker commissions |
| `journey_` | Foundation | journeys, continuous legs, participant and cargo commitments, progress, jump attempts, refueling, passage, ship conveyance identity, active ship crew commitments, and planned/actual ship resource use | freight/mail contracts, vehicle conveyance, and remaining procedural receipts |
| `ship_` | Substantial | all 18 published common starships and 6 common small craft with source-located profiles, canonical hull/drive/computer/electronics relations, construction armor selections, accommodation, cargo, utility components, hangars, carried craft and inventory-backed carried probe drones, escape systems, explicit source assertions, armament declarations, and complete weapon/ammunition/screen loadouts; versioned immutable whole-design receipts with 475 retained calculation lines, current-receipt and variance-audit projections, and explicit reconciliation states; structural-completeness projection; instances backed by inventory identity; source-defined construction catalogues; crew, costs, legal interests, maintenance, damage, and journey integration | continue source adjudication of the five unexplained tonnage and eighteen current unitemized cost variances; ship-combat integration |
| `vehicle_` | Relationally complete | published chassis, configurations and configuration options, armor, power-plant, propulsion, drive-performance, drive options, speed, agility, fuel, control, drone-controller, robot-brain, autopilot, communication, sensor, computer, crew accommodation, life-support, additional-component, weapon-point, gun-port, weapon-mount, gun-shield, turret, coaxial-mount, pop-up-turret, armament-option, vehicular-weapon, ammunition, ordnance-bay, bomb, torpedo, missile, and anti-missile definitions; the complete VDS weapon-range difficulty matrix; alien-design assumptions; lift-envelope, aircraft-environment, missile/torpedo attack, animal-power, sailing-speed, and off-road movement rules; exact scaling formulae, capacities, effects, prerequisites, environmental protections, submersible-depth rules, and an exclusive ship-scale construction bridge for large watercraft; all 20 currently published common and uncommon vehicle profiles, including ship-drive-scale watercraft; relational component, configuration-option, drive-option, autopilot, computer-option, fuel, alternative-communication, armament, ammunition, missile, and torpedo selections for every profile; immutable versioned published construction receipts for all 20 profiles with 264 retained fractional-cost and typed capacity/allocation/remainder lines, explicit published/source-gap reconciliation states, and 10 issue-linked material variance audits; paired-source vehicle personal-combat procedure, occupant protection, weapon arcs, collision arithmetic, evasive, maneuver, ram, stunt, and weave action definitions, damage-to-hit bands, complete external/internal/robot hit-location matrices, escalating system effects and overflow rules, destruction explosions, and system/hull/structure repair formulae; campaign-bound vehicle engagement, force, participant, round, facing, speed, crew-turn, action, pursuit, immutable action-resolution, collision, and occupant-effect state; immutable mounted-weapon attack receipts retaining range-matrix identity, ordered modifiers, armor calculation, damage band, and hit-packet plan; atomic immutable damage applications retaining every location roll, typed overflow, staged system hit, and before/after integrity value while updating authoritative armor, hull, structure, lifecycle, and named system state; immutable repair receipts for Hull, Structure, damaged systems, destroyed systems, and jury-rigs with typed checks, dice, elapsed time, cost, facilities, materials, spare-part provenance, temporary restoration, and authoritative state transitions; inventory-backed instances; class and installed components; resources; crew stations and assignments; damage; operational control; an explicit catalogue-completeness projection proving all 20 published profiles have current finalized receipts, provenance, capacity, cargo, propulsion, component selections, and optional selections consistent with their receipts | source adjudication of the 18 retained publication reconciliation conflicts remains non-blocking |
| `enc_` | Substantial | campaign-safe general encounters with registered sides, participants, attitudes, immutable mode history, typed participant intentions, side or participant objectives with relational targets, objective results, immutable encounter outcomes, and atomic encounter/personal-combat closure; animal, social, starship-contact, and extensive personal-combat state including source-governed burst declarations, ammunition use, accuracy choice, extra damage, and immutable receipts | abstract units and remaining personal-combat coverage |
| `senc_` | Foundation | two-force engagements, participating vessels, pairwise range, rounds, crew turns, action budgets, reactions, attacks, damage allocation, and missile salvos | initiative and range procedures, weapon effects, defenses, pursuit, boarding, collisions, repair actions, and encounter resolution |
| `ability_` / `psi_` | Partial | psionic catalogue and activation | generalized effects, costs, targets, non-psionic extension boundary |
| `health_` | Early | damage instances and allocations | conditions, treatment, recovery, unconsciousness, healing |
| reusable creatures/NPCs | Early | animal reaction definitions | templates, generated instances, attacks, behavior, encounter roles |

“Substantial” means important relational work exists; it does not mean the
family is source-complete.

## Dependency Order

Implementation proceeds by whole relational families:

1. identity, campaign authority, installed packages, and authoritative time;
2. locations, containment, actors, relationships, factions, and positions;
3. item instances, containers, ownership, finance, and atomic transfers;
4. worlds, routes, travel, journeys, trade, and markets;
5. vehicles, spacecraft, crew, resources, components, and damage;
6. complete personal and ship encounter state;
7. abilities, health, recovery, NPCs, creatures, and reusable content;
8. canon, narration, revision, and operational completion;
9. clean-database structural verification and a schema-completeness gate.

Families 1 through 4 have relational foundations, the trade-code qualification
and trade modifier matrices are normalized, and family 5 now includes
operational spacecraft, ship-journey integration, normalized Vehicle Design
System drive and propulsion matrices, the standard vehicle catalogue, and the
first relational ship-combat state. Spacecraft construction now includes both
published drive matrices and the principal hull, armor, bridge, computer,
software, electronics, fuel, additional component, hangar, armament,
ammunition, and defensive-screen catalogues. All published common-vessel
profiles are loaded with their canonical core selections, accommodation,
utility components, cargo, hangars, carried craft, armament declarations, and
weapon loadouts. Every profile now has a finalized, immutable whole-design
receipt. Four published small craft reconcile exactly; all remaining source
gaps and tonnage or cost variances stay visible instead of being erased by
invented balancing entries. Receipts are versioned so corrections preserve the
prior calculation: the Cutter's second receipt adds its explicitly published
passenger cabin space. Four capped-armor tonnage differences are now classified
as common-design conflicts with the whole-increment construction rule.
Research and Survey Vessel receipt version 2 adds the separately published
Cr15,000 cost of every carried probe drone; the Research Vessel also exposes
the publication conflict between its TL9 hull and the TL11 probe-drone
catalogue entry. All 30 current construction discrepancies, four unresolved
ship assertions, and nineteen VDS catalogue questions are now published into the
common source-issue workflow. The generated reviewer projection separates
nineteen high-priority source gaps or conflicts, twenty-five medium-priority
questions, and twenty low-priority unitemized price differences. The
predecessor Cepheus
game was checked against all 64 findings: it directly parses the publication's
ship summary values and has no vehicle-construction subsystem or independent
construction adjudications. That negative result is retained relationally so
the comparison is not repeated. Source investigation can proceed alongside the
remaining database families instead of blocking them.

Within a family, definitions, campaign instances, history, receipts, provenance,
and constraints are designed together. Runtime feature work resumes after the
relational milestone unless it is required to prove a database invariant.

The empty-database bootstrap explicitly interleaves schema migrations with all
eleven reviewed catalogue importers at nine dependency boundaries. It refuses
to operate on a populated database and verifies the completed result, replacing
the former implicit setup history with a reproducible build procedure.

Database verification also scans every base-table text column. Values longer
than 80 characters are rejected outside explicitly narrative fields such as
descriptions, rationales, evidence, source values, and audit explanations.
Mechanical behavior must remain typed instead of accumulating in notes.
