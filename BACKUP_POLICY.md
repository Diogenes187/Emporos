# Base Cepheus Backup and Recovery Policy

## Purpose

Protect Base Cepheus work without publishing purchased material, credentials,
player data, or mutable production databases. Git history is one recovery
layer; it is not the complete backup system.

## The Three Copies

1. **Working copy** — `C:\Users\Raymond\Documents\baseCepheus`
2. **Private GitHub repository** — source code, migrations, tests, planning
   records, provenance manifests, and approved open rules data
3. **Encrypted independent backup** — purchased books, database backups,
   deployment configuration, and a mirror/bundle of the Git repository

The independent backup must not rely on GitHub credentials or the working
computer. At least one copy should be offline or version-retained by a separate
storage provider.

## What Goes to GitHub

- application and engine source;
- database migrations and deterministic seed/import code;
- tests and fixtures containing no personal or secret data;
- planning and architectural decisions;
- source manifests, URLs, versions, checksums, and ingestion audit reports;
- open rules content only after its license and provenance are recorded;
- documentation and deployment templates without credentials.

## What Never Goes to GitHub

- purchased Cepheus Universal books and supplied PDFs/images;
- `.env` files, API keys, tokens, private keys, or passwords;
- production databases or player/campaign data;
- raw database dumps;
- unreviewed copyrighted setting material;
- temporary extraction directories and generated caches.

These exclusions apply even while the GitHub repository is private.

## Upstream Cepheus SRD

The local `sources/cepheus-srd` checkout is reproducible and is not nested in
the Base Cepheus repository. Its governing revision is:

- repository: `https://github.com/orffen/cepheus-srd`
- tag: `v9.1`
- commit: `0839018902355215fb8148f0b4ce1b1f8e011080`

Our concordance report, captured website evidence, checksums, and record-level
provenance establish which GitHub/OGN source supplied each imported record.

## Commit and Push Practice

Codex will normally:

1. inspect the diff and verify no excluded or secret material is staged;
2. run checks appropriate to the change;
3. make a coherent checkpoint commit after an approved unit of work;
4. push the checkpoint to the private GitHub repository;
5. report the commit identifier and any uncommitted work.

Do not create a commit merely to hide an unfinished or failing state. Large
mechanical imports receive their own commit, separate from schema or engine
changes.

## Branches and Recovery Points

- `main` is recoverable and should pass the current verification suite.
- Material work may use short-lived branches.
- Before risky migrations, large imports, or releases, create an annotated
  recovery tag.
- Releases use immutable version tags after verification.
- Force-pushing shared or recovery branches is prohibited.

## Database Backup

PostgreSQL requires backups independent of Git:

- before every destructive or structural migration;
- daily while actively developing against valuable campaign data;
- immediately before a production deployment;
- with periodic restore tests into a disposable database.

Backups are encrypted, dated, checksummed, and retained outside the application
repository. A backup is not considered proven until a restore test succeeds.

Suggested retention once production data exists:

- 7 daily backups;
- 5 weekly backups;
- 12 monthly backups;
- release and pre-migration backups retained for the life of the release.

## Purchased Books

The `books` directory receives an encrypted independent backup. Its filenames,
purchase/source notes, and cryptographic checksums may be recorded in the
private project, but the files themselves are excluded.

## Verification Cadence

- Every push: secret/exclusion review and ordinary project checks.
- Monthly: confirm GitHub can be cloned into a clean temporary location.
- Quarterly: restore the latest database backup and verify its checksum.
- At releases: create a Git bundle or repository mirror in independent storage.

## Incident Rule

If credentials or restricted material are committed, stop pushing immediately.
Rotate exposed credentials first, preserve evidence, then remove the material
from history using a reviewed procedure. Deleting the latest file alone is not
sufficient because Git retains history.

