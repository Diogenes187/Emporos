# Cepheus Implementation Coverage

This audit compares the pinned GitHub v9.1 chapter hierarchy, the paired OGN
publication, and the relational schema through migration 0526. It measures
mechanical implementation, not merely citation coverage. The governing website
and repository agree on the space-combat turn-order mechanics used by 0394.

## Classification

- **Runtime complete**: normalized definitions, campaign-safe state, immutable
  receipts or history, database invariants, tests, and verification exist.
- **Relational foundation**: definitions and campaign state exist, but important
  source procedures are not yet executable end to end.
- **Catalogue complete**: published definitions are normalized, but operational
  use may remain elsewhere in the backlog.
- **Narrative**: referee advice or examples do not require authoritative runtime
  state.

## Chapter audit

| Source chapter | Current state | Principal remaining mechanical work |
|---|---|---|
| Character Creation | Runtime complete | None identified |
| Skills | Runtime complete | None identified |
| Psionics | Runtime complete | None identified |
| Equipment | Runtime complete for current consumers; catalogue complete | None; add specialized effects only with a future consuming procedure |
| Personal Combat | Runtime complete | None identified |
| Off-World Travel | Runtime complete for core procedures | Private messages and legal-case runtime are optional campaign detail |
| Trade and Commerce | Runtime complete | None identified |
| Ship Design and Construction | Catalogue complete | None identified after adjudication |
| Common Vessels | Catalogue complete | None identified after adjudication |
| Space Combat | Runtime complete | None identified |
| Environments and Hazards | Runtime complete | None identified |
| Worlds | Runtime complete | None identified |
| Planetary Wilderness Encounters | Runtime complete | None identified |
| Social Encounters | Runtime complete for published selection procedures | Reusable authored patron/NPC briefs where campaign reuse warrants authority |
| Starship Encounters | Runtime complete | None identified |
| Refereeing the Game | Mostly narrative | Reusable NPC templates where mechanics are specified |
| Adventures | Narrative | No authoritative mechanical runtime required |
| Vehicle Design System | Runtime and catalogue complete | None identified after adjudication |

## Ordered relational backlog

No mandatory core relational blocks remain in the audited Cepheus Engine
scope. Future genre or campaign features may add consumers for specialized
catalogue entries, but catalogue presence alone is not a reason to invent a
runtime procedure.

Planetary legal-case workflow, private-message jobs, distress-call logs, and
similar referee-facing campaign records are explicitly optional. Published
tables may be normalized without implying that every narrative prompt requires
an executable subsystem.

Migrations 0522 and 0523 normalize all 36 published patron-role outcomes and
all 36 rumor-content outcomes with row-level paired provenance. Campaign-owned
patron and rumor encounters now receive idempotent D66 selections, preserved
dice, immutable receipts, encounter-type invariants, and a read model that
supplies structured facts without prescribing generated prose.

Migration 0524 implements the published reusable patron format as campaign-safe
briefs with normalized skill/resource requirements, rewards, player mission
facts, multiple referee-truth variants, and prioritized NPC objectives. Each
creation command seals the complete revision with immutable counts; later AI
narration may phrase those facts but cannot rewrite their authoritative history.

Migrations 0525 and 0526 add the agreed structured-scene convention, grounded in the
paired improvisational-preparation advice but explicitly classified as an
agreed addition rather than a published procedure. Eight reusable blueprints
cover port arrival, docking/customs, jump transitions, wilderness travel,
weather, law stops, markets, and distress calls. Required typed facts are
validated and sealed in campaign-scoped snapshots while all connective prose
remains the AI Referee's work.

The final equipment-consumption audit found no mechanically required orphan for
the procedures currently exposed by the engine. Personal attacks, ammunition,
readying, armor and life support, explosives, battlefield communications,
computers and software, drugs and medical care, sensory aids, shelters,
survival gear, tools, robots/drones, vehicles, and ship weapons all have either
an executable consumer or an intentionally catalogue-only role. This closes
the core equipment backlog without manufacturing commands for descriptive
items that no implemented procedure consumes.

## Current boundary

