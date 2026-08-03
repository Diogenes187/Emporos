# Cepheus Rule Decision Register

## Purpose

This register prevents unapproved rules invention.

## Package-Scope Notice

The combat entries currently in this register were researched from the
**Cepheus Universal** SRD before the Cepheus Engine website was selected as the
governing corpus for the relational Cepheus engine.

They remain valid research and accepted decisions for a future Cepheus Universal
package. They do **not** describe Cepheus Engine rules and must not be
implemented in the Engine-governed package unless separately researched
from the Engine source and explicitly approved.

New entries must carry an explicit package code. Cepheus Engine and Cepheus
Universal decisions will not share an unqualified rule identifier.

Every implemented rule must be classified as one of:

- **Source rule** - stated by the governing Cepheus material.
- **Implementation interpretation** - structure required to execute a source
  rule without intentionally changing it.
- **Source option** - an optional procedure explicitly supplied by Cepheus.
- **Open ambiguity** - the source does not settle the implementation question.
- **Agreed product decision** - an interpretation, addition, or departure
  explicitly approved by Raymond and recorded here.

An open ambiguity is not permission to choose silently.

## Governing Sources

### CU-SRD-2024

- Work: *Cepheus Universal System Reference Document*
- File: `books/CepheusUniversal-SRD2.docx`
- Publisher: Zozer Games
- Copyright statement: 2024
- Role: primary mechanical and content authority for implementation
- Locator policy: heading path and extracted paragraph index during planning;
  imported source locators will later become database records

### CU-PB

- Work: *Cepheus Universal Player's Book*
- File: `books/players-book11.pdf`
- Role: player-facing presentation and cross-checking source
- Locator policy: printed/PDF page

The SRD governs when the Player's Book omits referee or construction procedures.
Any apparent contradiction must be examined and resolved explicitly.

## Decision Record Format

Each decision will record:

- identifier;
- subject;
- source and locator;
- source behavior;
- classification;
- implementation consequence;
- status;
- agreement date and rationale when applicable.

## Confirmed Personal-Combat Rules

### PCR-001 - Combat Round Duration

- **Source:** CU-SRD-2024, `COMBAT`, opening paragraphs 1983-1989; CU-PB,
  `COMBAT`, pp. 114 onward.
- **Source behavior:** Personal combat uses rounds of approximately six seconds.
- **Classification:** Source rule.
- **Implementation consequence:** Personal encounters require a round counter
  and six-second combat-time advancement.
- **Status:** Confirmed from source; no product decision required.

### PCR-002 - Personal Action Allowance

- **Source:** CU-SRD-2024, `COMBAT`, paragraphs 1985-1989.
- **Source behavior:** Each player character receives one significant action and
  one minor action in a combat round. Some activities require multiple
  significant actions.
- **Classification:** Source rule.
- **Implementation consequence:** Personal participants need round-scoped
  significant/minor action state and support for extended actions.
- **Status:** Confirmed from source.

### PCR-003 - Personal Range Bands

- **Source:** CU-SRD-2024, `COMBAT > RANGE`, paragraphs 1991-2019; CU-PB,
  `COMBAT > RANGE`, pp. 114-115 and quick reference p. 204.
- **Source behavior:** Personal combat uses named range bands from Personal
  through Distant, with metric distances. Melee distinguishes Personal and
  Close range.
- **Classification:** Source rule.
- **Implementation consequence:** Weapon legality and difficulty depend on
  source-defined range bands.
- **Status:** Confirmed from source. The storage interpretation remains open in
  PCR-OPEN-001.

### PCR-004 - Encounter Starting Range

- **Source:** CU-SRD-2024, `COMBAT > RANGE > ENCOUNTER RANGE`, paragraph 2016
  and associated table.
- **Source behavior:** The referee sets starting range from the situation and
  terrain or may use the supplied random procedure.
- **Classification:** Source rule plus source option.
- **Implementation consequence:** Encounter creation must accept an
  authoritative contextual range and may expose the Cepheus random table.
- **Status:** Confirmed from source.

### PCR-005 - Spotting, Surprise, and Initiative

- **Source:** CU-SRD-2024, `COMBAT > INITIATIVE`, paragraphs 2021-2040 and
  associated modifier tables.
- **Source behavior:** Potential conflict begins with opposed group perception.
  A side may detect the other first, enabling withdrawal or surprise. Context
  can determine the result without a roll.
- **Classification:** Source rule.
- **Implementation consequence:** Awareness and surprise precede ordinary
  combat ordering and must be stored separately from hostility.
- **Status:** Confirmed from source.

### PCR-006 - Order of Combat

- **Source:** CU-SRD-2024, `COMBAT > INITIATIVE > ORDER OF COMBAT`, paragraphs
  2042-2051; CU-PB p. 118.
- **Source behavior:** Player characters act, then allied NPC squad members,
  then enemies. Melee attacks precede Direct Fire.
- **Classification:** Source rule.
- **Implementation consequence:** The engine must implement Cepheus group order,
  not import an unrelated individual-initiative system.
- **Status:** Confirmed from source. Ordering among multiple player characters
  remains open in PCR-OPEN-003 if the source does not specify it elsewhere.

### PCR-007 - Melee Resolution

- **Source:** CU-SRD-2024, `COMBAT > MELEE COMBAT`, paragraphs 2053-2099.
- **Source behavior:** Melee uses a declared target, an 8+ skill check, the
  listed characteristic choices and modifiers, free eligible parrying,
  immediate counter-attack at the cost of the defender's round action, and
  distinct range, grappling, and two-weapon procedures.
- **Classification:** Source rule.
- **Implementation consequence:** Parry, counter-attack, melee range, grapple
  state, and two-weapon attacks require structured actions.
- **Status:** Confirmed from source.

### PCR-008 - Direct and Area Fire

- **Source:** CU-SRD-2024, `COMBAT > DIRECT FIRE`, paragraphs 2123-2192, and
  `COMBAT > AREA FIRE`, paragraphs 2193-2271.
- **Source behavior:** Visible/exposed targets use Direct Fire. Concealed enemy
  positions use Area Fire. Range, cover, movement, aiming, automatic fire,
  ammunition, recoil, and relevant weapon properties affect resolution.
- **Classification:** Source rule.
- **Implementation consequence:** Visibility/exposure and concealment are
  authoritative encounter state. Direct and Area Fire are different legal
  actions.
- **Status:** Confirmed from source.

### PCR-009 - Stance and Movement

- **Source:** CU-SRD-2024, `GAME SYSTEM > MOVEMENT`; `COMBAT`, opening;
  `COMBAT > MISCELLANEOUS > Stance`, paragraphs 2288-2293; CU-PB quick
  reference p. 204.
- **Source behavior:** Movement distances vary by action and movement type.
  Standing, crouched, and prone states affect movement, cover, and attacks.
- **Classification:** Source rule.
- **Implementation consequence:** Stance, movement mode, and distance moved in
  the round must be stored.
- **Status:** Confirmed from source.

### PCR-010 - Character Damage

- **Source:** CU-SRD-2024, `COMBAT > INJURY AND RECOVERY`, paragraphs
  2345-2395.
- **Source behavior:** Weapon damage adds attack Effect, armor reduces damage,
  and penetrating damage is applied to physical characteristics according to
  the stated sequence. Zeroed characteristics produce injury, unconsciousness,
  and death states. Treatment and recovery follow explicit procedures.
- **Classification:** Source rule.
- **Implementation consequence:** Damage allocations, characteristic changes,
  armor reduction, injuries, treatment, and recovery are structured and
  receipted.
- **Status:** Confirmed from source.

### PCR-011 - Abstract Squad and Enemy Procedure

- **Source:** CU-SRD-2024, `COMBAT > NPCs IN COMBAT`, paragraphs 2306-2339.
- **Source behavior:** Squad-based firefights may resolve friendly NPC teams and
  concealed enemy units through generalized group rolls intended to minimize
  referee dice rolling. The text explicitly describes the procedure as an
  approximation and gives simplified NPC casualties.
- **Classification:** Source rule/procedure with deliberately broad referee
  judgment.
- **Implementation consequence:** The product must represent this procedure if
  it offers Cepheus squad combat. Whether all NPCs use it is not settled.
- **Status:** Source procedure confirmed; scope decision open in PCR-OPEN-002.

## Confirmed Ship-Combat Rules

### SCR-001 - Ship Combat Scale

- **Source:** CU-SRD-2024, `SPACE COMBAT`, paragraphs 4178-4182.
- **Source behavior:** A starship round is six minutes. Adventure-class and
  capital ships use the same overall combat rules but differ in construction,
  attacks, and crew representation.
- **Classification:** Source rule.
- **Implementation consequence:** Ship encounters use their own clock and retain
  ship-class distinctions.
- **Status:** Confirmed from source.

### SCR-002 - Detection May Precede Combat

- **Source:** CU-SRD-2024, `SPACE COMBAT`, paragraph 4180; `PHASES OF COMBAT >
  DETECTION PHASE`, paragraphs 4199-4204.
- **Source behavior:** Combat may begin with detection, or circumstances may
  establish that vessels are already aware of each other. Detection,
  continuous tracking, identification, concealment, computer rating, and drive
  state matter.
