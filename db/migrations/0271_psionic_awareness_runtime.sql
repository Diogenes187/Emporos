CREATE TABLE cmd_psi_awareness_effect_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_activation_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    effect_kind text NOT NULL CHECK (
        effect_kind IN (
            'suspended_animation','characteristic_enhancement','regeneration'
        )
    ),
    activated_at timestamptz NOT NULL
);

CREATE TABLE cmd_psi_suspended_animation_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psi_awareness_effect_receipt(activation_command_id),
    scheduled_end_at timestamptz NOT NULL
);

CREATE TABLE cmd_psi_suspended_animation_end_receipt (
    end_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE CHECK (btrim(idempotency_key)<>''),
    activation_command_id bigint NOT NULL UNIQUE REFERENCES
        cmd_psi_suspended_animation_receipt(activation_command_id),
    ended_at timestamptz NOT NULL,
    ending_kind text NOT NULL CHECK (
        ending_kind IN ('duration_elapsed','external_stimulus')
    )
);

CREATE VIEW camp_active_psi_suspended_animation AS
SELECT effect.actor_id,effect.activation_command_id,effect.activated_at,
       suspension.scheduled_end_at
  FROM cmd_psi_awareness_effect_receipt effect
  JOIN cmd_psi_suspended_animation_receipt suspension
    USING (activation_command_id)
  LEFT JOIN cmd_psi_suspended_animation_end_receipt ending
    USING (activation_command_id)
 WHERE ending.end_receipt_id IS NULL
   AND suspension.scheduled_end_at>statement_timestamp();

CREATE TABLE cmd_psi_characteristic_enhancement_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psi_awareness_effect_receipt(activation_command_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    wounded_value_snapshot smallint NOT NULL CHECK (
        wounded_value_snapshot>=0
    ),
    racial_maximum_snapshot smallint NOT NULL CHECK (
        racial_maximum_snapshot>0
    ),
    awareness_level_snapshot smallint NOT NULL CHECK (
        awareness_level_snapshot>=0
    ),
    points_gained smallint NOT NULL CHECK (points_gained>0),
    peak_ends_at timestamptz NOT NULL,
    decline_ends_at timestamptz NOT NULL,
    CHECK (points_gained<=awareness_level_snapshot),
    CHECK (wounded_value_snapshot+points_gained<=racial_maximum_snapshot),
    CHECK (decline_ends_at=peak_ends_at+
           points_gained*interval '1 minute')
);

CREATE VIEW camp_current_psi_characteristic_enhancement AS
SELECT effect.actor_id,effect.activation_command_id,
       enhancement.characteristic_rule_id,
       enhancement.wounded_value_snapshot,
       enhancement.points_gained,
       CASE
         WHEN statement_timestamp()<enhancement.peak_ends_at
           THEN enhancement.points_gained
         ELSE greatest(
           0,enhancement.points_gained-
             floor(extract(epoch FROM (
               statement_timestamp()-enhancement.peak_ends_at
             ))/60)::integer-1
         )
       END AS current_bonus,
       enhancement.peak_ends_at,enhancement.decline_ends_at
  FROM cmd_psi_awareness_effect_receipt effect
  JOIN cmd_psi_characteristic_enhancement_receipt enhancement
    USING (activation_command_id)
 WHERE statement_timestamp()<enhancement.decline_ends_at;

CREATE TABLE cmd_psi_regeneration_receipt (
    activation_command_id bigint PRIMARY KEY REFERENCES
        cmd_psi_awareness_effect_receipt(activation_command_id),
    total_points_regenerated smallint NOT NULL CHECK (
        total_points_regenerated>0
    ),
    psionic_maximum_snapshot smallint NOT NULL CHECK (
        psionic_maximum_snapshot>0
    )
);

