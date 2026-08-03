INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT DISTINCT ON(work.work_code,source.heading_path) artifact.source_work_id,artifact.source_artifact_id,
 'heading',source.heading_path,CASE work.work_code WHEN 'cepheus-engine.ogn'
 THEN 'Cepheus Engine SRD, Trade and Commerce: '||source.label
 ELSE 'Cepheus Engine v9.1, Trade and Commerce: '||source.label END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
CROSS JOIN(VALUES
 ('Trade and Commerce > Determine Purchase Price','Determine Purchase Price'),
 ('Trade and Commerce > Selling Goods','Selling Goods')
) source(heading_path,label)
WHERE artifact.source_uri IN('src/book2/trade-and-commerce.md',
 'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-trade-and-commerce/')
ORDER BY work.work_code,source.heading_path,artifact.source_artifact_id ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'trade.rejected-quote-cooldown','Rejected Quote Cooldown','trade','approved',
 'A rejected purchase or sale quote prevents another negotiation with that counterparty for the same goods for seven days.'
FROM package;
CREATE TABLE rule_rejected_quote_cooldown(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 cooldown_days smallint NOT NULL CHECK(cooldown_days=7),
 purchase_same_supplier_required boolean NOT NULL CHECK(purchase_same_supplier_required),
 sale_new_buyer_allowed boolean NOT NULL CHECK(sale_new_buyer_allowed)
);
INSERT INTO rule_rejected_quote_cooldown SELECT rule_id,7,true,true FROM rule_rule
WHERE rule_code='trade.rejected-quote-cooldown';
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
 work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='trade.rejected-quote-cooldown'
 AND locator.heading_path IN('Trade and Commerce > Determine Purchase Price','Trade and Commerce > Selling Goods')
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

ALTER TABLE mkt_quote ADD COLUMN counterparty_supplier_id bigint,
 ADD COLUMN concurrency_version bigint NOT NULL DEFAULT 1 CHECK(concurrency_version>0),
 ADD CONSTRAINT mkt_quote_counterparty_scope_fkey FOREIGN KEY(counterparty_supplier_id,campaign_id)
 REFERENCES mkt_supplier(supplier_id,campaign_id),
 ADD CONSTRAINT mkt_quote_campaign_key UNIQUE(quote_id,campaign_id);

CREATE TABLE mkt_quote_rejection_receipt(
 quote_id bigint PRIMARY KEY,
 campaign_id bigint NOT NULL,
 market_session_id bigint NOT NULL,
 rejecting_actor_id bigint NOT NULL,
 counterparty_supplier_id bigint NOT NULL,
 trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),
 quote_side text NOT NULL CHECK(quote_side IN('buy','sell')),
 rejected_day bigint NOT NULL,
 rejected_second integer NOT NULL CHECK(rejected_second BETWEEN 0 AND 86399),
 eligible_again_day bigint NOT NULL,
 eligible_again_second integer NOT NULL CHECK(eligible_again_second BETWEEN 0 AND 86399),
 quote_version_before bigint NOT NULL,
 quote_version_after bigint NOT NULL CHECK(quote_version_after=quote_version_before+1),
 rejected_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint REFERENCES cmd_command(command_id),
 FOREIGN KEY(quote_id,campaign_id) REFERENCES mkt_quote(quote_id,campaign_id),
 FOREIGN KEY(market_session_id,campaign_id) REFERENCES mkt_session(market_session_id,campaign_id),
 FOREIGN KEY(rejecting_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(counterparty_supplier_id,campaign_id) REFERENCES mkt_supplier(supplier_id,campaign_id),
 CHECK((eligible_again_day,eligible_again_second)=(rejected_day+7,rejected_second))
);