- **Classification:** Source rule.
- **Implementation consequence:** Detection, tracking, and identity are
  persistent encounter state and not merely narration.
- **Status:** Confirmed from source.

### SCR-003 - Ship Combat Phase Order

- **Source:** CU-SRD-2024, `SPACE COMBAT > STARSHIP COMBAT CHECKLIST`,
  paragraphs 4184-4194; `PHASES OF COMBAT`, paragraphs 4197-4272.
- **Source behavior:** Detection, Range, Tactical, Advantage, Attack, Screen,
  Damage, Damage Control, and Return phases form the stated procedure.
- **Classification:** Source rule.
- **Implementation consequence:** Ship combat requires a phase state machine.
- **Status:** Confirmed from source.

### SCR-004 - Relative Range

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > RANGE PHASE`,
  paragraphs 4206-4207 and associated range table.
- **Source behavior:** Ship range is relative between opposing forces. The
  situation sets initial range, otherwise Long is assumed. The Advantage winner
  can change range by one band.
- **Classification:** Source rule.
- **Implementation consequence:** Ship positioning must support authoritative
  relative range bands.
- **Status:** Confirmed from source. More than two opposing forces remains open
  in SCR-OPEN-001.

### SCR-005 - Tactical Commitment and Escape

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > TACTICAL PHASE`,
  paragraphs 4210-4217.
- **Source behavior:** Sides decide whether to engage or evade and which weapons
  to commit. Avoiding and escaping combat use stated Pilot/Advantage procedures.
- **Classification:** Source rule.
- **Implementation consequence:** Weapon commitment, reserve, engagement, and
  escape are declared intentions before attack resolution.
- **Status:** Confirmed from source.

### SCR-006 - Advantage

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > ADVANTAGE
  PHASE`, paragraphs 4219-4222.
- **Source behavior:** Both sides make the stated opposed Advantage roll using
  current maneuver and Pilot skill or Crew Rating. The winner controls a range
  change and attacks first.
- **Classification:** Source rule.
- **Implementation consequence:** Advantage is resolved and receipted each
  round; AI does not award it narratively.
- **Status:** Confirmed from source.

### SCR-007 - Ship Attacks

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > ATTACK PHASE`,
  paragraphs 4224-4236 and associated tables.
- **Source behavior:** Attacks use the stated Gunnery/Crew Rating check and
  modifiers. Adventure and capital ships receive attacks according to their
  weapon organization. Adventure-class missiles and torpedoes create delayed
  salvos with interception rules.
- **Classification:** Source rule.
- **Implementation consequence:** Weapon groups, committed weapons, salvo
  flight, interception assignment, and crew skill must be structured state.
- **Status:** Confirmed from source.

### SCR-008 - Screens

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > SCREEN PHASE`,
  paragraphs 4238-4243.
- **Source behavior:** Screens may nullify or halve damage, degrade during
  combat, collapse, and recharge under the stated conditions.
- **Classification:** Source rule.
- **Implementation consequence:** Screen rating and degradation are persistent
  ship-encounter resources.
- **Status:** Confirmed from source.

### SCR-009 - Ship Damage

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > DAMAGE PHASE`,
  paragraphs 4244-4257 and associated Ship Damage table.
- **Source behavior:** Armor is subtracted, attack Effect is not added, and the
  Ship Damage table determines hull and component effects. Hull depletion
  precedes Structure loss; Structure zero destroys the ship.
- **Classification:** Source rule.
- **Implementation consequence:** Ship damage must preserve raw damage, armor,
  table result, hull, structure, and component consequences.
- **Status:** Confirmed from source.

### SCR-010 - Damage Control and Repair

- **Source:** CU-SRD-2024, `SPACE COMBAT > PHASES OF COMBAT > DAMAGE CONTROL
  PHASE`, paragraphs 4260-4263.
- **Source behavior:** Crew and repair robots may temporarily restore disabled
  systems during battle. Post-battle assessment and repair use separate
  procedures. Some losses cannot be restored during combat.
- **Classification:** Source rule.
- **Implementation consequence:** Temporary combat restoration and permanent
  repair state must be separate.
- **Status:** Confirmed from source.

### SCR-011 - Boarding Approach

- **Source:** CU-SRD-2024, `SPACE TRAVEL > MISCELLANEOUS TOPICS > Boarding`,
  paragraphs 3993-3994.
- **Source behavior:** Boarding an unresponsive ship involves docking and
  airlock access. A maneuvering target requires velocity matching and a
  Difficult task; failure leads to external hull access or cutting through.
- **Classification:** Source rule.
- **Implementation consequence:** A boarding operation begins with ship-scale
  approach/access resolution and may transition to personal-scale action.
- **Status:** Confirmed from source. Detailed hostile boarding integration
  remains open in SCR-OPEN-002.

### SCR-012 - Airlock and Hull Access

- **Source:** CU-SRD-2024, `SPACE TRAVEL > MISCELLANEOUS TOPICS > Airlocks,
  Docking, Boarding`, paragraphs 3982-3997.
- **Source behavior:** A normal ship has one or more airlocks; the typical
  airlock holds three suited people and cycles in six seconds. Airlocks are
  normally locked from the bridge and require the stated Difficult Electronics
  task to override. Nonresisting ships may dock when close. An unresponsive
  ship can be boarded by docking and opening the airlocks. A maneuvering target
  requires velocity matching and a Difficult task. After failed docking,
  boarders may reach the hull in vacc suits and use an airlock or cut through.
  Cutting through a ship hull uses the stated Routine Mechanical task and time.
- **Classification:** Source rule.
- **Implementation consequence:** Docking state, airlock location/capacity,
  bridge lock state, cycling time, external access, breach task, and elapsed time
  are authoritative boarding state.
- **Status:** Confirmed from source.

## Open Decisions - No Implementation Yet

### PCR-OPEN-001 - Personal Position Storage

- **Question:** Should the engine store only range bands, exact metric
  positions, or both?
- **Source evidence:** Cepheus declares range bands with metric boundaries,
  gives movement in metres, uses adjacency and distances for cover, grenades,
  melee, and movement.
- **Why source does not fully settle it:** These rules describe tabletop
  adjudication but do not prescribe a software state representation.
- **Candidate interpretation:** Store authoritative local positions/distances
  where a map is used and derive range bands; allow an authoritative
  band/engagement representation for theatre-of-the-mind scenes.
- **Decision:** Approved as proposed. Mapped encounters store authoritative
  local positions or distances and derive the Cepheus range band. Encounters
  without a tactical map store an authoritative Cepheus range-band/engagement
  relationship. Both presentations resolve through the same source range rules.
- **Classification:** Agreed product decision; software representation of
  source rules.
- **Status:** Approved by Raymond on 2026-07-27.

### PCR-OPEN-002 - Full NPCs Versus Abstract Units

- **Question:** When does an NPC use full character combat and when does a group
  use the abstract NPC-unit procedure?
- **Source evidence:** Cepheus gives full character/animal rules and separately
  gives a deliberately generalized squad/enemy procedure for firefights.
- **Candidate interpretation:** Named or individually engaged NPCs use complete
  actor rules; background squads and concealed enemy units may use the stated
  group procedure.
- **Risk:** This is a scope interpretation, even though both procedures are
  source-derived.
- **Decision:** Approved as proposed. Named or individually engaged NPCs use
  complete character combat state. Background squads and concealed enemy units
  may use the Cepheus abstract unit procedure. When an abstract NPC becomes
  individually significant, the engine creates or reveals a persistent actor
  through a recorded transition rather than inventing statistics in narration.
- **Classification:** Agreed product decision; scope selection between two
  source procedures.
- **Status:** Approved by Raymond on 2026-07-27.

### PCR-OPEN-003 - Ordering Within the Player Group

- **Question:** In what order do multiple player characters take their turns?
- **Source evidence:** Cepheus establishes player characters before allied NPCs
  and enemies and establishes melee before Direct Fire, but the inspected text
  does not define ordering among player characters.
- **Candidate interpretations:** player-chosen order each round; fixed
  table/party order; simultaneous declarations with ordered resolution.
- **Research result:** A full paragraph-text search located the group order and
  melee-before-fire rules but no additional rule governing order among multiple
  player characters.
- **Decision:** Players choose their order within the player-character phase
  each round. The source rule that Melee attacks resolve before Direct Fire
  remains controlling. A player who delays or commits to a multi-round action
  follows the applicable Cepheus procedure.
- **Classification:** Agreed product decision filling a source omission.
- **Status:** Approved by Raymond on 2026-07-27.

### SCR-OPEN-001 - More Than Two Ship Forces

- **Question:** How does relative range and Advantage operate with three or more
  independently maneuvering forces?
- **Source evidence:** The combat text consistently describes two combatants or
  opposing forces.
- **Research result:** A full paragraph-text search found no procedure for
  multiple independently maneuvering forces. The source uses an opposed
  Advantage roll and pairwise relative range. The campaign guidance mentions
  fleet actions, but supplies no additional fleet-combat resolution rule.
- **Candidate product decision:** Implement the source procedure initially for
  exactly two ship combatants. Permit any number of ships to coexist in a
  noncombat encounter, but do not place a third independently maneuvering ship
  into combat until a separately researched and approved extension defines
  range and Advantage.
