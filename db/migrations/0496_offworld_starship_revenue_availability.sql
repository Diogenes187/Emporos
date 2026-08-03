INSERT INTO src_locator (
    source_work_id, source_artifact_id, locator_type,
    heading_path, display_citation
)
SELECT DISTINCT ON (work.work_code, source.heading_path)
       artifact.source_work_id, artifact.source_artifact_id, 'heading',
       source.heading_path,
       CASE work.work_code
         WHEN 'cepheus-engine.ogn' THEN
           'Cepheus Engine SRD, Off-World Travel: ' || source.label
         ELSE 'Cepheus Engine v9.1, Off-World Travel: ' || source.label
       END
FROM src_artifact artifact
JOIN src_work work USING (source_work_id)
CROSS JOIN (VALUES
    ('Off-World Travel > Starship Revenue', 'Starship Revenue'),
    ('Off-World Travel > Starship Revenue > Bulk Cargo', 'Bulk Cargo'),
    ('Off-World Travel > Starship Revenue > Passengers', 'Passengers'),
    ('Off-World Travel > Starship Revenue > Mail and Incidentals', 'Mail and Incidentals'),
    ('Off-World Travel > Starship Revenue > Charters', 'Charters')
) source(heading_path, label)
WHERE artifact.source_uri IN (
    'src/book2/off-world-travel.md',
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-off-world-travel/'
)
ORDER BY work.work_code, source.heading_path, artifact.source_artifact_id
ON CONFLICT DO NOTHING;

WITH package AS (
    SELECT content_package_id FROM sys_content_package
    WHERE package_code='cepheus-engine'
)
INSERT INTO rule_rule (
    content_package_id, rule_code, name, rule_category, rule_status, description
)
SELECT content_package_id, 'travel.starship-revenue', 'Starship Revenue',
       'travel', 'approved',
       'Freight and passenger availability, delivery revenue, postal contracts, and charter pricing.'
FROM package;

CREATE TABLE rule_ship_revenue_system (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    availability_refresh_days smallint NOT NULL CHECK (availability_refresh_days=3),
    freight_payment_per_ton_credits integer NOT NULL CHECK (freight_payment_per_ton_credits=1000),
    postal_reserved_tons smallint NOT NULL CHECK (postal_reserved_tons=5),
    postal_payment_credits integer NOT NULL CHECK (postal_payment_credits=25000),
    postal_actual_dice_count smallint NOT NULL CHECK (postal_actual_dice_count=1),
    postal_actual_die_sides smallint NOT NULL CHECK (postal_actual_die_sides=6),
    postal_actual_modifier smallint NOT NULL CHECK (postal_actual_modifier=-1),
    postal_actual_maximum_tons smallint NOT NULL CHECK (postal_actual_maximum_tons=5),
    armed_ship_required boolean NOT NULL CHECK (armed_ship_required),
    active_gunner_required boolean NOT NULL CHECK (active_gunner_required),
    freight_and_passengers_rolled_together boolean NOT NULL CHECK (freight_and_passengers_rolled_together)
);

INSERT INTO rule_ship_revenue_system
SELECT rule_id,3,1000,5,25000,1,6,-1,5,true,true,true
FROM rule_rule WHERE rule_code='travel.starship-revenue';

CREATE TABLE rule_ship_charter_rate (
    charter_kind text PRIMARY KEY CHECK (charter_kind IN ('non-starship','starship')),
    billing_block_hours integer NOT NULL CHECK (billing_block_hours>0),
    minimum_blocks smallint NOT NULL CHECK (minimum_blocks>0),
    hull_ton_rate_credits integer,
    cargo_ton_rate_credits integer,
    high_berth_rate_credits integer,
    low_berth_rate_credits integer,
    owner_pays_overhead boolean NOT NULL,
    owner_supplies_crew boolean NOT NULL,
    CHECK (
      (charter_kind='non-starship' AND hull_ton_rate_credits=1
       AND cargo_ton_rate_credits IS NULL AND high_berth_rate_credits IS NULL
       AND low_berth_rate_credits IS NULL)
      OR
      (charter_kind='starship' AND hull_ton_rate_credits IS NULL
       AND cargo_ton_rate_credits=900 AND high_berth_rate_credits=9000
       AND low_berth_rate_credits=900)
    )
);

