CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE sys_schema_migration (
    version             integer PRIMARY KEY CHECK (version > 0),
    name                text NOT NULL CHECK (btrim(name) <> ''),
    checksum_sha256     text NOT NULL
                        CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
    applied_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    application_build   text NOT NULL CHECK (btrim(application_build) <> '')
);

CREATE TABLE sys_content_package (
    content_package_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    package_code        text NOT NULL CHECK (
                            package_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
                        ),
    package_version     text NOT NULL CHECK (btrim(package_version) <> ''),
    display_name        text NOT NULL CHECK (btrim(display_name) <> ''),
    package_kind        text NOT NULL CHECK (
                            package_kind IN (
                                'foundation', 'rules', 'setting',
                                'house_rules', 'product_seed'
                            )
                        ),
    lifecycle_status    text NOT NULL DEFAULT 'draft' CHECK (
                            lifecycle_status IN (
                                'draft', 'review', 'released', 'retired'
                            )
                        ),
    content_sha256      text CHECK (
                            content_sha256 IS NULL
                            OR content_sha256 ~ '^[0-9a-f]{64}$'
                        ),
    source_package_id   bigint REFERENCES sys_content_package(content_package_id),
    created_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    released_at         timestamptz,
    notes               text,
    UNIQUE (package_code, package_version),
    CHECK (source_package_id IS NULL OR source_package_id <> content_package_id),
    CHECK (
        lifecycle_status NOT IN ('released', 'retired')
        OR (content_sha256 IS NOT NULL AND released_at IS NOT NULL)
    )
);

CREATE INDEX sys_content_package_source_idx
    ON sys_content_package(source_package_id)
    WHERE source_package_id IS NOT NULL;

CREATE TABLE sys_product_seed (
    product_seed_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id           uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    product_code        text NOT NULL CHECK (
                            product_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
                        ),
    seed_package_id     bigint NOT NULL
                        REFERENCES sys_content_package(content_package_id),
    adopted_version     text NOT NULL CHECK (btrim(adopted_version) <> ''),
    adopted_at          timestamptz NOT NULL DEFAULT clock_timestamp(),
    adoption_status     text NOT NULL CHECK (
                            adoption_status IN ('tracking', 'detached', 'omitted')
                        ),
    detachment_rationale text,
    UNIQUE (product_code, seed_package_id, adopted_version),
    CHECK (
        adoption_status <> 'detached'
        OR btrim(COALESCE(detachment_rationale, '')) <> ''
    )
);

