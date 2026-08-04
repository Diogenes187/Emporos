# Cepheus Website/GitHub Concordance Report

- Generated: 2026-08-04T15:12:19.369457+00:00
- Repository commit: `0839018902355215fb8148f0b4ce1b1f8e011080`
- Exact tag: `v9.1`
- Compared website pages: 25

## Page Results

| Page | Similarity | GitHub coverage | Website coverage | GitHub tokens | Website tokens |
|---|---:|---:|---:|---:|---:|
| Introduction | 97.16% | 99.91% | 94.56% | 4661 | 4925 |
| Adventures | 99.87% | 100.00% | 99.73% | 2252 | 2258 |
| Character Creation | 90.54% | 83.13% | 99.41% | 10053 | 8407 |
| Environments and Hazards | 99.67% | 100.00% | 99.34% | 1954 | 1967 |
| Equipment | 98.23% | 98.48% | 97.98% | 11520 | 11579 |
| Off-World Travel | 99.47% | 99.56% | 99.38% | 6395 | 6407 |
| Personal Combat | 99.71% | 99.93% | 99.50% | 6787 | 6816 |
| Planetary Wilderness Encounters | 99.57% | 100.00% | 99.15% | 3025 | 3051 |
| Psionics | 98.92% | 99.26% | 98.58% | 3911 | 3938 |
| Refereeing the Game | 99.91% | 99.94% | 99.88% | 3254 | 3256 |
| Skills | 99.31% | 99.56% | 99.06% | 4571 | 4594 |
| Social Encounters | 99.45% | 99.73% | 99.16% | 2257 | 2270 |
| Space Combat | 99.30% | 99.80% | 98.80% | 5460 | 5515 |
| Starship Encounters | 98.18% | 98.78% | 97.59% | 984 | 996 |
| Worlds | 99.18% | 99.88% | 98.49% | 3467 | 3516 |
| Legal | 99.72% | 99.55% | 99.89% | 1784 | 1778 |
| Common Aircraft | 98.69% | 100.00% | 97.41% | 751 | 771 |
| Common Grav Vehicles | 98.97% | 100.00% | 97.95% | 1819 | 1857 |
| Common Ground Vehicles | 98.90% | 100.00% | 97.82% | 1394 | 1425 |
| Common Vessels | 99.78% | 99.89% | 99.66% | 5639 | 5652 |
| Common Watercraft | 99.15% | 100.00% | 98.31% | 1690 | 1719 |
| Ship Design and Construction | 99.03% | 99.59% | 98.47% | 7153 | 7235 |
| Trade and Commerce | 99.33% | 99.53% | 99.13% | 1481 | 1487 |
| Uncommon Vehicles | 98.43% | 100.00% | 96.90% | 313 | 323 |
| Vehicle Design System | 98.91% | 99.23% | 98.59% | 15599 | 15700 |

## Interpretation

Similarity below 100% does not by itself mean a rules difference. Generated
website tables of contents, headings, link labels, punctuation, and WordPress
presentation produce normalization differences. Every low-scoring page and
every numeric replacement requires manual review before certification.

## Manual Certification Findings

- **Shared rules text:** Concordant. After correcting UTF-8 dash handling,
  23 of 25 pages exceed 98% token similarity; the remaining Introduction
  variance is site navigation/presentation.
- **Character Creation:** Not complete on the website. The rendered page
  includes the Athlete-through-Bureaucrat career tables but omits the
  remaining 18 careers present in the pinned GitHub source (three blocks:
  Colonist-through-Marine, Maritime Defense-through-Physician, and
  Pirate-through-Technician). This is a substantive publication omission.
- **Numbers reviewed:** Remaining numeric replacements in the largest-diff
  audit are typography/rendering differences (for example `TL9`/`TL 9`,
  superscript rendering, and concatenated display text), not detected rule
  value conflicts.
- **Certification:** The two publications agree on content they share, but
  neither is assumed to be the complete corpus. Treat GitHub tag `v9.1`
  and the captured OGN pages as paired governing sources: use either to
  fill an omission in the other, retain record-level provenance, and stop
  for review if a genuine conflict is found. Preserve repository-only
  tools and the updated vehicle table as separately classified material.

## Repository-Only Material

- `src/tools/sector-generator.md`
- `src/tools/sector.js`
- `src/tools/space-encounter-generator.md`
- `src/tools/space-encounter.js`
- `src/tools/roll.js`
- `src/tools/pseudohex.js`
- `src/vds/updated-common-vehicles-table.md`

## Difference Samples

### Introduction

- **insert** — GitHub: ``; Website: `home subpages adventures character creation environments and hazards equipment legal off world travel personal combat planetary wilderness encounters psionics refereeing the game skills social encounters space combat starship encounters worlds welcome to the cepheus engine`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``
- **delete** — GitHub: `3`; Website: ``
- **insert** — GitHub: ``; Website: `table common cepheus engine themes`

### Adventures

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table example weekly event`

### Character Creation

- **insert** — GitHub: ``; Website: `home home`
- **replace** — GitHub: `chapter`; Website: `section`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``

### Environments and Hazards

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table sample diseases`
- **insert** — GitHub: ``; Website: `table extreme temperatures`
- **insert** — GitHub: ``; Website: `table sample poisons`
- **insert** — GitHub: ``; Website: `table`