- **Rationale:** This implements the complete rule actually supplied without
  pretending that a mention of fleet actions defines missing mechanics.
- **Decision:** Approved as proposed. The initial source-faithful ship-combat
  implementation supports exactly two ship combatants. A larger encounter may
  contain additional vessels, but they do not enter mechanical combat until a
  separately researched and approved multi-force extension exists.
- **Classification:** Agreed product-scope decision preserving the supplied
  two-combatant procedure.
- **Status:** Approved by Raymond on 2026-07-27.

### SCR-OPEN-002 - Hostile Boarding Integration

- **Question:** What exact state transition connects ship combat, docking or
  hull entry, and a personal encounter?
- **Source evidence:** Cepheus specifies ordinary docking, maneuvering-target
  boarding, airlock capacity and override, external hull access, cutting through
  a hull, vacc-suit operations, pressure loss, and personal combat. The inspected
  material does not supply an explicit bridge-capture or vessel-control-transfer
  rule.
- **Candidate interpretation:** Resolve approach and access under ship/travel
  rules, then create a linked personal encounter using actual ship deck
  locations and participants. Only source-supported personal outcomes occur
  automatically; control of the vessel requires a later agreed rule if no source
  procedure is found.
- **Further research:** The SRD discusses piracy, hijacking, boarding troops,
  ships forced into submission by damage, and Crew Rating as a possible morale
  measure. It supplies no automatic capture threshold, bridge-control rule, or
  ownership-transfer procedure.
- **Candidate product decision:** Do not create an automatic capture roll.
  Operational control may transfer only when (a) the defending command
  surrenders or abandons resistance, or no defender remains capable of
  resistance; (b) the boarding side physically reaches usable command controls;
  and (c) a character capable of operating the vessel assumes those controls.
  Remaining hostile defenders and uncontrolled compartments persist. Legal
  ownership never changes merely because operational control changes.
- **Rationale:** This uses source personal combat, movement, access, surrender
  judgment, skills, and ship state while avoiding an invented universal
  capture-number mechanic.
- **Decision:** Approved as proposed. Operational control transfers only after
  surrender, abandonment, or inability to resist; physical access to usable
  command controls; and assumption of those controls by a capable character.
  Uncontrolled compartments and remaining hostiles persist. Legal ownership is
  never transferred automatically.
- **Classification:** Agreed product decision connecting source procedures
  without adding a capture roll.
- **Status:** Approved by Raymond on 2026-07-27.

### SCR-OPEN-003 - Player's Book Omission of Ship Combat

- **Question:** Is ship combat intentionally referee-facing in this product, or
  omitted from the Player's Book only for space?
- **Source evidence:** The Player's Book includes personal combat and player
  quick-reference material, while the located full Space Combat procedure is in
  the SRD.
- **Implementation consequence:** This affects UI explanation and rules access,
  not the authority of the SRD procedure.
- **Research result:** The Player's Book contents and extracted pages include
  personal combat and a personal-combat quick reference but no full Space
  Combat chapter. Vehicle and weapon material may reference spacecraft, but the
  governing phase procedure remains in the SRD.
- **Status:** Verified as a publication-scope difference. The SRD remains the
  governing source; no product rule decision is required.

## Source-Fidelity Tests Implied

The eventual test suite must demonstrate at minimum:

- personal rounds provide one significant and one minor action;
- source range thresholds select the correct attack difficulty;
- group perception can establish awareness and surprise;
- player characters, allies, and enemies act in source order;
- melee resolves before Direct Fire where both occur;
- parry and counter-attack obey their source costs;
- Direct Fire cannot target a source-defined concealed enemy as though exposed;
- damage adds Effect in personal combat and does not add Effect in ship damage;
- personal armor and ship armor apply according to their distinct procedures;
- ship rounds follow the source phase order;
- Advantage controls ship range change and attack order;
- committed missile salvos persist until their stated arrival phase;
- screen degradation persists across ship rounds;
- combat damage control is not mistaken for permanent repair;
- a retried command never consumes a second roll or resource.

## Cepheus Engine Source Adjudications

### CE-SRC-005 - Apparent Omissions Require Source Reconciliation

- **Package:** Cepheus Engine 9.1.
- **Sources:** Paired Cepheus Engine SRD publications, related rules tables and
  standard designs, and the read-only prior implementation as supporting
  evidence.
- **Evidence:** One Markdown transcription omitted the Beam Laser row, while
  the fuller published turret-weapons table supplies its standard TL 9,
  Medium-range, `1D6`, MCr1 profile. The Space Combat damage and range rules
  corroborate the interpretation of those fields. The same reconciliation
  found that the Markdown Briefing Room section omits its final construction
  sentence; the complete published edition specifies 4 tons and MCr0.5.
- **Decision:** Absence from one transcription is not absence from Cepheus.
  Apparent gaps must be reconciled across paired publications, editions,
  adjacent rules, scaling tables, standard examples or designs, and the prior
  implementation before a rule can be classified as `source_unspecified`.
  Recovered values retain field-level provenance; actual conflicts require
  explicit adjudication rather than convenient selection.
- **Classification:** Source-ingestion and fidelity procedure.
- **Implementation consequence:** The Beam Laser and Briefing Room are stored
  with their published standard profiles rather than invented or unspecified
  placeholders. Future apparent omissions follow the same documented
  reconciliation process.
- **Status:** Approved by Raymond and implemented 2026-07-28.

### CE-SRC-006 - Common-Vessel Conflicts Remain Queryable

- **Package:** Cepheus Engine 9.1.
- **Sources:** `Common Vessels`, `Ship Hull`, `Drive Performance by Hull
  Volume`, and `Armaments`.
- **Evidence:** The Raider paragraph repeats 6 Hull and 6 Structure for a
  600-ton hull, claims three hardpoints while installing six weapon systems,
  and transposes drive letters M and D. The hull, hardpoint, drive-performance,
  and installed-weapon rules jointly resolve these as 12 Hull, 12 Structure,
  six hardpoints, jump drive D, and maneuver drive M. The System Monitor's
  run-together `drivexand` text resolves to drive X. The Destroyer's printed
  drive letters D/M do not produce its stated Jump-2/4-G performance; its fuel
  supports the printed power plant M but does not resolve both drive conflicts.
- **Decision:** Reconciled values are canonical only when independent Cepheus
  rules converge. Every changed field retains the published and canonical
  values with rationale. The Destroyer retains its printed drive letters and
  stated performance as an explicit `published_conflict`; the engine does not
  silently invent replacement letters.
- **Classification:** Source fidelity and relational conflict preservation.
- **Implementation consequence:** Ordinary drive selections must satisfy the
  construction matrix. A published conflict is permitted only when a matching
  unresolved source assertion exists, so contradictory source data remains
  visible and cannot be mistaken for a validated design.
- **Status:** Implemented 2026-07-28.

### CE-SRC-007 - The Asteroid-Miner Smelter Remains Unspecified

- **Package:** Cepheus Engine 9.1.
- **Sources searched:** Paired GitHub and OGN `Common Vessels`; the complete
  `Ship Design and Construction` component and hangar rules; alternate
  renderings of the same authorized SRD; and the read-only prior
  implementation.
- **Evidence:** The Asteroid Miner consistently names a mining drone and a
  smelter. Mining drones have a complete published profile. No checked source
  supplies the smelter's tonnage, cost, capacity, processing rate, tech level,
  or construction formula.
- **Decision:** Preserve the smelter as a relational component and record its
  effect identity, but classify its construction fields as
  `source_unspecified`. Do not infer its profile from the ship's residual cargo
  or published total, because multiple undocumented discounts and fees make
  that subtraction non-unique.
- **Classification:** Exhausted-source gap under CE-SRC-005.
- **Implementation consequence:** The Asteroid Miner remains structurally
  queryable, while whole-design cost and tonnage reconciliation must identify
  the smelter as an unresolved source input rather than silently treating it as
  free and massless.
- **Status:** Implemented 2026-07-28.

### CE-SRC-008 - Common-Vessel Totals Are Reconciled Without Balancing Fiction

- **Package:** Cepheus Engine 9.1.
- **Evidence:** Reconstructing all 24 common vessels from the published hull,
  configuration, armor, drive, fuel, bridge, computer, electronics,
  accommodation, component, hangar, carried-craft, weapon, screen, and
  ammunition rules produces exact tonnage and cost totals for the Launch,
  Pinnace, Ship's Boat, and Shuttle. Other designs retain measurable tonnage or
  cost differences, while the publication describes final prices only as
  including unspecified "discounts and fees."
- **Decision:** Store each formula input and result as an immutable construction
  line and classify the final comparison as `reconciled`, `source_gap`,
  `tonnage_variance`, or `cost_variance`. Never insert an invented fee,
  discount, component, or residual adjustment solely to force equality with a
  published total.
- **Implementation consequence:** A published common vessel remains usable and
  queryable even when its arithmetic cannot be reproduced, and later source
  adjudication can identify the exact line or variance that changed.
- **Status:** Implemented 2026-07-28.

### CE-SRC-009 - Capped Common-Vessel Armor Uses Fractional Construction Arithmetic

