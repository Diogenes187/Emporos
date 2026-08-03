# Cepheus Source Coverage

This report is generated from the canonical relational source manifest, rule provenance, and source-issue register. Run `python tools/generate_source_coverage_report.py --output CEPHEUS_SOURCE_COVERAGE.md` to regenerate it.

## Classification

- **Covered**: a normalized rule has citations to both the governing OGN website and the pinned GitHub v9.1 repository.
- **Partial — source gap**: a normalized rule intentionally relies on one source and is marked `fills_source_gap`.
- **Partial — unlinked**: a normalized rule exists but has no individual citation to either member of the paired source set.
- **Open**: a concrete discrepancy or evidence question remains active in `src_issue`; open questions do not erase or silently change published data.

These labels measure provenance coverage, not whether every Cepheus procedure has already been implemented.

## Snapshot

- Latest schema migration: 0544
- Normalized rules: 1086
- Covered by paired sources: 1061
- Partial — explicit source gap: 25
- Partial — not individually linked: 0
- Open source questions: 0

## Source manifest

| Work | Role | Classification |
|---|---|---|
| `cepheus-engine.ogn` | governing | website |
| `cepheus-engine.github-v9.1` | verification | repository |
| `cepheus-game.legacy-local` | comparison | repository |

The legacy local implementation is comparison-only and never governs a mechanical decision. Artifact and locator inventory counts are omitted because they retain ingestion history and can legitimately differ between a long-lived database and a clean rebuild.

## Rule provenance by domain

| Domain | Rules | Covered | Source gap | Unlinked | Status |
|---|---:|---:|---:|---:|---|
| career | 25 | 25 | 0 | 0 | **covered** |
| characteristic | 7 | 7 | 0 | 0 | **covered** |
| combat | 126 | 126 | 0 | 0 | **covered** |
| difficulty | 7 | 7 | 0 | 0 | **covered** |
| encounter | 50 | 50 | 0 | 0 | **covered** |
| equipment | 197 | 197 | 0 | 0 | **covered** |
| other | 12 | 12 | 0 | 0 | **covered** |
| psionics | 42 | 42 | 0 | 0 | **covered** |
| ship | 66 | 41 | 25 | 0 | **partial** |
| skill | 103 | 103 | 0 | 0 | **covered** |
| species | 6 | 6 | 0 | 0 | **covered** |
| species_trait | 33 | 33 | 0 | 0 | **covered** |
| task | 18 | 18 | 0 | 0 | **covered** |
| trade | 45 | 45 | 0 | 0 | **covered** |
| travel | 3 | 3 | 0 | 0 | **covered** |
| vehicle | 320 | 320 | 0 | 0 | **covered** |
| world | 26 | 26 | 0 | 0 | **covered** |
| **Total** | **1086** | **1061** | **25** | **0** | **partial** |

## Open source questions

| Domain | Priority | Open |
|---|---|---:|
| **Total** |  | **0** |

Question-level evidence and reviewer prompts are in [CEPHEUS_SOURCE_ISSUES.md](CEPHEUS_SOURCE_ISSUES.md). Source-text differences are in [CEPHEUS_CONCORDANCE_REPORT.md](CEPHEUS_CONCORDANCE_REPORT.md).
