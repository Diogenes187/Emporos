INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT DISTINCT ON(work.work_code) artifact.source_work_id,artifact.source_artifact_id,'heading',
       'Trade and Commerce > Determine Goods Available',
       CASE work.work_code WHEN 'cepheus-engine.ogn'
         THEN 'Cepheus Engine SRD, Trade and Commerce: Determine Goods Available'
         ELSE 'Cepheus Engine v9.1, Trade and Commerce: Determine Goods Available' END
FROM src_artifact artifact JOIN src_work work USING(source_work_id)
WHERE artifact.source_uri IN(
 'src/book2/trade-and-commerce.md',
 'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-trade-and-commerce/'
)
ORDER BY work.work_code,artifact.source_artifact_id
ON CONFLICT DO NOTHING;

WITH package AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'trade.supplier-stock-generation','Supplier Stock Generation','trade','approved',
       'All common goods plus one D6 random D66 goods, with black-market exceptions and additive duplicate quantities.'
FROM package;

CREATE TABLE rule_supplier_stock_generation(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 common_goods_included boolean NOT NULL CHECK(common_goods_included),
 random_good_count_dice smallint NOT NULL CHECK(random_good_count_dice=1),
 random_good_count_sides smallint NOT NULL CHECK(random_good_count_sides=6),
 random_selection_dice smallint NOT NULL CHECK(random_selection_dice=2),
 random_selection_sides smallint NOT NULL CHECK(random_selection_sides=6),
 legal_ignores_illegal_results boolean NOT NULL CHECK(legal_ignores_illegal_results),
 duplicate_quantities_add boolean NOT NULL CHECK(duplicate_quantities_add),
 black_market_includes_matching_illegal boolean NOT NULL CHECK(black_market_includes_matching_illegal)
);
INSERT INTO rule_supplier_stock_generation
SELECT rule_id,true,1,6,2,6,true,true,true FROM rule_rule
WHERE rule_code='trade.supplier-stock-generation';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
 CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
 work.work_code='cepheus-engine.ogn'
FROM rule_rule rule CROSS JOIN src_locator locator JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='trade.supplier-stock-generation'
 AND locator.heading_path='Trade and Commerce > Determine Goods Available'
 AND work.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE mkt_supplier_stock_generation(
 supplier_stock_generation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 campaign_id bigint NOT NULL,
 market_session_id bigint NOT NULL,
 supplier_id bigint NOT NULL UNIQUE,
 world_profile_id bigint NOT NULL REFERENCES loc_world_profile(world_profile_id),
 market_kind_snapshot text NOT NULL CHECK(market_kind_snapshot IN('legal','black','mixed','private')),
 random_good_count_roll smallint NOT NULL CHECK(random_good_count_roll BETWEEN 1 AND 6),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint REFERENCES cmd_command(command_id),
 FOREIGN KEY(market_session_id,campaign_id) REFERENCES mkt_session(market_session_id,campaign_id),
 FOREIGN KEY(supplier_id,campaign_id) REFERENCES mkt_supplier(supplier_id,campaign_id),
 UNIQUE(supplier_stock_generation_id,campaign_id)
);

CREATE TABLE mkt_supplier_stock_selection_draw(
 supplier_stock_generation_id bigint NOT NULL REFERENCES mkt_supplier_stock_generation(supplier_stock_generation_id),
 selection_order smallint NOT NULL CHECK(selection_order>0),
 tens_die smallint NOT NULL CHECK(tens_die BETWEEN 1 AND 6),
 ones_die smallint NOT NULL CHECK(ones_die BETWEEN 1 AND 6),
 d66_result smallint NOT NULL,
 trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),
 selection_outcome text NOT NULL CHECK(selection_outcome IN('included','ignored-illegal','unusual-referee')),
 PRIMARY KEY(supplier_stock_generation_id,selection_order),
 CHECK(d66_result=tens_die*10+ones_die)
);

