CREATE TABLE auth_user_account (
    user_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    email text NOT NULL,
    display_name text NOT NULL,
    password_hash text NOT NULL,
    account_status text NOT NULL DEFAULT 'active'
        CHECK (account_status IN ('active','disabled')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT auth_user_email_normalized CHECK (email=lower(btrim(email))),
    CONSTRAINT auth_user_email_unique UNIQUE (email)
);

CREATE TABLE auth_user_session (
    session_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES auth_user_account(user_id) ON DELETE CASCADE,
    token_digest bytea NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    revoked_at timestamptz,
    CHECK (expires_at>created_at)
);

CREATE TABLE auth_campaign_membership (
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id) ON DELETE CASCADE,
    user_id bigint NOT NULL REFERENCES auth_user_account(user_id) ON DELETE CASCADE,
    membership_role text NOT NULL CHECK (membership_role IN ('owner','member')),
    joined_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (campaign_id,user_id)
);

CREATE UNIQUE INDEX auth_campaign_single_owner
ON auth_campaign_membership(campaign_id)
WHERE membership_role='owner';

CREATE TABLE auth_campaign_invitation (
    invitation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id) ON DELETE CASCADE,
    invited_by_user_id bigint NOT NULL REFERENCES auth_user_account(user_id),
    invited_email text NOT NULL,
    invitation_digest bytea NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    accepted_by_user_id bigint REFERENCES auth_user_account(user_id),
    accepted_at timestamptz,
    revoked_at timestamptz,
    CHECK (invited_email=lower(btrim(invited_email))),
    CHECK (expires_at>created_at),
    CHECK ((accepted_by_user_id IS NULL)=(accepted_at IS NULL))
);

CREATE INDEX auth_session_user_active ON auth_user_session(user_id,expires_at)
WHERE revoked_at IS NULL;
CREATE INDEX auth_campaign_membership_user ON auth_campaign_membership(user_id,campaign_id);

