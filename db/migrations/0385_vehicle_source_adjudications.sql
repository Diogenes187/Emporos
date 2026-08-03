ALTER TABLE vehicle_component_definition
    DROP CONSTRAINT vehicle_component_definition_calculation_status_check,
    ADD CONSTRAINT vehicle_component_definition_calculation_status_check CHECK (
        calculation_status IN (
            'published','formula','included','source_unspecified','adjudicated'
        )
    );

UPDATE vehicle_component_definition
SET minimum_tech_level=1,calculation_status='adjudicated'
WHERE component_code='control.primitive';

UPDATE vehicle_component_definition
SET unit_spaces=1.5,unit_cost_minor=2000,calculation_status='adjudicated'
WHERE component_code='additional.wet-bar';

UPDATE rule_vehicle_configuration_option
SET calculation_status='adjudicated'
WHERE option_code IN ('open-frame','insidious-environmental-protection');

UPDATE rule_vehicle_sensor_package
SET published_range_text='Very Long (500 m)'
WHERE sensor_code='standard';

ALTER TABLE rule_vehicle_missile
    DROP CONSTRAINT rule_vehicle_missile_radiation_rule_status_check,
    ADD CONSTRAINT rule_vehicle_missile_radiation_rule_status_check CHECK (
        radiation_rule_status IN (
            'not-applicable','published','prose-table-conflict','adjudicated'
        )
    );

UPDATE rule_vehicle_missile
SET radiation_hit_count=1,radiation_rule_status='adjudicated'
WHERE missile_code='nuclear-nas-guided';

ALTER TABLE rule_vehicle_ordnance_definition
    DROP CONSTRAINT rule_vehicle_ordnance_definition_check,
    ADD CONSTRAINT rule_vehicle_ordnance_definition_range_state_check CHECK (
        (range_status IN ('published','adjudicated')
         AND range_profile_code IS NOT NULL)
        OR
        (range_status='source-malformed' AND range_profile_code IS NULL)
    ),
    DROP CONSTRAINT rule_vehicle_ordnance_definition_range_status_check,
    ADD CONSTRAINT rule_vehicle_ordnance_definition_range_status_check CHECK (
        range_status IN ('published','source-malformed','adjudicated')
    ),
    DROP CONSTRAINT rule_vehicle_ordnance_definition_radiation_unit_status_check,
    ADD CONSTRAINT rule_vehicle_ordnance_definition_radiation_unit_status_check CHECK (
        radiation_unit_status IN (
            'not-applicable','published-rads','source-omitted','adjudicated-rads'
        )
    );

UPDATE rule_vehicle_ordnance_definition
SET range_profile_code='very-distant',
    published_range_token='ranged (very distant)',
    range_status='adjudicated',
    radiation_unit_status='adjudicated-rads'
WHERE ordnance_code='torpedo-nuclear-heavy';

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation',source.entry,source.rationale
FROM (VALUES
    ('vehicle.component.additional.wet-bar','CE-VDS-001',
     'The coherent component prose governs: a Wet Bar occupies 1.5 Spaces and costs Cr2,000; the malformed summary row remains source provenance.'),
    ('vehicle.configuration-option.open-frame','CE-VDS-002',
     'The Open Frame paragraph conditions refer to Open Frame; its repeated Open Cargo Bed wording is copied text.'),
    ('vehicle.component.control.primitive','CE-VDS-003',
     'The normalized mechanical table governs Primitive Controls at TL1; the TL2 prose label remains source provenance.'),
    ('vehicle.ordnance.torpedo-nuclear-heavy','CE-VDS-004',
     'Parallel heavy and standard torpedo rows restore the truncated Heavy Nuclear Torpedo to Very Distant range and 2D6x10 rads.'),
    ('vehicle.component.sensor.standard','CE-VDS-005',
     'Standard Sensors use Very Long range at 500 metres, preserving the ordered 0.5/5/50/500/5000 kilometre sensor progression.'),
    ('vehicle.missile.nuclear-nas-guided','CE-VDS-006',
     'The general nuclear-missile rule applies to the NAS-guided nuclear missile, adding one automatic radiation hit.'),
    ('vehicle.configuration-option.insidious-environmental-protection','CE-VDS-007',
     'Insidious environmental protection costs Cr50,000 per chassis Space; the two tracked examples omitted multiplication by 120 Spaces.')
) source(rule_code,entry,rationale)
JOIN rule_rule rule ON rule.rule_code=source.rule_code;

UPDATE src_issue issue
SET issue_status='resolved',resolved_at=clock_timestamp(),
    resolution_summary=source.summary,engine_disposition='preserve_rule'
FROM (VALUES
    ('vehicle.components.wet-bar-table',
     'CE-VDS-001 adopts the coherent prose values of 1.5 Spaces and Cr2,000.'),
    ('vehicle.configuration.open-frame-copy-error',
     'CE-VDS-002 treats the repeated Open Cargo Bed labels as copied text naming Open Frame.'),
    ('vehicle.controls.primitive-tech-level',
     'CE-VDS-003 retains the mechanical table value TL1.'),
    ('vehicle.ordnance.heavy-nuclear-torpedo-row',
     'CE-VDS-004 reconstructs Very Distant range and the omitted rads unit from parallel ordnance rows.'),
    ('vehicle.sensors.standard-range-distance',
     'CE-VDS-005 restores Standard Sensors to Very Long range at 500 metres.'),
    ('vehicle.missile.nas-radiation-hit',
     'CE-VDS-006 applies the governing automatic radiation-hit rule to the NAS-guided nuclear missile.')
) source(issue_code,summary)
WHERE issue.issue_code=source.issue_code;
