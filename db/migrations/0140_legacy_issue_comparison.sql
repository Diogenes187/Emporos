INSERT INTO src_work (
    work_code,title,edition,classification,source_revision,notes
)
VALUES (
    'cepheus-game.legacy-local',
    'Legacy Cepheus Game Implementation',
    'Local reference implementation',
    'repository',
    'fa849d9540b02e915cb55696c1764da9388a86f5',
    'Nonauthoritative predecessor inspected for working behavior and prior adjudications; never used to override a governing publication.'
);

INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    media_type,local_role
)
SELECT work.source_work_id,'repository_file',source.source_uri,
       work.source_revision,source.media_type,'comparison'
FROM src_work work
CROSS JOIN (
    VALUES
        ('engine/ships.py','text/x-python'),
        ('scripts/parse_ships.py','text/x-python'),
        ('engine/data/ships.json','application/json')
) source(source_uri,media_type)
WHERE work.work_code='cepheus-game.legacy-local';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'repository_path',artifact.source_uri,
       'Legacy Cepheus @ fa849d9: '||artifact.source_uri
FROM src_artifact artifact
JOIN src_work work USING (source_work_id)
WHERE work.work_code='cepheus-game.legacy-local';

CREATE TABLE src_issue_comparison_check (
    source_issue_id bigint NOT NULL REFERENCES
        src_issue(source_issue_id),
    comparison_work_id bigint NOT NULL REFERENCES
        src_work(source_work_id),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    check_status text NOT NULL CHECK (
        check_status IN (
            'supports_published_usage','no_independent_calculation',
            'potential_resolution','contradicts'
        )
    ),
    evidence_summary text NOT NULL CHECK (btrim(evidence_summary)<>''),
    checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (source_issue_id,comparison_work_id)
);

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor parses the Common Vessels prose into summary fields and uses the published hull, performance, cargo, and final price directly. It has no component construction worksheet and contains no independent smelter, drive, armor, probe-drone, tonnage, or price adjudication.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='scripts/parse_ships.py'
WHERE issue.issue_status IN ('open','investigating');