- **Package:** Cepheus Engine 9.1.
- **Evidence:** The construction rule requires armor to be purchased in whole
  5% hull-tonnage increments. The Destroyer, Heavy Cruiser, Light Cruiser, and
  System Monitor published cargo arithmetic instead matches prorating the last
  increment to the tech-level-capped armor rating. The exact resulting
  differences are 10, 25, 12.5, and 25 tons respectively.
- **Decision:** Retain whole increments as the governing construction rule and
  preserve the four common-vessel differences as `capped-armor-proration`
  publication conflicts. Do not weaken the general armor constraint to emulate
  those examples.
- **Implementation consequence:** Construction can distinguish a legal armor
  selection from a published standard design that used conflicting arithmetic,
  while the standard design remains available as published.
- **Status:** Implemented 2026-07-28.

### CE-SRC-010 - Carried Probe Drones Use the Equipment Catalogue

- **Package:** Cepheus Engine 9.1.
- **Evidence:** The hangar rule states that hangar prices exclude the vehicles
  or drones stored in them. The equipment catalogue separately defines a TL11
  Probe Drone costing Cr15,000. The Research Vessel carries 15 and the Survey
  Vessel carries 20 probe drones.
- **Decision:** Represent the drones as carried inventory definitions linked to
  their ship hangars, and include their published unit prices in revised
  construction receipts. Preserve the Research Vessel's TL9/TL11 mismatch as a
  source conflict rather than lowering the equipment tech level.
- **Implementation consequence:** Hangar installation cost, drone payload cost,
  capacity, and tech compatibility are independently queryable. Receipt
  versions 2 retain the earlier arithmetic while adding Cr225,000 and Cr300,000
  respectively before the standard-design discount.
- **Status:** Implemented 2026-07-28.

### CE-SRC-004 - Species Is a Reusable Rules Composition

- **Package:** Cepheus Engine 9.1.
- **Source:** GitHub v9.1,
  `Book 1: Character Creation > On Alien Species`.
- **Evidence:** The source defines baseline humans, five example species,
  characteristic-generation changes, maturity and aging ages, physical
  formulas, characteristic replacement, and reusable alien traits. It leaves
  campaign availability and additional species to the Referee.
- **Decision:** A species is composed relationally from characteristic
  generation overrides, age thresholds, physical-generation formulas, and
  ordered reusable traits. Species assignment is player-controlled and
  revisioned, so imported characters and newly generated characters share the
  same representation.
- **Classification:** Direct source implementation and shared-engine
  composition.
- **Implementation consequence:** Species maturity initializes prior
  experience and species aging thresholds govern term-end aging. Product
  packages can add genre-specific species without changing the common engine
  schema.
- **Status:** Catalogue, assignment, and lifecycle ages implemented
  2026-07-28. Anti-Psionic, Armored, Fast Speed, and Slow Speed are enforced
  by their psionic, attack, and movement consumers. Flyer, Great Leaper, and
  Natural Weapon character-creation skill grants are also enforced without
  reducing an existing higher skill. A species Natural Weapon is actor-bound,
  Personal-range only, uses Natural Weapons with Strength or Dexterity, and
  records its flat +1 damage separately. Remaining individual trait consumers
  continue in subsequent units. Great Leaper consumes a significant action,
  resolves a recorded Athletics check using an explicitly selected canonical
  characteristic and difficulty, and moves four 1.5-metre squares plus Effect
  on success. Flyer is persistent personal-combat state: grounded Flyers may
  take off using their species flight speed, aloft Flyers record movement and
  altitude, and landing returns altitude to zero. An aloft Flyer that does not
  spend a minor movement action in the round deterministically becomes falling.
  The engine records the transition but does not yet resolve impact because an
  encounter has no authoritative world-gravity context. The Endurance-hours
  limit and equal rest likewise await the shared authoritative campaign clock;
  neither concern is represented with a parallel Flyer-only clock. Natural
  Pilot contributes its source DM+2 only to Piloting and Navigation checks.
  Natural Swimmer contributes DM+2 when the task is explicitly classified with
  the bounded `swimming` context; the generic task receipt records each applied
  species modifier separately. Bad First Impression initializes a cross-species
  non-player participant's encounter attitude as Unfriendly regardless of
  participant-addition order. It never forces a player-character attitude and
  is not a permanent floor: later source-governed influence or an explicit
  referee attitude command may replace it. Hive Mentality resolves the required
  Intelligence check against the caller-selected source range of difficulty
  and records the identified family group and perceived benefit; failure means
  the actor does not avoid the family-benefiting risk. Fast and Slow Metabolism
  contribute separately audited +2 and -2 combat initiative modifiers,
  respectively. Their life-support and fatigue effects remain deferred until
  those authoritative resource/time consumers exist. Naturally Curious uses
  the same source-bounded Intelligence-check pattern, recording the perceived
  mystery and whether the actor avoided the impulse. Low-Light Vision doubles
  a supplied human visibility distance only for starlight, moonlight,
  torchlight, or explicitly similar poor illumination, while retaining color
  and detail; it does not grant vision in total darkness. Cold-Blooded uses a
  persistent, audited continuous-exposure counter: unprotected extreme cold
  applies its immediate initiative DM-2 and creates one recorded 1D6 damage
  interval per completed ten minutes, while protective equipment prevents both
  effects. Heat Endurance records and prevents each completed hourly
  hot-weather damage interval without inventing a base damage amount that the
  trait does not define. Environmental damage uses the shared health pipeline;
  damage beyond all remaining physical characteristics is retained as lethal
  overflow rather than making the final allocation impossible. Caste social
  DMs and Amphibious land Dexterity remain deferred because both sources say to
  halve integer values without specifying how odd positive or negative values
  round.

### CE-SRC-003 - Final Details Remain Player-Owned Revisions

- **Package:** Cepheus Engine 9.1.
- **Source:** GitHub v9.1,
  `Book 1: Character Creation > Final Details`.
- **Evidence:** The source directs the player to choose a name, gender,
  appearance, and long-term personal goals; it explicitly allows goals to
  change as the character grows.
- **Decision:** These details are player-authored and editable. Each edit
  creates an append-only relational profile revision, and personal goals are
  stored as ordered rows rather than a JSON document. The latest revision is
  canonical; prior revisions remain auditable.
- **Classification:** Direct source implementation and product data-ownership
  application.
- **Implementation consequence:** AI may use these details in prose but cannot
  silently change them. Imported characters use the same revision command.
- **Status:** Implemented 2026-07-28.

### CE-SRC-002 - Anagathics Are a Stateful Career Procedure

- **Package:** Cepheus Engine 9.1.
- **Source:** GitHub v9.1,
  `Book 1: Character Creation > Aging > Anagathics`, and the preceding
  Finishing Touches rule.
- **Evidence:** Use adds the number of terms since treatment began as a
  positive aging-table DM, requires a second Survival check, costs
  `1D6 × 2,500` Credits per term, and stopping requires an immediate aging
  roll. Medical and anagathic costs are paid from Benefits before other cash
  is retained.
- **Decision:** Anagathics are stored per term as a player declaration, not as
  narration or an untracked aging modifier. Their second Survival check uses
  the same career Survival characteristic, target, modifier, and natural-two
  rule as the first. Stopping reuses the canonical aging allocation and
  aging-crisis procedures.
- **Classification:** Direct source implementation; no house rule introduced.
- **Implementation consequence:** Cost, course length, both Survival rolls,
  immediate stopping shock, aging modifier, and benefit-paid debt remain
  relational and auditable.
- **Status:** Implemented 2026-07-28.

### CE-SRC-001 - Aircraft Includes Airship

- **Package:** Cepheus Engine 9.1.
- **Sources:** GitHub v9.1, `Skills > Skill Descriptions > Aircraft`;
  OGN, `Skills > Skill Descriptions > Aircraft`; OGN,
  `Vehicle Design System > New Skill > Airship`.
- **Evidence:** GitHub v9.1 lists Airship among the Aircraft cascade
  specialties. The OGN Skills page omits Airship from that list, although the
  OGN Vehicle Design System separately defines the Airship skill.
- **Decision:** GitHub v9.1 is correct. The OGN Skills-page difference is a
  publication omission.
- **Classification:** Agreed source adjudication.
- **Implementation consequence:** The canonical Aircraft cascade includes
  Airship. Its relationship provenance is GitHub `fills_source_gap`; the
  database concordance records the OGN omission as `left_only`.
- **Status:** Approved by Raymond on 2026-07-27.

## Change Log

- **2026-07-27:** Register created. Initial personal- and ship-combat rules
  extracted from the Cepheus Universal SRD and cross-checked against located
  Player's Book personal-combat pages. Five implementation questions remain
  explicitly open.
- **2026-07-27:** Raymond approved the hybrid mapped/range-band representation
  for personal positioning and the full-named-NPC/abstract-background-unit
  division. Three unresolved research questions and the Player's Book scope
  verification remain open.
- **2026-07-27:** Added the reusable Vessel-to-Personal Encounter Product Seed.
  Further SRD search confirmed airlock, docking, override, hull-access, and
  hull-cutting procedures. The SRD appears silent on player ordering within the
  PC group, multi-force ship Advantage/range, and exact transfer of captured
  vessel control.
- **2026-07-27:** Raymond approved player-chosen ordering within the
  player-character phase. Cepheus group order and melee-before-Direct-Fire
  precedence remain unchanged.
