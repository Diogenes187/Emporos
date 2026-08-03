ALTER TABLE rule_personal_combat_drug_effect
    ADD COLUMN activation_runtime_basis text NOT NULL
        DEFAULT 'unresolved',
    ADD COLUMN effective_activation_rounds integer;

UPDATE rule_personal_combat_drug_effect
SET activation_runtime_basis='completed-rounds',
    effective_activation_rounds=activation_rounds;

ALTER TABLE rule_personal_combat_drug_effect
    ALTER COLUMN effective_activation_rounds SET NOT NULL,
    ADD CONSTRAINT personal_combat_drug_runtime_basis_check CHECK (
        activation_runtime_basis='completed-rounds'
    ),
    ADD CONSTRAINT personal_combat_drug_effective_rounds_check CHECK (
        effective_activation_rounds=activation_rounds
    );

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation','CE-DRUG-001',
       'Combat runtime activates the drug after its printed number of completed rounds; the conflicting printed seconds remain source provenance.'
FROM rule_rule rule
WHERE rule.rule_code IN (
    'equipment.drug.combat','equipment.drug.metabolic-accelerator'
);

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary='CE-DRUG-001 uses the printed round count as combat runtime authority while preserving the conflicting seconds.',
    engine_disposition='preserve_rule'
WHERE issue.issue_code IN (
    'equipment.drug.combat-activation-timing',
    'equipment.drug.metabolic-accelerator-activation-timing'
);

CREATE FUNCTION personal_protect_drug_timing_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.activation_seconds<>OLD.activation_seconds
       OR NEW.activation_rounds<>OLD.activation_rounds
       OR NEW.activation_runtime_basis<>'completed-rounds'
       OR NEW.effective_activation_rounds<>NEW.activation_rounds THEN
        RAISE EXCEPTION 'CE-DRUG-001 timing adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER personal_drug_timing_adjudication_immutable
BEFORE UPDATE ON rule_personal_combat_drug_effect
FOR EACH ROW EXECUTE FUNCTION personal_protect_drug_timing_adjudication();

UPDATE vehicle_class_autopilot autopilot
SET calculation_status='adjudicated'
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=autopilot.vehicle_class_rule_id
  AND class.class_code='grav-tank';

INSERT INTO vehicle_class_construction_receipt (
    vehicle_class_rule_id,receipt_version,supersedes_receipt_id,
    standard_design_discount_rate,stated_subtotal_credits,
    receipt_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,prior.receipt_version+1,
       prior.construction_receipt_id,prior.standard_design_discount_rate,
       prior.stated_subtotal_credits,'adjudicated',prior.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_construction_receipt prior USING(vehicle_class_rule_id)
WHERE class.class_code='helicopter'
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
    WHERE class.class_code='helicopter' AND NOT new_receipt.finalized
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

UPDATE vehicle_class
SET construction_cost_minor=154850
WHERE class_code='helicopter';

UPDATE vehicle_class_construction_receipt receipt
SET finalized=true
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=receipt.vehicle_class_rule_id
  AND class.class_code='helicopter'
  AND NOT receipt.finalized;

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation',decision.entry,
       decision.rationale
FROM (VALUES
    ('vehicle.class.grav-tank','CE-VDS-029',
     'The TL9 introduction rule and Cr2,000 price make Grav Vehicle-0 effective; the lone level-1 table note remains provenance.'),
    ('vehicle.class.helicopter','CE-VDS-030',
     'The published Cr172,055.95 subtotal receives the standard ten-percent discount and source rounding, producing Cr154,850.')
) decision(rule_code,entry,rationale)
JOIN rule_rule rule ON rule.rule_code=decision.rule_code;

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary=decision.summary,
    engine_disposition='preserve_rule'
FROM (VALUES
    ('vehicle.class.grav-tank-autopilot-label',
     'CE-VDS-029 adopts Grav Vehicle-0 at Cr2,000 from the governing autopilot formula.'),
    ('vehicle.class.helicopter-final-price',
     'CE-VDS-030 corrects the effective discounted final price to Cr154,850 while preserving Cr154,810 in the superseded receipt and issue provenance.')
) decision(issue_code,summary)
WHERE issue.issue_code=decision.issue_code;

CREATE OR REPLACE FUNCTION vehicle_protect_medium_adjudications()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME='vehicle_class_autopilot' THEN
        IF OLD.vehicle_class_rule_id IN (
            SELECT vehicle_class_rule_id FROM vehicle_class
            WHERE class_code IN ('g-carrier','afv-tracked','atv-tracked')
        ) AND (NEW.skill_level<>OLD.skill_level OR
               NEW.published_cost_minor<>OLD.published_cost_minor OR
               NEW.calculation_status<>'adjudicated') THEN
            RAISE EXCEPTION 'CE-VDS-020/024 autopilot adjudication is immutable'
                USING ERRCODE='23514';
        END IF;
        IF OLD.vehicle_class_rule_id=(
            SELECT vehicle_class_rule_id FROM vehicle_class
            WHERE class_code='grav-tank'
        ) AND (NEW.skill_level<>0 OR NEW.published_cost_minor<>2000 OR
               NEW.calculation_status<>'adjudicated') THEN
            RAISE EXCEPTION 'CE-VDS-029 Grav Tank autopilot adjudication is immutable'
                USING ERRCODE='23514';
        END IF;
    ELSIF TG_TABLE_NAME='rule_vehicle_armament_option' THEN
        IF OLD.option_code='heavy-turret-weapon' AND
           (NEW.rate_of_fire_multiplier<>0.5 OR
            NEW.rate_of_fire_rounding_method<>'exact-rational') THEN
            RAISE EXCEPTION 'CE-VDS-015 ROF adjudication is immutable'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION vehicle_protect_medium_class_adjudications()
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
    IF OLD.class_code='submersible' AND
       (NEW.minimum_tech_level<>7 OR
        NEW.construction_cost_minor<>31062370) THEN
        RAISE EXCEPTION 'CE-VDS-023 Submersible adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    IF OLD.class_code='helicopter' AND
       NEW.construction_cost_minor<>154850 THEN
        RAISE EXCEPTION 'CE-VDS-030 Helicopter price adjudication is immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TABLE ship_class_effective_cost_adjudication (
    ship_class_rule_id bigint PRIMARY KEY
        REFERENCES ship_class(ship_class_rule_id),
    construction_receipt_id bigint NOT NULL,
    effective_cost_minor bigint NOT NULL CHECK (effective_cost_minor>0),
    decision_register_entry text NOT NULL CHECK (
        decision_register_entry='CE-SHIP-008'
    ),
    FOREIGN KEY (construction_receipt_id,ship_class_rule_id)
        REFERENCES ship_class_construction_receipt(
            construction_receipt_id,ship_class_rule_id
        )
);

