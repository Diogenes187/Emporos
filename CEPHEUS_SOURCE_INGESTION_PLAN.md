# Cepheus Source Ingestion and Normalization Plan

## Status

Planning workflow for converting Cepheus source material into reviewed,
versioned PostgreSQL records.

No ingestion run is authorized by this document alone. Physical migrations,
extractors, and content imports follow after schema review.

## Governing Principle

Source files are evidence and import inputs. Reviewed PostgreSQL records are the
authoritative rules/content representation used by the released product.

The pipeline is:

```text
unaltered source file
  -> deterministic extraction
  -> temporary staging
  -> structural classification
  -> normalized candidates
  -> automated validation
  -> human review
  -> approved relational records
  -> provenance links
  -> generated projections/exports
```

No step silently invents missing rules or mechanics.

## Source Priority Decision

The Cepheus Engine SRD published through the Open Gaming Network website and the
related `orffen/cepheus-srd` repository is the governing source corpus for the
first normalized package and the relational Cepheus engine.

The importer treats the pinned GitHub release and a timestamped/checksummed OGN
website capture as paired governing inputs. Either may supply material absent
from the other. Every candidate record retains source-level provenance. Where
both contain the same material, they are compared; an actual conflict is held
for review rather than resolved by automatic source priority.

The purchased Cepheus Universal material is imported later as a separate
package. Universal rules never overwrite or silently fill gaps in the Cepheus
Engine package.

**Status:** Approved by Raymond on 2026-07-27.

## Apparent Omission Reconciliation

Absence from one transcription, page, or table is not enough to classify a
Cepheus rule as unspecified. Before creating a `source_unspecified` record, the
ingestion review must:

1. inspect both paired governing inputs and other editions or renderings of the
   same authorized Cepheus work;
2. inspect adjacent rules text, related combat or construction tables,
   cross-scale conversion rules, and standard published examples or designs;
3. inspect the reference-only prior implementation for locators and working
   behavior, treating it as evidence rather than authority;
4. reconcile every recovered field against the governing rules and retain
   field-level provenance;
5. classify a missing row or field in one source as a publication or
   transcription omission when another governing representation supplies it;
6. hold actual conflicts for explicit adjudication instead of selecting the
   convenient value.

`source_unspecified` is a last-resort classification. It requires a documented
search of the relevant sources and a decision-register entry identifying what
was searched, what remains absent, and which consumer is blocked. A standard
rule must not be downgraded merely because a convenient transcription omitted
it.

**Status:** Approved by Raymond on 2026-07-28 after reconciliation of the
standard Beam Laser profile.

## Source Roles

### Paired Mechanical Sources - Cepheus Engine SRD

- Website: `https://cepheus-srd.opengamingnetwork.com/`
- Repository: `https://github.com/orffen/cepheus-srd`
- Import artifacts: pinned repository release or commit plus captured OGN pages

Role:

- governing rules and tables for the relational Cepheus engine;
- clean Markdown headings, tables, lists, and file paths where available;
- website material where the repository is incomplete or differs in coverage;
- stable provenance through repository revision, URL, capture time, and checksum;
- mutual concordance checks for content present in both publications.

### Separate Package Source - Cepheus Universal

`books/CepheusUniversal-SRD2.docx`

Observed structure:

- approximately 7,075 paragraphs;
- 155 Word tables;
- approximately 161 headings;
- major coverage from character creation through setting construction;
- full personal and ship combat procedures;
- source text designated under its stated license, subject to Product Identity
  exclusions and attribution requirements.

Role:

- source for the independent Cepheus Universal content package;
- source locators by heading path, paragraph anchor, and table anchor;
- package comparison and reviewed crosswalks;
- Universal-specific and expanded systems;
- never an automatic fallback for missing Cepheus Engine rules.

### Player-Facing Cross-Check

`books/players-book11.pdf`

Observed structure:

- 208 pages;
- player-facing rules, examples, equipment, and quick-reference material;
- full personal combat coverage;
- no located full Space Combat phase chapter.

Role:

- terminology and player-presentation cross-check;
- page-stable citations;
- detection of meaningful differences or omissions;
- source for material not present in the SRD only after license and provenance
  review.

