# Base Cepheus Database

PostgreSQL is the authoritative store for released rules and game state.
The schema targets PostgreSQL 15 or newer.

## Migration order

Migrations in `migrations` are forward-only and run in filename order:

1. `0001_system_and_packages.sql`
2. `0002_sources_and_provenance.sql`
3. `0003_rules_characteristics_and_skills.sql`
4. `0004_cepheus_engine_source_manifest.sql`
5. `0005_relationship_provenance.sql`

`tools/migrate.py` runs each unapplied migration in one transaction and records
its version and SHA-256 checksum in `sys_schema_migration`. Migration SQL does
not contain transaction statements or insert its own checksum.

Run:

```powershell
python tools/migrate.py --dsn postgresql://user:password@host/database
```

The DSN may instead be stored in `BASE_CEPHEUS_DATABASE_URL`. It must never be
committed.

## Empty-database bootstrap

An empty database must interleave schema migrations with the reviewed catalogue
importers whose typed rows are dependencies of later migrations. Run:

```powershell
python tools/bootstrap_database.py
```

The command applies migrations through each explicit dependency boundary,
publishes the paired-source catalogues, finishes the remaining migrations, and
runs the database verifier. It refuses to operate if any public table, view,
sequence, or materialized view already exists. `tools/migrate.py --target N`
is the lower-level mechanism used by the bootstrap and remains useful for
diagnosing a particular phase.

## Local development cluster

The development cluster lives in `.postgres-data`, which is excluded from Git.
It uses PostgreSQL 17, SCRAM-SHA-256 authentication, and data checksums. Its DSN
is stored in the Windows user environment as
`BASE_CEPHEUS_DATABASE_URL`.

Start it when needed:

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' start `
  --pgdata '.\.postgres-data' --log '.\.postgres-data\server.log' --wait
```

Stop it cleanly:

```powershell
& 'C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe' stop `
  --pgdata '.\.postgres-data' --mode fast --wait
```

Verify the live foundation:

```powershell
$env:BASE_CEPHEUS_DATABASE_URL =
  [Environment]::GetEnvironmentVariable(
    'BASE_CEPHEUS_DATABASE_URL', 'User'
  )
python tools/verify_database.py
```

The installer-owned `postgresql-x64-17` Windows service is not used by Base
Cepheus. The project-local cluster is started explicitly with `pg_ctl`.

## Foundation rules import

`tools/import_foundation_rules.py` deterministically imports:

- six core characteristics and Psionic Strength;
- twelve characteristic modifier bands;
- sixty-nine defined skills;
- eight cascade skills;
- thirty-six cascade-specialty relationships.

It reads the pinned GitHub v9.1 Markdown and fetches the corresponding OGN
Character Creation, Skills, and Vehicle Design pages. It stops before writing
if shared mechanics disagree. Publication, staging, review, and provenance are
committed in one database transaction.

Run:

```powershell
$env:BASE_CEPHEUS_DATABASE_URL =
  [Environment]::GetEnvironmentVariable(
    'BASE_CEPHEUS_DATABASE_URL', 'User'
  )
python tools/import_foundation_rules.py
python tools/verify_database.py
```

### Adjudicated paired-source omission

GitHub v9.1 lists Airship as an Aircraft cascade specialty. The OGN Skills page
omits Airship from the Aircraft cascade sentence, while the OGN Vehicle Design
page separately defines the Airship skill. Raymond adjudicated GitHub v9.1 as
correct and the OGN Skills-page difference as a publication omission. The
relationship is therefore published from GitHub with `fills_source_gap`
provenance; the Airship skill itself has provenance from both publications.

### Task-resolution vocabulary

Migration `0006_task_resolution.sql` supplies typed storage for the governing
check system, named Difficulty modifiers, and non-overlapping Effect bands.
Natural-roll behavior is explicit rather than hidden in application code.
Partial indexes permit only one default Difficulty, while PostgreSQL exclusion
constraints reject overlapping Effect ranges.

Migration `0007_task_context.sql` extends that vocabulary with task time frames,
pace and circumstance adjustments, and non-overlapping Law Level ranges linked
to canonical Difficulty records. Variable source units such as common months
remain variable; the database does not manufacture exact conversions.

## Authority boundary

Migration `0009_personal_combat_equipment.sql` establishes normalized personal
equipment, armor, weapon damage types, range bands, attack profiles, and
per-range Difficulty mappings. Weapons may have multiple attack modes; printed
range boundaries are preserved without inventing unstated inclusivity.

- Typed PostgreSQL rows are authoritative after review and publication.
- `src_import_candidate.staging_value` is temporary, nonauthoritative JSONB.
- Exports and runtime JSON are projections rebuilt from approved rows.
- Mechanical text columns may not contain long prose. The verifier permits
  long values only in explicitly narrative descriptions, rationales, evidence,
  source values, and audit explanations.
- Purchased books, credentials, databases, and database dumps never belong in
  Git.

## Source policy

The pinned `orffen/cepheus-srd` release and captured OGN pages are paired
governing sources. A record may cite either or both. Source gaps are filled from
the other publication. Genuine conflicts remain unresolved until reviewed.

## Source issue register

Migration `0139_source_issue_register.sql` provides the common relational
workflow for omissions, conflicts, arithmetic disagreements, and unexplained
published totals. Each issue has a stable code, priority, reviewer question,
requested evidence, current engine disposition, and links to its exact source
locator and originating typed record.

Export the current reviewer list after migration and verification:

```powershell
python tools/export_source_issues.py --output CEPHEUS_SOURCE_ISSUES.md
```

The generated Markdown is a convenience projection. The `src_issue` tables
remain authoritative.
