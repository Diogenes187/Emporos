# Cepheus SRD Website Evaluation

## Evaluation Target

Website:

`https://cepheus-srd.opengamingnetwork.com/`

Related machine-readable source:

`https://github.com/orffen/cepheus-srd`

Evaluation date: 2026-07-27

## Corrected Executive Finding

The website is not merely a convenient rendering of a few common Cepheus rules.
It is a substantial, navigable Cepheus Engine rules corpus with extensive
subsections and structured data.

It deserves a primary role in the Base Cepheus content strategy.

The website is still not identical to the purchased *Cepheus Universal* SRD.
The two corpora contain materially different rules and must remain separate
versioned packages. The website should not be used to overwrite Universal
differences, and Universal should not obscure how useful the website is as a
clean foundational source.

## Site Structure Evaluated

The main navigation exposes:

- Home and core terminology;
- Adventures;
- Character Creation;
- Environments and Hazards;
- Equipment;
- Off-World Travel;
- Personal Combat;
- Planetary Wilderness Encounters;
- Psionics;
- Refereeing the Game;
- Skills;
- Social Encounters;
- Space Combat;
- Starship Encounters;
- Worlds;
- Legal.

The Equipment branch expands further into:

- Common Aircraft;
- Common Grav Vehicles;
- Common Ground Vehicles;
- Common Vessels;
- Common Watercraft;
- Ship Design and Construction;
- Trade and Commerce;
- Uncommon Vehicles;
- Vehicle Design System.

The linked pages contain their own tables of contents, nested heading anchors,
rule prose, checklists, formulae, and data tables.

## Coverage Assessment

### Core Resolution

The home material includes:

- task resolution;
- difficulty and Effect;
- opposed checks;
- retries;
- circumstance modifiers;
- time and checks;
- aiding another;
- attack and characteristic checks;
- action categories;
- terminology and notation.

This is sufficient to seed a coherent rules vocabulary rather than isolated
lookups.

### Character Creation

The Character Creation page is extensive. It includes:

- a full checklist;
- characteristics and modifiers;
- UPP and character format;
- background/homeworld skills;
- careers;
- qualification and draft;
- terms;
- training;
- survival;
- commission and advancement;
- injuries and medical debt;
- aging;
- reenlistment and retirement;
- benefits;
- career tables;
- final details;
- alien species and traits.

The page is structurally favorable for normalizing careers, ranks, term
procedures, benefits, and events.

### Skills

The Skills page provides:

- task-description conventions;
- trained, untrained, and zero-level behavior;
- time changes;
- multiple actions;
- law-level interaction;
- a long individually headed skill catalogue;
- cascade skills and their specialties.

Individual skill headings make source locators and candidate generation much
cleaner than a flat Word extraction.

### Equipment

The Equipment page covers:

- technology levels and currency;
- armor;
- communications;
- computers and software;
- drugs;
- explosives;
- personal devices;
- robots and drones;
- sensory aids;
- shelters;
- survival equipment;
- tools;
- vehicles;
- melee, ranged, grenade, and heavy weapons.

This contains many natural relational records with stable fields such as name,
tech level, cost, mass, protection, damage, range, magazine, traits, and
description.

### Trade and Commerce

The trade branch contains an explicit procedure:

- find supplier;
- determine goods;
- determine purchase price;
- use local brokers;
- sell goods.

This is directly relevant to the engine-owned market and trade system.

### Travel and Ship Operations

Off-World Travel covers:

- interplanetary travel;
- interstellar travel;
- jump success and failure/misjump;
- ship operations;
- passage;
- standard procedures;
- mortgages and debts;
- crew salaries;
- fuel;
- life support;
- port fees;
- maintenance;
- cargo and revenue.

This is a strong source for deterministic travel and ship-finance workflows.

### Personal Combat

The Personal Combat page is a complete subsystem with:

- checklist;
- range and starting range;
- initiative;
- combat round and dynamic initiative;
- minor and significant actions;
- attacks;
- reactions;
- dodging and parrying;
- free and extended actions;
- additional combat consequences and procedures later in the page.

The structure is excellent for extracting action definitions, legal actions,
range bands, modifiers, reactions, and resolution rules.

It is materially different from the inspected Cepheus Universal personal-combat
procedure. It must therefore be its own rule package.

### Space Combat

The Space Combat page contains a full abstract vessel-combat system. It
explicitly states that movement and maneuvering are abstracted for cinematic
position, pursuit, and advantage, and uses named range bands for vessels.

Its page is extensive and structurally separate from:

- Ship Design and Construction;
- Common Vessels;
- Starship Encounters;
- Off-World Travel.

This separation is very useful for database domains and gameplay contracts.

The system is materially different from Cepheus Universal's Detection, Range,
Tactical, Advantage, Attack, Screen, Damage, Damage Control, and Return sequence.

### Ship Design and Vessels

Ship Design and Construction includes:

- design checklist;
- displacement;
- hull and configuration;
- armor;
- Hull and Structure;
- ship sections;
- drives and fuel;
- bridge;
- computer;
- further components and systems throughout the page.

Common Vessels supplies ready-made ship definitions. These are highly suitable
for ship-class and component records rather than AI-generated vessels.

### Vehicle Design and Examples

The Vehicle Design System is itself a very large linked section. It is
accompanied by common:

- aircraft;
- grav vehicles;
- ground vehicles;
- watercraft;
- uncommon vehicles.

Example vehicle pages contain both prose summaries and component-by-component
design specifications. These can validate the design-rule implementation: the
engine should be able to reconstruct the published example totals from
normalized components.

### Encounters and Refereeing

The site includes separate:

- social encounters;
- wilderness encounters;
- starship encounters;
- adventure construction;
- referee guidance.

Social encounters contain frequency/chance structures and multiple encounter
types. Starship encounter guidance addresses where encounters plausibly occur.
Adventure guidance includes casts, scenes, plot keys, chapters, and checklists.

Not all of this belongs in executable rules tables. Some should become curated
content, referee guidance, or optional adventure-building templates.

### Worlds

The Worlds page contains:

- UWP;
- star mapping;
- size;
- atmosphere;
- hydrographics;
- population;
- starport;
- government;
- law;
- technology;
- trade codes;
- belts and gas giants;
- further system-generation content.

This is a natural source for normalized world-generation definitions and
procedures.

### Psionics

The Psionics page includes:

- psionic strength;
- recovery and training;
- talents;
- use and range;
- Awareness;
- Clairvoyance;
- Telekinesis;
- Telepathy;
- Teleportation;
- psionic technology and social context.

The page explicitly identifies the chapter as optional, which must be retained
as rules metadata.

## Extraction Quality

### Advantages

The website provides:

- stable page URLs;
- nested heading anchors;
- page-level tables of contents;
- relatively clean textual hierarchy;
- HTML tables;
- explicit table titles;
- smaller source units than one large DOCX;
- natural source locators;
- easy change detection by page;
- straightforward link discovery.

The related GitHub repository provides mdBook source. Markdown is preferable to
scraping the rendered website because it avoids:

- navigation and advertising;
- affiliate links;
- repeated footer content;
- presentation markup;
- some ambiguity introduced by HTML table rendering.

### Limitations

The website is not itself an ideal immutable import artifact:

- the publisher can change pages;
- page navigation and advertisements surround source content;
- some tables are visually or semantically flattened in text extraction;
- site version does not by itself identify the exact rule-text revision of each
  page;
- external availability cannot be required at runtime;
- links and headings may change;
- a web page snapshot needs a checksum and retrieval date.

The GitHub source reduces these problems because imports can pin a release tag
or commit.

### Recommended Extraction Source

For Cepheus Engine content:

1. Pin an approved `orffen/cepheus-srd` release or commit.
2. Import Markdown source from that immutable revision.
3. Use the website to visually verify rendered headings and tables.
4. Retain the repository revision, file path, heading anchor, and content
   checksum in provenance.
5. Compare the website and pinned Markdown for unexpected divergence.

Do not scrape advertisements, store links, cross-promotional SRD navigation, or
site boilerplate.

## Licensing Findings

The site's legal material designates its SRD text as Open Gaming Content except
for specified Product Identity.

The GitHub repository separately states that the code used to display the SRD
in HTML format is released under the Unlicense. The source-code license does not
replace the rules text's Open Gaming Content and Product Identity
classifications.

The database must retain those distinctions.

## Relationship to Cepheus Universal

The website and purchased Universal SRD overlap in concepts but differ in
mechanics, terminology, procedures, and breadth.

Examples already observed include:

- combat action allowance;
- initiative and action/reaction structure;
- injury definitions;
- personal combat organization;
- space-combat procedure and terminology;
- careers and chargen organization;
- skill names and cascade behavior;
- psionics versus Universal mind-power presentation.

Therefore:

- a normalized concept may have multiple package-specific definitions;
- matching names do not authorize merging;
- crosswalks express equivalence, similarity, replacement, or incompatibility;
- each campaign selects an exact rules package;
- old receipts retain the package/rule version used.

## Revised Recommendation

The earlier framing of the website as merely a secondary cross-check was too
weak.

Recommended source architecture:

### Package 1 - Cepheus Engine SRD

Use the pinned GitHub Markdown and captured OGN website pages as paired import
artifacts. If either lacks material, use the other and retain exact provenance.
If both contain a rule, compare them; do not silently choose between genuine
conflicts.

This is the cleanest starting corpus for:

- schema validation;
- normalized rules extraction;
- extensive natural tables;
- travel and trade;
- characters and careers;
- equipment;
- personal and space combat;
- ships and vehicles;
- worlds and encounters.

### Package 2 - Cepheus Universal SRD

Import the purchased DOCX independently as a separate versioned package.

Use it for:

- the Universal Space product if selected;
- Universal-specific or expanded systems;
- low-tech and broader setting construction;
- alternate personal/ship combat;
- package comparison and future products.

### Crosswalk Package

Maintain reviewed relationships:

- identical;
- equivalent with renamed terminology;
- similar but mechanically different;
- Universal extends Engine;
- Engine-only;
- Universal-only;
- incompatible.

Crosswalks do not choose which rule governs a campaign.

## Product Decision Required

Before importing rules, the relational Cepheus engine must choose its governing
mechanical package:

1. Cepheus Engine SRD from the website/GitHub;
2. Cepheus Universal SRD from the purchased DOCX;
3. an explicitly approved derived package that selects rules from both.

Option 3 requires many individual decisions and is the highest-risk route for
accidental invention or inconsistency.

### Decision

The Cepheus Engine SRD website/GitHub corpus is the governing source package for
the first normalization and relational engine package.

Cepheus Universal remains a separate, valuable rules package. Universal rules
are not silently substituted into the Engine product, even where prior planning
or research used Universal terminology.

**Status:** Approved by Raymond on 2026-07-27.

## Final Assessment

The website is indeed a likely “sweet spot” for the Base Cepheus data effort.
It is broad, structured, openly designated, and backed by cleaner source files.
It should be treated as a major source, not merely a convenience.

The selected direction is to make it the first fully normalized Cepheus Engine
content package while preserving Cepheus Universal as a distinct package. This
gives Base Cepheus two valuable rules corpora without corrupting either one.