CREATE FUNCTION ship_validate_effective_cost_adjudication()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_cost bigint; is_finalized boolean;
BEGIN
    SELECT total.calculated_cost_minor,receipt.finalized
      INTO expected_cost,is_finalized
    FROM ship_class_construction_receipt_total total
    JOIN ship_class_construction_receipt receipt
      USING(construction_receipt_id,ship_class_rule_id)
    WHERE total.construction_receipt_id=NEW.construction_receipt_id
      AND total.ship_class_rule_id=NEW.ship_class_rule_id;
    IF expected_cost IS NULL OR NOT is_finalized
       OR NEW.effective_cost_minor<>expected_cost THEN
        RAISE EXCEPTION 'effective ship cost must adopt its finalized receipt total'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_effective_cost_adjudication_valid
BEFORE INSERT ON ship_class_effective_cost_adjudication
FOR EACH ROW EXECUTE FUNCTION ship_validate_effective_cost_adjudication();

CREATE FUNCTION ship_effective_cost_adjudication_immutable()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'CE-SHIP-008 effective cost adjudications are immutable'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER ship_effective_cost_adjudication_immutable
BEFORE UPDATE OR DELETE ON ship_class_effective_cost_adjudication
FOR EACH ROW EXECUTE FUNCTION ship_effective_cost_adjudication_immutable();

INSERT INTO ship_class_effective_cost_adjudication (
    ship_class_rule_id,construction_receipt_id,effective_cost_minor,
    decision_register_entry
)
SELECT class.ship_class_rule_id,total.construction_receipt_id,
       total.calculated_cost_minor,'CE-SHIP-008'
FROM ship_class class
JOIN ship_class_construction_total total USING(ship_class_rule_id)
WHERE class.class_code IN (
    'corvette','courier','cutter','dreadnought','fighter',
    'frontier-trader','heavy-cruiser','light-cruiser',
    'merchant-freighter','merchant-liner','merchant-trader',
    'patrol-frigate','raider','research-vessel','survey-vessel',
    'system-defense-boat','system-monitor','yacht'
);

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation','CE-SHIP-008',
       'The complete finalized relational construction receipt governs effective price; the unsupported printed total remains immutable provenance.'
FROM ship_class class
JOIN rule_rule rule ON rule.rule_id=class.ship_class_rule_id
WHERE class.class_code IN (
    'corvette','courier','cutter','dreadnought','fighter',
    'frontier-trader','heavy-cruiser','light-cruiser',
    'merchant-freighter','merchant-liner','merchant-trader',
    'patrol-frigate','raider','research-vessel','survey-vessel',
    'system-defense-boat','system-monitor','yacht'
);

UPDATE src_issue issue
SET calculated_value=effective.effective_cost_minor::text || ' credits',
    difference_value=class.construction_cost_minor-effective.effective_cost_minor,
    issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary='CE-SHIP-008 adopts the complete finalized relational receipt as effective cost while preserving the unsupported printed total.',
    engine_disposition='preserve_rule'
FROM ship_class class
JOIN ship_class_effective_cost_adjudication effective
  USING(ship_class_rule_id)
WHERE issue.subject_code=class.class_code
  AND issue.issue_code='ship.' || class.class_code || '.construction.cost';
