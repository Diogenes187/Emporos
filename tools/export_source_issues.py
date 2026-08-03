"""Export the relational source-issue register as a reviewer-ready Markdown list."""

from __future__ import annotations

import argparse
import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg


def markdown_cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        value = format(value.normalize(), "f")
    return str(value).replace("|", r"\|").replace("\n", " ")


def build_report(connection: psycopg.Connection) -> str:
    rows = connection.execute(
        """SELECT issue_code,review_priority,issue_type,title,
                  published_value,calculated_value,
                  difference_value,value_unit,reviewer_question,
                  requested_evidence,engine_disposition,
                  display_citation
           FROM src_open_issue_report
           ORDER BY
             CASE review_priority
               WHEN 'high' THEN 1
               WHEN 'medium' THEN 2
               ELSE 3
             END,
             issue_code"""
    ).fetchall()

    totals = connection.execute(
        """SELECT review_priority,count(*)
           FROM src_open_issue_report
           GROUP BY review_priority"""
    ).fetchall()
    summary = dict(totals)
    comparison_totals = dict(
        connection.execute(
            """SELECT check_status,count(*)
               FROM src_issue_comparison_check
               GROUP BY check_status"""
        ).fetchall()
    )

    lines = [
        "# Cepheus Source Issues",
        "",
        "Generated from the relational `src_issue` register. Open findings are "
        "questions, not silent corrections; published values remain preserved "
        "until evidence resolves them.",
        "",
        "## Summary",
        "",
        f"- High priority: {summary.get('high', 0)}",
        f"- Medium priority: {summary.get('medium', 0)}",
        f"- Low priority: {summary.get('low', 0)}",
        f"- Total open findings: {len(rows)}",
        "- Legacy implementation checks with no independent calculation: "
        f"{comparison_totals.get('no_independent_calculation', 0)}",
        "",
        "The legacy Cepheus game was checked as nonauthoritative comparison "
        "evidence. Its ship parser uses the published summary values directly, "
        "and it has neither an independent ship component worksheet nor a "
        "vehicle construction subsystem capable of adjudicating these "
        "findings.",
        "",
    ]

    for priority in ("high", "medium", "low"):
        selected = [row for row in rows if row[1] == priority]
        if not selected:
            continue
        lines.extend(
            [
                f"## {priority.title()} priority",
                "",
                "| Issue | Type | Published | Calculated | Difference | "
                "Question |",
                "|---|---|---:|---:|---:|---|",
            ]
        )
        for row in selected:
            (
                issue_code,
                _,
                issue_type,
                _title,
                published,
                calculated,
                difference,
                unit,
                question,
                _evidence,
                _disposition,
                _citation,
            ) = row
            difference_text = (
                "-"
                if difference is None
                else f"{markdown_cell(difference)} {unit}"
            )
            lines.append(
                "| "
                + " | ".join(
                    markdown_cell(value)
                    for value in (
                        issue_code,
                        issue_type,
                        published,
                        calculated,
                        difference_text,
                        question,
                    )
                )
                + " |"
            )
        lines.append("")

        lines.extend(["### Evidence requested", ""])
        for row in selected:
            lines.extend(
                [
                    f"- `{row[0]}` — {row[9]}",
                    f"  Citation: {row[11]}",
                    f"  Current disposition: `{row[10]}`.",
                ]
            )
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")

    with psycopg.connect(dsn) as connection:
        report = build_report(connection)

    if args.output:
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        sys.stdout.write(report + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