CREATE FUNCTION mkt_validate_quote_counterparty_and_cooldown() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE counterparty mkt_supplier%ROWTYPE; today bigint; now_second integer;
BEGIN
 IF NEW.counterparty_supplier_id IS NULL THEN RETURN NEW; END IF;
 SELECT * INTO STRICT counterparty FROM mkt_supplier WHERE supplier_id=NEW.counterparty_supplier_id AND campaign_id=NEW.campaign_id;
 SELECT day_number,second_of_day INTO STRICT today,now_second FROM camp_clock WHERE campaign_id=NEW.campaign_id;
 IF counterparty.market_session_id<>NEW.market_session_id
    OR counterparty.supplier_kind<>(CASE NEW.quote_side WHEN 'sell' THEN 'supplier' ELSE 'buyer' END)
    OR NEW.quoted_actor_id IS NULL OR NEW.quoted_faction_id IS NOT NULL THEN
  RAISE EXCEPTION 'Market quote counterparty does not match side, session, or merchant' USING ERRCODE='23514';
 END IF;
 IF EXISTS(SELECT 1 FROM mkt_quote_rejection_receipt rejection
   WHERE rejection.campaign_id=NEW.campaign_id AND rejection.rejecting_actor_id=NEW.quoted_actor_id
    AND rejection.counterparty_supplier_id=NEW.counterparty_supplier_id
    AND rejection.trade_good_rule_id=NEW.trade_good_rule_id AND rejection.quote_side=NEW.quote_side
    AND (rejection.eligible_again_day,rejection.eligible_again_second)>(today,now_second)) THEN
  RAISE EXCEPTION 'Rejected quote counterparty remains unavailable for one week' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_quote_counterparty_cooldown_valid BEFORE INSERT ON mkt_quote
FOR EACH ROW EXECUTE FUNCTION mkt_validate_quote_counterparty_and_cooldown();

CREATE FUNCTION mkt_validate_quote_rejection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE quote mkt_quote%ROWTYPE; today bigint; now_second integer;
BEGIN
 SELECT * INTO STRICT quote FROM mkt_quote WHERE quote_id=NEW.quote_id AND campaign_id=NEW.campaign_id FOR UPDATE;
 SELECT day_number,second_of_day INTO STRICT today,now_second FROM camp_clock WHERE campaign_id=NEW.campaign_id;
 IF quote.quote_status<>'open' OR quote.market_session_id<>NEW.market_session_id
   OR quote.quoted_actor_id<>NEW.rejecting_actor_id OR quote.counterparty_supplier_id<>NEW.counterparty_supplier_id
   OR quote.trade_good_rule_id<>NEW.trade_good_rule_id OR quote.quote_side<>NEW.quote_side
   OR quote.concurrency_version<>NEW.quote_version_before OR NEW.quote_version_after<>quote.concurrency_version+1
   OR (NEW.rejected_day,NEW.rejected_second)<>(today,now_second) THEN
  RAISE EXCEPTION 'Quote rejection receipt does not match open quote, clock, or version' USING ERRCODE='23514';
 END IF;
 UPDATE mkt_quote SET quote_status='rejected',concurrency_version=NEW.quote_version_after WHERE quote_id=NEW.quote_id;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_quote_rejection_valid BEFORE INSERT ON mkt_quote_rejection_receipt
FOR EACH ROW EXECUTE FUNCTION mkt_validate_quote_rejection();

CREATE FUNCTION mkt_guard_rejected_quote() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.quote_status='rejected' AND NEW IS DISTINCT FROM OLD THEN
  RAISE EXCEPTION 'Rejected market quotes are immutable' USING ERRCODE='23514';
 END IF;
 IF OLD.quote_status<>'rejected' AND NEW.quote_status='rejected' AND pg_trigger_depth()<2 THEN
  RAISE EXCEPTION 'Quote rejection requires an immutable rejection receipt' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_rejected_quote_guard BEFORE UPDATE ON mkt_quote FOR EACH ROW EXECUTE FUNCTION mkt_guard_rejected_quote();
CREATE FUNCTION mkt_reject_quote_rejection_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Quote rejection receipts are immutable'; END $$;
CREATE TRIGGER mkt_quote_rejection_immutable BEFORE UPDATE OR DELETE ON mkt_quote_rejection_receipt FOR EACH ROW EXECUTE FUNCTION mkt_reject_quote_rejection_mutation();
