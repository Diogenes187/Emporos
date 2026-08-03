WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'trade.local-broker-settlement','Local Broker Settlement','trade','approved',
 'Local broker skill replaces merchant Broker skill; commission is due on the negotiated lot even when a sale is declined.'
FROM package;

CREATE TABLE rule_local_broker_settlement(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 commission_basis text NOT NULL CHECK(commission_basis='complete-negotiated-lot'),
 commission_rounding text NOT NULL CHECK(commission_rounding='ceiling-credit'),
 commission_due_on_declined_sale boolean NOT NULL CHECK(commission_due_on_declined_sale),
 broker_skill_replaces_merchant_skill boolean NOT NULL CHECK(broker_skill_replaces_merchant_skill)
);
INSERT INTO rule_local_broker_settlement
SELECT rule_id,'complete-negotiated-lot','ceiling-credit',true,true FROM rule_rule
WHERE rule_code='trade.local-broker-settlement';

INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-TRADE-001',
 'Raymond approved rounding fractional local-broker percentage commissions upward to the next whole Credit so the broker is never underpaid.'
FROM rule_rule WHERE rule_code='trade.local-broker-settlement';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
 work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='trade.local-broker-settlement'
 AND locator.heading_path='Trade and Commerce > Local Brokers'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

INSERT INTO src_issue(issue_code,domain_code,issue_type,review_priority,issue_status,subject_code,title,
 problem_statement,published_value,calculated_value,reviewer_question,requested_evidence,engine_disposition,
 resolved_at,resolution_summary)
VALUES('trade.local-broker.commission-rounding','trade','source_omission','low','resolved',
 'trade.local-broker-settlement','Local broker fractional commission rounding',
 'The source states percentage commissions but does not specify conversion of a fractional Credit into whole-Credit ledger entries.',
 'Percentage of final negotiated price','Ceiling to the next whole Credit',
 'Which whole-Credit rounding method should govern local broker commission settlement?',
 'A publisher clarification or explicit table rounding instruction.','preserve_rule',clock_timestamp(),
 'CE-TRADE-001: Raymond approved ceiling to a whole Credit so the broker is not underpaid.');