CREATE TABLE mkt_supplier_stock_quantity_draw(
 supplier_stock_generation_id bigint NOT NULL REFERENCES mkt_supplier_stock_generation(supplier_stock_generation_id),
 source_kind text NOT NULL CHECK(source_kind IN('common','random','matched-illegal')),
 source_order smallint NOT NULL CHECK(source_order>0),
 trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),
 die_order smallint NOT NULL CHECK(die_order>0),
 die_sides smallint NOT NULL CHECK(die_sides>1),
 result smallint NOT NULL CHECK(result>0 AND result<=die_sides),
 multiplier smallint NOT NULL CHECK(multiplier>0),
 PRIMARY KEY(supplier_stock_generation_id,source_kind,source_order,die_order)
);

CREATE TABLE mkt_supplier_stock_result(
 supplier_stock_generation_id bigint NOT NULL REFERENCES mkt_supplier_stock_generation(supplier_stock_generation_id),
 trade_good_rule_id bigint NOT NULL REFERENCES rule_trade_good(trade_good_rule_id),
 stock_id bigint NOT NULL UNIQUE,
 campaign_id bigint NOT NULL,
 occurrence_count smallint NOT NULL CHECK(occurrence_count>0),
 quantity_tons numeric NOT NULL CHECK(quantity_tons>0),
 PRIMARY KEY(supplier_stock_generation_id,trade_good_rule_id),
 FOREIGN KEY(stock_id,campaign_id) REFERENCES mkt_stock(stock_id,campaign_id)
);

CREATE TABLE mkt_supplier_stock_final_receipt(
 supplier_stock_generation_id bigint PRIMARY KEY REFERENCES mkt_supplier_stock_generation(supplier_stock_generation_id),
 selection_attempt_count smallint NOT NULL CHECK(selection_attempt_count BETWEEN 1 AND 6),
 included_random_count smallint NOT NULL CHECK(included_random_count BETWEEN 0 AND 6),
 ignored_selection_count smallint NOT NULL CHECK(ignored_selection_count BETWEEN 0 AND 6),
 distinct_stock_count smallint NOT NULL CHECK(distinct_stock_count>0),
 total_quantity_tons numeric NOT NULL CHECK(total_quantity_tons>0),
 finalized_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 source_command_id bigint REFERENCES cmd_command(command_id)
);

CREATE FUNCTION mkt_validate_supplier_stock_generation() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE supplier mkt_supplier%ROWTYPE; market_kind text; market_location bigint; profile_location bigint;
BEGIN
 SELECT * INTO STRICT supplier FROM mkt_supplier WHERE supplier_id=NEW.supplier_id AND campaign_id=NEW.campaign_id;
 SELECT market.market_kind,market.location_id INTO STRICT market_kind,market_location
 FROM mkt_session session JOIN mkt_market market USING(market_id,campaign_id)
 WHERE session.market_session_id=NEW.market_session_id AND session.campaign_id=NEW.campaign_id;
 SELECT location_id INTO STRICT profile_location FROM loc_world_profile
 WHERE world_profile_id=NEW.world_profile_id AND campaign_id=NEW.campaign_id AND profile_status='current';
 IF supplier.market_session_id<>NEW.market_session_id OR supplier.supplier_kind<>'supplier'
    OR market_kind<>NEW.market_kind_snapshot OR market_location<>profile_location THEN
  RAISE EXCEPTION 'Supplier stock generation scope does not match supplier, market, or current world' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_supplier_stock_generation_valid BEFORE INSERT ON mkt_supplier_stock_generation
FOR EACH ROW EXECUTE FUNCTION mkt_validate_supplier_stock_generation();

CREATE FUNCTION mkt_validate_supplier_stock_selection() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE generation mkt_supplier_stock_generation%ROWTYPE; good rule_trade_good%ROWTYPE; expected text;
BEGIN
 SELECT * INTO STRICT generation FROM mkt_supplier_stock_generation WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id;
 SELECT * INTO STRICT good FROM rule_trade_good WHERE trade_good_rule_id=NEW.trade_good_rule_id;
 expected:=CASE WHEN good.d66_result=66 THEN 'unusual-referee'
   WHEN good.black_market_only AND generation.market_kind_snapshot NOT IN('black','mixed') THEN 'ignored-illegal'
   ELSE 'included' END;
 IF NEW.selection_order>generation.random_good_count_roll OR good.d66_result<>NEW.d66_result
    OR NEW.selection_outcome<>expected THEN
  RAISE EXCEPTION 'Supplier stock selection does not match D66 or market legality' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_supplier_stock_selection_valid BEFORE INSERT ON mkt_supplier_stock_selection_draw
