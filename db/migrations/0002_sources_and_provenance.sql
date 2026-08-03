CREATE TABLE src_work (
    source_work_id      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    work_code           text NOT NULL UNIQUE CHECK (
                            work_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
                        ),
    title               text NOT NULL CHECK (btrim(title) <> ''),
    edition             text,
    publisher           text,
    publication_date    date,
    classification      text NOT NULL CHECK (
                            classification IN (
                                'open_rules', 'purchased_rules',
                                'website', 'repository', 'supplement',
                                'implementation_decision'
                            )
                        ),
    canonical_url       text,
    source_revision     text,
    notes               text,
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE src_license (
    source_license_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    license_code        text NOT NULL UNIQUE CHECK (
                            license_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
                        ),
    name                text NOT NULL CHECK (btrim(name) <> ''),
    version             text,
    reference_url       text,
    obligations         text,
    notes               text
);

CREATE TABLE src_work_license (
    source_work_license_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_work_id      bigint NOT NULL
                        REFERENCES src_work(source_work_id),
    source_license_id   bigint NOT NULL
                        REFERENCES src_license(source_license_id),
    scope_description   text NOT NULL CHECK (btrim(scope_description) <> ''),
    effective_from      date,
    reviewed_at         timestamptz,
    reviewed_by         text,
    UNIQUE (source_work_id, source_license_id, scope_description)
);

CREATE TABLE src_work_relation (
    source_work_relation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    left_work_id        bigint NOT NULL REFERENCES src_work(source_work_id),
    right_work_id       bigint NOT NULL REFERENCES src_work(source_work_id),
    relation_type       text NOT NULL CHECK (
                            relation_type IN (
                                'paired_publication', 'renders',
                                'derived_from', 'supersedes', 'supplements'
                            )
                        ),
    decision_status     text NOT NULL DEFAULT 'reviewed' CHECK (
                            decision_status IN ('proposed', 'reviewed', 'rejected')
                        ),
    rationale           text NOT NULL CHECK (btrim(rationale) <> ''),
    decided_at          timestamptz,
    decided_by          text,
    UNIQUE (left_work_id, right_work_id, relation_type),
    CHECK (left_work_id <> right_work_id)
);

CREATE TABLE src_artifact (
    source_artifact_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    source_work_id      bigint NOT NULL REFERENCES src_work(source_work_id),
    artifact_kind       text NOT NULL CHECK (
                            artifact_kind IN (
                                'repository_file', 'repository_snapshot',
                                'web_page', 'document', 'pdf', 'image'
                            )
                        ),
    source_uri          text NOT NULL CHECK (btrim(source_uri) <> ''),
    source_revision     text,
    captured_at         timestamptz,
    byte_length         bigint CHECK (byte_length IS NULL OR byte_length >= 0),
    checksum_sha256     text CHECK (
                            checksum_sha256 IS NULL
                            OR checksum_sha256 ~ '^[0-9a-f]{64}$'
                        ),
    media_type          text,
    local_role          text NOT NULL CHECK (
                            local_role IN (
                                'governing', 'verification', 'comparison',
                                'licensed_reference'
                            )
                        ),
    UNIQUE NULLS NOT DISTINCT (
        source_work_id, source_uri, source_revision, checksum_sha256
    ),
    UNIQUE (source_artifact_id, source_work_id)
);

CREATE TABLE src_locator (
    source_locator_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    source_work_id      bigint NOT NULL REFERENCES src_work(source_work_id),
    source_artifact_id  bigint,
    locator_type        text NOT NULL CHECK (
                            locator_type IN (
                                'work', 'heading', 'paragraph', 'table',
                                'table_row', 'page', 'repository_path',
                                'decision_entry'
                            )
                        ),
    heading_path        text,
    printed_page        integer CHECK (printed_page IS NULL OR printed_page > 0),
    anchor              text,
    display_citation    text NOT NULL CHECK (btrim(display_citation) <> ''),
    source_order        integer CHECK (source_order IS NULL OR source_order >= 0),
    UNIQUE NULLS NOT DISTINCT (
        source_work_id, source_artifact_id, locator_type,
        heading_path, printed_page, anchor
    ),
    UNIQUE (source_locator_id, source_artifact_id),
    FOREIGN KEY (source_artifact_id, source_work_id)
        REFERENCES src_artifact(source_artifact_id, source_work_id)
);

CREATE TABLE src_import_batch (
    import_batch_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    content_package_id  bigint NOT NULL
                        REFERENCES sys_content_package(content_package_id),
    source_artifact_id  bigint NOT NULL
                        REFERENCES src_artifact(source_artifact_id),
    importer_name       text NOT NULL CHECK (btrim(importer_name) <> ''),
    importer_version    text NOT NULL CHECK (btrim(importer_version) <> ''),
    source_checksum_sha256 text NOT NULL
                        CHECK (source_checksum_sha256 ~ '^[0-9a-f]{64}$'),
    started_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at        timestamptz,
    batch_status        text NOT NULL DEFAULT 'running' CHECK (
                            batch_status IN (
                                'running', 'extracted', 'validated',
                                'reviewed', 'published', 'failed', 'abandoned'
                            )
                        ),
    failure_message     text,
    CHECK (
        batch_status <> 'failed'
        OR btrim(COALESCE(failure_message, '')) <> ''
    ),
    UNIQUE (import_batch_id, source_artifact_id)
);

CREATE TABLE src_import_candidate (
    import_candidate_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    import_batch_id     bigint NOT NULL
                        REFERENCES src_import_batch(import_batch_id),
    source_artifact_id  bigint NOT NULL,
    source_locator_id   bigint NOT NULL,
    candidate_type      text NOT NULL CHECK (btrim(candidate_type) <> ''),
    candidate_key       text NOT NULL CHECK (btrim(candidate_key) <> ''),
    staging_value       jsonb NOT NULL,
    validation_status   text NOT NULL DEFAULT 'pending' CHECK (
                            validation_status IN (
                                'pending', 'valid', 'invalid', 'warning'
                            )
                        ),
    review_status       text NOT NULL DEFAULT 'unreviewed' CHECK (
                            review_status IN (
                                'unreviewed', 'approved', 'corrected',
                                'rejected', 'deferred'
                            )
                        ),
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (import_batch_id, candidate_type, candidate_key),
    UNIQUE (import_candidate_id, source_locator_id),
    FOREIGN KEY (import_batch_id, source_artifact_id)
        REFERENCES src_import_batch(import_batch_id, source_artifact_id),
    FOREIGN KEY (source_locator_id, source_artifact_id)
        REFERENCES src_locator(source_locator_id, source_artifact_id)
);

COMMENT ON COLUMN src_import_candidate.staging_value IS
    'Temporary nonauthoritative extraction data; approved state is published to typed tables.';

CREATE TABLE src_review (
    source_review_id    bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    import_candidate_id bigint NOT NULL
                        REFERENCES src_import_candidate(import_candidate_id),
    reviewer            text NOT NULL CHECK (btrim(reviewer) <> ''),
    decision            text NOT NULL CHECK (
                            decision IN (
                                'approve', 'approve_with_correction',
                                'reject', 'defer'
                            )
                        ),
    correction_summary  text,
    rationale           text NOT NULL CHECK (btrim(rationale) <> ''),
    decided_at          timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE src_concordance (
    source_concordance_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    left_locator_id     bigint NOT NULL REFERENCES src_locator(source_locator_id),
    right_locator_id    bigint NOT NULL REFERENCES src_locator(source_locator_id),
    concordance_status  text NOT NULL CHECK (
                            concordance_status IN (
                                'equivalent', 'left_only', 'right_only',
                                'presentation_difference', 'conflict',
                                'not_compared'
                            )
                        ),
    comparison_method   text NOT NULL CHECK (btrim(comparison_method) <> ''),
    evidence_summary    text NOT NULL CHECK (btrim(evidence_summary) <> ''),
    reviewed_at         timestamptz,
    reviewed_by         text,
    UNIQUE (left_locator_id, right_locator_id),
    CHECK (left_locator_id <> right_locator_id)
);