- **2026-07-27:** Broader searches found no multi-force ship-combat or automatic
  vessel-capture procedure. Added minimal source-faithful candidates: initially
  limit the supplied ship-combat procedure to two combatants, and transfer
  operational control only through surrender/incapacity plus physical access to
  usable controls and a capable operator. Verified that the Player's Book omits
  the full Space Combat chapter; the SRD governs it.
- **2026-07-27:** Raymond approved the initial two-vessel mechanical-combat
  boundary and the proposed operational-control conditions. Multi-force combat
  remains a possible later extension requiring separate research and agreement;
  capture does not automatically transfer legal ownership.
- **2026-07-27:** Raymond adjudicated the paired-source Aircraft cascade
  difference: GitHub v9.1 is correct that Aircraft includes Airship; the OGN
  Skills-page omission is a publication error.
- **2026-07-28:** Implemented the complete Cepheus Engine anagathics procedure,
  including term costs, the second Survival check, aging protection, and the
  immediate stopping shock.
- **2026-07-28:** Implemented player-owned Final Details as append-only
  relational revisions with ordered personal goals.
- **2026-07-28:** Added the normalized species and trait catalogue,
  revisioned actor assignment, physical and characteristic formulas, and
  species-specific maturity and aging integration.
- **2026-07-28:** Connected Anti-Psionic, Armored, Fast Speed, and Slow Speed
  to psionic activation and targeting, recorded attack armor, and personal
  movement.
- **2026-07-28:** Added relational species-trait skill grants for Athletics
  and Natural Weapons, applied only during native character creation and
  recorded against the species assignment.
- **2026-07-28:** Implemented species Natural Weapons as inherent, actor-bound
  Personal-range attacks with separately recorded flat damage.
- **2026-07-28:** Implemented Great Leaper as a recorded Athletics task and
  significant combat action, preserving referee selection of characteristic
  and difficulty where the species text does not choose them.
- **2026-07-28:** Implemented persistent Flyer combat state, including
  source-speed takeoff, airborne movement, altitude, landing, and audited
  transition from aloft to falling when the required per-round minor movement
  action is missed. Falling impact awaits authoritative encounter gravity and
  sustained-flight fatigue/rest awaits the shared campaign-time model.
- **2026-07-28:** Added audited general actor-task resolution and relational
  species task modifiers. Natural Pilot applies DM+2 only to Piloting and
  Navigation; Natural Swimmer applies DM+2 only to checks explicitly marked as
  swimming-related.
- **2026-07-28:** Connected Bad First Impression to encounter participation.
  Cross-species NPC attitudes begin Unfriendly with a pairing receipt, while
  same-species and player-character attitudes remain unaffected; subsequent
  influence and referee decisions can overcome the starting response.
- **2026-07-28:** Implemented Hive Mentality as an audited Intelligence check
  using the source-permitted difficulty range and explicit family-benefit
  context. Failure records that the actor did not avoid the required risk.
- **2026-07-28:** Applied Fast and Slow Metabolism's unconditional combat
  initiative modifiers with a separate initialization field. Life-support and
  fatigue effects await their shared deterministic consumers.
- **2026-07-28:** Implemented Naturally Curious as an audited, source-bounded
  Intelligence check with explicit mystery context and compelled-impulse
  outcome.
- **2026-07-28:** Implemented Low-Light Vision as a relational two-times
  visibility projection for the source-listed poor-light conditions, retaining
  color and detail and explicitly excluding total darkness.
- **2026-07-28:** Implemented persistent Cold-Blooded and Heat Endurance
  exposure state. Extreme cold records elapsed ten-minute intervals, initiative
  DM, protection, dice, and resulting shared health damage; Heat Endurance
  records prevented hourly hot-weather damage. General damage allocation now
  records lethal overflow beyond all remaining physical characteristics.
- **2026-07-28:** Deferred Caste and Amphibious halving consumers pending an
  explicit adjudication for odd-value rounding; neither paired source nor the
  prior implementation supplies one.
- **2026-07-28:** Established apparent-omission reconciliation as a mandatory
  ingestion procedure and applied it to the standard Beam Laser and Briefing
  Room profiles.
- **2026-07-28:** Loaded all 24 common vessels, reconciled convergent
  publication errors, preserved the Destroyer drive conflict explicitly, and
  normalized the published armament, ammunition, and screen loadouts.
- **2026-07-28:** Normalized common-vessel accommodation, cargo, utility,
  hangar, escape-system, drone, and carried-craft relations. The smelter is
  retained as the sole exhausted-source construction gap.
- **2026-07-28:** Added finalized whole-design construction receipts for all 24
  common vessels, including 424 immutable calculation lines and explicit
  source-gap, tonnage-variance, and cost-variance outcomes.
- **2026-07-28:** Made construction receipts versionable without rewriting
  history, added the Cutter's published passenger cabin space in receipt
  version 2, and normalized 30 current variance-audit records, including four
  capped-armor publication conflicts.
- **2026-07-28:** Linked Research and Survey Vessel probe-drone payloads to the
  equipment catalogue, preserved the Research Vessel's TL9/TL11 conflict, and
  issued version-2 receipts including the carried drone purchase costs.
- **2026-07-28:** Established a shared relational source-issue register. The
  current ship audit publishes 34 independently resolvable findings with stable
  codes, priorities, exact typed-record and source-locator links, direct
  reviewer questions, requested evidence, and explicit engine dispositions.
  `CEPHEUS_SOURCE_ISSUES.md` is a generated reviewer projection; database rows
  remain authoritative.
- **2026-07-28:** Inspected the legacy Cepheus game and its campaign databases
  as nonauthoritative comparison evidence. Its ship parser copies the
  publication's summary fields and has no component worksheet or adjudication
  capable of resolving the 34 current findings. Recorded that negative result
  against every issue so future audits do not repeat the same search.
- **2026-07-28:** Repaired clean database construction without rewriting
  applied migrations. `tools/bootstrap_database.py` now interleaves all eleven
  reviewed catalogue importers at their nine proven schema boundaries, refuses
  populated targets, completes all migrations, and runs the verifier. A
  disposable empty database completed the bootstrap and all 136 tests.
- **2026-07-28:** Normalized the VDS control and electronics layer: 28 generic
  component definitions plus typed controls, drone controllers, robot brains,
  autopilot progression, electronics ranges, communicators, sensor
  capabilities, underwater conversion, computers, and hardening. Registered
  the Primitive Controls TL1/TL2 and Standard Sensors 500m/500km conflicts for
  review instead of hiding either discrepancy.
- **2026-07-28:** Added a whole-database long-text boundary. Mechanical text
  columns may not accumulate values over 80 characters; legitimate prose is
  confined to explicitly narrative descriptions, rationales, evidence, source
  values, and audit explanations.
- **2026-07-28:** Normalized the VDS crew-accommodation, life-support, and
  additional-component layer: 49 component rules, twelve accommodation
  profiles, two life-support systems, and exact typed formulae for trailers,
  aircraft fittings, galleys, cranes, manipulators, medical facilities,
  refrigeration, refueling, laboratories, samplers, and other equipment.
  Adopted the Wet Bar's coherent prose values over its corrupted summary row,
  retained Folding Wings/Rotors despite its summary-table omission, and used
  the identical core Emergency Low Berth's four-person survival capacity.
  All three decisions remain visible in the source-issue register.
- **2026-07-28:** Extended the legacy comparison audit to all five vehicle
  catalogue issues. The predecessor contains vehicle skill names but no
  vehicle construction catalogue or calculator capable of resolving them.
- **2026-07-28:** Restored migration 0142's original final newline after its
  post-application removal caused the checksum guard to reject the working
  tree. Applied migration bytes remain immutable, including whitespace.
- **2026-07-28:** Normalized both vehicle configurations and all eleven VDS
  configuration options, including cover and firing access, propulsion
  applicability, exact price and space bases, environmental hazard protection,
  included systems, submersible depth bands, world-size adjustment, and depth
  upgrade costs. The Open Frame paragraph's copied Open Cargo Bed wording is
  treated as a parallel-rule publication error; the submersible ballast
  rounding direction remains explicitly source-unspecified.
- **2026-07-28:** Normalized all ten VDS drive options with typed category
  prerequisites and exact agility, fuel, price, drive-space, terrain, flight,
  altitude, and attack modifiers. The legacy implementation has no independent
  construction behavior for either new source question.
- **2026-07-29 — CE-COMBAT-001:** Raymond adjudicated Panic Fire ammunition
  counts between published Burst Fire table rows. Panic Fire consumes every
  remaining round and uses the greatest published damage tier that does not
  exceed the rounds consumed. The paired publications define the surrounding
  procedure but omit this intermediate-count mapping; the legacy repository
  contains no executable fallback ruling.
- **2026-07-29 — CE-COMBAT-002:** Raymond adjudicated Shotgun Spread wording
  and shared resolution. Every occurrence of “frag shell” in the published
  paragraph is corrected to “flechette shell.” A Medium- or Long-range spread
  uses one shared attack roll and one shared 2D6 damage roll for the primary
  target and every declared combatant within Personal range of that target;
  each affected combatant resolves armor separately. The correction and
  shared-roll procedure are agreed interpretations because the paired
  publications and legacy repository do not settle them.
