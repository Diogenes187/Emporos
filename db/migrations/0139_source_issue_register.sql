CREATE TABLE src_issue (
    source_issue_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    issue_code text NOT NULL UNIQUE CHECK (
        issue_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    domain_code text NOT NULL CHECK (
        domain_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    issue_type text NOT NULL CHECK (
        issue_type IN (
            'source_omission','source_conflict','tech_level_conflict',
            'arithmetic_conflict','published_total_variance',
            'source_gap_variance'
        )
    ),
    review_priority text NOT NULL CHECK (
        review_priority IN ('high','medium','low')
    ),
    issue_status text NOT NULL DEFAULT 'open' CHECK (
        issue_status IN (
            'open','investigating','resolved','accepted_as_published',
            'not_errata'
        )
    ),
    subject_code text NOT NULL CHECK (btrim(subject_code)<>''),
    title text NOT NULL CHECK (btrim(title)<>''),
    problem_statement text NOT NULL CHECK (btrim(problem_statement)<>''),
    published_value text,
    calculated_value text,
    difference_value numeric,
    value_unit text,
    reviewer_question text NOT NULL CHECK (btrim(reviewer_question)<>''),
    requested_evidence text NOT NULL CHECK (btrim(requested_evidence)<>''),
    engine_disposition text NOT NULL CHECK (
        engine_disposition IN (
            'preserve_published','preserve_rule','source_gap_pending'
        )
    ),
    opened_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at timestamptz,
    resolution_summary text,
    CHECK (
        (issue_status IN ('open','investigating')
         AND resolved_at IS NULL
         AND resolution_summary IS NULL)
        OR
        (issue_status IN (
             'resolved','accepted_as_published','not_errata'
         )
         AND resolved_at IS NOT NULL
         AND btrim(COALESCE(resolution_summary,''))<>'')
    ),
    CHECK (
        (difference_value IS NULL AND value_unit IS NULL)
        OR
        (difference_value IS NOT NULL
         AND btrim(COALESCE(value_unit,''))<>'')
    )
);

CREATE TABLE src_issue_locator (
    source_issue_id bigint NOT NULL REFERENCES
        src_issue(source_issue_id),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    evidence_role text NOT NULL CHECK (
        evidence_role IN (
            'primary','corroborating','conflicting','resolution'
        )
    ),
    PRIMARY KEY (source_issue_id,source_locator_id,evidence_role)
);

CREATE UNIQUE INDEX src_issue_one_primary_locator
    ON src_issue_locator(source_issue_id)
    WHERE evidence_role='primary';

CREATE TABLE src_issue_construction_variance (
    source_issue_id bigint PRIMARY KEY REFERENCES
        src_issue(source_issue_id),
    construction_variance_id bigint NOT NULL UNIQUE REFERENCES
        ship_class_construction_variance(construction_variance_id)
);

CREATE TABLE src_issue_ship_assertion (
    source_issue_id bigint PRIMARY KEY REFERENCES
        src_issue(source_issue_id),
    ship_class_rule_id bigint NOT NULL,
    field_code text NOT NULL,
    UNIQUE (ship_class_rule_id,field_code),
    FOREIGN KEY (ship_class_rule_id,field_code)
        REFERENCES ship_class_source_assertion(
            ship_class_rule_id,field_code
        )
);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,difference_value,value_unit,
    reviewer_question,requested_evidence,engine_disposition
)
SELECT 'ship.'||class.class_code||'.construction.'||
           variance.variance_dimension,
       'ship.construction',
       CASE
           WHEN variance.audit_status='source_gap'
               THEN 'source_gap_variance'
           WHEN variance.audit_status='rule_conflict'
               THEN 'arithmetic_conflict'
           ELSE 'published_total_variance'
       END,
       CASE
           WHEN variance.audit_status='source_gap' THEN 'high'
           WHEN variance.variance_dimension='tonnage' THEN 'medium'
           ELSE 'low'
       END,
       class.class_code,
       rule.name||' construction '||
           variance.variance_dimension||' discrepancy',
       variance.explanation,
       CASE variance.variance_dimension
           WHEN 'tonnage' THEN total.hull_tons::text||' tons'
           ELSE total.published_cost_minor::text||' credits'
       END,
       CASE variance.variance_dimension
           WHEN 'tonnage' THEN total.allocated_tons::text||' tons'
           ELSE total.calculated_cost_minor::text||' credits'
       END,
       variance.variance_amount,
       CASE variance.variance_dimension
           WHEN 'tonnage' THEN 'tons'
           ELSE 'credits'
       END,
       CASE
           WHEN variance.explanation_code='capped-armor-proration' THEN
               'Is the common design intentionally prorating the final capped armor increment, or is its cargo figure in error?'
           WHEN variance.explanation_code='source-unspecified' THEN
               'Does another authorized Cepheus source specify the omitted component or correct the published design total?'
           ELSE
               'Can an itemized worksheet, errata notice, or corrected printing account for this difference?'
       END,
       CASE
           WHEN variance.variance_dimension='tonnage' THEN
               'A component-by-component tonnage worksheet, corrected cargo value, or published errata.'
           ELSE
               'A component-by-component price worksheet, stated fee or discount, corrected total, or published errata.'
       END,
       CASE
           WHEN variance.audit_status='rule_conflict'
               THEN 'preserve_rule'
           WHEN variance.audit_status='source_gap'
               THEN 'source_gap_pending'
           ELSE 'preserve_published'
       END
FROM ship_class_construction_variance variance
JOIN ship_class_construction_total total USING (
    construction_receipt_id
)
JOIN ship_class class USING (ship_class_rule_id)
JOIN rule_rule rule
  ON rule.rule_id=class.ship_class_rule_id;

INSERT INTO src_issue_construction_variance (
    source_issue_id,construction_variance_id
)
SELECT issue.source_issue_id,variance.construction_variance_id
FROM ship_class_construction_variance variance
JOIN ship_class_construction_total total USING (
    construction_receipt_id
)
JOIN ship_class class USING (ship_class_rule_id)
JOIN src_issue issue
  ON issue.issue_code='ship.'||class.class_code||
     '.construction.'||variance.variance_dimension;

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,variance.source_locator_id,'primary'
FROM src_issue_construction_variance link
JOIN src_issue issue USING (source_issue_id)
JOIN ship_class_construction_variance variance USING (
    construction_variance_id
);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
SELECT 'ship.'||class.class_code||'.source.'||assertion.field_code,
       'ship.catalogue',
       CASE
           WHEN assertion.field_code='smelter-specification'
               THEN 'source_omission'
           WHEN assertion.field_code='probe-drone-tech-level'
               THEN 'tech_level_conflict'
           ELSE 'source_conflict'
       END,
       'high',class.class_code,
       rule.name||': '||
           replace(assertion.field_code,'-',' '),
       assertion.rationale,assertion.published_value,
       assertion.canonical_value,
       CASE assertion.field_code
           WHEN 'smelter-specification' THEN
               'What tonnage, price, capacity, and construction rule should the published smelter use?'
           WHEN 'probe-drone-tech-level' THEN
               'Is the Research Vessel tech level, the Probe Drone tech level, or their inclusion in the design incorrect?'
           WHEN 'jump-drive-performance' THEN
               'Should the Destroyer mount a different jump drive, have Jump-1 performance, or use a different hull tonnage?'
           WHEN 'maneuver-drive-performance' THEN
               'Should the Destroyer mount a different maneuver drive, have 3-G performance, or use a different hull tonnage?'
       END,
       'A corrected printing, publisher errata, or a corroborating authorized source with explicit replacement values.',
       'source_gap_pending'
FROM ship_class_source_assertion assertion
JOIN ship_class class USING (ship_class_rule_id)
JOIN rule_rule rule
  ON rule.rule_id=class.ship_class_rule_id
WHERE assertion.assertion_status IN (
    'unresolved_conflict','source_unspecified'
);

INSERT INTO src_issue_ship_assertion (
    source_issue_id,ship_class_rule_id,field_code
)
SELECT issue.source_issue_id,assertion.ship_class_rule_id,
       assertion.field_code
FROM ship_class_source_assertion assertion
JOIN ship_class class USING (ship_class_rule_id)
JOIN src_issue issue
  ON issue.issue_code='ship.'||class.class_code||
     '.source.'||assertion.field_code
WHERE assertion.assertion_status IN (
    'unresolved_conflict','source_unspecified'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,assertion.source_locator_id,'primary'
FROM src_issue_ship_assertion link
JOIN src_issue issue USING (source_issue_id)
JOIN ship_class_source_assertion assertion USING (
    ship_class_rule_id,field_code
);

CREATE VIEW src_open_issue_report AS
SELECT issue.issue_code,issue.domain_code,issue.issue_type,
       issue.review_priority,issue.issue_status,
       issue.subject_code,issue.title,issue.problem_statement,
       issue.published_value,issue.calculated_value,
       issue.difference_value,issue.value_unit,
       issue.reviewer_question,issue.requested_evidence,
       issue.engine_disposition,locator.display_citation
FROM src_issue issue
JOIN src_issue_locator link
  ON link.source_issue_id=issue.source_issue_id
 AND link.evidence_role='primary'
JOIN src_locator locator USING (source_locator_id)
WHERE issue.issue_status IN ('open','investigating');
