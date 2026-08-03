ALTER TABLE vehicle_class_autopilot
    DROP CONSTRAINT vehicle_class_autopilot_calculation_status_check,
    ADD CONSTRAINT vehicle_class_autopilot_calculation_status_check CHECK (
        calculation_status IN ('matches','published_override','adjudicated')
    );

ALTER TABLE vehicle_class_component
    DROP CONSTRAINT vehicle_class_component_calculation_status_check,
    ADD CONSTRAINT vehicle_class_component_calculation_status_check CHECK (
        calculation_status IN (
            'matches','formula','published_override','adjudicated'
        )
    ),
    DROP CONSTRAINT vehicle_class_component_tech_level_status_check,
    ADD CONSTRAINT vehicle_class_component_tech_level_status_check CHECK (
        tech_level_status IN (
            'matches','published_override','adjudicated'
        )
    );

ALTER TABLE rule_vehicle_anti_missile_guidance_claim
    ADD COLUMN mechanically_effective boolean NOT NULL DEFAULT true;

UPDATE rule_vehicle_anti_missile_guidance_claim claim
SET mechanically_effective=(claim.claim_role='primary-label')
FROM rule_vehicle_anti_missile_system system
WHERE system.system_rule_id=claim.system_rule_id
  AND system.system_code='decoys';

ALTER TABLE rule_vehicle_armament_option
    ADD COLUMN rate_of_fire_rounding_method text,
    ADD COLUMN calculation_status text NOT NULL DEFAULT 'published',
    ADD CHECK (
        rate_of_fire_rounding_method IS NULL OR
        rate_of_fire_rounding_method IN ('exact-rational','floor','ceiling','nearest')
    ),
    ADD CHECK (calculation_status IN ('published','adjudicated'));

UPDATE rule_vehicle_armament_option
SET rate_of_fire_rounding_method='exact-rational',
    calculation_status='adjudicated'
WHERE option_code='heavy-turret-weapon';