INSERT INTO src_issue_locator(source_issue_id,source_locator_id,evidence_role)
SELECT issue.source_issue_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'primary' ELSE 'corroborating' END
FROM src_issue issue CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE issue.issue_code='trade.local-broker.commission-rounding'
 AND locator.heading_path='Trade and Commerce > Local Brokers'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE mkt_local_broker_engagement(
 local_broker_engagement_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id bigint NOT NULL,
 market_session_id bigint NOT NULL,
 merchant_actor_id bigint NOT NULL,
 broker_supplier_id bigint NOT NULL,
 broker_skill_level smallint NOT NULL CHECK(broker_skill_level BETWEEN 1 AND 4),
 commission_percent smallint NOT NULL CHECK(commission_percent IN(5,10,15,20)),
 starport_code_snapshot text NOT NULL REFERENCES rule_starport_class(starport_code),
 merchant_settlement_account_id bigint NOT NULL,
 broker_settlement_account_id bigint NOT NULL,
 engaged_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint REFERENCES cmd_command(command_id),
 FOREIGN KEY(market_session_id,campaign_id) REFERENCES mkt_session(market_session_id,campaign_id),
 FOREIGN KEY(merchant_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(broker_supplier_id,campaign_id) REFERENCES mkt_supplier(supplier_id,campaign_id),
 FOREIGN KEY(merchant_settlement_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id),
 FOREIGN KEY(broker_settlement_account_id,campaign_id) REFERENCES fin_account(account_id,campaign_id),
 UNIQUE(local_broker_engagement_id,campaign_id)
);

ALTER TABLE mkt_quote ADD COLUMN local_broker_engagement_id bigint,
 ADD CONSTRAINT mkt_quote_local_broker_scope_fkey FOREIGN KEY(local_broker_engagement_id,campaign_id)
 REFERENCES mkt_local_broker_engagement(local_broker_engagement_id,campaign_id);

CREATE TABLE mkt_local_broker_negotiation_receipt(
 quote_id bigint PRIMARY KEY,
 campaign_id bigint NOT NULL,
 local_broker_engagement_id bigint NOT NULL,
 broker_operation_command_id bigint NOT NULL UNIQUE REFERENCES cmd_broker_operation_receipt(command_id),
 negotiated_quantity_tons numeric NOT NULL CHECK(negotiated_quantity_tons>0),
 negotiated_total_credits numeric NOT NULL CHECK(negotiated_total_credits>0),
 commission_percent smallint NOT NULL CHECK(commission_percent IN(5,10,15,20)),
 exact_commission_credits numeric NOT NULL CHECK(exact_commission_credits>0),
 settled_commission_credits bigint NOT NULL CHECK(settled_commission_credits>0),
 rounding_method text NOT NULL CHECK(rounding_method='ceiling-credit'),
 commission_due_if_quote_rejected boolean NOT NULL CHECK(commission_due_if_quote_rejected),
 financial_transaction_id bigint NOT NULL UNIQUE,
 settled_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint REFERENCES cmd_command(command_id),
 FOREIGN KEY(quote_id,campaign_id) REFERENCES mkt_quote(quote_id,campaign_id),
 FOREIGN KEY(local_broker_engagement_id,campaign_id)
 REFERENCES mkt_local_broker_engagement(local_broker_engagement_id,campaign_id),
 FOREIGN KEY(financial_transaction_id,campaign_id) REFERENCES fin_transaction(transaction_id,campaign_id),
 CHECK(settled_commission_credits=ceil(exact_commission_credits))
);

CREATE FUNCTION mkt_validate_local_broker_engagement() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE broker mkt_supplier%ROWTYPE; market_location bigint; port text; expected_commission smallint;
        maximum_level smallint; broker_actor bigint;
BEGIN
 SELECT * INTO STRICT broker FROM mkt_supplier WHERE supplier_id=NEW.broker_supplier_id AND campaign_id=NEW.campaign_id;
 SELECT market.location_id,profile.starport_code INTO STRICT market_location,port
 FROM mkt_session session JOIN mkt_market market USING(market_id,campaign_id)
 JOIN loc_world_profile profile ON profile.location_id=market.location_id AND profile.campaign_id=market.campaign_id
  AND profile.profile_status='current'
 WHERE session.market_session_id=NEW.market_session_id AND session.campaign_id=NEW.campaign_id;
 SELECT commission_percent INTO STRICT expected_commission FROM rule_local_broker WHERE skill_level=NEW.broker_skill_level;
 maximum_level:=CASE port WHEN 'A' THEN 4 WHEN 'B' THEN 3 WHEN 'C' THEN 2 WHEN 'D' THEN 1 WHEN 'E' THEN 1 ELSE 0 END;
 broker_actor:=broker.actor_id;
 IF broker.market_session_id<>NEW.market_session_id OR broker.supplier_kind<>'broker'
   OR broker.broker_skill_level<>NEW.broker_skill_level OR NEW.broker_skill_level>maximum_level
   OR NEW.commission_percent<>expected_commission OR NEW.starport_code_snapshot<>port
   OR NOT EXISTS(SELECT 1 FROM fin_actor_account WHERE account_id=NEW.merchant_settlement_account_id
      AND campaign_id=NEW.campaign_id AND actor_id=NEW.merchant_actor_id)
   OR NOT EXISTS(SELECT 1 FROM fin_actor_account WHERE account_id=NEW.broker_settlement_account_id
      AND campaign_id=NEW.campaign_id AND actor_id=broker_actor) THEN
  RAISE EXCEPTION 'Local broker engagement does not match broker, starport cap, commission, or accounts' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_local_broker_engagement_valid BEFORE INSERT ON mkt_local_broker_engagement
FOR EACH ROW EXECUTE FUNCTION mkt_validate_local_broker_engagement();

CREATE FUNCTION mkt_validate_local_broker_negotiation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE quote mkt_quote%ROWTYPE; engagement mkt_local_broker_engagement%ROWTYPE;
 broker_operation cmd_broker_operation_receipt%ROWTYPE; broker_actor bigint; base_price bigint;
 negative_entry bigint; positive_entry bigint; entry_count integer; tx_status text;
 expected_operation text;
BEGIN
 SELECT * INTO STRICT quote FROM mkt_quote WHERE quote_id=NEW.quote_id AND campaign_id=NEW.campaign_id;
 SELECT * INTO STRICT engagement FROM mkt_local_broker_engagement
 WHERE local_broker_engagement_id=NEW.local_broker_engagement_id AND campaign_id=NEW.campaign_id;
 SELECT * INTO STRICT broker_operation FROM cmd_broker_operation_receipt WHERE command_id=NEW.broker_operation_command_id;
 SELECT actor_id INTO STRICT broker_actor FROM mkt_supplier WHERE supplier_id=engagement.broker_supplier_id;
 SELECT base_price_credits INTO STRICT base_price FROM rule_trade_good WHERE trade_good_rule_id=quote.trade_good_rule_id;
 SELECT transaction_status INTO STRICT tx_status FROM fin_transaction
 WHERE transaction_id=NEW.financial_transaction_id AND campaign_id=NEW.campaign_id;
 SELECT count(*),sum(amount_minor) FILTER(WHERE account_id=engagement.merchant_settlement_account_id),
        sum(amount_minor) FILTER(WHERE account_id=engagement.broker_settlement_account_id)
 INTO entry_count,negative_entry,positive_entry FROM fin_entry WHERE transaction_id=NEW.financial_transaction_id;
 expected_operation:=CASE quote.quote_side WHEN 'sell' THEN 'determine-purchase-price' ELSE 'determine-sale-price' END;
 IF quote.local_broker_engagement_id<>NEW.local_broker_engagement_id
   OR quote.market_session_id<>engagement.market_session_id OR quote.quoted_actor_id<>engagement.merchant_actor_id
   OR broker_operation.actor_id<>broker_actor OR broker_operation.market_session_id<>quote.market_session_id
   OR broker_operation.operation_code<>expected_operation OR broker_operation.trade_good_rule_id<>quote.trade_good_rule_id
   OR broker_operation.price_percent<>quote.price_percent OR quote.price_percent IS NULL
   OR quote.unit_price_minor<>base_price*quote.price_percent/100
   OR quote.maximum_quantity_tons IS DISTINCT FROM NEW.negotiated_quantity_tons
   OR NEW.negotiated_total_credits<>quote.unit_price_minor*NEW.negotiated_quantity_tons
   OR NEW.commission_percent<>engagement.commission_percent
   OR NEW.exact_commission_credits<>NEW.negotiated_total_credits*NEW.commission_percent/100
   OR NEW.rounding_method<>'ceiling-credit' OR NOT NEW.commission_due_if_quote_rejected
   OR tx_status<>'posted' OR entry_count<>2
   OR negative_entry<>-NEW.settled_commission_credits OR positive_entry<>NEW.settled_commission_credits THEN
  RAISE EXCEPTION 'Local broker settlement does not match quote, negotiation, adjudicated commission, or ledger' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_local_broker_negotiation_valid BEFORE INSERT ON mkt_local_broker_negotiation_receipt
FOR EACH ROW EXECUTE FUNCTION mkt_validate_local_broker_negotiation();

CREATE FUNCTION mkt_require_local_broker_settlement() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.local_broker_engagement_id IS NOT NULL AND NOT EXISTS(
   SELECT 1 FROM mkt_local_broker_negotiation_receipt WHERE quote_id=NEW.quote_id) THEN
  RAISE EXCEPTION 'Local-broker quote requires paid commission settlement' USING ERRCODE='23514';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER mkt_local_broker_settlement_required AFTER INSERT OR UPDATE OF local_broker_engagement_id ON mkt_quote
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION mkt_require_local_broker_settlement();

CREATE FUNCTION mkt_reject_local_broker_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Local broker receipts are immutable'; END $$;
CREATE TRIGGER mkt_local_broker_engagement_immutable BEFORE UPDATE OR DELETE ON mkt_local_broker_engagement FOR EACH ROW EXECUTE FUNCTION mkt_reject_local_broker_receipt_mutation();
CREATE TRIGGER mkt_local_broker_negotiation_immutable BEFORE UPDATE OR DELETE ON mkt_local_broker_negotiation_receipt FOR EACH ROW EXECUTE FUNCTION mkt_reject_local_broker_receipt_mutation();