- **2026-07-29 — CE-COMBAT-003:** Raymond approved encounter sides as the
  executable meaning of a Battlefield Comms “unit.” Tactics applies to
  communicated members of the commander's side, and Leadership targets another
  communicated member of that side. Commander-to-member communication links
  record their method and current method-specific blocker explicitly.
- **2026-07-29 — CE-COMBAT-004:** Raymond approved Infra-Red, Densitometer,
  Laser-Assisted Targeting, Light Intensification, Motion Sensor, and NAS as
  targeting-capable sensors that can avoid the visibility penalty from extreme
  weather. Bioscanners and Electromagnetic Detectors do not qualify. A sensor
  that is currently blocked or jammed supplies no such benefit.
- **2026-07-29 — CE-COMBAT-005:** Raymond approved a referee-declared roster as
  the executable set of eligible targets in a blind-fire firing line. The
  roster may include friend or foe, is frozen with the declaration, and is
  randomly sampled only after the blind-fire attack check succeeds.
- **2026-07-29 — CE-COMBAT-006:** Raymond approved a referee-declared, frozen
  affected roster for explosions and one shared damage roll. Each target
  independently chooses no reaction, dodge, or dive. Dodge reduces damage by
  its own 1D6; dive halves damage, rounded down, ends prone, and loses the next
  significant action. Reaction reductions occur before armor, and armor is
  resolved separately for every target.
- **2026-07-29 — CE-COMBAT-007:** Raymond approved referee designation as the
  executable extreme-range boundary because the published Distant band has no
  upper distance. The declaration records line of sight and a nonempty firing
  rest without inventing an action cost. The weapon must support Distant fire,
  the applicable skill must be Level 3+, and the firer must be stationary.
  Vehicle platforms use relational stationary encounter state. Energy damage
  is halved after damage additions and before armor, rounding up; Aiming for
  the Kill remains compatible.
- **2026-07-29 — CE-COMBAT-008:** Raymond approved a referee-controlled
  encounter gravity state. In zero gravity, effective attack skill is the
  lower of the applicable combat skill and Zero-G; Zero-G Level 0 counts as
  trained. Without Zero-G, the attack uses the applicable combat skill's
  normalized untrained modifier, currently DM -3. The cap applies to all
  weapon attacks, while weapons with normalized recoil receive a separate
  DM -2. All contributing facts are frozen with the attack.
- **2026-07-29 — CE-COMBAT-009:** Raymond approved a referee-declared, frozen
  roster of combatants at Personal range to the original target for Firing
  into Combat. Shooting attacks receive DM -2. On a miss, 1D6 results of 4+
  redirect the hit to the nearest proximity tier; ties are selected randomly
  within that tier, with friend and foe equally eligible. Redirected damage
  uses the original negative Effect and target-specific armor, but excludes
  Aiming-for-the-Kill damage intended for the original target.
- **2026-07-29 — CE-COMBAT-010:** Raymond approved relational Grappling as
  opposed Natural Weapons checks at Personal range. Higher total wins; ties
  produce no option, and Effect is the winning margin. Either participant may
  win every check. Each attempt costs one significant action, one active
  grapple is allowed per actor, and grappled actors are restricted to grapple
  checks. The seven source options are normalized with immutable check,
  option, movement, stance, item-custody, damage, and state-transition facts.
  Damage ignores armor; throws always end the grapple, while other applicable
  options freeze the winner's continue-or-end choice.
- **2026-07-29 — CE-COMBAT-011:** Raymond approved normalized thrown delivery
  as either impact or payload. Impact weapons add attack Effect to damage;
  payloads do not inflict impact damage or add Effect to payload damage. A
  miss scatters by the source-literal `max(0, 6 + Effect)` metres in an
  auditable uniform D360 direction. Target-point reference, polar offset,
  original Effect, delivery type, and any distinct payload-resolution link
  are immutable relational facts.
- **2026-07-29 — CE-COMBAT-012:** Raymond approved the unspecified Endurance
  recovery check for unconsciousness as Average 8+, attempted after each
  elapsed minute with cumulative DM +1 per prior failure. Waking after
  repeated-fatigue unconsciousness leaves the actor fatigued. Required rest is
  frozen at fatigue onset as `max(0, 3 - Endurance DM)` hours, and fatigue's
  DM -2 applies to personal attacks and ordinary actor task checks.
- **2026-07-29 — CE-COMBAT-013:** Raymond approved derived physical injury
  status and one natural-healing resolution per actor and campaign day.
  Natural-healing formulas remain signed: negative results cause real
  characteristic degradation, allocated by the actor's controller among
  physical characteristics above zero. Positive recovery is controller
  allocated among damaged physical characteristics and never exceeds maximum.
- **2026-07-29 — CE-COMBAT-014:** Raymond approved Average 8+ Medicine checks,
  source-defined self-treatment and cross-species modifiers, one First Aid
  benefit per applied injury, and Surgery linked to that First Aid episode.
  Failed Surgery loses `abs(Effect)` points. Surgery and daily Medical Care
  require a relational hospital or sickbay. Medical Care uses
  `max(0, 2 + Endurance DM + Medicine)` and divides points evenly, with
  controller-selected remainder points and maximum-value caps.
- **2026-07-29 — CE-COMBAT-015:** The paired Healing and Mental
  Characteristics sources are implemented as one campaign-day receipt that
  restores one point to each damaged Intelligence and Education
  characteristic, capped at maximum. Psionic Strength is explicitly excluded;
  a more specific future damage rule must override this general recovery rule.
- **2026-07-29 — CE-COMBAT-016:** Raymond approved ground-force volleys against
  starship-scale targets as separate per-weapon attacks with the source DM +4.
  Only successful attacks contribute. The controller designates one successful
  primary weapon at full dice; all other successful dice are combined, halved,
  and rounded down. Rolled damage is divided by 50 and rounded down before
  armor. Positive post-armor damage reduces Hull; cross-scale minimum damage
  does not apply. Every weapon, roll, contribution, and mutation is relational
  and immutable.
- **2026-07-29 — CE-EQUIP-001:** Raymond approved the structured Common
  Personal Armor table as authoritative where its Tech Levels conflict with
  armor-description headings: Cloth TL 6, Hostile Environment Vacc Suit TL 12,
  and Vacc Suit TL 9. All three prose conflicts remain explicit source issues.
  The nine armor rows normalize general/laser AR, cost, mass, required skill,
  catalogue order, the ordinary one-armor limit, and outside-in layering.
- **2026-07-29 — CE-EQUIP-002:** Personal armor capabilities remain typed:
  Ablat loses one laser AR per laser hit; Reflec is the sole two-layer
  exception; Battle Dress adds +4 effective Strength and Dexterity without
  changing damage-tracking values and inherits HEV protection. Six-hour life
  support, computer/expert software, vacuum, environmental, NBC, and exact
  radiation reductions are normalized independently of campaign state.
- **2026-07-29 — CE-EQUIP-003:** Personal armor runtime state is item-instance
  based. An actor may wear one armor or exactly one Reflec plus one other
  armor, with explicit inside-out layer order. Ablat laser AR and six-hour
  life support are concurrency-versioned resources. Equipping, unequipping,
  layer snapshots, and every resource change produce immutable command
  receipts; Battle Dress modifies effective values without mutating damage
  tracking.
- **2026-07-29 — CE-EQUIP-004:** The paired Communicators sources agree.
  Four catalogue entries preserve exact base range, channels, cost, mass,
  TL 7 mass/form upgrades, orbital and official-channel capabilities, and
  unquantified underground/underwater reduction. Personal communicators
  require a TL 8 world network; their channel is private but not secure and
  network access requires a fee.
- **2026-07-29 — CE-EQUIP-005:** Raymond approved preserving the Computers
  section's TL 7 scalable Hand Computer form factor separately from the
  Personal Devices section's fixed TL 11 handcomp. Standard laptops retain
  all eight published TL/model/mass/cost rows; same-TL handhelds cost twice
  standard with source-unquantified mass. Battery, storage, terminal, and
  mechanically neutral desktop rules remain typed.
- **2026-07-29 — CE-EQUIP-006:** Paired Computer Options sources agree.
  DD/R and Data Wafer preserve exact TL and cost while omitted mass remains
  unquantified. A specialization adds exactly 1 or 2 Rating for one selected
  program, adds 25% of base computer cost per Rating, and makes that program
  consume zero simultaneous-program capacity. Campaign installations use
  immutable receipts with database-checked computer identity and arithmetic.
  Surcharges use exact quarter-Credit units because 25% of some published
  computer prices is fractional and the source supplies no rounding rule.
- **2026-07-29 — CE-EQUIP-007:** The paired Computer Software catalogues
  agree. Nine families and all 25 printed profiles preserve Rating, TL, and
  exact cost state. Database remains unranked with its published cost range;
  included software is distinct from fixed-price software; Intrusion/4 remains
  unavailable; and Intellect/3+ remains open-ended and unpriced. Down-rating
  stops at each family's printed minimum, while difficult copying begins above
  Rating/1 with source-unquantified transfer bandwidth.
