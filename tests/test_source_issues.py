from __future__ import annotations

import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, UniqueViolation


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "BASE_CEPHEUS_DATABASE_URL is not configured",
)
class SourceIssueTests(unittest.TestCase):
    def test_ship_findings_are_closed_but_audit_links_remain(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            counts = connection.execute(
                """SELECT issue_type,count(*)
                   FROM src_open_issue_report
                   WHERE domain_code LIKE 'ship.%'
                   GROUP BY issue_type
                   ORDER BY issue_type"""
            ).fetchall()
            self.assertEqual(counts, [])

            linkage = connection.execute(
                """SELECT
                     (SELECT count(*)
                        FROM src_issue_construction_variance),
                     (SELECT count(*)
                        FROM src_issue_ship_assertion),
                     (SELECT count(*)
                        FROM src_issue_locator locator
                        JOIN src_issue issue USING (source_issue_id)
                       WHERE locator.evidence_role='primary'
                         AND issue.domain_code LIKE 'ship.%'),
                     (SELECT count(*)
                        FROM src_issue_comparison_check comparison
                        JOIN src_issue issue USING (source_issue_id)
                       WHERE comparison.check_status=
                         'no_independent_calculation'
                         AND issue.domain_code LIKE 'ship.%')"""
            ).fetchone()
            self.assertEqual(linkage, (31, 4, 35, 35))

    def test_vehicle_catalogue_conflicts_are_registered(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            issues = connection.execute(
                """SELECT issue_code,published_value,
                          calculated_value,engine_disposition
                   FROM src_issue
                   WHERE domain_code='vehicle.catalogue'
                   ORDER BY issue_code"""
            ).fetchall()
            self.assertEqual(
                issues,
                [
                    (
                        "vehicle.aircraft.environment-tolerance-wording",
                        "Within one code: both proper operation and "
                        "Agility DM -1",
                        "Exact match operates normally; difference of one "
                        "applies DM -1",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.anti-missile.decoy-guidance-label",
                        "DM+2 vs smart missile attacks "
                        "(radar-guided missiles)",
                        "Smart-guided and radar-guided claims "
                        "retained separately",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.armament.heavy-weapon-rof-rounding",
                        "Rate of fire multiplied by 0.5",
                        "Rounding method source-unspecified",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.afv-weapon-points",
                        "One weapon point",
                        "Two weapon points",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.air-raft-construction-arithmetic",
                        "48 spaces; subtotal Cr104,614.5; final "
                        "Cr94,160 or Cr94,340",
                        "42.89 itemized spaces; line subtotal "
                        "Cr104,614.51; discounted Cr94,150",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.basic-life-support-profile-price",
                        "3 spaces at Cr3,500 in each profile",
                        "Cr10,500 normally; Cr0 with Hostile "
                        "Environmental Protection",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.biplane-chassis-code",
                        "One ton and 12 spaces, labelled Code 4",
                        "One ton and 12 spaces require Code 5",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.destroyer-design-table-copy",
                        "Table repeats Twin Engine Jet cargo and totals",
                        "Narrative retains 70.615 tons cargo and "
                        "KCr51,521.940 final cost",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.destroyer-heavy-weapon-labels",
                        "Heavy Mass Driver TL8 and Heavy Rocket "
                        "Artillery TL7",
                        "Mapped to the unique TL8 Mass Driver and TL7 "
                        "Rocket Artillery entries",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.destroyer-used-weapon-points",
                        "23 weapon points used",
                        "22 weapon points reconstructed from listed "
                        "armament",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.g-carrier-autopilot",
                        "Grav Vehicle-2 at Cr2,000",
                        "Grav Vehicle-3 at Cr17,000",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.g-carrier-design-subtotal",
                        "Cr3,487,282.24",
                        "Cr1,518,682.24 itemized",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.grav-tank-autopilot-label",
                        "Prose: level 0; table note: level 1; "
                        "price: Cr2,000",
                        "TL9 ground-vehicle formula: level 0 at Cr2,000",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.grav-tank-subtotal-omits-weapon",
                        "Cr1,632,659.48",
                        "Cr1,732,659.48 including the listed Beam Laser",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.helicopter-final-price",
                        "Cr154,810",
                        "Cr154,850 from the stated subtotal",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.speeder-unitemized-subtotal",
                        "Cr366,957.256",
                        "Cr364,957.256 itemized",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.steamship-cargo-space",
                        "2,400 chassis spaces; 516.6 cargo spaces",
                        "1,991.4 allocated spaces; 408.6 spaces "
                        "remaining for cargo",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.submersible-life-support-tech-level",
                        "TL6 class with TL7 component",
                        "Published component retained as an explicit "
                        "tech-level override",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.tracked-autopilot-price",
                        "Tracked Vehicle-1 at Cr2,000",
                        "Tracked Vehicle-1 at Cr7,000",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.tracked-insidious-protection-price",
                        "Cr50,000 on each 120-space chassis",
                        "Cr6,000,000 on each 120-space chassis",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.class.tunnel-boring-electronics-omission",
                        "No sensor or computer rows in the design table",
                        "Standard sensors plus Model 1 computer: "
                        "3.01 spaces and Cr5,500",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.components.emergency-low-berth-capacity",
                        "Vehicle capacity unspecified",
                        "Four-person survival capacity",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.components.folding-wings-summary-omission",
                        "No summary-table row",
                        "Prose rule retained",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.components.wet-bar-table",
                        'Table: 1 Space; "5 Cr2,000"',
                        "Prose: 1.5 Spaces; Cr2,000",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.configuration.open-frame-copy-error",
                        "Open Frame heading; Open Cargo Bed conditions",
                        "Open Frame uses the parallel aircraft prohibition "
                        "and combined 25% reduction",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.configuration.submersible-ballast-rounding",
                        "Half remaining spaces, rounded off",
                        "Rounding method source-unspecified",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.controls.primitive-tech-level",
                        "Prose TL2; table TL1",
                        "TL1 table value",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.missile.nas-radiation-hit",
                        "Nuclear missiles: 1 radiation hit; "
                        "NAS row: 13D6",
                        "Published table row retains zero radiation hits",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.ordnance.heavy-nuclear-torpedo-row",
                        "Range: ranged (v; Damage: 28D6 + 2D6x10",
                        "Range and radiation unit source-malformed",
                        "preserve_rule",
                    ),
                    (
                        "vehicle.sensors.standard-range-distance",
                        "Very Long (500 km)",
                        "Very Long (500 m)",
                        "preserve_rule",
                    ),
                ],
            )

    def test_high_priority_questions_are_specific(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            questions = connection.execute(
                """SELECT issue_code,reviewer_question
                   FROM src_open_issue_report
                   WHERE review_priority='high'
                     AND domain_code LIKE 'ship.%'
                   ORDER BY issue_code"""
            ).fetchall()
            self.assertEqual(questions, [])

    def test_issue_resolution_requires_an_audit_summary(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            with connection.transaction(force_rollback=True):
                with self.assertRaises(CheckViolation):
                    connection.execute(
                        """UPDATE src_issue
                           SET resolution_summary=NULL
                           WHERE issue_code=
                             'ship.corvette.construction.cost'"""
                    )

    def test_each_finding_has_only_one_primary_locator(self) -> None:
        with psycopg.connect(
            os.environ["BASE_CEPHEUS_DATABASE_URL"]
        ) as connection:
            issue_id, locator_id = connection.execute(
                """SELECT source_issue_id,source_locator_id
                   FROM src_issue_locator
                   WHERE evidence_role='primary'
                   LIMIT 1"""
            ).fetchone()
            with connection.transaction(force_rollback=True):
                with self.assertRaises(UniqueViolation):
                    connection.execute(
                        """INSERT INTO src_issue_locator (
                               source_issue_id,source_locator_id,evidence_role
                           )
                           VALUES (%s,%s,'primary')""",
                        (issue_id, locator_id + 1),
                    )


if __name__ == "__main__":
    unittest.main()