FOR EACH ROW EXECUTE FUNCTION mkt_validate_supplier_stock_selection();

CREATE FUNCTION mkt_validate_supplier_stock_quantity_draw() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE generation mkt_supplier_stock_generation%ROWTYPE; good rule_trade_good%ROWTYPE;
BEGIN
 SELECT * INTO STRICT generation FROM mkt_supplier_stock_generation WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id;
 SELECT * INTO STRICT good FROM rule_trade_good WHERE trade_good_rule_id=NEW.trade_good_rule_id;
 IF NEW.die_order>good.availability_dice_count OR NEW.die_sides<>good.availability_die_sides
    OR NEW.multiplier<>good.availability_multiplier OR good.good_kind='unusual'
    OR (NEW.source_kind='common' AND (good.good_kind<>'common' OR NEW.source_order<>(
       SELECT count(*) FROM rule_trade_good ordered
       WHERE ordered.good_kind='common' AND ordered.good_code<=good.good_code)))
    OR (NEW.source_kind='random' AND NOT EXISTS(
       SELECT 1 FROM mkt_supplier_stock_selection_draw selection
       WHERE selection.supplier_stock_generation_id=NEW.supplier_stock_generation_id
         AND selection.selection_order=NEW.source_order AND selection.trade_good_rule_id=NEW.trade_good_rule_id
         AND selection.selection_outcome='included'))
    OR (NEW.source_kind='matched-illegal' AND (generation.market_kind_snapshot NOT IN('black','mixed')
       OR NOT good.black_market_only OR NOT EXISTS(
         SELECT 1 FROM rule_trade_good_modifier modifier JOIN loc_world_trade_code world_code
           ON world_code.trade_code_rule_id=modifier.trade_code_rule_id
         WHERE modifier.trade_good_rule_id=NEW.trade_good_rule_id
           AND world_code.world_profile_id=generation.world_profile_id))) THEN
  RAISE EXCEPTION 'Supplier quantity draw does not match its published stock source' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_supplier_stock_quantity_valid BEFORE INSERT ON mkt_supplier_stock_quantity_draw
FOR EACH ROW EXECUTE FUNCTION mkt_validate_supplier_stock_quantity_draw();

CREATE FUNCTION mkt_validate_supplier_stock_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE generation mkt_supplier_stock_generation%ROWTYPE; selections integer; included integer; ignored integer;
        expected_matched integer; actual_matched integer; bad_occurrences integer; result_count integer;
        result_total numeric; bad_results integer;