CREATE TABLE rule_vehicle_space_rounding_policy (
    rounding_policy_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_code text NOT NULL UNIQUE CHECK (
        policy_code~'^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    rounding_method text NOT NULL CHECK (
        rounding_method IN ('floor','ceiling','nearest')
    ),
    half_tie_method text NOT NULL CHECK (
        half_tie_method IN ('up','down','to-even','not-applicable')
    ),
    calculation_status text NOT NULL CHECK (
        calculation_status IN ('published','adjudicated')
    ),
    source_locator_id bigint NOT NULL REFERENCES src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_space_rounding_policy (
    policy_code,rounding_method,half_tie_method,calculation_status,
    source_locator_id
)
SELECT 'submersible-ballast','nearest','up','adjudicated',source_locator_id
FROM rule_vehicle_configuration_option
WHERE option_code='submersible';

UPDATE rule_vehicle_aircraft_environment
SET exact_match_maximum_code_difference=0,
    operational_maximum_code_difference=1,
    degraded_agility_dm=-1
WHERE environment_code='standard';

UPDATE vehicle_class
SET chassis_code='5'
WHERE class_code='biplane';

UPDATE vehicle_class
SET minimum_tech_level=7
WHERE class_code='submersible';

UPDATE vehicle_class_autopilot autopilot
SET skill_level=CASE class.class_code
                    WHEN 'g-carrier' THEN 3 ELSE 1 END,
    published_cost_minor=CASE class.class_code
                            WHEN 'g-carrier' THEN 17000 ELSE 7000 END,
    calculation_status='adjudicated'
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=autopilot.vehicle_class_rule_id
  AND class.class_code IN ('g-carrier','afv-tracked','atv-tracked');

UPDATE vehicle_class_component selection
SET published_cost_minor=CASE
        WHEN class.class_code IN (
            'afv-tracked','atv-tracked','tunnel-boring-machine'
        ) THEN 0 ELSE 10500 END,
    calculation_status='adjudicated'
FROM vehicle_class class,vehicle_component_definition component
WHERE class.vehicle_class_rule_id=selection.vehicle_class_rule_id
  AND component.component_rule_id=selection.component_rule_id
  AND component.component_code='life-support.basic'
  AND class.class_code IN (
      'afv-tracked','atv-tracked','g-carrier','grav-tank','speeder',
      'tunnel-boring-machine'
  );

UPDATE vehicle_class_component selection
SET calculation_status='adjudicated'
FROM vehicle_class class,vehicle_component_definition component
WHERE class.vehicle_class_rule_id=selection.vehicle_class_rule_id
  AND component.component_rule_id=selection.component_rule_id
  AND class.class_code='tunnel-boring-machine'
  AND component.component_code IN ('sensor.standard','computer.model-1');

UPDATE vehicle_class_component selection
SET tech_level_status='adjudicated'
FROM vehicle_class class,vehicle_component_definition component
WHERE class.vehicle_class_rule_id=selection.vehicle_class_rule_id
  AND component.component_rule_id=selection.component_rule_id
  AND class.class_code='submersible'
  AND component.component_code='life-support.extended';

UPDATE vehicle_component_definition
SET calculation_status='adjudicated'
WHERE component_code IN (
    'additional.emergency-low-berth','additional.folding-wings-rotors'
);

-- Each corrected worksheet is a new immutable receipt. Published receipts
-- remain untouched and reachable through supersedes_receipt_id.
INSERT INTO vehicle_class_construction_receipt (
    vehicle_class_rule_id,receipt_version,supersedes_receipt_id,
    standard_design_discount_rate,stated_subtotal_credits,
    receipt_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,prior.receipt_version+1,
       prior.construction_receipt_id,prior.standard_design_discount_rate,
       CASE class.class_code
           WHEN 'air-raft' THEN 104614.51
           WHEN 'g-carrier' THEN 1540682.24
           WHEN 'grav-tank' THEN 1739659.48
           WHEN 'speeder' THEN 371957.256
           WHEN 'afv-tracked' THEN 6266260.48
           WHEN 'atv-tracked' THEN 6118060.48
           WHEN 'steamship' THEN 6366700
           WHEN 'submersible' THEN 34660744
           WHEN 'tunnel-boring-machine' THEN 310549.244
       END,'adjudicated',prior.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_construction_receipt prior USING(vehicle_class_rule_id)
WHERE class.class_code IN (
    'air-raft','g-carrier','grav-tank','speeder','afv-tracked','atv-tracked',
    'steamship','submersible','tunnel-boring-machine'
)
AND prior.receipt_version=(
    SELECT max(candidate.receipt_version)
    FROM vehicle_class_construction_receipt candidate
    WHERE candidate.vehicle_class_rule_id=class.vehicle_class_rule_id
);

WITH receipt_pair AS (
    SELECT class.class_code,new_receipt.construction_receipt_id AS new_id,
           old_receipt.construction_receipt_id AS old_id
    FROM vehicle_class class
    JOIN vehicle_class_construction_receipt new_receipt
      USING(vehicle_class_rule_id)
    JOIN vehicle_class_construction_receipt old_receipt
      ON old_receipt.construction_receipt_id=new_receipt.supersedes_receipt_id
    WHERE class.class_code IN (
        'air-raft','g-carrier','grav-tank','speeder','afv-tracked','atv-tracked',
        'steamship','submersible','tunnel-boring-machine'
    ) AND NOT new_receipt.finalized
)
INSERT INTO vehicle_class_construction_line (
    construction_receipt_id,vehicle_class_rule_id,line_order,line_kind,
    reference_code,quantity,space_role,published_spaces,
    published_cost_credits,discount_eligible,line_status,source_locator_id
)
SELECT pair.new_id,line.vehicle_class_rule_id,line.line_order,line.line_kind,
       line.reference_code,line.quantity,line.space_role,
       CASE
           WHEN pair.class_code='air-raft' AND line.line_kind='cargo'
               THEN 29.68
           WHEN pair.class_code='steamship'
                AND line.reference_code='accommodation.control-cabin-standard'
               THEN 108
           ELSE line.published_spaces
       END,
       CASE
           WHEN line.line_kind='life_support' THEN
               CASE WHEN pair.class_code IN (
                    'afv-tracked','atv-tracked','tunnel-boring-machine'
               ) THEN 0 ELSE 10500 END
           WHEN line.line_kind='autopilot' AND pair.class_code='g-carrier'
               THEN 17000
           WHEN line.line_kind='autopilot' AND pair.class_code IN (
                    'afv-tracked','atv-tracked'
               ) THEN 7000
           ELSE line.published_cost_credits
       END,
       line.discount_eligible,
       CASE
           WHEN pair.class_code='air-raft' AND line.line_kind='cargo'
               THEN 'adjudicated'
           WHEN pair.class_code='steamship'
                AND line.reference_code='accommodation.control-cabin-standard'
               THEN 'adjudicated'
           WHEN line.line_kind IN ('life_support','autopilot')
               THEN 'adjudicated'
           WHEN pair.class_code='tunnel-boring-machine'
                AND line.line_kind IN ('sensor','computer')
               THEN 'adjudicated'
           ELSE line.line_status
       END,
       line.source_locator_id
FROM receipt_pair pair
JOIN vehicle_class_construction_line line
  ON line.construction_receipt_id=pair.old_id;

UPDATE vehicle_class_construction_receipt receipt
SET finalized=true
FROM vehicle_class class
WHERE class.vehicle_class_rule_id=receipt.vehicle_class_rule_id
  AND class.class_code IN (
      'air-raft','g-carrier','grav-tank','speeder','afv-tracked','atv-tracked',
      'steamship','submersible','tunnel-boring-machine'
  )
  AND NOT receipt.finalized;

UPDATE vehicle_class
SET allocated_spaces=18.32,cargo_spaces=29.68,
    construction_cost_minor=94160
WHERE class_code='air-raft';

UPDATE vehicle_class
SET construction_cost_minor=CASE class_code
    WHEN 'g-carrier' THEN 1386640
    WHEN 'grav-tank' THEN 1565750
    WHEN 'speeder' THEN 334760
    WHEN 'afv-tracked' THEN 5639640
    WHEN 'atv-tracked' THEN 5506260
    WHEN 'tunnel-boring-machine' THEN 279550
END
WHERE class_code IN (
    'g-carrier','grav-tank','speeder','afv-tracked','atv-tracked',
    'tunnel-boring-machine'
);

UPDATE vehicle_class
SET allocated_spaces=1883.4,cargo_spaces=516.6
WHERE class_code='steamship';

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation',decision.entry,decision.rationale
FROM (VALUES
 ('vehicle.special.aircraft-environment','CE-VDS-013','Exact design codes operate normally; a one-code difference applies Agility DM -1.'),
 ('vehicle.anti-missile-system.decoys','CE-VDS-014','The primary smart-missile label is mechanically effective; the radar parenthetical remains provenance only.'),
 ('vehicle.armament-option.heavy-turret-weapon','CE-VDS-015','The ROF multiplier remains an exact rational cadence and is not rounded.'),
 ('vehicle.class.air-raft','CE-VDS-016','Air/Raft cargo is 29.68 Spaces and the correctly discounted final price is Cr94,160.'),
 ('vehicle.component.life-support.basic','CE-VDS-017','Basic Life Support costs Cr3,500 per Space, or zero where Hostile protection supplies it free.'),
 ('vehicle.class.biplane','CE-VDS-018','A one-ton twelve-Space chassis is Code 5.'),
 ('vehicle.class.destroyer-watercraft','CE-VDS-019','Heavy names apply the Heavy Turret Weapon modifier to catalogue weapons; they are not separate variants.'),
 ('vehicle.class.g-carrier','CE-VDS-020','The TL15 G/Carrier has Grav Vehicle-3 autopilot at Cr17,000.'),
 ('vehicle.class.speeder','CE-VDS-021','The unexplained Cr2,000 is rejected; the itemized worksheet governs before other adjudicated corrections.'),
 ('vehicle.class.steamship','CE-VDS-022','The five-person control cabin consumes 108 Spaces, leaving the published 516.6 cargo Spaces.'),
 ('vehicle.class.submersible','CE-VDS-023','The completed Submersible profile is TL7 because it installs Extended Life Support.'),
 ('vehicle.class.afv-tracked','CE-VDS-024','Tracked Vehicle-1 autopilot costs Cr7,000 in both tracked profiles.'),
 ('vehicle.class.tunnel-boring-machine','CE-VDS-025','Standard sensors and a Model 1 computer stated in prose are restored to the effective worksheet.'),
 ('vehicle.component.additional.emergency-low-berth','CE-VDS-026','A vehicle Emergency Low Berth has the core four-person survival capacity.'),
 ('vehicle.component.additional.folding-wings-rotors','CE-VDS-027','The prose Folding Wings/Rotors formula is the effective component-summary entry.'),
 ('vehicle.configuration-option.submersible','CE-VDS-028','Submersible ballast rounds to nearest whole Space with exact halves upward.')
) decision(rule_code,entry,rationale)
JOIN rule_rule rule ON rule.rule_code=decision.rule_code;

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary=decision.summary,
    engine_disposition='preserve_rule'
FROM (VALUES
 ('vehicle.aircraft.environment-tolerance-wording','CE-VDS-013 establishes exact-match normal operation and the one-code Agility penalty.'),
 ('vehicle.anti-missile.decoy-guidance-label','CE-VDS-014 makes only the primary smart-guidance labels effective.'),
 ('vehicle.armament.heavy-weapon-rof-rounding','CE-VDS-015 preserves exact rational cadence without rounding.'),
 ('vehicle.class.air-raft-construction-arithmetic','CE-VDS-016 corrects cargo to 29.68 Spaces and final cost to Cr94,160.'),
 ('vehicle.class.basic-life-support-profile-price','CE-VDS-017 applies the governing per-Space price and free Hostile installations.'),
 ('vehicle.class.biplane-chassis-code','CE-VDS-018 confirms chassis Code 5.'),
 ('vehicle.class.destroyer-heavy-weapon-labels','CE-VDS-019 treats Heavy as an armament option, not a weapon variant.'),
 ('vehicle.class.g-carrier-autopilot','CE-VDS-020 applies level 3 at Cr17,000.'),
 ('vehicle.class.speeder-unitemized-subtotal','CE-VDS-021 rejects the unexplained Cr2,000 and adopts the itemized total.'),
 ('vehicle.class.steamship-cargo-space','CE-VDS-022 corrects the control cabin to 108 Spaces.'),
 ('vehicle.class.submersible-life-support-tech-level','CE-VDS-023 corrects the completed profile to TL7.'),
 ('vehicle.class.tracked-autopilot-price','CE-VDS-024 prices both level-1 autopilots at Cr7,000.'),
 ('vehicle.class.tunnel-boring-electronics-omission','CE-VDS-025 restores the prose sensors and computer.'),
 ('vehicle.components.emergency-low-berth-capacity','CE-VDS-026 adopts the core four-person capacity.'),
 ('vehicle.components.folding-wings-summary-omission','CE-VDS-027 adopts the complete prose formula.'),
 ('vehicle.configuration.submersible-ballast-rounding','CE-VDS-028 uses nearest rounding with half ties upward.')
) decision(issue_code,summary)
WHERE issue.issue_code=decision.issue_code;

CREATE FUNCTION vehicle_protect_medium_adjudications()
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

CREATE TRIGGER vehicle_medium_autopilot_adjudication_immutable
BEFORE UPDATE ON vehicle_class_autopilot
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_medium_adjudications();

CREATE TRIGGER vehicle_medium_armament_adjudication_immutable
BEFORE UPDATE ON rule_vehicle_armament_option
FOR EACH ROW EXECUTE FUNCTION vehicle_protect_medium_adjudications();