### Worksheets and Character Sheet

- `books/CU-Data-Character-Sheet-FILLABLE.pdf`
- `books/CU-Data-Term-Worksheet1-FILLABLE.pdf`
- `books/CU-Data-Term-Worksheet2-FILLABLE.pdf`

Role:

- validate required character and chargen fields;
- validate player workflow and terminology;
- inform UI projections;
- never treated as complete rules authority.

### Logos

The supplied logos are product assets subject to their own permitted use. They
are not rules content and do not enter the rules database.

## Source Preservation

Source files remain unchanged in `books`.

For every import:

- calculate and record a cryptographic checksum;
- record file name, size, modified time, importer version, and source-work
  identity;
- reject an unexpected checksum until the source edition is reviewed;
- never rewrite, normalize, rename, or resave the purchased source as part of
  ingestion;
- write all temporary artifacts outside `books`.

## Ingestion Layers

### Layer 0 - Source Manifest

One reviewed manifest entry per source file:

- stable source-work code;
- edition/version label;
- publisher;
- copyright year;
- source classification;
- license relationship;
- checksum;
- ingestion role;
- review status.

The manifest is represented in `src_work`, `src_license`, and
`src_work_license`, not only in a repository file.

### Layer 1 - Deterministic Extraction

DOCX extraction captures:

- paragraph order;
- paragraph text;
- paragraph style;
- heading level and active heading path;
- table order;
- row and cell order;
- merged-cell structure where recoverable;
- list/numbering identity;
- footnotes/endnotes if present;
- embedded image identity when relevant to a rule;
- OOXML anchor sufficient to reproduce the locator.

PDF extraction captures:

- PDF page number;
- printed page label where present;
- text blocks and order;
- detected headings;
- table regions;
- form fields for worksheets;
- page rendering references for visual verification.

Extraction is deterministic: identical input and importer version produce the
same extracted identities and checksums.

### Layer 2 - Temporary Staging

Staging preserves source shape without claiming semantic correctness.

Permitted staging records include:

- extracted paragraph;
- heading;
- table;
- row;
- cell;
- list item;
- image reference;
- PDF text block;
- form field.

Temporary JSON may represent complex OOXML/PDF extraction details here. Staging
records are nonauthoritative and removable after approved records and audit
artifacts are secure.

### Layer 3 - Structural Classification

Each extracted unit receives one or more candidate classifications:

- heading/navigation;
- explanatory prose;
- rule statement;
- procedure step;
- definition;
- modifier;
- random table;
- lookup table;
- equipment record;
- weapon/armor record;
- characteristic/skill;
- career/assignment/rank;
- chargen event/mishap/benefit;
- vehicle/ship/component;
- world-generation rule;
- creature/NPC template;
- encounter entry;
- example;
- optional rule;
- referee advice;
- player advice;
- setting suggestion;
- license/product-identity material.

Classification proposes a destination; it does not publish content.

### Layer 4 - Normalized Candidates

A normalizer converts classified source units into typed candidates.

Examples:

- a skill heading and definition become a `rule_skill` candidate;
- a difficulty row becomes a `rule_difficulty` candidate;
- a career rank table becomes `cg_rank` candidates;
- a weapon table row becomes `inv_item_definition`,
  `inv_weapon_definition`, and range/property candidates;
- a starship component row becomes `ship_component_definition`;
- a random encounter row becomes `rule_random_table_entry` linked to typed
  encounter content.

Every candidate retains all contributing source locators.

### Layer 5 - Automated Validation

Validation checks syntax and cross-record integrity before human review.

Examples:

- codes and names are unique within package scope;
- referenced skills and characteristics exist;
- result ranges are complete and non-overlapping where the source expects them
  to be;
- dice expressions parse;
- numeric values retain units;
- equipment references valid categories and tech levels;
- career tables reference valid outcomes;
- ship components reference valid design categories;
- damage and range codes match known source definitions;
- every candidate has provenance;
- no prohibited Product Identity is accidentally classified as open rules
  content;
- no normalizer supplies a value absent from its source or an approved decision.

