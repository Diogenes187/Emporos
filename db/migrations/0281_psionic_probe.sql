CREATE TABLE rule_psi_probe (
 power_rule_id bigint PRIMARY KEY REFERENCES psi_power(power_rule_id),
 probe_mode text NOT NULL CHECK(probe_mode IN('deliberate','rapid')),
 reads_innermost_thoughts boolean NOT NULL CHECK(reads_innermost_thoughts),
 permits_questioning boolean NOT NULL CHECK(permits_questioning),
 forces_specific_information boolean NOT NULL CHECK(forces_specific_information),
 detects_deliberate_untruths boolean NOT NULL CHECK(detects_deliberate_untruths),
 shield_blocks boolean NOT NULL CHECK(shield_blocks),
 effect_controls_clarity boolean NOT NULL CHECK(effect_controls_clarity)
);
CREATE TABLE cmd_psi_probe_receipt(
 activation_command_id bigint PRIMARY KEY REFERENCES cmd_psionic_activation_receipt(command_id),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 target_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 probe_mode text NOT NULL CHECK(probe_mode IN('deliberate','rapid')),
 effect_snapshot smallint NOT NULL,
 timing_total_snapshot smallint NOT NULL CHECK(timing_total_snapshot>0),
 timing_unit_snapshot text NOT NULL CHECK(timing_unit_snapshot IN('minutes','seconds')),
 innermost_thoughts text NOT NULL CHECK(btrim(innermost_thoughts)<>''),
 clarity_evidence text NOT NULL CHECK(btrim(clarity_evidence)<>''),
 question_count smallint NOT NULL CHECK(question_count>=0),
 probed_at timestamptz NOT NULL,
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(target_actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id)
);
CREATE TABLE cmd_psi_probe_question(
 activation_command_id bigint NOT NULL REFERENCES cmd_psi_probe_receipt(activation_command_id),
 question_order smallint NOT NULL CHECK(question_order>0),
 question_text text NOT NULL CHECK(btrim(question_text)<>''),
 divulged_information text NOT NULL CHECK(btrim(divulged_information)<>''),
 deliberate_untruth_detected boolean NOT NULL,
 PRIMARY KEY(activation_command_id,question_order)
);
CREATE FUNCTION cmd_validate_psi_probe() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a cmd_psionic_activation_receipt%ROWTYPE; DECLARE m text;
BEGIN
 SELECT * INTO STRICT a FROM cmd_psionic_activation_receipt WHERE command_id=NEW.activation_command_id;
 SELECT probe_mode INTO STRICT m FROM rule_psi_probe WHERE power_rule_id=a.power_rule_id;
 IF NOT a.succeeded OR a.actor_id<>NEW.actor_id OR a.target_actor_id<>NEW.target_actor_id
 OR a.effect<>NEW.effect_snapshot OR a.timing_total<>NEW.timing_total_snapshot
 OR a.timing_unit<>NEW.timing_unit_snapshot OR m<>NEW.probe_mode THEN
  RAISE EXCEPTION 'Probe receipt does not match activation';
 END IF; RETURN NEW;
END $$;
CREATE TRIGGER cmd_psi_probe_valid BEFORE INSERT ON cmd_psi_probe_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_probe();
CREATE FUNCTION cmd_validate_psi_probe_count() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE receipt_id bigint; DECLARE n integer; DECLARE expected integer;
BEGIN
 receipt_id := COALESCE(NEW.activation_command_id,OLD.activation_command_id);
 SELECT count(*) INTO n FROM cmd_psi_probe_question WHERE activation_command_id=receipt_id;
 SELECT question_count INTO STRICT expected FROM cmd_psi_probe_receipt WHERE activation_command_id=receipt_id;
 IF n<>expected THEN RAISE EXCEPTION 'Probe question count mismatch'; END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER cmd_psi_probe_count_valid AFTER INSERT OR UPDATE ON cmd_psi_probe_receipt
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_probe_count();
CREATE CONSTRAINT TRIGGER cmd_psi_probe_question_count_valid
AFTER INSERT OR UPDATE OR DELETE ON cmd_psi_probe_question
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
EXECUTE FUNCTION cmd_validate_psi_probe_count();
CREATE FUNCTION cmd_reject_psi_probe_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Probe receipts are immutable'; END $$;
CREATE TRIGGER cmd_psi_probe_immutable BEFORE UPDATE OR DELETE ON cmd_psi_probe_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_probe_mutation();
CREATE TRIGGER cmd_psi_probe_question_immutable BEFORE UPDATE OR DELETE ON cmd_psi_probe_question
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_probe_mutation();
COMMENT ON TABLE rule_psi_probe IS
 'CE-PSI-012 paired-source deliberate and rapid Probe mechanics.';
COMMENT ON TABLE cmd_psi_probe_receipt IS
 'Immutable Probe result, timing, Effect-dependent clarity, and evidence count.';
COMMENT ON TABLE cmd_psi_probe_question IS
 'Immutable ordered questioning evidence and deliberate-untruth findings.';