Migrations 0394 through 0396 complete initial initiative and deterministic
vessel sequencing. They retain the approved CE-SC-001 interpretation, paired
provenance, immutable roll and Tactics receipts, pilot Dexterity snapshots,
fastest-hostile Thrust comparison, atomic round opening, simultaneous groups,
and crew-turn enforcement. Migration 0397 adds opposed Navigation Range Checks,
the general opposed-check tie sequence, immutable receipts, one-band range
changes, and atomic authoritative range updates. Migration 0398 implements CE-SC-002 as an
immutable Captain Leadership receipt: only positive Effect modifies ordering,
the modifier is applied by the atomic opener to the following round only, and
base initiative remains unchanged. Migrations 0399 through 0405 implement
CE-SC-003 pursuit end to end: paired-source mechanics, eligible pairwise state,
opposed Piloting establishment and break receipts, check-free significant-action
maintenance, capped attack bonuses, immutable transitions, mandatory full-tie
rerolls, and immediate invalidation when range reaches Medium or the target gains
a speed advantage of 7 or more. Prior receipts remain immutable after a break;
re-establishment requires a new opposed action.
Migration 0406 completes Evasive Maneuvers with the paired Average Piloting
rule, immutable current-round receipts, a DM-1 attack penalty on success,
DM-2 at exceptional Effect 6+, and no benefit (but a spent action) on failure.
Migration 0407 completes Line Up the Shot with the paired Piloting rule and an
immutable current-round receipt granting all vessel attacks DM+1 on success or
DM+2 at exceptional Effect 6+, with no bonus on failure.
Migration 0408 implements CE-SC-004 combat docking: attempts begin at Adjacent,
unresisted docking uses Average Piloting, resisted docking uses opposed Piloting
with a DM-2 on the docking vessel, full ties require rerolls, and success
atomically advances authoritative pairwise range to Docked for boarding.
Migrations 0409 and 0410 implement CE-SC-005 ramming: Close-range faster-vessel
eligibility, opposed Piloting with full-tie rerolls, normalized immutable shared
damage dice, the same speed-difference damage applied to both vessels, independent
armor snapshots, atomic hull/structure updates, and relational damage allocations.
Migration 0411 completes the paired Pilot movement minor actions: Adjust Speed
atomically changes speed by no more than current Thrust, while Maintain Course
preserves speed exactly; neither action invents a skill check and both retain
immutable vessel-state receipts.
Migrations 0412 and 0413 complete Avoid Collision: the four published hazard
difficulties and speed-difference modifier are normalized, declared hazards
must resolve before round completion, successful checks avoid damage, and
failures apply immutable 1D6-per-current-speed collision dice through armor and
atomic hull/structure history.
Migration 0414 establishes the shared space-combat reaction economy with the
published Initiative bands and completes Dodge Incoming Fire as an active-Pilot
Piloting receipt imposing DM-2 on success while consuming reaction capacity on
failure as well.
Migration 0415 completes the beam-defense path of Fire Sand: an installed
sandcaster and active Gunner are required, each reaction atomically consumes one
canister, and success records one immutable D6 reduction per incoming beam. The
published 8D6 boarding-party effect is normalized pending boarding targets.
Migration 0416 completes missile Point Defense with installed turret lasers,
ordered Turret Weapons receipts, one destroyed missile per success, cumulative
DM-1 checks, and termination at the first miss. Migration 0417 completes
Trigger Screens with installed-screen compatibility, Screens 0 eligibility,
immutable 2D6-plus-skill reduction, and nuclear-radiation removal semantics.
Migration 0418 completes Coordinate Crew with an immutable Average Leadership
receipt and a capped, current-round pool of per-crewmember check modifiers.
Migrations 0419 and 0420 complete Sensor Targeting with target-specific,
current-round Education-based Comms receipts, published DM+1/DM+2 outcomes,
missile applicability flags, electronics/jamming snapshots, and explicit
engagement-scoped crew-role assignments for specialist stations.
Migration 0421 normalizes all 42 cells of the published six-profile
space-weapon range matrix, including explicit unavailable ranges, and maps the
seven conventional weapon definitions to their authoritative attack profiles.
Migration 0422 adds immutable physical-mount attack declarations and per-weapon
checks, enforcing active Gunner roles, installed slots, Turret/Bay Weapons,
range Difficulty, one firing per mount instance per round, and recomputation of
weapon, Coordinate Crew, Line Up, Sensor Targeting, Pursuit, Evasive Maneuvers,
and Dodge modifiers from relational receipts.
Migration 0423 records CE-SC-006 and normalizes the corrected continuous
damage bands, excess-damage increments, and all external, internal, and small-
craft hit-location rows without overlapping boundary values.
Migrations 0424 and 0425 record CE-SC-007 and stage immutable per-weapon damage
dice, armor snapshots, post-armor results, complete mount aggregation, and
damage-band hit-group receipts without mutating the target before location
resolution.
Migrations 0426 through 0429 connect per-beam Fire Sand and per-mount screen
reductions to staged damage, record complete immutable 2D6 location-roll sets,
normalize all 52 published location-hit progression states, and establish
bounded campaign-safe ship armor state so later attacks snapshot damage-reduced
armor rather than silently restoring the class value.
Migration 0430 records CE-SC-008, routing zero-Hull small-craft Hull results to
the same roll row of the Internal column, and establishes campaign-scoped,
installation-bounded state for progressive damage to ship systems.
Migrations 0431 and 0432 apply location groups one hit at a time in authoritative
order, atomically mutating Hull, Structure, Armor, and progressive system state
while retaining immutable routing and before/after receipts. Double and triple
hits therefore preserve their shared rolled location while still honoring
mid-group Hull depletion and subsequent-hit overflow.
Migration 0433 normalizes all ten published Normal and Radiation Crew Damage
outcomes, including roll ranges, random-one versus all-crew targeting, damage
dice, and the explicit ten-rad multiplier.
Migration 0434 stages Crew Damage resolution with source-bound active-crew
snapshots, exactly two immutable outcome dice, and band-recomputed Normal or
Radiation outcome receipts.
Migration 0435 freezes the eligible crew population, enforces uniform ordinal
selection for one-random outcomes or exact enumeration for all-crew outcomes,
and records per-target immutable dice with recomputed normal damage or rads.
Migration 0436 routes normal Crew Damage into the existing pending personal-
damage allocation system and atomically records cumulative radiation exposure
with immutable before/after history. Migration 0437 permits the mount damage
receipt to become applied only after every ordered hit and required secondary
consequence has an immutable application receipt.
Migration 0438 records CE-SC-009, establishes exact fractional-ton ship cargo
custody, and completes Fuel and Hold consequences. Variable results use staged
immutable D6 receipts; percentage losses are allocated proportionally across
both stored fuel grades or every aboard cargo lot; fuel leaks persist as an
hourly campaign-state rate; destroyed tanks and holds remove all stored contents;
and mount completion now requires these secondary consequences to resolve.
Migration 0439 corrects transactional ordering so the immutable final storage
receipt exists before its proportional allocation rows and campaign-state
effects are applied.
Migration 0440 enforces progressive Bridge, Sensors, turret, bay, and Power
Plant damage in active combat: unavailable actions and mounts are rejected,
published sensor and attack penalties are recomputed into immutable checks,
and destroyed Power Plants disable every engaged instance of the vessel.
Migration 0441 completes disabled-Sensors enforcement by rejecting mount attacks
beyond Adjacent range while retaining Adjacent fire as explicitly permitted.
Migration 0442 records CE-SC-010 and propagates progressive M-drive damage into
live combat Thrust: the first hit subtracts one, the second halves then-current
Thrust rounded down, and the third sets Thrust to zero. Immutable before/after
receipts preserve each affected vessel instance and existing speed is retained
as momentum rather than incorrectly capped by damaged Thrust.
Migration 0443 normalizes the three published battlefield-repair Effect bands
and implements active Damage Control Education-based Mechanics checks against
a selected damaged system. Successful repairs atomically reduce system hits,
restore derived penalties and M-drive Thrust, and create immutable receipts plus
separate temporary-restoration state without misclassifying combat work as a
permanent paid repair.
Migration 0444 expires those temporary repairs when an engagement resolves,
escapes, or aborts, reapplies restored hits in receipt order, recomputes live
system effects, and retains immutable expiration history. Consequential losses
such as destroyed stores and prior crew injury are not incorrectly restored.
Migration 0445 records CE-SC-011, normalizes repair-drone Auto-Repair capacity,
and makes each vessel's per-round autonomous-or-assist allocation immutable.
Migration 0446 resolves autonomous checks as the governing default Average 8+
2D6 task with the published +1 DM, enforces ordered installation capacity,
applies Effect-band temporary repairs, records failures without mutation, and
expires successful repairs through immutable end-of-engagement receipts.
Migration 0447 normalizes Reload Weapons System and gives every installed
ammunition-using mount instance and weapon slot campaign-safe ready/spent state.
Firing consumes the published ammunition quantity through the ship-resource
ledger and an immutable receipt; one significant reload action readies exactly
one matching spent system with optimistic version checks.
Migration 0448 hardens readiness initialization and makes Fire Sand select and
spend a deterministic ready sandcaster while sharing its existing immutable
resource movement rather than double-consuming ammunition.
Migration 0449 prevents a reload receipt from readying a weapon unless the
ship still carries at least the weapon's published per-attack ammunition.
Migration 0450 normalizes missile launch ranges, arrival timing, launch-Effect
target bands, Thrust 10, four-turn endurance, and smart-missile behavior. It
adds immutable launcher-backed launch receipts and creates in-flight salvos
from installed rack/bank ammunition counts without treating launch as impact.
Migration 0451 gives every surviving missile an immutable arrival roll, derives
standard/nuclear termination and smart-missile next-round retries, enforces the
four-turn endurance ceiling, and updates salvo state only through a recomputed
final receipt.
Migration 0452 gives each scheduled arrival an explicit reaction window,
allows reactions to target delayed arrivals without fabricating crew actions,
reuses authoritative Dodge and Point Defense receipts, and closes the window
with immutable surviving-missile and effective-target snapshots.

