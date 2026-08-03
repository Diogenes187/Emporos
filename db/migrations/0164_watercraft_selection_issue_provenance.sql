INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=CASE
      WHEN issue.issue_code=
           'vehicle.class.submersible-life-support-tech-level'
          THEN 'Common Watercraft > TL6 Submersible'
      ELSE 'Common Watercraft > TL9 Destroyer'
  END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code IN (
    'vehicle.class.submersible-life-support-tech-level',
    'vehicle.class.destroyer-used-weapon-points',
    'vehicle.class.destroyer-heavy-weapon-labels'
);

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       CASE
           WHEN issue.issue_code=
                'vehicle.class.submersible-life-support-tech-level'
               THEN 'The predecessor retains the same TL6 Submersible and TL7 Extended Life Support text but has no vehicle-construction technology validator.'
           WHEN issue.issue_code=
                'vehicle.class.destroyer-used-weapon-points'
               THEN 'The predecessor retains the same Destroyer prose but has no vehicle weapon-point calculator or independent armament reconstruction.'
           ELSE
               'The predecessor retains the same Heavy weapon labels but has no independent weapon catalogue or variant adjudication.'
       END
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=
     'reference/srd/src/vds/common-watercraft.md'
WHERE issue.issue_code IN (
    'vehicle.class.submersible-life-support-tech-level',
    'vehicle.class.destroyer-used-weapon-points',
    'vehicle.class.destroyer-heavy-weapon-labels'
);
