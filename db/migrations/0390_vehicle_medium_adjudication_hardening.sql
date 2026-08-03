-- The Submersible's published subtotal itself includes an unexplained
-- Cr147,000 variance.  The TL adjudication does not authorize preserving that
-- arithmetic error as an effective total, so publish a corrected successor.
INSERT INTO vehicle_class_construction_receipt (
    vehicle_class_rule_id,receipt_version,supersedes_receipt_id,
    standard_design_discount_rate,stated_subtotal_credits,
    receipt_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,prior.receipt_version+1,
       prior.construction_receipt_id,prior.standard_design_discount_rate,
       34513744,'adjudicated',prior.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_construction_receipt prior USING(vehicle_class_rule_id)
WHERE class.class_code='submersible'
  AND prior.receipt_version=(
      SELECT max(candidate.receipt_version)
      FROM vehicle_class_construction_receipt candidate
      WHERE candidate.vehicle_class_rule_id=class.vehicle_class_rule_id
  );

WITH receipt_pair AS (
    SELECT new_receipt.construction_receipt_id AS new_id,
           old_receipt.construction_receipt_id AS old_id
    FROM vehicle_class class
    JOIN vehicle_class_construction_receipt new_receipt
      USING(vehicle_class_rule_id)
    JOIN vehicle_class_construction_receipt old_receipt
      ON old_receipt.construction_receipt_id=new_receipt.supersedes_receipt_id
    WHERE class.class_code='submersible' AND NOT new_receipt.finalized
)
INSERT INTO vehicle_class_construction_line (
    construction_receipt_id,vehicle_class_rule_id,line_order,line_kind,
    reference_code,quantity,space_role,published_spaces,
    published_cost_credits,discount_eligible,line_status,source_locator_id
)
SELECT pair.new_id,line.vehicle_class_rule_id,line.line_order,line.line_kind,
       line.reference_code,line.quantity,line.space_role,line.published_spaces,
       line.published_cost_credits,line.discount_eligible,line.line_status,
       line.source_locator_id
FROM receipt_pair pair
JOIN vehicle_class_construction_line line
  ON line.construction_receipt_id=pair.old_id;

UPDATE vehicle_class_construction_receipt receipt
SET finalized=true
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=receipt.vehicle_class_rule_id
  AND class.class_code='submersible'
  AND NOT receipt.finalized;

CREATE FUNCTION vehicle_protect_medium_class_adjudications()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.class_code='air-raft' AND
       (NEW.cargo_spaces<>29.68 OR NEW.allocated_spaces<>18.32 OR
        NEW.construction_cost_minor<>94160) THEN
        RAISE EXCEPTION 'CE-VDS-016 Air/Raft adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='biplane' AND NEW.chassis_code<>'5' THEN
        RAISE EXCEPTION 'CE-VDS-018 Biplane adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='steamship' AND
       (NEW.allocated_spaces<>1883.4 OR NEW.cargo_spaces<>516.6) THEN
        RAISE EXCEPTION 'CE-VDS-022 Steamship adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='submersible' AND NEW.minimum_tech_level<>7 THEN
        RAISE EXCEPTION 'CE-VDS-023 Submersible adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_medium_class_adjudication_immutable
BEFORE UPDATE ON vehicle_class
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_medium_class_adjudications();

CREATE FUNCTION vehicle_protect_medium_policy_adjudications()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME='rule_vehicle_space_rounding_policy' AND
       OLD.policy_code='submersible-ballast' AND
       (NEW.rounding_method<>'nearest' OR NEW.half_tie_method<>'up' OR
        NEW.calculation_status<>'adjudicated') THEN
        RAISE EXCEPTION 'CE-VDS-028 ballast adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF TG_TABLE_NAME='rule_vehicle_anti_missile_guidance_claim' AND
       OLD.system_rule_id=(SELECT system_rule_id
          FROM rule_vehicle_anti_missile_system WHERE system_code='decoys') AND
       NEW.mechanically_effective<>(OLD.claim_role='primary-label') THEN
        RAISE EXCEPTION 'CE-VDS-014 Decoy adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_medium_rounding_adjudication_immutable
BEFORE UPDATE ON rule_vehicle_space_rounding_policy
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_medium_policy_adjudications();

CREATE TRIGGER vehicle_medium_decoy_adjudication_immutable
BEFORE UPDATE ON rule_vehicle_anti_missile_guidance_claim
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_medium_policy_adjudications();