Validation failures return to staging or review. They never acquire defaults
merely to make an import pass.

### Layer 6 - Human Review

Every candidate receives a review disposition:

- approved unchanged;
- approved with transcription correction;
- approved as a documented implementation interpretation;
- deferred for source ambiguity;
- rejected as non-rule prose;
- rejected as duplicate;
- rejected because rights/classification do not permit inclusion.

Review records:

- reviewer;
- timestamp;
- source view;
- proposed normalized view;
- differences;
- rationale;
- related Rule Decision Register entry where required.

AI may assist classification and comparison. AI cannot approve a candidate.

### Layer 7 - Publication

Approved candidates are published into a versioned content package within one
transaction.

Publication:

- inserts immutable definition records;
- attaches `src_record_provenance`;
- creates rule-version identities;
- runs all package integrity tests;
- calculates a package checksum;
- marks the package installable only after tests pass.

Published records are never edited in place. Corrections create a new package
version and explicit supersession relationships.

### Layer 8 - Generated Projections

The product may generate:

- API JSON;
- browser catalogues;
- AI rule excerpts;
- printable reference sheets;
- search indexes;
- test fixtures;
- content-package exports.

All are reproducible from approved PostgreSQL records and package versions.

## Heading-Path Locators

DOCX pagination can change between renderers. The primary SRD locator therefore
uses:

- source-work identity;
- heading hierarchy;
- extracted paragraph or table anchor;
- source checksum;
- optional rendered page recorded for human convenience.

Example conceptual locator:

```text
CU-SRD-2024
SPACE COMBAT > PHASES OF COMBAT > ADVANTAGE PHASE
paragraph-anchor: p-004219
source-checksum: ...
```

Player's Book locators use PDF page plus heading and text-block/table anchor.

## Table Extraction Policy

Tables require visual and structural inspection because Word/PDF extraction can
lose:

- merged headers;
- repeated header rows;
- footnote markers;
- blank cells that mean “same as above”;
- wrapped text;
- dice ranges;
- column grouping;
- symbols or formatting that change meaning.

For each source table:

1. Extract raw OOXML/PDF structure.
2. Render and inspect the relevant source page.
3. Identify table title and heading path.
4. Define column semantics explicitly.
5. Preserve source row order.
6. Normalize units, ranges, references, and effects.
7. Compare normalized rows to the rendered source.
8. Require human approval.

A table is not approved merely because its row count matches.

## Formula and Procedure Policy

Rules expressed as formulas or procedural prose require:

- exact source locator;
- structured input definitions;
- structured output definition;
- ordering of operations;
- rounding behavior if stated;
- random inputs;
- optional/mandatory classification;
- edge cases explicitly present in source;
- implementation interpretation record for any unstated software detail;
- executable fidelity tests.

The importer does not translate arbitrary prose directly into executable code.
It creates a reviewed rule specification that a human-authored implementation
must satisfy.

## Content Domains and Import Order

Dependencies require deliberate import order.

### Phase 1 - Foundation Vocabulary

- source works and licenses;
- content packages;
- characteristics;
- skills and specialties;
- task difficulties;
- dice/random-table primitives;
- tech levels and common units.

### Phase 2 - Character Creation

- chargen methods;
- careers and assignments;
- ranks;
- skill tables;
- qualification, survival, advancement;
- events and mishaps;
- benefits;
- life-path procedures.

### Phase 3 - Personal Rules

- movement;
- stress and hazards;
- personal combat;
- damage, armor, injury, treatment, recovery;
- equipment, weapons, ammunition, and armor;
- mind powers and their effects.

### Phase 4 - Vehicles and Ships

- vehicle definitions and design rules;
- space travel;
- ship operations and crew;
- ship classes/components;
- ship design;
- space combat;
- boarding and environmental interfaces.

### Phase 5 - Worlds and Encounters

- sectors, systems, and world generation;
- trade classifications and goods;
- creatures and alien life;
- encounter tables;
- planetary travel;
- factions and setting-construction tools.

Each phase becomes a separately reviewable package milestone. Later phases do
not block proving the first vertical slice with a deliberately small approved
subset.

