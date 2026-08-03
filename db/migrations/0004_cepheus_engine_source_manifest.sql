INSERT INTO sys_content_package (
    package_code, package_version, display_name, package_kind,
    lifecycle_status, notes
) VALUES (
    'cepheus-engine', '9.1-draft', 'Cepheus Engine SRD 9.1',
    'rules', 'draft',
    'Normalization package built from paired GitHub v9.1 and OGN publications.'
);

INSERT INTO src_work (
    work_code, title, edition, publisher, classification,
    canonical_url, source_revision, notes
) VALUES
(
    'cepheus-engine.github-v9.1',
    'Cepheus Engine SRD GitHub Publication',
    'v9.1',
    'Cepheus Engine SRD contributors',
    'repository',
    'https://github.com/orffen/cepheus-srd',
    '0839018902355215fb8148f0b4ce1b1f8e011080',
    'Paired governing source. Supplies repository-only and website-omitted material.'
),
(
    'cepheus-engine.ogn',
    'Cepheus Engine SRD Open Gaming Network Publication',
    NULL,
    'Open Gaming Network',
    'website',
    'https://cepheus-srd.opengamingnetwork.com/',
    NULL,
    'Paired governing source. Captures rendered pages and any material absent from GitHub.'
);

INSERT INTO src_work_relation (
    left_work_id, right_work_id, relation_type, decision_status,
    rationale, decided_at, decided_by
)
SELECT
    github.source_work_id,
    ogn.source_work_id,
    'paired_publication',
    'reviewed',
    'Use both publications. Either may fill omissions in the other; genuine conflicts require review.',
    TIMESTAMPTZ '2026-07-27 00:00:00-05',
    'Raymond'
FROM src_work github
CROSS JOIN src_work ogn
WHERE github.work_code = 'cepheus-engine.github-v9.1'
  AND ogn.work_code = 'cepheus-engine.ogn';

INSERT INTO src_artifact (
    source_work_id, artifact_kind, source_uri, source_revision,
    captured_at, checksum_sha256, media_type, local_role
)
SELECT
    source_work_id,
    'repository_snapshot',
    'https://github.com/orffen/cepheus-srd/tree/v9.1',
    '0839018902355215fb8148f0b4ce1b1f8e011080',
    TIMESTAMPTZ '2026-07-27 00:00:00-05',
    NULL,
    'text/markdown',
    'governing'
FROM src_work
WHERE work_code = 'cepheus-engine.github-v9.1';

INSERT INTO src_artifact (
    source_work_id, artifact_kind, source_uri, source_revision,
    captured_at, checksum_sha256, media_type, local_role
)
SELECT
    source_work_id,
    'web_page',
    'https://cepheus-srd.opengamingnetwork.com/',
    NULL,
    TIMESTAMPTZ '2026-07-27 00:00:00-05',
    NULL,
    'text/html',
    'governing'
FROM src_work
WHERE work_code = 'cepheus-engine.ogn';