BEGIN
 SELECT * INTO STRICT generation FROM mkt_supplier_stock_generation WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id;
 SELECT count(*),count(*) FILTER(WHERE selection_outcome='included'),count(*) FILTER(WHERE selection_outcome<>'included')
 INTO selections,included,ignored FROM mkt_supplier_stock_selection_draw WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id;
 SELECT count(DISTINCT good.trade_good_rule_id) INTO expected_matched
 FROM rule_trade_good good WHERE good.black_market_only AND generation.market_kind_snapshot IN('black','mixed')
 AND EXISTS(SELECT 1 FROM rule_trade_good_modifier modifier JOIN loc_world_trade_code world_code
   ON world_code.trade_code_rule_id=modifier.trade_code_rule_id
   WHERE modifier.trade_good_rule_id=good.trade_good_rule_id AND world_code.world_profile_id=generation.world_profile_id);
 SELECT count(DISTINCT trade_good_rule_id) INTO actual_matched FROM mkt_supplier_stock_quantity_draw
 WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id AND source_kind='matched-illegal';
 SELECT count(*) INTO bad_occurrences FROM(
   SELECT draw.source_kind,draw.source_order,draw.trade_good_rule_id
   FROM mkt_supplier_stock_quantity_draw draw JOIN rule_trade_good good USING(trade_good_rule_id)
   WHERE draw.supplier_stock_generation_id=NEW.supplier_stock_generation_id
   GROUP BY draw.source_kind,draw.source_order,draw.trade_good_rule_id,good.availability_dice_count
   HAVING count(*)<>good.availability_dice_count
 ) bad;
 SELECT count(*),coalesce(sum(quantity_tons),0) INTO result_count,result_total
 FROM mkt_supplier_stock_result WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id;
 SELECT count(*) INTO bad_results FROM mkt_supplier_stock_result result
 JOIN mkt_stock stock USING(stock_id,campaign_id) WHERE result.supplier_stock_generation_id=NEW.supplier_stock_generation_id
 AND (stock.market_session_id<>generation.market_session_id OR stock.supplier_id<>generation.supplier_id
   OR stock.trade_good_rule_id<>result.trade_good_rule_id OR stock.quantity_tons<>result.quantity_tons
   OR result.quantity_tons<>(SELECT sum(draw.result*draw.multiplier) FROM mkt_supplier_stock_quantity_draw draw
      WHERE draw.supplier_stock_generation_id=result.supplier_stock_generation_id AND draw.trade_good_rule_id=result.trade_good_rule_id)
   OR result.occurrence_count<>(SELECT count(*) FROM(SELECT DISTINCT source_kind,source_order
      FROM mkt_supplier_stock_quantity_draw draw WHERE draw.supplier_stock_generation_id=result.supplier_stock_generation_id
       AND draw.trade_good_rule_id=result.trade_good_rule_id) occurrence));
 IF selections<>generation.random_good_count_roll OR actual_matched<>expected_matched OR bad_occurrences<>0
   OR NOT EXISTS(SELECT 1 FROM mkt_supplier_stock_quantity_draw draw JOIN rule_trade_good good USING(trade_good_rule_id)
      WHERE draw.supplier_stock_generation_id=NEW.supplier_stock_generation_id AND draw.source_kind='common'
      GROUP BY draw.supplier_stock_generation_id HAVING count(DISTINCT good.trade_good_rule_id)=6)
   OR result_count<>(SELECT count(DISTINCT trade_good_rule_id) FROM mkt_supplier_stock_quantity_draw WHERE supplier_stock_generation_id=NEW.supplier_stock_generation_id)
   OR bad_results<>0 OR (NEW.selection_attempt_count,NEW.included_random_count,NEW.ignored_selection_count,
      NEW.distinct_stock_count,NEW.total_quantity_tons) IS DISTINCT FROM
      (selections,included,ignored,result_count,result_total) THEN
  RAISE EXCEPTION 'Supplier stock final receipt does not match complete published draws and stock' USING ERRCODE='23514';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER mkt_supplier_stock_final_valid BEFORE INSERT ON mkt_supplier_stock_final_receipt
FOR EACH ROW EXECUTE FUNCTION mkt_validate_supplier_stock_final();

CREATE FUNCTION mkt_reject_supplier_stock_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Supplier stock generation receipts are immutable'; END $$;
CREATE TRIGGER mkt_supplier_stock_generation_immutable BEFORE UPDATE OR DELETE ON mkt_supplier_stock_generation FOR EACH ROW EXECUTE FUNCTION mkt_reject_supplier_stock_receipt_mutation();
CREATE TRIGGER mkt_supplier_stock_selection_immutable BEFORE UPDATE OR DELETE ON mkt_supplier_stock_selection_draw FOR EACH ROW EXECUTE FUNCTION mkt_reject_supplier_stock_receipt_mutation();
CREATE TRIGGER mkt_supplier_stock_quantity_immutable BEFORE UPDATE OR DELETE ON mkt_supplier_stock_quantity_draw FOR EACH ROW EXECUTE FUNCTION mkt_reject_supplier_stock_receipt_mutation();
CREATE TRIGGER mkt_supplier_stock_result_immutable BEFORE UPDATE OR DELETE ON mkt_supplier_stock_result FOR EACH ROW EXECUTE FUNCTION mkt_reject_supplier_stock_receipt_mutation();
CREATE TRIGGER mkt_supplier_stock_final_immutable BEFORE UPDATE OR DELETE ON mkt_supplier_stock_final_receipt FOR EACH ROW EXECUTE FUNCTION mkt_reject_supplier_stock_receipt_mutation();
