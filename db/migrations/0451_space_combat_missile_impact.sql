CREATE TABLE senc_missile_impact_attempt(
 missile_impact_attempt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,missile_salvo_id bigint NOT NULL REFERENCES senc_missile_salvo(missile_salvo_id),
 space_combat_round_id bigint NOT NULL,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,attempt_round integer NOT NULL CHECK(attempt_round>0),
 missiles_before smallint NOT NULL CHECK(missiles_before>0),target_number smallint NOT NULL CHECK(target_number BETWEEN 2 AND 12),
 smart_missiles boolean NOT NULL,endurance_expires_after_round integer NOT NULL,attempt_order smallint NOT NULL CHECK(attempt_order>0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id) REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 UNIQUE(missile_salvo_id,attempt_order),UNIQUE(missile_salvo_id,attempt_round));
CREATE TABLE senc_missile_impact_roll(
 missile_impact_attempt_id bigint NOT NULL REFERENCES senc_missile_impact_attempt(missile_impact_attempt_id),missile_order smallint NOT NULL CHECK(missile_order>0),
 die_one smallint NOT NULL CHECK(die_one BETWEEN 1 AND 6),die_two smallint NOT NULL CHECK(die_two BETWEEN 1 AND 6),roll_total smallint NOT NULL,
 target_number smallint NOT NULL,hit boolean NOT NULL,PRIMARY KEY(missile_impact_attempt_id,missile_order),
 CHECK(roll_total=die_one+die_two),CHECK(hit=(roll_total>=target_number)));
CREATE TABLE senc_missile_impact_final_receipt(
 missile_impact_attempt_id bigint PRIMARY KEY REFERENCES senc_missile_impact_attempt(missile_impact_attempt_id),hits smallint NOT NULL CHECK(hits>=0),
 misses smallint NOT NULL CHECK(misses>=0),missiles_remaining_after smallint NOT NULL CHECK(missiles_remaining_after>=0),
 resulting_salvo_status text NOT NULL CHECK(resulting_salvo_status IN('in_flight','impacted','missed')),next_attack_round integer,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),CHECK((resulting_salvo_status='in_flight')=(next_attack_round IS NOT NULL)));

CREATE FUNCTION senc_validate_missile_impact_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE salvo senc_missile_salvo%ROWTYPE; launch senc_missile_launch_receipt%ROWTYPE; actual_round integer; prior_count integer; expected_attempt_round integer;
BEGIN
 SELECT * INTO STRICT salvo FROM senc_missile_salvo WHERE missile_salvo_id=NEW.missile_salvo_id FOR UPDATE;
 SELECT * INTO STRICT launch FROM senc_missile_launch_receipt WHERE missile_launch_receipt_id=salvo.launch_receipt_id;
 SELECT round_number INTO STRICT actual_round FROM senc_round WHERE space_combat_round_id=NEW.space_combat_round_id;
 SELECT count(*) INTO prior_count FROM senc_missile_impact_attempt WHERE missile_salvo_id=NEW.missile_salvo_id;
 IF prior_count=0 THEN expected_attempt_round:=salvo.impact_round; ELSE
  SELECT final.next_attack_round INTO STRICT expected_attempt_round FROM senc_missile_impact_final_receipt final
  JOIN senc_missile_impact_attempt attempt USING(missile_impact_attempt_id) WHERE attempt.missile_salvo_id=NEW.missile_salvo_id
  ORDER BY attempt.attempt_order DESC LIMIT 1;
 END IF;
 IF salvo.engagement_id<>NEW.engagement_id OR salvo.campaign_id<>NEW.campaign_id OR actual_round<>NEW.attempt_round
  OR salvo.salvo_status<>'in_flight' OR salvo.missiles_remaining<>NEW.missiles_before OR NEW.attempt_order<>prior_count+1
  OR NEW.attempt_round<>expected_attempt_round
  OR NEW.target_number<>launch.impact_target_number OR NEW.smart_missiles<>salvo.smart_missiles
  OR NEW.endurance_expires_after_round<>salvo.launched_round+(SELECT endurance_turns FROM rule_space_combat_missile_behavior) THEN
  RAISE EXCEPTION 'Missile impact attempt must occur on its scheduled round with the current surviving salvo' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_missile_impact_attempt_valid BEFORE INSERT ON senc_missile_impact_attempt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_impact_attempt();
CREATE FUNCTION senc_validate_missile_impact_roll() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE attempt senc_missile_impact_attempt%ROWTYPE; BEGIN
 SELECT * INTO STRICT attempt FROM senc_missile_impact_attempt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id FOR UPDATE;
 IF EXISTS(SELECT 1 FROM senc_missile_impact_final_receipt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id)
  OR NEW.missile_order>attempt.missiles_before OR NEW.target_number<>attempt.target_number THEN
  RAISE EXCEPTION 'Missile impact roll must be an unfinalized surviving missile with the launch-derived target' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_missile_impact_roll_valid BEFORE INSERT ON senc_missile_impact_roll FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_impact_roll();
CREATE FUNCTION senc_finalize_missile_impact() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attempt senc_missile_impact_attempt%ROWTYPE; roll_count integer; actual_hits integer; actual_misses integer; expected_remaining integer; expected_status text; expected_next integer;
BEGIN
 SELECT * INTO STRICT attempt FROM senc_missile_impact_attempt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id FOR UPDATE;
 SELECT count(*),count(*) FILTER(WHERE hit),count(*) FILTER(WHERE NOT hit) INTO roll_count,actual_hits,actual_misses
 FROM senc_missile_impact_roll WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id;
 IF roll_count<>attempt.missiles_before THEN RAISE EXCEPTION 'Missile impact requires one roll for every surviving missile' USING ERRCODE='23514'; END IF;
 expected_remaining:=CASE WHEN attempt.smart_missiles AND attempt.attempt_round<attempt.endurance_expires_after_round THEN actual_misses ELSE 0 END;
 expected_status:=CASE WHEN expected_remaining>0 THEN 'in_flight' WHEN actual_hits>0 THEN 'impacted' ELSE 'missed' END;
 expected_next:=CASE WHEN expected_remaining>0 THEN attempt.attempt_round+1 ELSE NULL END;
 IF NEW.hits<>actual_hits OR NEW.misses<>actual_misses OR NEW.missiles_remaining_after<>expected_remaining
  OR NEW.resulting_salvo_status<>expected_status OR NEW.next_attack_round IS DISTINCT FROM expected_next THEN
  RAISE EXCEPTION 'Missile impact final receipt does not match rolls, smart retry, or endurance' USING ERRCODE='23514'; END IF;
 UPDATE senc_missile_salvo SET missiles_remaining=expected_remaining,salvo_status=expected_status WHERE missile_salvo_id=attempt.missile_salvo_id;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_missile_impact_final_valid BEFORE INSERT ON senc_missile_impact_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_finalize_missile_impact();
CREATE FUNCTION senc_reject_missile_impact_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Missile impact receipts and rolls are immutable'; END $$;
CREATE TRIGGER senc_missile_impact_attempt_immutable BEFORE UPDATE OR DELETE ON senc_missile_impact_attempt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_impact_mutation();
CREATE TRIGGER senc_missile_impact_roll_immutable BEFORE UPDATE OR DELETE ON senc_missile_impact_roll FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_impact_mutation();
CREATE TRIGGER senc_missile_impact_final_immutable BEFORE UPDATE OR DELETE ON senc_missile_impact_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_impact_mutation();
