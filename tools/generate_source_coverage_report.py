"""Generate the reproducible Cepheus source-coverage report."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "CEPHEUS_SOURCE_COVERAGE.md"


def markdown_cell(value: object) -> str:
    return str(value).replace("|", r"\|").replace("\n", " ")


def build_report(connection: psycopg.Connection) -> str:
    migration = connection.execute(
        "SELECT max(version) FROM sys_schema_migration"
    ).fetchone()[0]
    works = connection.execute(
        """SELECT work.work_code,work.classification,work.local_role
             FROM (
               SELECT source_work_id,work_code,classification,
                      CASE work_code
                        WHEN 'cepheus-engine.ogn' THEN 'governing'
                        WHEN 'cepheus-engine.github-v9.1' THEN 'verification'
                        ELSE 'comparison'
                      END AS local_role
                 FROM src_work
             ) work
            ORDER BY CASE work.local_role
                       WHEN 'governing' THEN 1
                       WHEN 'verification' THEN 2
                       ELSE 3
                     END,work.work_code"""
    ).fetchall()
    coverage = connection.execute(
        """WITH per_rule AS (
               SELECT rule.rule_id,rule.rule_category,
                      bool_or(work.classification='website') AS has_website,
                      bool_or(work.work_code='cepheus-engine.github-v9.1')
                        AS has_pinned_repository,
                      bool_or(provenance.provenance_class='fills_source_gap')
                        AS fills_source_gap
                 FROM rule_rule rule
                 LEFT JOIN src_record_provenance provenance
                   ON provenance.rule_id=rule.rule_id
                 LEFT JOIN src_locator locator
                   ON locator.source_locator_id=provenance.source_locator_id
                 LEFT JOIN src_work work
                   ON work.source_work_id=locator.source_work_id
                GROUP BY rule.rule_id,rule.rule_category
             )
             SELECT rule_category,count(*),
                    count(*) FILTER (
                      WHERE COALESCE(has_website,false)
                        AND COALESCE(has_pinned_repository,false)
                        AND NOT COALESCE(fills_source_gap,false)),
                    count(*) FILTER (
                      WHERE COALESCE(fills_source_gap,false)),
                    count(*) FILTER (
                      WHERE NOT COALESCE(has_website,false)
                        AND NOT COALESCE(has_pinned_repository,false)
                        AND NOT COALESCE(fills_source_gap,false))
               FROM per_rule
              GROUP BY rule_category
              ORDER BY rule_category"""
    ).fetchall()
    issues = connection.execute(
        """SELECT domain_code,review_priority,count(*)
             FROM src_issue
            WHERE issue_status IN ('open','investigating')
            GROUP BY domain_code,review_priority
            ORDER BY domain_code,
                     CASE review_priority WHEN 'high' THEN 1
                       WHEN 'medium' THEN 2 ELSE 3 END"""
    ).fetchall()

    totals = tuple(sum(row[index] for row in coverage) for index in range(1, 5))
    issue_total = sum(row[2] for row in issues)
    lines = [
        "# Cepheus Source Coverage",
        "",
        "This report is generated from the canonical relational source manifest, "
        "rule provenance, and source-issue register. Run "
        "`python tools/generate_source_coverage_report.py --output "
        "CEPHEUS_SOURCE_COVERAGE.md` to regenerate it.",
        "",
        "## Classification",
        "",
        "- **Covered**: a normalized rule has citations to both the governing OGN "
        "website and the pinned GitHub v9.1 repository.",
        "- **Partial — source gap**: a normalized rule intentionally relies on one "
        "source and is marked `fills_source_gap`.",
        "- **Partial — unlinked**: a normalized rule exists but has no individual "
        "citation to either member of the paired source set.",
        "- **Open**: a concrete discrepancy or evidence question remains active in "
        "`src_issue`; open questions do not erase or silently change published data.",
        "",
        "These labels measure provenance coverage, not whether every Cepheus "
        "procedure has already been implemented.",
        "",
        "## Snapshot",
        "",
        f"- Latest schema migration: {migration:04d}",
        f"- Normalized rules: {totals[0]}",
        f"- Covered by paired sources: {totals[1]}",
        f"- Partial — explicit source gap: {totals[2]}",
        f"- Partial — not individually linked: {totals[3]}",
        f"- Open source questions: {issue_total}",
        "",
        "## Source manifest",
        "",
        "| Work | Role | Classification |",
        "|---|---|---|",
    ]
    for work_code, classification, role in works:
        lines.append(
            f"| `{markdown_cell(work_code)}` | {role} | {classification} |"
        )
    lines.extend([
        "",
        "The legacy local implementation is comparison-only and never governs a "
        "mechanical decision. Artifact and locator inventory counts are omitted "
        "because they retain ingestion history and can legitimately differ between "
        "a long-lived database and a clean rebuild.",
        "",
        "## Rule provenance by domain",
        "",
        "| Domain | Rules | Covered | Source gap | Unlinked | Status |",
        "|---|---:|---:|---:|---:|---|",
    ])
    for category, total, paired, source_gap, unlinked in coverage:
        status = "covered" if paired == total else "partial"
        lines.append(
            f"| {markdown_cell(category)} | {total} | {paired} | {source_gap} | "
            f"{unlinked} | **{status}** |"
        )
    lines.extend([
        f"| **Total** | **{totals[0]}** | **{totals[1]}** | "
        f"**{totals[2]}** | **{totals[3]}** | **partial** |",
        "",
        "## Open source questions",
        "",
        "| Domain | Priority | Open |",
        "|---|---|---:|",
    ])
    for domain, priority, count in issues:
        lines.append(f"| `{domain}` | {priority} | {count} |")
    lines.extend([
        f"| **Total** |  | **{issue_total}** |",
        "",
        "Question-level evidence and reviewer prompts are in "
        "[CEPHEUS_SOURCE_ISSUES.md](CEPHEUS_SOURCE_ISSUES.md). Source-text "
        "differences are in "
        "[CEPHEUS_CONCORDANCE_REPORT.md](CEPHEUS_CONCORDANCE_REPORT.md).",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    output = args.output or DEFAULT_OUTPUT
    with psycopg.connect(dsn) as connection:
        report = build_report(connection)
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != report:
            sys.stderr.write(f"source coverage report is stale: {output}\n")
            return 1
    elif args.output:
        output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