INSERT INTO rule_ship_charter_rate VALUES
    ('non-starship',1,12,1,NULL,NULL,NULL,true,true),
    ('starship',336,1,NULL,900,9000,900,true,true);

INSERT INTO src_record_provenance (
    rule_id, content_package_id, source_locator_id,
    provenance_class, is_primary_citation
)
SELECT rule.rule_id, rule.content_package_id, locator.source_locator_id,
       CASE work.work_code
         WHEN 'cepheus-engine.ogn' THEN 'direct'
         ELSE 'corroborating'
       END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule
CROSS JOIN src_locator locator
JOIN src_work work USING (source_work_id)
WHERE rule.rule_code='travel.starship-revenue'
  AND locator.heading_path LIKE 'Off-World Travel > Starship Revenue%'
  AND work.work_code IN ('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE journey_revenue_availability_cycle (
    revenue_availability_cycle_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
    origin_location_id bigint NOT NULL,
    destination_location_id bigint NOT NULL,
    starport_code text NOT NULL REFERENCES rule_starport_class(starport_code),
    available_day bigint NOT NULL,
    refresh_number integer NOT NULL CHECK (refresh_number>0),
    cycle_status text NOT NULL DEFAULT 'open' CHECK (cycle_status IN ('open','finalized','expired')),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (concurrency_version>0),
    source_command_id bigint REFERENCES cmd_command(command_id),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (origin_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (destination_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id),
    UNIQUE (revenue_availability_cycle_id,campaign_id),
    UNIQUE (campaign_id,origin_location_id,destination_location_id,refresh_number),
    UNIQUE (campaign_id,origin_location_id,destination_location_id,available_day),
    CHECK (origin_location_id<>destination_location_id)
);

CREATE FUNCTION journey_validate_revenue_cycle_refresh()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE previous_day bigint; previous_refresh integer;
BEGIN
    SELECT available_day,refresh_number INTO previous_day,previous_refresh
    FROM journey_revenue_availability_cycle
    WHERE campaign_id=NEW.campaign_id
      AND origin_location_id=NEW.origin_location_id
      AND destination_location_id=NEW.destination_location_id
      AND revenue_availability_cycle_id<>coalesce(NEW.revenue_availability_cycle_id,0)
      AND refresh_number<NEW.refresh_number
    ORDER BY refresh_number DESC LIMIT 1;
    IF NEW.refresh_number=1 THEN
        IF previous_day IS NOT NULL THEN
            RAISE EXCEPTION 'First revenue cycle cannot follow an earlier refresh' USING ERRCODE='23514';
        END IF;
    ELSIF previous_refresh IS NULL OR previous_refresh<>NEW.refresh_number-1
       OR NEW.available_day<previous_day+3 THEN
        RAISE EXCEPTION 'Revenue availability refreshes require the preceding cycle and three campaign days' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_revenue_cycle_refresh_valid
BEFORE INSERT OR UPDATE OF campaign_id,origin_location_id,destination_location_id,
    available_day,refresh_number ON journey_revenue_availability_cycle
FOR EACH ROW EXECUTE FUNCTION journey_validate_revenue_cycle_refresh();

CREATE TABLE journey_revenue_availability_draw (
    revenue_availability_cycle_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    traffic_kind text NOT NULL CHECK (traffic_kind IN ('freight_tons','high_passengers','middle_passengers','low_passengers')),
    dice_count smallint NOT NULL CHECK (dice_count>=0),
    die_sides smallint NOT NULL CHECK (die_sides>=0),
    flat_modifier smallint NOT NULL,
    multiplier smallint NOT NULL CHECK (multiplier>0),
    natural_total smallint NOT NULL CHECK (natural_total>=0),
    available_quantity integer NOT NULL CHECK (available_quantity>=0),
    PRIMARY KEY (revenue_availability_cycle_id,traffic_kind),
    FOREIGN KEY (revenue_availability_cycle_id,campaign_id)
        REFERENCES journey_revenue_availability_cycle(revenue_availability_cycle_id,campaign_id),
    CHECK (
      (dice_count=0 AND die_sides=0 AND natural_total=0)
      OR (dice_count>0 AND die_sides>1 AND natural_total BETWEEN dice_count AND dice_count*die_sides)
    ),
    CHECK (available_quantity=greatest(0,natural_total+flat_modifier)*multiplier)
);

CREATE TABLE journey_revenue_availability_receipt (
    revenue_availability_cycle_id bigint PRIMARY KEY,
    campaign_id bigint NOT NULL,
    draw_count smallint NOT NULL CHECK (draw_count=4),
    finalized_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (revenue_availability_cycle_id,campaign_id)
        REFERENCES journey_revenue_availability_cycle(revenue_availability_cycle_id,campaign_id)
);

CREATE FUNCTION journey_validate_revenue_availability_draw()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cycle journey_revenue_availability_cycle%ROWTYPE; expression rule_starport_traffic_expression%ROWTYPE;
BEGIN
    SELECT * INTO STRICT cycle FROM journey_revenue_availability_cycle
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id FOR UPDATE;
    IF cycle.campaign_id<>NEW.campaign_id OR cycle.cycle_status<>'open' THEN
        RAISE EXCEPTION 'Revenue draws require their open campaign cycle' USING ERRCODE='23514';
    END IF;
    SELECT * INTO STRICT expression FROM rule_starport_traffic_expression
    WHERE starport_code=cycle.starport_code AND traffic_kind=NEW.traffic_kind;
    IF (NEW.dice_count,NEW.die_sides,NEW.flat_modifier,NEW.multiplier)
       IS DISTINCT FROM
       (expression.dice_count,expression.die_sides,expression.flat_modifier,expression.multiplier) THEN
        RAISE EXCEPTION 'Revenue draw expression does not match the starport table' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_revenue_availability_draw_valid
BEFORE INSERT OR UPDATE ON journey_revenue_availability_draw
FOR EACH ROW EXECUTE FUNCTION journey_validate_revenue_availability_draw();

CREATE FUNCTION journey_finalize_revenue_availability()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_count integer; current_status text;
BEGIN
    SELECT cycle_status INTO STRICT current_status
    FROM journey_revenue_availability_cycle
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id
      AND campaign_id=NEW.campaign_id FOR UPDATE;
    SELECT count(*) INTO actual_count FROM journey_revenue_availability_draw
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id;
    IF current_status<>'open' OR actual_count<>4 OR NEW.draw_count<>actual_count THEN
        RAISE EXCEPTION 'Revenue availability finalization requires all four simultaneous draws' USING ERRCODE='23514';
    END IF;
    UPDATE journey_revenue_availability_cycle
    SET cycle_status='finalized',concurrency_version=concurrency_version+1
    WHERE revenue_availability_cycle_id=NEW.revenue_availability_cycle_id;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_revenue_availability_finalize
BEFORE INSERT ON journey_revenue_availability_receipt
FOR EACH ROW EXECUTE FUNCTION journey_finalize_revenue_availability();

CREATE FUNCTION journey_reject_revenue_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'Starship revenue draws and receipts are immutable';
END $$;

CREATE TRIGGER journey_revenue_draw_immutable
BEFORE UPDATE OR DELETE ON journey_revenue_availability_draw
FOR EACH ROW EXECUTE FUNCTION journey_reject_revenue_receipt_mutation();
CREATE TRIGGER journey_revenue_receipt_immutable
BEFORE UPDATE OR DELETE ON journey_revenue_availability_receipt
FOR EACH ROW EXECUTE FUNCTION journey_reject_revenue_receipt_mutation();

CREATE FUNCTION journey_guard_revenue_cycle_state()
RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
    IF OLD.cycle_status='finalized' AND (
       NEW.campaign_id,NEW.origin_location_id,NEW.destination_location_id,
       NEW.starport_code,NEW.available_day,NEW.refresh_number
    ) IS DISTINCT FROM (
       OLD.campaign_id,OLD.origin_location_id,OLD.destination_location_id,
       OLD.starport_code,OLD.available_day,OLD.refresh_number
    ) THEN
        RAISE EXCEPTION 'Finalized revenue cycle facts are immutable' USING ERRCODE='23514';
    END IF;
    IF OLD.cycle_status='finalized' AND NEW.cycle_status='open' THEN
        RAISE EXCEPTION 'Finalized revenue cycle cannot reopen' USING ERRCODE='23514';
    END IF;
    IF NEW.concurrency_version<>OLD.concurrency_version+1 THEN
        RAISE EXCEPTION 'Revenue cycle update requires the next concurrency version' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER journey_revenue_cycle_state_guard
BEFORE UPDATE ON journey_revenue_availability_cycle
FOR EACH ROW EXECUTE FUNCTION journey_guard_revenue_cycle_state();
