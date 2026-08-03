CREATE TABLE fin_currency (
    currency_code text PRIMARY KEY CHECK (
        currency_code ~ '^[A-Z][A-Z0-9]{1,7}$'
    ),
    content_package_id bigint NOT NULL REFERENCES
        sys_content_package(content_package_id),
    name text NOT NULL UNIQUE CHECK (btrim(name) <> ''),
    minor_unit_scale smallint NOT NULL CHECK (
        minor_unit_scale BETWEEN 0 AND 6
    ),
    currency_status text NOT NULL DEFAULT 'active' CHECK (
        currency_status IN ('active','withdrawn')
    )
);

INSERT INTO fin_currency (
    currency_code,content_package_id,name,minor_unit_scale
)
SELECT 'CR',content_package_id,'Credits',0
FROM sys_content_package
WHERE package_code='cepheus-engine'
ORDER BY content_package_id
LIMIT 1;

CREATE TABLE fin_account (
    account_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    currency_code text NOT NULL REFERENCES fin_currency(currency_code),
    account_code text NOT NULL CHECK (
        account_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    name text NOT NULL CHECK (btrim(name) <> ''),
    account_kind text NOT NULL CHECK (
        account_kind IN (
            'asset','liability','equity','income','expense','external'
        )
    ),
    account_status text NOT NULL DEFAULT 'open' CHECK (
        account_status IN ('open','frozen','closed')
    ),
    opened_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    closed_at timestamptz,
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (
        concurrency_version > 0
    ),
    UNIQUE (account_id,campaign_id),
    UNIQUE (account_id,campaign_id,currency_code),
    UNIQUE (campaign_id,currency_code,account_code),
    CHECK (
        (account_status<>'closed' AND closed_at IS NULL)
        OR (account_status='closed' AND closed_at IS NOT NULL)
    )
);

CREATE TABLE fin_actor_account (
    account_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    FOREIGN KEY (account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id),
    FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    UNIQUE (actor_id,account_id)
);

CREATE TABLE fin_faction_account (
    account_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    faction_id bigint NOT NULL,
    FOREIGN KEY (account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id),
    FOREIGN KEY (faction_id,campaign_id)
        REFERENCES actor_faction(faction_id,campaign_id),
    UNIQUE (faction_id,account_id)
);

CREATE TABLE fin_campaign_account (
    account_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    FOREIGN KEY (account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id)
);

CREATE TABLE fin_external_account (
    account_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    external_party_name text NOT NULL CHECK (
        btrim(external_party_name) <> ''
    ),
    FOREIGN KEY (account_id,campaign_id)
        REFERENCES fin_account(account_id,campaign_id)
);

CREATE OR REPLACE FUNCTION fin_reject_multiple_account_owners()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    owner_count integer;
    kind text;
BEGIN
    SELECT account_kind INTO kind
    FROM fin_account
    WHERE account_id=NEW.account_id
    FOR UPDATE;

    IF (
        TG_TABLE_NAME='fin_external_account'
        AND kind<>'external'
    ) OR (
        TG_TABLE_NAME<>'fin_external_account'
        AND kind='external'
    ) THEN
        RAISE EXCEPTION 'Financial account kind and owner type disagree'
            USING ERRCODE='23514';
    END IF;

    SELECT
        (SELECT count(*) FROM fin_actor_account
         WHERE account_id=NEW.account_id)
      + (SELECT count(*) FROM fin_faction_account
         WHERE account_id=NEW.account_id)
      + (SELECT count(*) FROM fin_campaign_account
         WHERE account_id=NEW.account_id)
      + (SELECT count(*) FROM fin_external_account
         WHERE account_id=NEW.account_id)
    INTO owner_count;

    IF owner_count > 0 THEN
        RAISE EXCEPTION 'Financial account already has a typed owner'
            USING ERRCODE='23505';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER fin_actor_account_one_owner
BEFORE INSERT ON fin_actor_account
FOR EACH ROW EXECUTE FUNCTION fin_reject_multiple_account_owners();

CREATE TRIGGER fin_faction_account_one_owner
BEFORE INSERT ON fin_faction_account
FOR EACH ROW EXECUTE FUNCTION fin_reject_multiple_account_owners();

CREATE TRIGGER fin_campaign_account_one_owner
BEFORE INSERT ON fin_campaign_account
FOR EACH ROW EXECUTE FUNCTION fin_reject_multiple_account_owners();

CREATE TRIGGER fin_external_account_one_owner
BEFORE INSERT ON fin_external_account
FOR EACH ROW EXECUTE FUNCTION fin_reject_multiple_account_owners();

CREATE TABLE fin_transaction (
    transaction_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    currency_code text NOT NULL REFERENCES fin_currency(currency_code),
    transaction_status text NOT NULL DEFAULT 'pending' CHECK (
        transaction_status IN ('pending','posted','rejected','reversed')
    ),
    description text NOT NULL CHECK (btrim(description) <> ''),
    command_id bigint REFERENCES cmd_command(command_id),
    reversal_of_transaction_id bigint UNIQUE REFERENCES
        fin_transaction(transaction_id),
    occurred_day bigint,
    occurred_second integer CHECK (
        occurred_second IS NULL OR occurred_second BETWEEN 0 AND 86399
    ),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    posted_at timestamptz,
    UNIQUE (transaction_id,campaign_id),
    UNIQUE (transaction_id,campaign_id,currency_code),
    CHECK (
        (occurred_day IS NULL)=(occurred_second IS NULL)
    ),
    CHECK (
        (transaction_status='pending' AND posted_at IS NULL)
        OR (transaction_status<>'pending' AND posted_at IS NOT NULL)
    ),
    CHECK (
        reversal_of_transaction_id IS NULL
        OR reversal_of_transaction_id<>transaction_id
    )
);

CREATE TABLE fin_entry (
    entry_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    currency_code text NOT NULL,
    account_id bigint NOT NULL,
    entry_order smallint NOT NULL CHECK (entry_order > 0),
    amount_minor bigint NOT NULL CHECK (amount_minor<>0),
    memo text CHECK (memo IS NULL OR btrim(memo) <> ''),
    FOREIGN KEY (transaction_id,campaign_id,currency_code)
        REFERENCES fin_transaction(
            transaction_id,campaign_id,currency_code
        ),
    FOREIGN KEY (account_id,campaign_id,currency_code)
        REFERENCES fin_account(account_id,campaign_id,currency_code),
    UNIQUE (transaction_id,entry_order)
);

CREATE OR REPLACE FUNCTION fin_require_pending_entry_transaction()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_transaction bigint;
    status text;
BEGIN
    target_transaction := CASE
        WHEN TG_OP='DELETE' THEN OLD.transaction_id
        ELSE NEW.transaction_id
    END;
    SELECT transaction_status INTO status
    FROM fin_transaction
    WHERE transaction_id=target_transaction
    FOR UPDATE;
    IF status<>'pending' THEN
        RAISE EXCEPTION 'Entries of a non-pending transaction are immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END;
$$;

CREATE TRIGGER fin_entry_pending_transaction
BEFORE INSERT OR UPDATE OR DELETE ON fin_entry
FOR EACH ROW EXECUTE FUNCTION fin_require_pending_entry_transaction();

CREATE OR REPLACE FUNCTION fin_validate_transaction_posting()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    entry_count integer;
    balance numeric;
BEGIN
    IF NEW.transaction_status='posted'
       AND OLD.transaction_status IS DISTINCT FROM 'posted' THEN
        IF OLD.transaction_status<>'pending' THEN
            RAISE EXCEPTION 'Only pending transactions may be posted'
                USING ERRCODE='23514';
        END IF;
        SELECT count(*),COALESCE(sum(amount_minor),0)
        INTO entry_count,balance
        FROM fin_entry
        WHERE transaction_id=NEW.transaction_id;
        IF entry_count<2 THEN
            RAISE EXCEPTION
                'Posted transaction requires at least two entries'
                USING ERRCODE='23514';
        END IF;
        IF balance<>0 THEN
            RAISE EXCEPTION 'Posted transaction must balance to zero'
                USING ERRCODE='23514';
        END IF;
    END IF;

    IF OLD.transaction_status IN ('posted','reversed')
       AND NEW.transaction_status<>OLD.transaction_status THEN
        IF NOT (
            OLD.transaction_status='posted'
            AND NEW.transaction_status='reversed'
        ) THEN
            RAISE EXCEPTION 'Posted financial transaction is immutable'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER fin_transaction_posting_invariant
BEFORE UPDATE OF transaction_status ON fin_transaction
FOR EACH ROW EXECUTE FUNCTION fin_validate_transaction_posting();

CREATE OR REPLACE FUNCTION fin_post_transaction(
    target_transaction_id bigint
)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE fin_transaction
    SET transaction_status='posted',posted_at=clock_timestamp()
    WHERE transaction_id=target_transaction_id
      AND transaction_status='pending';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Financial transaction is not pending'
            USING ERRCODE='23514';
    END IF;
END;
$$;

CREATE VIEW fin_account_balance AS
SELECT
    account.account_id,
    account.campaign_id,
    account.currency_code,
    COALESCE(sum(entry.amount_minor),0)::bigint AS balance_minor
FROM fin_account account
LEFT JOIN fin_entry entry ON entry.account_id=account.account_id
LEFT JOIN fin_transaction transaction
  ON transaction.transaction_id=entry.transaction_id
 AND transaction.transaction_status IN ('posted','reversed')
GROUP BY account.account_id,account.campaign_id,account.currency_code;

CREATE TABLE fin_obligation (
    obligation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    currency_code text NOT NULL REFERENCES fin_currency(currency_code),
    debtor_account_id bigint NOT NULL,
    creditor_account_id bigint NOT NULL,
    principal_minor bigint NOT NULL CHECK (principal_minor>0),
    obligation_kind text NOT NULL CHECK (
        obligation_kind IN (
            'loan','medical_debt','anagathic_debt','mortgage',
            'fine','tax','wage','pension','other'
        )
    ),
    description text NOT NULL CHECK (btrim(description) <> ''),
    due_day bigint,
    due_second integer CHECK (
        due_second IS NULL OR due_second BETWEEN 0 AND 86399
    ),
    obligation_status text NOT NULL DEFAULT 'open' CHECK (
        obligation_status IN (
            'open','satisfied','defaulted','forgiven','cancelled'
        )
    ),
    opened_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    source_command_id bigint REFERENCES cmd_command(command_id),
    FOREIGN KEY (debtor_account_id,campaign_id,currency_code)
        REFERENCES fin_account(account_id,campaign_id,currency_code),
    FOREIGN KEY (creditor_account_id,campaign_id,currency_code)
        REFERENCES fin_account(account_id,campaign_id,currency_code),
    UNIQUE (obligation_id,campaign_id),
    UNIQUE (obligation_id,campaign_id,currency_code),
    CHECK (debtor_account_id<>creditor_account_id),
    CHECK ((due_day IS NULL)=(due_second IS NULL)),
    CHECK (
        (obligation_status='open' AND ended_at IS NULL)
        OR (obligation_status<>'open' AND ended_at IS NOT NULL)
    )
);

CREATE TABLE fin_obligation_payment (
    obligation_payment_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    obligation_id bigint NOT NULL,
    transaction_id bigint NOT NULL UNIQUE,
    campaign_id bigint NOT NULL,
    currency_code text NOT NULL,
    amount_minor bigint NOT NULL CHECK (amount_minor>0),
    paid_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (obligation_id,campaign_id,currency_code)
        REFERENCES fin_obligation(
            obligation_id,campaign_id,currency_code
        ),
    FOREIGN KEY (transaction_id,campaign_id,currency_code)
        REFERENCES fin_transaction(
            transaction_id,campaign_id,currency_code
        )
);

CREATE OR REPLACE FUNCTION fin_validate_obligation_payment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    transaction_status_value text;
    debtor bigint;
    creditor bigint;
    paid bigint;
    principal bigint;
BEGIN
    SELECT transaction_status INTO transaction_status_value
    FROM fin_transaction
    WHERE transaction_id=NEW.transaction_id;
    IF transaction_status_value<>'posted' THEN
        RAISE EXCEPTION 'Obligation payment requires a posted transaction'
            USING ERRCODE='23514';
    END IF;

    SELECT debtor_account_id,creditor_account_id,principal_minor
    INTO debtor,creditor,principal
    FROM fin_obligation
    WHERE obligation_id=NEW.obligation_id
    FOR UPDATE;

    IF NOT EXISTS (
        SELECT 1 FROM fin_entry
        WHERE transaction_id=NEW.transaction_id
          AND account_id=debtor
          AND amount_minor=-NEW.amount_minor
    ) OR NOT EXISTS (
        SELECT 1 FROM fin_entry
        WHERE transaction_id=NEW.transaction_id
          AND account_id=creditor
          AND amount_minor=NEW.amount_minor
    ) THEN
        RAISE EXCEPTION
            'Payment entries must move value from debtor to creditor'
            USING ERRCODE='23514';
    END IF;

    SELECT COALESCE(sum(amount_minor),0) INTO paid
    FROM fin_obligation_payment
    WHERE obligation_id=NEW.obligation_id;
    IF paid+NEW.amount_minor>principal THEN
        RAISE EXCEPTION 'Obligation payment exceeds principal'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER fin_obligation_payment_invariant
BEFORE INSERT ON fin_obligation_payment
FOR EACH ROW EXECUTE FUNCTION fin_validate_obligation_payment();

CREATE VIEW fin_obligation_balance AS
SELECT
    obligation.obligation_id,
    obligation.campaign_id,
    obligation.currency_code,
    obligation.principal_minor,
    COALESCE(sum(payment.amount_minor),0)::bigint AS paid_minor,
    (
        obligation.principal_minor
        -COALESCE(sum(payment.amount_minor),0)
    )::bigint AS outstanding_minor
FROM fin_obligation obligation
LEFT JOIN fin_obligation_payment payment
  ON payment.obligation_id=obligation.obligation_id
GROUP BY
    obligation.obligation_id,
    obligation.campaign_id,
    obligation.currency_code,
    obligation.principal_minor;
