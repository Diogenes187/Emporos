CREATE TABLE sys_database_bootstrap_completion (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    completed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    application_build text NOT NULL CHECK (btrim(application_build) <> '')
);

COMMENT ON TABLE sys_database_bootstrap_completion IS
    'Singleton written only after phased catalogue imports and verification pass.';
