ALTER TABLE rule_space_combat_procedure
    ADD COLUMN higher_thrust_breaks_initiative_ties boolean NOT NULL DEFAULT true,
    ADD COLUMN remaining_initiative_ties_simultaneous boolean NOT NULL DEFAULT true,
    ADD COLUMN vessel_crew_acts_together boolean NOT NULL DEFAULT true,
    ADD COLUMN initiative_is_dynamic boolean NOT NULL DEFAULT true;

CREATE TABLE senc_vessel_turn_order_receipt (
    space_combat_round_id bigint NOT NULL,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    senc_vessel_id bigint NOT NULL,
    initiative_snapshot integer NOT NULL,
    thrust_snapshot smallint NOT NULL CHECK (thrust_snapshot >= 0),
    turn_order_rank smallint NOT NULL CHECK (turn_order_rank > 0),
    simultaneous_group_size smallint NOT NULL CHECK (simultaneous_group_size > 0),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (space_combat_round_id,senc_vessel_id),
    FOREIGN KEY (space_combat_round_id,engagement_id,campaign_id)
        REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
    FOREIGN KEY (senc_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id)
);

COMMENT ON TABLE senc_vessel_turn_order_receipt IS
    'Immutable per-round initiative and Thrust snapshots defining vessel order and simultaneous groups.';

CREATE UNIQUE INDEX senc_one_unfinished_round_per_engagement
    ON senc_round(engagement_id)
    WHERE round_status IN ('open','resolving_damage');

CREATE FUNCTION senc_reject_turn_order_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'Space combat turn-order receipts are immutable';
END;
$$;

CREATE TRIGGER senc_vessel_turn_order_receipt_immutable
BEFORE UPDATE OR DELETE ON senc_vessel_turn_order_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_turn_order_receipt_mutation();

CREATE FUNCTION senc_open_next_round(p_engagement_id bigint)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
    engagement senc_engagement%ROWTYPE;
    next_round integer;
    new_round_id bigint;
BEGIN
    SELECT * INTO STRICT engagement
    FROM senc_engagement
    WHERE engagement_id=p_engagement_id
    FOR UPDATE;

    IF engagement.engagement_status<>'active' THEN
        RAISE EXCEPTION 'Space combat round requires an active engagement'
            USING ERRCODE='23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM senc_round
        WHERE engagement_id=p_engagement_id
          AND round_status IN ('open','resolving_damage')
    ) THEN
        RAISE EXCEPTION 'Space combat engagement already has an unfinished round'
            USING ERRCODE='23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM senc_vessel
        WHERE engagement_id=p_engagement_id
          AND vessel_status='engaged'
          AND initiative_current IS NULL
    ) THEN
        RAISE EXCEPTION 'Every engaged vessel requires initiative before opening a round'
            USING ERRCODE='23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM senc_vessel
        WHERE engagement_id=p_engagement_id
          AND vessel_status='engaged'
    ) THEN
        RAISE EXCEPTION 'Space combat round requires an engaged vessel'
            USING ERRCODE='23514';
    END IF;

    next_round:=coalesce(engagement.current_round,0)+1;
    INSERT INTO senc_round(engagement_id,campaign_id,round_number)
    VALUES (engagement.engagement_id,engagement.campaign_id,next_round)
    RETURNING space_combat_round_id INTO new_round_id;

    INSERT INTO senc_vessel_turn_order_receipt(
        space_combat_round_id,engagement_id,campaign_id,senc_vessel_id,
        initiative_snapshot,thrust_snapshot,turn_order_rank,
        simultaneous_group_size
    )
    SELECT new_round_id,v.engagement_id,v.campaign_id,v.senc_vessel_id,
           v.initiative_current,v.thrust_current,
           dense_rank() OVER (
               ORDER BY v.initiative_current DESC,v.thrust_current DESC
           )::smallint,
           count(*) OVER (
               PARTITION BY v.initiative_current,v.thrust_current
           )::smallint
    FROM senc_vessel v
    WHERE v.engagement_id=p_engagement_id
      AND v.vessel_status='engaged';

    UPDATE senc_engagement
    SET current_round=next_round
    WHERE engagement_id=p_engagement_id;
    RETURN new_round_id;
END;
$$;

CREATE OR REPLACE FUNCTION senc_validate_crew_turn()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    vessel_ship bigint;
    assignment_ship bigint;
    assignment_status text;
    ordered_initiative integer;
BEGIN
    SELECT ship_id INTO vessel_ship
    FROM senc_vessel
    WHERE senc_vessel_id=NEW.senc_vessel_id
      AND engagement_id=NEW.engagement_id
      AND campaign_id=NEW.campaign_id;
    SELECT ship_id,duty_status INTO assignment_ship,assignment_status
    FROM ship_crew_assignment
    WHERE crew_assignment_id=NEW.crew_assignment_id;
    IF vessel_ship<>assignment_ship OR assignment_status<>'active' THEN
        RAISE EXCEPTION
            'Space combat crew turn requires active crew aboard vessel'
            USING ERRCODE='23514';
    END IF;
    SELECT initiative_snapshot INTO ordered_initiative
    FROM senc_vessel_turn_order_receipt
    WHERE space_combat_round_id=NEW.space_combat_round_id
      AND senc_vessel_id=NEW.senc_vessel_id
      AND engagement_id=NEW.engagement_id
      AND campaign_id=NEW.campaign_id;
    IF ordered_initiative IS NULL
       OR NEW.initiative_at_action<>ordered_initiative THEN
        RAISE EXCEPTION
            'Space combat crew turn must match its vessel turn-order receipt'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE FUNCTION senc_validate_turn_order_receipt_set()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    expected_count integer;
    actual_count integer;
BEGIN
    SELECT count(*) INTO expected_count
    FROM senc_vessel
    WHERE engagement_id=NEW.engagement_id
      AND vessel_status='engaged';
    SELECT count(*) INTO actual_count
    FROM senc_vessel_turn_order_receipt
    WHERE space_combat_round_id=NEW.space_combat_round_id;
    IF actual_count<>expected_count THEN
        RAISE EXCEPTION 'Space combat turn-order receipt set is incomplete'
            USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER senc_turn_order_receipt_set_complete
AFTER INSERT ON senc_vessel_turn_order_receipt
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION senc_validate_turn_order_receipt_set();