- **2026-07-29 — CE-EQUIP-008:** Personal software behavior uses canonical
  Difficulty, Skill, and Characteristic keys. Security maps Ratings 0–3 to
  Average through Formidable. Expert requires Intelligent Interface, grants
  program Rating minus one for Intelligence/Education checks, or DM +1 when
  the user's skill is higher. Agent has Computer equal to Rating and is
  relationally composed from Expert and Intellect; Intellect's simultaneous
  Expert-skill capacity equals Rating. Translator's source term “Language
  skills” is preserved without equating it to the distinct Linguistics skill.
- **2026-07-29 — CE-EQUIP-009:** The paired Drugs catalogues agree on all
  nine entries. Omitted mass remains unquantified. Medicinal Drugs preserve
  both the table's Cr5 minimum and the prose's 1D6×Cr1,000 variable-cost
  mechanism rather than inventing one fixed price. Anagathics separately
  preserve catalogue TL11, natural forms at all TLs, and synthetic production
  beginning at TL15, together with their widespread legal restriction.
- **2026-07-29 — CE-EQUIP-010:** Combat-facing drug mechanics preserve exact
  initiative, free-dodge, damage-reduction, radiation, fatigue, and aftermath
  values. Combat Drug's 20 seconds/4 rounds and Metabolic Accelerator's 45
  seconds/8 rounds do not equal one another under the canonical six-second
  combat round; both printed forms remain authoritative facts and two open
  arithmetic issues request publisher errata. “Around ten minutes” remains
  explicitly approximate.
- **2026-07-29 — CE-EQUIP-011:** Support-drug mechanics preserve Fast Drug's
  60:1 metabolic ratio and subjective-day conversion; Medicinal Drugs'
  canonical Medic requirement, unquantified positive resistance DM, and
  wrong-drug poison; Medicinal Slow's explicitly approximate thirtyfold rate;
  Panacea's Medic 0 treatment scope; and Anagathics' calendar-month dosing and
  immediate missed-dose aging roll. No numeric resistance bonus is invented.
- **2026-07-29 — CE-EQUIP-012:** The paired Explosives catalogues agree on
  Plastic, Pocket Nuke, and TDX technology, cost, damage, and variable blast
  radius. All three retain unquantified mass. Explosive use requires canonical
  Demolitions; Effect 0 or 1 has the printed minimum ×1 multiplier, positive
  Effect supplies the multiplier, and the unstated negative-Effect damage
  outcome remains unquantified. Availability ends at Law Level 1. Pocket Nuke
  launcher size and TDX's horizontal-only blast are explicit capabilities.
- **2026-07-29 — CE-EQUIP-013:** The paired Personal Devices tables agree on
  all twelve TL, cost, and mass entries. Missing mass for Magnetic Compass,
  Wrist Watch, and Electromagnetic Probe remains unquantified. The fixed TL11,
  Cr1,000, 0.5 kg Hand Computer is preserved as the already-reviewed distinct
  Personal Devices form and does not overwrite the scalable computer family.
- **2026-07-29 — CE-EQUIP-014:** Personal Device descriptions are normalized
  into relational capabilities, canonical skill links, exact or explicitly
  approximate ranges, and hologram upgrade rows. Existing battlefield sensor
  rules remain authoritative for combat visibility. Bioscanner and NAS data
  interpretation uses only the printed skills; the electromagnetic probe's
  diagnostic bonus is exactly +1. No unstated device check difficulty exists.
- **2026-07-29 — CE-EQUIP-015:** The Robot and Drone framework uses canonical
  Comms for drone control and preserves the shared combat-as-character,
  vehicle-damage, Hull/Structure, and Endurance DM 0 rules. Robots require
  Intellect and possess Intelligence/Education; drones are remote controlled,
  possess neither, and use the operator's Social Standing only for social use.
  The source's stated robot Social Standing exceptions remain possible.
- **2026-07-29 — CE-EQUIP-016:** Seven robot/drone chassis preserve printed
  TL, price, physical and mental characteristics, Hull, Structure, and Armor.
  Probe Drone reuses the canonical ship-carried inventory identity. The
  mounted vehicle Autodoc remains distinct from the complete personal robot.
  Combat Drone's Cr90,000 excludes its selected weapon; Cargo Robot separately
  preserves the TL9 cargo-drone variant and its pre-Intellect utility warning.
- **2026-07-30 — CE-EQUIP-017:** Chassis systems, programs, weapons, Probe
  Drone mobility, and Combat Drone operation are relational. Fixed skills use
  canonical rules; open “appropriate skill” and “any gun” selections remain
  unresolved slots. Repair Robot Engineering is an alternative to Mechanics.
  Servitor Liaison remains the printed unresolved specialization; Carousing
  and Gambling are unranked reprogramming options, not installed programs.
- **2026-07-30 — CE-EQUIP-018:** Robot and Drone Options preserve exact +5
  Armor, +25% chassis cost, +50% integral-device cost, and Cr10,000 plus
  weapon cost mechanics. Campaign installations use immutable receipts with
  database-checked chassis and selected-item prices. Surcharges use exact
  quarter-Credit units so no unstated rounding rule is introduced. Multiple
  independently receipted integral installations are permitted.
- **2026-07-30 — CE-EQUIP-019:** The paired Sensory Aids tables agree on all
  eight TL, cost, and mass entries. Omitted mass for Lamp Oil, Infrared
  Goggles, and Light Intensifier Goggles remains explicitly unquantified.
  Operational descriptions and Binocular upgrades are reserved for the
  following relational capability block.
- **2026-07-30 — CE-EQUIP-020:** Sensory Aid capabilities preserve exact
  illumination geometry and continuous-use duration, including the Electric
  Torch's approximate six hours and its source-unquantified “later TL” for
  adjustable modes. Infrared and light-intensifier vision remain distinct.
  Binocular viewing distance remains unquantified; TL8 and TL12 upgrades retain
  their separate costs and capabilities without inventing cumulative pricing.
- **2026-07-30 — CE-EQUIP-021:** The paired Shelters sources agree on all six
  catalogue entries. Capacity, pressure, weather bands, temperature limits,
  person-hours, modular geometry, and life-support person-days are relational.
  Qualitative wind and “all but the most extreme” temperature protection stay
  named source categories; no unstated physical thresholds are invented.
- **2026-07-30 — CE-EQUIP-022:** The paired Survival Equipment tables agree
  on all twelve TL, cost, and mass entries. Omitted mass for Filter Mask,
  Combination Mask, Respirator, and Environment Suit remains explicitly
  unquantified. Operational effects are reserved for the following relational
  capability block.
- **2026-07-30 — CE-EQUIP-023:** Survival Equipment mechanics use canonical
  world-atmosphere and skill keys. Cold and swimming thresholds/modifiers,
  tank durations and refills, Rescue Bubble person-hours, Thruster Pack
  constraints, and generator duration are exact. No check difficulty is
  invented for the source's unqualified Zero-G check.
- **2026-07-30 — CE-EQUIP-024:** The paired Tools catalogue and descriptions
  agree. Eight exact items, fourteen operation scopes, and the Medical Kit's
  canonical Medicine link are relational. Unstated skill mappings remain open.
  Lock Picks become illegal at Law Level 8; Cr100 is a minimum illegal-market
  price because the source explicitly says “or more.”
- **2026-07-30 — CE-EQUIP-025:** Book 1's sixteen compact vehicle profiles are
  a distinct published catalogue, not replacements for VDS designs. Fifteen
  profiles link to matching VDS class identities; Grav Belt remains unlinked.
  Book 1 TL, agility, speed, occupancy, defenses, weapons, and prices remain
  independently authoritative. Grav Belt's missing speed unit stays unknown.
- **2026-07-30 — CE-EQUIP-026:** Book 1 vehicle descriptions are normalized
  as profile-specific capabilities rather than folded into conflicting VDS
  designs. Cargo, orbit timing, altitude protection, pressure, amphibious
  limits, atmosphere limits, batteries, and weapon exceptions remain exact.
  AFV lasers use canonical Energy Rifle; G/Carrier radiation leakage is false.
- **2026-07-30 — CE-EQUIP-027:** The eight Book 1 vehicle options are
  executable, campaign-scoped installations. Percentages, exact fixed or
  selected-computer costs, prerequisites, included sealing, multiplicity,
  mechanical snapshots, and immutable receipts remain relational. Style is
  only a bounded Cr200–Cr2,000 customization; it grants no invented bonus.
- **2026-07-30 — CE-EQUIP-028:** The twelve-row Book 1 melee table preserves
  exact TL, price, mass, range profiles, damage types, damage dice, and Law
  Levels. Eleven physical weapons use canonical inventory definitions.
  Unarmed Strike is a combat attack rule, never a fictional inventory item.
- **2026-07-30 — CE-EQUIP-029:** Melee descriptions preserve ten exact,
  approximate, or ranged lengths; three two-handed weapons; Dagger's worn-load
  exception; and typed shipboard, tool, survival, and emergency roles.
  Bayonet only equals Dagger while unattached. Cudgel improvisation requires
  an unloaded non-laser long gun; no unstated attached-Bayonet bonus exists.
