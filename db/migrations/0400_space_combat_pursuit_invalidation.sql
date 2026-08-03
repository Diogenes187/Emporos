DO $$ DECLARE constraint_name text; BEGIN
 SELECT conname INTO STRICT constraint_name FROM pg_constraint
 WHERE conrelid='senc_pursuit'::regclass AND contype='c'
   AND pg_get_constraintdef(oid) LIKE '%attack_modifier = LEAST%';
 EXECUTE format('ALTER TABLE senc_pursuit DROP CONSTRAINT %I',constraint_name);
END $$;
ALTER TABLE senc_pursuit ADD CONSTRAINT senc_pursuit_attack_modifier_state_check CHECK(
 (pursuit_status='active' AND attack_modifier=least(greatest(consecutive_maintained_turns-1,0),4))
 OR (pursuit_status='broken' AND attack_modifier=0)
);

CREATE FUNCTION senc_break_pursuit_for_range()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p senc_pursuit%ROWTYPE; current_round integer; band_order smallint;
BEGIN
 SELECT display_order INTO band_order FROM rule_space_range_band
 WHERE range_band_code=NEW.range_band_code;
 IF band_order<(SELECT automatic_break_minimum_range_order FROM rule_space_combat_pursuit) THEN RETURN NEW; END IF;
 SELECT coalesce(e.current_round,1) INTO current_round FROM senc_engagement e
 WHERE e.engagement_id=NEW.engagement_id;
 FOR p IN SELECT * FROM senc_pursuit
   WHERE engagement_id=NEW.engagement_id AND pursuit_status='active'
     AND ((pursuing_vessel_id=NEW.first_vessel_id AND target_vessel_id=NEW.second_vessel_id)
       OR (pursuing_vessel_id=NEW.second_vessel_id AND target_vessel_id=NEW.first_vessel_id))
   FOR UPDATE
 LOOP
   UPDATE senc_pursuit SET pursuit_status='broken',ended_round=current_round,ended_reason='range',attack_modifier=0
   WHERE pursuit_id=p.pursuit_id;
   INSERT INTO senc_pursuit_transition_receipt
    (pursuit_id,engagement_id,campaign_id,round_number,transition_kind,reason,attack_modifier_before,attack_modifier_after)
   VALUES(p.pursuit_id,p.engagement_id,p.campaign_id,current_round,'broken','range',p.attack_modifier,0);
 END LOOP;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_range_breaks_invalid_pursuit
AFTER INSERT OR UPDATE OF range_band_code ON senc_vessel_range
FOR EACH ROW EXECUTE FUNCTION senc_break_pursuit_for_range();

CREATE FUNCTION senc_break_pursuit_for_speed()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE p senc_pursuit%ROWTYPE; pursuer_speed numeric; current_round integer;
BEGIN
 SELECT coalesce(e.current_round,1) INTO current_round FROM senc_engagement e
 WHERE e.engagement_id=NEW.engagement_id;
 FOR p IN SELECT * FROM senc_pursuit
   WHERE engagement_id=NEW.engagement_id AND pursuit_status='active'
     AND target_vessel_id=NEW.senc_vessel_id FOR UPDATE
 LOOP
   SELECT speed_current INTO pursuer_speed FROM senc_vessel WHERE senc_vessel_id=p.pursuing_vessel_id;
   IF NEW.speed_current>=pursuer_speed+(SELECT automatic_break_speed_advantage FROM rule_space_combat_pursuit) THEN
     UPDATE senc_pursuit SET pursuit_status='broken',ended_round=current_round,ended_reason='speed',attack_modifier=0
     WHERE pursuit_id=p.pursuit_id;
     INSERT INTO senc_pursuit_transition_receipt
      (pursuit_id,engagement_id,campaign_id,round_number,transition_kind,reason,attack_modifier_before,attack_modifier_after)
     VALUES(p.pursuit_id,p.engagement_id,p.campaign_id,current_round,'broken','speed',p.attack_modifier,0);
   END IF;
 END LOOP;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_speed_breaks_invalid_pursuit
AFTER UPDATE OF speed_current ON senc_vessel
FOR EACH ROW WHEN(OLD.speed_current IS DISTINCT FROM NEW.speed_current)
EXECUTE FUNCTION senc_break_pursuit_for_speed();