CREATE TABLE cmd_psi_regeneration_allocation (
    activation_command_id bigint NOT NULL REFERENCES
        cmd_psi_regeneration_receipt(activation_command_id),
    allocation_order smallint NOT NULL CHECK (allocation_order>0),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    points_regenerated smallint NOT NULL CHECK (points_regenerated>0),
    value_before smallint NOT NULL CHECK (value_before>=0),
    value_after smallint NOT NULL,
    maximum_value_snapshot smallint NOT NULL,
    PRIMARY KEY (activation_command_id,allocation_order),
    UNIQUE (activation_command_id,characteristic_rule_id),
    CHECK (value_after=value_before+points_regenerated),
    CHECK (value_after<=maximum_value_snapshot)
);

CREATE TABLE camp_psi_regeneration_recovery_lock (
    actor_id bigint PRIMARY KEY REFERENCES actor_actor(actor_id),
    activation_command_id bigint NOT NULL UNIQUE REFERENCES
        cmd_psi_regeneration_receipt(activation_command_id),
    psionic_maximum_snapshot smallint NOT NULL CHECK (
        psionic_maximum_snapshot>0
    )
);

CREATE TABLE cmd_psi_regeneration_release_receipt (
    recovery_command_id bigint PRIMARY KEY REFERENCES
        cmd_psionic_recovery_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    regeneration_activation_command_id bigint NOT NULL UNIQUE REFERENCES
        cmd_psi_regeneration_receipt(activation_command_id),
    psionic_strength_after smallint NOT NULL,
    psionic_maximum_snapshot smallint NOT NULL,
    CHECK (psionic_strength_after=psionic_maximum_snapshot)
);

CREATE FUNCTION cmd_validate_psi_awareness_effect()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE activation cmd_psionic_activation_receipt%ROWTYPE;
DECLARE power_code text;
DECLARE expected_kind text;
BEGIN
 SELECT * INTO STRICT activation
   FROM cmd_psionic_activation_receipt
  WHERE command_id=NEW.activation_command_id;
 SELECT power.power_code INTO STRICT power_code
   FROM psi_power power
  WHERE power.power_rule_id=activation.power_rule_id;
 expected_kind=CASE power_code
   WHEN 'suspended-animation' THEN 'suspended_animation'
   WHEN 'enhanced-strength' THEN 'characteristic_enhancement'
   WHEN 'enhanced-endurance' THEN 'characteristic_enhancement'
   WHEN 'regeneration' THEN 'regeneration'
 END;
 IF NOT activation.succeeded OR activation.actor_id<>NEW.actor_id
    OR expected_kind IS NULL OR NEW.effect_kind<>expected_kind THEN
   RAISE EXCEPTION 'Awareness effect does not match successful activation';
 END IF;
 RETURN NEW;
END; $$;

CREATE TRIGGER cmd_psi_awareness_effect_valid
BEFORE INSERT ON cmd_psi_awareness_effect_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_psi_awareness_effect();

CREATE FUNCTION cmd_reject_psi_awareness_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Awareness effect receipts are immutable'; END; $$;

CREATE TRIGGER cmd_psi_awareness_effect_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_awareness_effect_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();
CREATE TRIGGER cmd_psi_suspension_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_suspended_animation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();
CREATE TRIGGER cmd_psi_suspension_end_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_suspended_animation_end_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();
CREATE TRIGGER cmd_psi_enhancement_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_characteristic_enhancement_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();
CREATE TRIGGER cmd_psi_regeneration_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_regeneration_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();
CREATE TRIGGER cmd_psi_regeneration_allocation_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_regeneration_allocation
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();
CREATE TRIGGER cmd_psi_regeneration_release_immutable
BEFORE UPDATE OR DELETE ON cmd_psi_regeneration_release_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_psi_awareness_history_mutation();

COMMENT ON TABLE cmd_psi_awareness_effect_receipt IS
    'CE-PSI-003 immutable successful Awareness effect root.';
COMMENT ON VIEW camp_current_psi_characteristic_enhancement IS
    'Campaign projection retaining the wounded baseline while temporary enhancement declines.';