- **2026-07-30 — CE-EQUIP-030:** The already paired 18-weapon ranged catalogue
  is reconciled without replacing canonical identities. Rate of Fire is split
  into typed single, burst, and automatic counts. The Snub Pistol's published
  6/15 ammunition row becomes two capacity variants sharing its Cr10/30g
  listing, yielding nineteen variants from eighteen source rows.
- **2026-07-30 — CE-EQUIP-031:** Ranged descriptions add typed zero-g,
  detector-evasion, external-power, and optic facts; TL2/TL4/TL9 Crossbow
  reload states; Auto Rifle mode-switch timing; and Revolver's expedited
  reload/evasion trade. Ammunition and magazine compatibility remain separate.
- **2026-07-30 - CE-EQUIP-032:** Ten ranged weapon options preserve printed
  TL, mass, eligibility, upgrades, timing, and typed effects. By agreement,
  Laser Sight canonically costs Cr200 everywhere; the conflicting Cr100 table
  entry remains a non-operative source assertion. Campaign installations use
  active same-campaign instances, exact snapshots, and immutable receipts.
- **2026-07-30 - CE-EQUIP-033:** Four grenade profiles preserve cases of six,
  per-grenade mass, two delivery modes, Frag distance damage, Smoke and
  Aerosol persistence/interference, and Stun's post-armor Endurance outcome.
  Qualitative weather shortening remains unquantified; no duration adjustment
  is invented.
- **2026-07-30 - CE-EQUIP-034:** Five carried heavy weapons and their five
  ammunition or power-pack rows remain distinct from VDS weapon designs.
  Exact TL, cost, mass, RoF, range, recoil, legality, and capacity are typed.
  Grenade launchers derive damage from the selected grenade; no substitute
  damage dice are invented.
- **2026-07-30 - CE-EQUIP-035:** Heavy-weapon descriptions preserve FGMP
  Strength 9 and unprotected 2D6x20-rad exposure, PGMP Strength 12 shortfall
  penalties, launcher incompatibility and reload timing, RAM full-auto without
  burst, and all rocket backblast and miss mechanics. "Immediate vicinity"
  and random miss direction remain source-unquantified.
- **2026-07-30 - CE-PSI-001:** Psionic Strength determination uses immutable
  2D6-minus-actual-career-terms receipts and preserves raw zero or negative
  results rather than inventing a clamp. Eligible four-month, Cr100,000
  training uses exact talent modifiers, cumulative attempt penalties, level-0
  acquisition, contiguous attempts, and immutable learning receipts.
- **2026-07-30 - CE-PSI-002:** Awareness power mechanics are stored as typed,
  relational rule data. Suspended animation preserves its exact seven-day
  duration and waking requirements; Strength and Endurance enhancement preserve
  skill and racial caps, ten-minute peak and one-point-per-minute decline; and
  regeneration is restricted to Strength, Dexterity, and Endurance without
  inventing a per-use maximum or permission to reverse aging.
- **2026-07-30 - CE-PSI-003:** Successful Awareness activations produce typed,
  immutable effect receipts. Suspended animation and temporary enhancement are
  derived campaign projections; enhancement retains the wounded baseline and
  snapshots the source-defined 15-plus-species racial cap. Regeneration alone
  updates physical injury state through allocations and remains locked until a
  recovery receipt proves Psionic Strength has returned to its snapshotted
  maximum.
- **2026-07-30 - CE-PSI-004:** Clairvoyance preserves the four published
  sensory modes, location targeting, range costs, undetectability, and the
  stated Effect dependencies without inventing numeric clarity or detail
  thresholds. Failed activations retain the declared location; successful
  observations add immutable Effect, timing, sensory-channel, duration, and
  Referee-evidence receipts within the actor's campaign.
- **2026-07-30 - CE-PSI-005:** Telekinesis preserves six exact gram-based mass
  ceilings and published throwing damage, physical-equivalent manipulation
  without danger or pain feedback, Effect-based duration, Ranged (thrown)
  attacks, the greater of the two stated distances, Effect-added damage, and
  equal damage to a thrown creature and its target. Actor mass must be supplied
  as an immutable campaign snapshot; species averages are not actor facts.
- **2026-07-30 - CE-PSI-006:** Successful Telekinesis establishes immutable
  item-or-creature manipulation state. Item mass must match a known active
  inventory definition; creature mass is an explicit campaign snapshot. Both
  are constrained by the activated power's exact mass ceiling. Duration is
  recorded as a positive Referee resolution because the source says Effect
  determines rounds but publishes no numeric conversion.
- **2026-07-30 - CE-PSI-007:** A telekinetic throw is a separate audited
  Ranged (thrown) check within the successful activation command. SQL selects
  the greater psion-to-target or object-origin-to-target distance, validates
  the supplied permitted combat range, adds the throw check's Effect—not the
  activation Effect—to published impact damage, and mirrors raw damage to a
  thrown creature without pretending the object is a catalogue weapon.
- **2026-07-30 - CE-PSI-008:** Life Detection results normalize each
  significant detected mind by general type, approximate location, optional
  campaign actor, and known-person recognition. Natural telepathic shields
  exclude actors from detection. Referee summary, type, location, and
  recognition-basis wording are immutable evidence because the paired sources
  provide no numeric precision or automatic acquaintance model.
- **2026-07-30 - CE-PSI-009:** Telempathy records reading, projection, or both
  as explicit operations. Projected emotion strength is the activation Effect;
  target behavior remains immutable Referee evidence because the source warns
  that influence need not work as desired. A telepathic target recognizes
  projected influence, while a nontelepath does not recognize its source.
- **2026-07-30 - CE-PSI-010:** Read Surface Thoughts receipts contain only
  active/current thought evidence and a separate Effect-dependent clarity
  statement. Nontelepathic subjects are marked unaware. A telepathic subject
  must have an open shield and an immutable consent reference; SQL does not
  infer willing consent merely from the shield-state boolean.
- **2026-07-30 - CE-PSI-011:** Send Thoughts records exact transmitted content
  and derives whether the recipient is a telepath. Nontelepaths can receive;
  trained telepaths must have lowered their shield. No Effect-based fidelity,
  comprehension, or reply mechanic is invented because the paired sources
  assign none.
- **2026-07-30 - CE-PSI-012:** Probe is normalized as deliberate and rapid
  modes with their published difficulty, timing, and costs retained by the
  power catalogue. Successful receipts preserve innermost-thought evidence,
  a separate Effect-dependent clarity statement, and optional ordered
  questioning results. Deliberate untruth detection is explicit evidence;
  SQL does not infer truth, invent information, or convert Effect to an
  unpublished numeric clarity scale.
- **2026-07-30 - CE-PSI-013:** The live OGN page and paired GitHub Markdown
  agree on Assault's unshielded damage and recovery, but both currently omit
  its activation line and shielded-mind paragraph. The complete Traveller SRD
  and published Cepheus SRD preserve Formidable, 1D6 seconds, 8+Range, and
  opposed Telepathy against shields; the reference-only old Markdown retains
  the numeric table row but mislabels it as a second Probe. The reconciled rule
  therefore inflicts 2D6+Effect in Psionic Strength, Intelligence, Endurance
  order, with Intelligence returning one point per day.
- **2026-07-30 - CE-PSI-014:** A successful Assault activation reuses its
  undistorted Telepathy roll as the attacker's opposed total against a raised
  shield; ties protect the defender. Penetrating or unshielded Assault rolls
  separate 2D6 damage, adds activation Effect, and exhausts Psionic Strength,
  Intelligence, then Endurance. Immediate unconsciousness uses audited
  personal-condition state. Normal minute-by-minute Endurance recovery can
  restore consciousness without falsely adding fatigue; Intelligence remains
  governed by daily mental healing.
- **2026-07-31 - CE-PSI-015:** Every trained telepath has a naturally raised
  Shield with no maintenance cost. Lowering or raising it is a free combat
  action, and raised Shield prevents the telepath from using Telepathy.
  Commands preserve campaign, actor-version, state-change, and timestamp
  snapshots. Deferred SQL auditing rejects shield-state writes without an
  immutable matching command receipt.
- **2026-07-31 - CE-PSI-016:** Teleportation is self-only and always moves the
  psion's body; load profiles determine whether clothing and possessions may
  accompany it. Destination knowledge must derive from direct viewing,
  telepathic implantation, or clairvoyance, never a recording. Planetary
  jumps stop at Very Distant range; that band causes 2D6x10 seconds of
  disorientation. Altitude and fast-vehicle conservation hazards remain
  explicit normalized mechanics rather than narrative guesses.
- **2026-08-01 - CE-SHIP-001:** The Asteroid Miner smelter occupies four tons
  and costs Cr90,000 installed, exactly filling the publication's retained
  tonnage and final-cost gaps. Its processing capacity remains unspecified.
- **2026-08-01 - CE-SHIP-002:** The 800-ton Destroyer uses jump drive H for
  Jump-2 and maneuver drive N for 4-G, as required by the published drive
  matrix. The resulting cost and hull-volume discrepancies remain explicit
  source questions rather than being hidden by invented component changes.
- **2026-08-01 - CE-SHIP-003:** The Research Vessel remains a TL9 spacecraft
  design carrying fifteen explicitly published TL11 probe drones. Those drones
  are separately procured payload and require TL11 availability; they do not
  raise the underlying spacecraft design tech level.