### Equipment

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table technology level overview`
- **insert** — GitHub: ``; Website: `table common personal armor`
- **insert** — GitHub: ``; Website: `table communications equipment`
- **insert** — GitHub: ``; Website: `table computers by tl`

### Off-World Travel

- **insert** — GitHub: ``; Website: `home home`
- **delete** — GitHub: `center math xmlns http www w3 org 1998 math mathml mi`; Website: ``
- **delete** — GitHub: `mi mo mo mn`; Website: ``
- **replace** — GitHub: `mn msqrt mfrac mi d mi mi a mi mfrac msqrt math center`; Website: `da 2`
- **insert** — GitHub: ``; Website: `table common travel times by acceleration`

### Personal Combat

- **insert** — GitHub: ``; Website: `home home`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``
- **delete** — GitHub: `3`; Website: ``
- **delete** — GitHub: `4`; Website: ``

### Planetary Wilderness Encounters

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table terrain dm chart`
- **insert** — GitHub: ``; Website: `table subtype by animal type`
- **insert** — GitHub: ``; Website: `table`
- **insert** — GitHub: ``; Website: `table`

### Psionics

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table learning dms by talent`
- **insert** — GitHub: ``; Website: `table psionic range costs`
- **insert** — GitHub: ``; Website: `table awareness`
- **insert** — GitHub: ``; Website: `table clairvoyance`

### Refereeing the Game

- **insert** — GitHub: ``; Website: `home home`
- **replace** — GitHub: `chapter`; Website: `section`
- **replace** — GitHub: `revenue`; Website: `revenues`

### Skills

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table time frames`
- **insert** — GitHub: ``; Website: `table base difficulty by law level`
- **insert** — GitHub: ``; Website: `table available skills`
- **replace** — GitHub: `airship`; Website: `grav vehicle`

### Social Encounters

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table encounter types overview`
- **insert** — GitHub: ``; Website: `table random encounters`
- **insert** — GitHub: ``; Website: `table patron encounters`
- **delete** — GitHub: `1`; Website: ``

### Space Combat

- **insert** — GitHub: ``; Website: `home home`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``
- **delete** — GitHub: `3`; Website: ``
- **delete** — GitHub: `4`; Website: ``

### Starship Encounters

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table`
- **replace** — GitHub: `encounter table`; Website: `encounters`
- **insert** — GitHub: ``; Website: `table`
- **replace** — GitHub: `table`; Website: `type`

### Worlds

- **insert** — GitHub: ``; Website: `home home`
- **insert** — GitHub: ``; Website: `table world size`
- **insert** — GitHub: ``; Website: `table atmosphere`
- **insert** — GitHub: ``; Website: `table hydrographic dms by size and atmosphere`
- **insert** — GitHub: ``; Website: `table hydrographics`

### Legal

- **insert** — GitHub: ``; Website: `home home`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``
- **delete** — GitHub: `3`; Website: ``
- **delete** — GitHub: `4`; Website: ``

### Common Aircraft

- **insert** — GitHub: ``; Website: `home home equipment`
- **insert** — GitHub: ``; Website: `table tl5 biplane design specifications`
- **insert** — GitHub: ``; Website: `table tl7 helicopter design specifications`
- **insert** — GitHub: ``; Website: `table tl7 twin engine jet design specifications`

### Common Grav Vehicles

- **insert** — GitHub: ``; Website: `home home equipment`
- **insert** — GitHub: ``; Website: `table tl9 air raft design specifications`
- **insert** — GitHub: ``; Website: `table tl15 g carrier design specifications`
- **insert** — GitHub: ``; Website: `table tl12 grav bike design specifications`
- **insert** — GitHub: ``; Website: `table tl11 grav floater design specifications`

### Common Ground Vehicles

- **insert** — GitHub: ``; Website: `home home equipment`
- **insert** — GitHub: ``; Website: `table tl12 afv tracked design specifications`
- **insert** — GitHub: ``; Website: `table tl12 atv tracked design specifications`
- **insert** — GitHub: ``; Website: `table tl5 ground car design specifications`
- **insert** — GitHub: ``; Website: `table tl3 stagecoach design specifications`

### Common Vessels

- **insert** — GitHub: ``; Website: `home home equipment`
- **replace** — GitHub: `tl9`; Website: `tl 9`
- **insert** — GitHub: ``; Website: `table cutter module options`
- **replace** — GitHub: `tl9`; Website: `tl 9`
- **replace** — GitHub: `tl9`; Website: `tl 9`

### Common Watercraft

- **insert** — GitHub: ``; Website: `home home equipment`
- **insert** — GitHub: ``; Website: `table tl9 destroyer design specifications`
- **insert** — GitHub: ``; Website: `table tl7 hovercraft design specifications`
- **insert** — GitHub: ``; Website: `table tl5 motor boat design specifications`
- **insert** — GitHub: ``; Website: `table tl4 steamship design specifications`

### Ship Design and Construction

- **insert** — GitHub: ``; Website: `home home equipment`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``
- **delete** — GitHub: `2`; Website: ``

### Trade and Commerce

- **insert** — GitHub: ``; Website: `home home equipment`
- **replace** — GitHub: `revenue`; Website: `revenues`
- **delete** — GitHub: `1`; Website: ``
- **delete** — GitHub: `2`; Website: ``
- **delete** — GitHub: `3`; Website: ``

### Uncommon Vehicles

- **insert** — GitHub: ``; Website: `home home equipment`
- **insert** — GitHub: ``; Website: `table tl8 tunnel boring machine design specifications`

### Vehicle Design System

- **insert** — GitHub: ``; Website: `home home equipment`
- **delete** — GitHub: `introduction`; Website: ``
- **insert** — GitHub: ``; Website: `table task difficulty abbreviations`
- **insert** — GitHub: ``; Website: `table`
- **delete** — GitHub: `vehicle design`; Website: ``
