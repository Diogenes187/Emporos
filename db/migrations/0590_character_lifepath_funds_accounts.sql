-- Finished lifepaths historically retained cash only in actor_financial_state,
-- while equipment purchases correctly require a double-entry actor account.
-- Create that missing bridge for existing characters. Future completions do it
-- in the authoritative finish_character_creation command.
INSERT INTO fin_account(
    campaign_id,currency_code,account_code,name,account_kind
)
SELECT actor.campaign_id,'CR','personal-'||actor.actor_id,
       actor.name||' Personal Funds','asset'
FROM actor_actor actor
JOIN actor_lifepath_state lifepath USING(actor_id)
WHERE lifepath.lifepath_status='completed'
  AND actor.lifecycle_status='active'
  AND NOT EXISTS(
      SELECT 1 FROM fin_actor_account ownership
      JOIN fin_account account USING(account_id,campaign_id)
      WHERE ownership.actor_id=actor.actor_id
        AND account.account_status='open'
  )
ON CONFLICT(campaign_id,currency_code,account_code) DO NOTHING;

INSERT INTO fin_actor_account(account_id,campaign_id,actor_id)
SELECT account.account_id,actor.campaign_id,actor.actor_id
FROM actor_actor actor
JOIN actor_lifepath_state lifepath USING(actor_id)
JOIN fin_account account
  ON account.campaign_id=actor.campaign_id
 AND account.account_code='personal-'||actor.actor_id
WHERE lifepath.lifepath_status='completed'
  AND NOT EXISTS(
      SELECT 1 FROM fin_actor_account ownership
      WHERE ownership.actor_id=actor.actor_id
        AND ownership.account_id=account.account_id
  );

INSERT INTO fin_account(
    campaign_id,currency_code,account_code,name,account_kind
)
SELECT DISTINCT actor.campaign_id,'CR','campaign-opening-equity',
       'Campaign Opening Equity','equity'
FROM actor_actor actor
JOIN actor_lifepath_state lifepath USING(actor_id)
WHERE lifepath.lifepath_status='completed'
  AND EXISTS(
      SELECT 1 FROM actor_financial_state finance
      WHERE finance.actor_id=actor.actor_id AND finance.cash_credits>0
  )
ON CONFLICT(campaign_id,currency_code,account_code) DO NOTHING;

INSERT INTO fin_campaign_account(account_id,campaign_id)
SELECT account.account_id,account.campaign_id
FROM fin_account account
WHERE account.account_code='campaign-opening-equity'
  AND NOT EXISTS(
      SELECT 1 FROM fin_campaign_account ownership
      WHERE ownership.account_id=account.account_id
  );

DO $$
DECLARE row record; transaction_key bigint;
BEGIN
  FOR row IN
    SELECT actor.actor_id,actor.campaign_id,actor.name,
           personal.account_id AS personal_account_id,
           equity.account_id AS equity_account_id,
           finance.cash_credits
    FROM actor_actor actor
    JOIN actor_lifepath_state lifepath USING(actor_id)
    JOIN actor_financial_state finance USING(actor_id)
    JOIN fin_account personal
      ON personal.campaign_id=actor.campaign_id
     AND personal.account_code='personal-'||actor.actor_id
    JOIN fin_account equity
      ON equity.campaign_id=actor.campaign_id
     AND equity.account_code='campaign-opening-equity'
    WHERE lifepath.lifepath_status='completed'
      AND finance.cash_credits>0
      AND NOT EXISTS(
          SELECT 1 FROM fin_entry entry
          JOIN fin_transaction transaction USING(transaction_id,campaign_id)
          WHERE entry.account_id=personal.account_id
            AND transaction.transaction_status='posted'
      )
  LOOP
    INSERT INTO fin_transaction(campaign_id,currency_code,description)
    VALUES(row.campaign_id,'CR','Lifepath funds for '||row.name)
    RETURNING transaction_id INTO transaction_key;
    INSERT INTO fin_entry(
        transaction_id,campaign_id,currency_code,account_id,
        entry_order,amount_minor
    ) VALUES
      (transaction_key,row.campaign_id,'CR',row.personal_account_id,
       1,row.cash_credits),
      (transaction_key,row.campaign_id,'CR',row.equity_account_id,
       2,-row.cash_credits);
    PERFORM fin_post_transaction(transaction_key);
  END LOOP;
END $$;