Migrations 0453-0454 resolve every confirmed missile hit independently through
damage dice, current-armor subtraction, damage bands, location rolls, and atomic
ship or system mutations. Nuclear hits also record their additional radiation
crew-hit roll with the target's armor applied as the published negative DM.
Migration 0455 carries missile-created normal and radiation crew hits through
immutable active-population snapshots, published target scopes, consequence
dice, individual health damage, and cumulative radiation exposure.
Migrations 0456-0457 implement abstract boarding as docked, opposed
Intelligence/Tactics rounds with CSO/Captain role enforcement, success and
exceptional outcomes, reaction denial, next-round DMs, delayed control, and
atomic internal-location damage application.
Migration 0458 normalizes orbital insertion and atmospheric entry, including
world size and atmosphere modifiers, automatic success, current world-profile
snapshots, and versioned orbit, decaying-orbit, and atmosphere vessel state.

Migrations 0459 through 0462 complete special ship weapons and personal-scale
attacks against spacecraft, including radiation, sand, damage scaling,
campaign-state application, and immutable receipts. Migrations 0463 through
0488 complete the environmental chapter's executable hazards: acid, carrying
capacity, disease, temperature, fire, falling, poison, radiation and sickness,
starvation, dehydration, suffocation, vacuum, weather, and recovery guards.
Migrations 0489 through 0494 complete ship-security access, cybersecurity,
compartment alarms, gravity, atmosphere venting, tranquilizer gas, recurring
checks, and source-specific unconscious state. Migration 0495 normalizes the
published planetary law-encounter and sentencing tables without expanding into
optional legal-case runtime. Migrations 0496 through 0498 complete the prior
starship-revenue backlog: paired-source revenue constants, simultaneous freight
and passenger availability, three-day refreshes, capacity-safe freight and
passenger acceptance, delivery payment receipts, armed-ship and active-gunner
postal contracts, and immutable two-week starship charter quotes and contracts.
Migrations 0499 through 0504 complete the remaining core ship-passage work:
paired-source Aiding Another Effect bands; normalized high, middle, low,
working, and stowaway passage terms; fare and accommodation invariants;
installed stateroom and low-berth capacity; steward manifest limits; and
audited low-berth revival with applied Medicine assistance, immutable outcomes,
optimistic passage versions, and explicit failed-revival death state.
Migrations 0505 through 0508 complete the speculative-trade lifecycle: every
supplier's six common goods and 1D6 D66 selections have normalized immutable
draws, duplicate quantities aggregate, legal markets ignore illegal selections,
and black markets retain matching illegal goods. Rejected purchase and sale
quotes create counterparty-specific seven-day cooldown receipts. Local brokers
are limited by starport class, replace the merchant's Broker skill through the
existing audited task path, and receive a posted commission even when the
merchant rejects the resulting quote. CE-TRADE-001 records the approved
whole-Credit ceiling for fractional commissions.
Migrations 0509 through 0511 complete relational world generation: one-D6
subsector density checks map to exact campaign hexes; every UWP roll, derived
modifier, clamp, technology minimum, and trade code is reproducible; population
multipliers, planetoid belts, gas giants, and base checks are immutable; and
append-only travel-zone events preserve both generated Amber candidacy and later
Referee-assigned campaign changes.
Migrations 0512 through 0516 complete planetary wilderness generation. The
published terrain, locomotion, subtype, characteristic, size, number appearing,
weapon, armor, damage, speed, and encounter-template charts are normalized from
paired sources. Campaign-scoped reusable animal definitions are sealed by
immutable receipts that reproduce every roll and derived statistic. Finalized
terrain encounter tables enforce their published animal-type or event slots,
and append-only travelling and halted occurrence receipts reproduce the 5+
check and selected entry.
Migrations 0517 through 0520 complete the starship-encounter subtype handoff.
All ten published one-D6 category tables and the nested warship table resolve
through normalized, paired-source rows. Immutable command-linked draw chains
preserve recursive qualifiers such as derelict, captured, and enemy before
terminating at a concrete ship class, alien vessel, facility, object,
phenomenon, or scenario. Environmental results expose their published Comms,
Piloting, damage-per-Thrust, second-encounter, or trade-generation mechanics
without inventing the subsequent campaign outcome.
Migration 0521 completes contact-to-combat initialization for concrete ship-class
results. An explicit caller supplies the campaign's player and contact ship
instances; the database validates the resolved class and lifecycle, then
atomically creates a forming engagement, opposing forces, vessel memberships,
and the published contact range without inventing crew, initiative, or hostility.
