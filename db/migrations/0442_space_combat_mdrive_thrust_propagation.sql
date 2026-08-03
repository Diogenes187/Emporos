INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-010',
 'Raymond approved resolving the second M-drive hit by halving then-current Thrust after the first-hit reduction and rounding fractional Thrust down.'
FROM rule_rule WHERE rule_code='combat.space.hit-locations';

CREATE TABLE senc_mdrive_thrust_damage_receipt(
 damage_location_hit_receipt_id bigint NOT NULL REFERENCES senc_damage_location_hit_receipt(damage_location_hit_receipt_id),
 senc_vessel_id bigint NOT NULL,engagement_id bigint NOT NULL,campaign_id bigint NOT NULL,
 ship_id bigint NOT NULL,system_hit_ordinal smallint NOT NULL CHECK(system_hit_ordinal BETWEEN 1 AND 3),
 thrust_before smallint NOT NULL CHECK(thrust_before>=0),thrust_after smallint NOT NULL CHECK(thrust_after>=0 AND thrust_after<=thrust_before),
 speed_preserved numeric NOT NULL CHECK(speed_preserved>=0),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(damage_location_hit_receipt_id,senc_vessel_id),
 FOREIGN KEY(senc_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 CHECK(thrust_after=CASE system_hit_ordinal WHEN 1 THEN greatest(0,thrust_before-1)
  WHEN 2 THEN floor(thrust_before::numeric/2)::smallint ELSE 0 END)
);

CREATE FUNCTION senc_apply_mdrive_thrust_damage() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE vessel_row record; new_thrust smallint;
BEGIN
 IF NEW.applied_location<>'m-drive' OR NEW.system_hits_after IS NULL OR NEW.system_hits_after=NEW.system_hits_before THEN
  RETURN NEW;
 END IF;
 FOR vessel_row IN
  SELECT vessel.* FROM senc_vessel vessel JOIN senc_engagement engagement USING(engagement_id)
  WHERE vessel.ship_id=NEW.target_ship_id AND vessel.campaign_id=NEW.campaign_id
   AND engagement.engagement_status='active' AND vessel.vessel_status IN('engaged','disabled')
  ORDER BY vessel.senc_vessel_id FOR UPDATE OF vessel
 LOOP
  new_thrust:=CASE NEW.system_hits_after WHEN 1 THEN greatest(0,vessel_row.thrust_current-1)
   WHEN 2 THEN floor(vessel_row.thrust_current::numeric/2)::smallint ELSE 0 END;
  UPDATE senc_vessel SET thrust_current=new_thrust WHERE senc_vessel_id=vessel_row.senc_vessel_id;
  INSERT INTO senc_mdrive_thrust_damage_receipt(damage_location_hit_receipt_id,senc_vessel_id,engagement_id,campaign_id,
   ship_id,system_hit_ordinal,thrust_before,thrust_after,speed_preserved)
  VALUES(NEW.damage_location_hit_receipt_id,vessel_row.senc_vessel_id,vessel_row.engagement_id,vessel_row.campaign_id,
   vessel_row.ship_id,NEW.system_hits_after,vessel_row.thrust_current,new_thrust,vessel_row.speed_current);
 END LOOP;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_damage_location_mdrive_thrust
AFTER INSERT ON senc_damage_location_hit_receipt
FOR EACH ROW EXECUTE FUNCTION senc_apply_mdrive_thrust_damage();

CREATE FUNCTION senc_reject_mdrive_thrust_damage_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'M-drive Thrust damage receipts are immutable'; END $$;
CREATE TRIGGER senc_mdrive_thrust_damage_immutable BEFORE UPDATE OR DELETE ON senc_mdrive_thrust_damage_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_mdrive_thrust_damage_mutation();
