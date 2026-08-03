CREATE TABLE iam_account (
    account_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    account_reference text NOT NULL UNIQUE CHECK (
        btrim(account_reference) <> ''
    ),
    display_name text NOT NULL CHECK (btrim(display_name) <> ''),
    account_status text NOT NULL DEFAULT 'active' CHECK (
        account_status IN ('active','suspended','closed')
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE iam_role (
    role_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_code text NOT NULL UNIQUE CHECK (
        role_code IN ('player','referee','administrator')
    ),
    role_name text NOT NULL UNIQUE CHECK (btrim(role_name) <> '')
);

INSERT INTO iam_role (role_code,role_name) VALUES
    ('player','Player'),
    ('referee','Referee'),
    ('administrator','Administrator');

CREATE TABLE iam_campaign_membership (
    campaign_membership_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    account_id bigint NOT NULL REFERENCES iam_account(account_id),
    role_id bigint NOT NULL REFERENCES iam_role(role_id),
    membership_status text NOT NULL DEFAULT 'active' CHECK (
        membership_status IN ('active','ended','revoked')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    UNIQUE (campaign_membership_id,campaign_id),
    CHECK (
        (membership_status='active' AND ended_at IS NULL)
        OR (membership_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX iam_one_active_campaign_membership_role
    ON iam_campaign_membership(campaign_id,account_id,role_id)
    WHERE membership_status='active';

CREATE TABLE iam_character_controller (
    character_controller_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    actor_id bigint NOT NULL,
    campaign_membership_id bigint NOT NULL,
    authority_level text NOT NULL CHECK (
        authority_level IN ('owner','editor','viewer')
    ),
    controller_status text NOT NULL DEFAULT 'active' CHECK (
        controller_status IN ('active','ended','revoked')
    ),
    effective_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (campaign_membership_id,campaign_id)
        REFERENCES iam_campaign_membership(
            campaign_membership_id,campaign_id
        ),
    CHECK (
        (controller_status='active' AND ended_at IS NULL)
        OR (controller_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE UNIQUE INDEX iam_one_active_controller_authority
    ON iam_character_controller(actor_id,campaign_membership_id)
    WHERE controller_status='active';

ALTER TABLE camp_campaign
    ADD COLUMN play_mode text NOT NULL DEFAULT 'player_directed' CHECK (
        play_mode IN (
            'player_directed','human_refereed',
            'ai_assisted','ai_refereed'
        )
    ),
    ADD COLUMN campaign_status text NOT NULL DEFAULT 'active' CHECK (
        campaign_status IN ('active','completed','archived')
    ),
    ADD COLUMN concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    );

CREATE TABLE camp_installed_package (
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    content_package_id bigint NOT NULL REFERENCES
        sys_content_package(content_package_id),
    installation_status text NOT NULL DEFAULT 'active' CHECK (
        installation_status IN ('active','superseded','removed')
    ),
    installed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    PRIMARY KEY (campaign_id,content_package_id),
    CHECK (
        (installation_status='active' AND ended_at IS NULL)
        OR (installation_status<>'active' AND ended_at IS NOT NULL)
    )
);

CREATE TABLE camp_clock (
    campaign_id bigint PRIMARY KEY REFERENCES camp_campaign(campaign_id),
    day_number bigint NOT NULL DEFAULT 0,
    second_of_day integer NOT NULL DEFAULT 0 CHECK (
        second_of_day BETWEEN 0 AND 86399
    ),
    calendar_rule_id bigint REFERENCES rule_rule(rule_id),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    advanced_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE camp_clock_change (
    camp_clock_change_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id bigint NOT NULL REFERENCES camp_clock(campaign_id),
    command_id bigint REFERENCES cmd_command(command_id),
    day_number_before bigint NOT NULL,
    second_of_day_before integer NOT NULL CHECK (
        second_of_day_before BETWEEN 0 AND 86399
    ),
    day_number_after bigint NOT NULL,
    second_of_day_after integer NOT NULL CHECK (
        second_of_day_after BETWEEN 0 AND 86399
    ),
    reason text NOT NULL CHECK (btrim(reason) <> ''),
    changed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (
        day_number_before <> day_number_after
        OR second_of_day_before <> second_of_day_after
    )
);

CREATE OR REPLACE FUNCTION iam_ensure_account(reference text)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
    result bigint;
BEGIN
    INSERT INTO iam_account (account_reference,display_name)
    VALUES (reference,reference)
    ON CONFLICT (account_reference) DO UPDATE
        SET account_reference=EXCLUDED.account_reference
    RETURNING account_id INTO result;
    RETURN result;
END;
$$;

CREATE OR REPLACE FUNCTION iam_sync_campaign_foundation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    account bigint;
    referee_role bigint;
    engine_package bigint;
BEGIN
    INSERT INTO camp_clock (campaign_id) VALUES (NEW.campaign_id)
    ON CONFLICT (campaign_id) DO NOTHING;

    SELECT content_package_id INTO engine_package
    FROM sys_content_package
    WHERE package_code='cepheus-engine'
    ORDER BY released_at DESC NULLS LAST,created_at DESC,
             content_package_id DESC
    LIMIT 1;
    IF engine_package IS NOT NULL THEN
        INSERT INTO camp_installed_package(campaign_id,content_package_id)
        VALUES (NEW.campaign_id,engine_package)
        ON CONFLICT (campaign_id,content_package_id) DO NOTHING;
    END IF;

    IF (
        TG_OP='UPDATE'
        AND OLD.owner_reference IS DISTINCT FROM NEW.owner_reference
        AND OLD.owner_reference IS NOT NULL
    ) THEN
        UPDATE iam_campaign_membership membership
        SET membership_status='ended',ended_at=clock_timestamp()
        FROM iam_account old_account,iam_role old_role
        WHERE membership.campaign_id=NEW.campaign_id
          AND membership.account_id=old_account.account_id
          AND old_account.account_reference=OLD.owner_reference
          AND membership.role_id=old_role.role_id
          AND old_role.role_code='referee'
          AND membership.membership_status='active';
    END IF;

    IF NEW.owner_reference IS NOT NULL THEN
        account := iam_ensure_account(NEW.owner_reference);
        SELECT role_id INTO referee_role
        FROM iam_role WHERE role_code='referee';
        INSERT INTO iam_campaign_membership(campaign_id,account_id,role_id)
        VALUES (NEW.campaign_id,account,referee_role)
        ON CONFLICT (campaign_id,account_id,role_id)
            WHERE membership_status='active'
        DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER camp_campaign_relational_foundation
AFTER INSERT OR UPDATE OF owner_reference ON camp_campaign
FOR EACH ROW EXECUTE FUNCTION iam_sync_campaign_foundation();

CREATE OR REPLACE FUNCTION iam_sync_actor_controller()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    account bigint;
    player_role bigint;
    membership bigint;
BEGIN
    IF (
        TG_OP='UPDATE'
        AND OLD.controller_reference IS DISTINCT FROM NEW.controller_reference
    ) THEN
        UPDATE iam_character_controller
        SET controller_status='ended',ended_at=clock_timestamp()
        WHERE actor_id=NEW.actor_id AND controller_status='active';
    END IF;

    account := iam_ensure_account(NEW.controller_reference);
    SELECT role_id INTO player_role FROM iam_role WHERE role_code='player';
    INSERT INTO iam_campaign_membership(campaign_id,account_id,role_id)
    VALUES (NEW.campaign_id,account,player_role)
    ON CONFLICT (campaign_id,account_id,role_id)
        WHERE membership_status='active'
    DO UPDATE SET membership_status='active'
    RETURNING campaign_membership_id INTO membership;

    INSERT INTO iam_character_controller(
        campaign_id,actor_id,campaign_membership_id,authority_level
    )
    VALUES (NEW.campaign_id,NEW.actor_id,membership,'owner')
    ON CONFLICT (actor_id,campaign_membership_id)
        WHERE controller_status='active'
    DO NOTHING;
    RETURN NEW;
END;
$$;

CREATE TRIGGER actor_actor_relational_controller
AFTER INSERT OR UPDATE OF controller_reference ON actor_actor
FOR EACH ROW EXECUTE FUNCTION iam_sync_actor_controller();

INSERT INTO camp_clock(campaign_id)
SELECT campaign_id FROM camp_campaign
ON CONFLICT (campaign_id) DO NOTHING;

INSERT INTO camp_installed_package(campaign_id,content_package_id)
SELECT campaign.campaign_id,package.content_package_id
FROM camp_campaign campaign
CROSS JOIN LATERAL (
    SELECT content_package_id
    FROM sys_content_package
    WHERE package_code='cepheus-engine'
    ORDER BY released_at DESC NULLS LAST,created_at DESC,
             content_package_id DESC
    LIMIT 1
) package
ON CONFLICT (campaign_id,content_package_id) DO NOTHING;

INSERT INTO iam_account(account_reference,display_name)
SELECT reference,reference
FROM (
    SELECT owner_reference AS reference FROM camp_campaign
    UNION
    SELECT controller_reference FROM actor_actor
) source
WHERE reference IS NOT NULL
ON CONFLICT (account_reference) DO NOTHING;

INSERT INTO iam_campaign_membership(campaign_id,account_id,role_id)
SELECT campaign.campaign_id,account.account_id,role.role_id
FROM camp_campaign campaign
JOIN iam_account account
  ON account.account_reference=campaign.owner_reference
JOIN iam_role role ON role.role_code='referee'
ON CONFLICT (campaign_id,account_id,role_id)
    WHERE membership_status='active'
DO NOTHING;

INSERT INTO iam_campaign_membership(campaign_id,account_id,role_id)
SELECT DISTINCT actor.campaign_id,account.account_id,role.role_id
FROM actor_actor actor
JOIN iam_account account
  ON account.account_reference=actor.controller_reference
JOIN iam_role role ON role.role_code='player'
ON CONFLICT (campaign_id,account_id,role_id)
    WHERE membership_status='active'
DO NOTHING;

INSERT INTO iam_character_controller(
    campaign_id,actor_id,campaign_membership_id,authority_level
)
SELECT actor.campaign_id,actor.actor_id,membership.campaign_membership_id,
       'owner'
FROM actor_actor actor
JOIN iam_account account
  ON account.account_reference=actor.controller_reference
JOIN iam_role role ON role.role_code='player'
JOIN iam_campaign_membership membership
  ON membership.campaign_id=actor.campaign_id
 AND membership.account_id=account.account_id
 AND membership.role_id=role.role_id
 AND membership.membership_status='active'
ON CONFLICT (actor_id,campaign_membership_id)
    WHERE controller_status='active'
DO NOTHING;

COMMENT ON COLUMN camp_campaign.owner_reference IS
    'Compatibility projection; iam_campaign_membership is relational authority.';
COMMENT ON COLUMN actor_actor.controller_reference IS
    'Compatibility projection; iam_character_controller is relational authority.';