## Rule Decision Integration

The normalizer may publish only:

- explicit source behavior;
- explicit source options;
- implementation interpretations approved in
  `CEPHEUS_RULE_DECISION_REGISTER.md`;
- approved product additions contained in a separate house-rule package.

Examples already approved:

- hybrid exact-position/range-band personal representation;
- named NPC full combat versus abstract background units;
- player-selected order within the PC phase;
- initial two-vessel ship-combat boundary;
- boarding-to-personal encounter transition;
- operational control conditions without an invented capture roll.

These decisions do not rewrite source records. They attach to implementation or
house-rule metadata as appropriate.

## Duplicate and Conflict Handling

The same concept may appear:

- in multiple SRD sections;
- in prose and a quick-reference table;
- in both SRD and Player's Book;
- in a worksheet field and a rules section.

The importer does not choose by last-write-wins.

It creates:

- one normalized candidate concept;
- multiple provenance links;
- a comparison record;
- a conflict requiring review when values differ.

Quick references are validation aids unless explicitly authoritative. A
conflict between full rule text and quick reference is logged and resolved, not
silently merged.

## Rights and Product Identity Gate

Before publication, every content candidate must be classified:

- open game/rules content permitted by the governing license;
- original product content;
- Product Identity;
- third-party content with separate permission;
- private campaign content;
- uncertain.

Uncertain and Product Identity candidates do not enter a distributable package
without a documented rights basis.

Attribution and license text are generated from package provenance and reviewed
before release.

## Import Idempotency

Re-running an importer against the same source checksum and importer version:

- does not duplicate staging units;
- does not duplicate candidates;
- does not alter approved published records;
- produces the same extraction checksums;
- reports any nondeterministic difference as an error.

A new source checksum or importer semantic version creates a new import batch.

## Review Interface Requirements

The future review tool should show:

- rendered source page or DOCX region;
- extracted raw structure;
- active heading path;
- normalized candidate fields;
- provenance;
- automated validation;
- differences from the previous package;
- related decision-register entries;
- approve, correct, defer, reject actions.

Bulk approval is allowed only for mechanically simple, uniformly validated
records and must remain attributable.

## Initial Import Slice

The first ingestion exercise should be deliberately small:

1. Pin and register the selected Cepheus Engine SRD repository revision, legal
   material, checksums, and package.
2. Extract Markdown headings, tables, links, and source locators and compare
   them to the OGN rendering.
3. Import the six core characteristics.
4. Import a small skill subset needed by the vertical slice.
5. Import task difficulties and core 2D6 task resolution references.
6. Import one personal weapon, armor definition, and trade good.
7. Import the personal round/action/range rules needed by one encounter.
8. Import two simple ship definitions/components and the ship phases needed by
   the second slice.
9. Import only boarding, access, or related source references actually present
   in the selected Cepheus Engine package; do not substitute Universal rules.
10. Generate an API projection entirely from PostgreSQL.

The slice succeeds only when every published value can be traced to a rendered
source location or an approved decision.

## Validation Reports

Every package build produces:

- extraction manifest;
- unclassified-source report;
- rejected/deferred candidate report;
- missing-provenance report;
- unresolved-reference report;
- overlapping/gapped-table-range report;
- source conflict report;
- optional-rule report;
- agreed-interpretation report;
- rights-classification report;
- package diff;
- package checksum and test result.

## What the Pipeline Must Never Do

- treat AI output as source text;
- infer a missing numeric value;
- silently repair an apparent source inconsistency;
- merge distinct rules because their names look similar;
- publish unreviewed candidates;
- overwrite an approved content package;
- make JSON files the released authority;
- import protected settings because the schema can represent them;
- allow browser code to become the only implementation of an imported rule;
- discard source wording needed to review an interpretation.

## Next Planning Deliverables

Before implementation:

1. approve the source manifest and rights classifications;
2. define PostgreSQL migration `001` for system/source/package metadata;
3. define the normalized extraction identity scheme;
4. specify the review-state machine;
5. select the exact first vertical-slice rules and content records;
6. build source-fidelity acceptance fixtures from those records.
