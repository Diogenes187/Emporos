INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT source_work_id,'repository_file',source.source_uri,
       '0839018902355215fb8148f0b4ce1b1f8e011080',
       source.byte_length,source.checksum,'text/markdown','governing'
FROM src_work
CROSS JOIN (
    VALUES
        ('src/book2/ship-design-and-construction.md',45425::bigint,
         'd27e67dff7c8dc61dc0583aadbb0f42f1daf4875916010f4589425ad4864f1b5'),
        ('src/book2/common-vessels.md',33278::bigint,
         'a64e49da2b14ff9dbc4adbddfc5500e91490c52ba25792d9aaf7474db77a8eff'),
        ('src/vds/vehicle-design.md',92134::bigint,
         '34d54e19abd8ac5b6f9ac4b0444f32adc2e49fabc210176b365ef3a28e2be6db')
) source(source_uri,byte_length,checksum)
WHERE work_code='cepheus-engine.github-v9.1';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('src/book2/ship-design-and-construction.md',
         'Ship Design and Construction > Ship Hull',
         'Cepheus Engine v9.1, Ship Design: Ship Hull'),
        ('src/book2/ship-design-and-construction.md',
         'Ship Design and Construction > Ship Crew',
         'Cepheus Engine v9.1, Ship Design: Ship Crew'),
        ('src/book2/ship-design-and-construction.md',
         'Ship Design and Construction > Additional Ship Components',
         'Cepheus Engine v9.1, Ship Design: Additional Components'),
        ('src/book2/ship-design-and-construction.md',
         'Ship Design and Construction > Armaments',
         'Cepheus Engine v9.1, Ship Design: Armaments'),
        ('src/book2/common-vessels.md',
         'Common Vessels',
         'Cepheus Engine v9.1, Common Vessels'),
        ('src/vds/vehicle-design.md',
         'Vehicle Design > Vehicle Chassis',
         'Cepheus Engine VDS, Vehicle Chassis'),
        ('src/vds/vehicle-design.md',
         'Vehicle Design > Vehicle Armor',
         'Cepheus Engine VDS, Vehicle Armor'),
        ('src/vds/vehicle-design.md',
         'Vehicle Design > Vehicle Drives',
         'Cepheus Engine VDS, Vehicle Drives')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('Off-World Travel > Starship Expenses',
         'Cepheus Engine v9.1, Off-World Travel: Starship Expenses'),
        ('Off-World Travel > Crew Salaries',
         'Cepheus Engine v9.1, Off-World Travel: Crew Salaries'),
        ('Off-World Travel > Life Support',
         'Cepheus Engine v9.1, Off-World Travel: Life Support'),
        ('Off-World Travel > Port Fees',
         'Cepheus Engine v9.1, Off-World Travel: Port Fees'),
        ('Off-World Travel > Routine Maintenance',
         'Cepheus Engine v9.1, Off-World Travel: Routine Maintenance')
) source(heading_path,display_citation)
  ON artifact.source_uri='src/book2/off-world-travel.md';

ALTER TABLE ship_class
    ADD COLUMN hull_configuration text CHECK (
        hull_configuration IS NULL
        OR hull_configuration IN (
            'standard','streamlined','distributed','sphere',
            'close_structure','other'
        )
    ),
    ADD COLUMN construction_weeks integer CHECK (construction_weeks>0),
    ADD COLUMN standard_design boolean NOT NULL DEFAULT false,
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

ALTER TABLE ship_class_characteristic
    DROP CONSTRAINT ship_class_characteristic_characteristic_code_check;

ALTER TABLE ship_class_characteristic
    ADD CONSTRAINT ship_class_characteristic_characteristic_code_check CHECK (
        characteristic_code IN (
            'armor','computer','sensors','fuel_tons',
            'staterooms','low_berths','hardpoints','crew',
            'passenger_capacity','barracks','hangar_tons'
        )
    );

ALTER TABLE ship_component_definition
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

ALTER TABLE ship_weapon_definition
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

ALTER TABLE ship_crew_position_definition
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,'ship.crew.'||source.position_code,
       source.position_name,'ship','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('master','Ship''s Master'),
        ('purser','Ship''s Purser'),
        ('pilot','Pilot'),
        ('navigator','Navigator'),
        ('engineer','Engineer'),
        ('steward','Steward'),
        ('medic','Medic'),
        ('gunner','Gunner'),
        ('other','Other Crewmember')
) source(position_code,position_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO ship_crew_position_definition (
    crew_position_rule_id,position_code,position_name,
    governing_skill_rule_id,standard_monthly_salary_minor,
    source_locator_id
)
SELECT position.rule_id,source.position_code,source.position_name,
       skill.rule_id,source.salary,
       locator.source_locator_id
FROM (
    VALUES
        ('master','Ship''s Master',NULL::text,NULL::bigint),
        ('purser','Ship''s Purser',NULL,3000),
        ('pilot','Pilot','skill.piloting',6000),
        ('navigator','Navigator','skill.navigation',5000),
        ('engineer','Engineer','skill.engineering',4000),
        ('steward','Steward','skill.steward',3000),
        ('medic','Medic','skill.medicine',2000),
        ('gunner','Gunner','skill.gun-combat',1000),
        ('other','Other Crewmember',NULL,1000)
) source(position_code,position_name,skill_code,salary)
JOIN rule_rule position
  ON position.rule_code='ship.crew.'||source.position_code
LEFT JOIN rule_rule skill ON skill.rule_code=source.skill_code
JOIN src_locator locator
  ON locator.heading_path='Off-World Travel > Crew Salaries';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'direct',true
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path='Off-World Travel > Crew Salaries'
WHERE rule.rule_code LIKE 'ship.crew.%';

CREATE TABLE rule_ship_operating_cost (
    operating_cost_code text PRIMARY KEY CHECK (
        operating_cost_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    cost_kind text NOT NULL CHECK (
        cost_kind IN (
            'mortgage','salary','fuel','life_support',
            'berthing','maintenance','repair_supply'
        )
    ),
    amount_minor bigint CHECK (amount_minor>=0),
    rate_numerator integer CHECK (rate_numerator>0),
    rate_denominator integer CHECK (rate_denominator>0),
    rate_basis text CHECK (
        rate_basis IS NULL OR rate_basis IN (
            'cash_price','stateroom','low_berth','fuel_ton',
            'repair_supply_ton','ship'
        )
    ),
    billing_period text CHECK (
        billing_period IS NULL OR billing_period IN (
            'day','six_days','month','year','transaction'
        )
    ),
    term_periods integer CHECK (term_periods>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (amount_minor IS NOT NULL)
        OR (rate_numerator IS NOT NULL AND rate_denominator IS NOT NULL)
    ),
    CHECK (
        (rate_numerator IS NULL)=(rate_denominator IS NULL)
    )
);

INSERT INTO rule_ship_operating_cost (
    operating_cost_code,cost_kind,amount_minor,
    rate_numerator,rate_denominator,rate_basis,
    billing_period,term_periods,source_locator_id
)
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('mortgage-standard','mortgage',NULL::bigint,1,240,
         'cash_price','month',480),
        ('fuel-refined','fuel',500, NULL,NULL,
         'fuel_ton','transaction',NULL),
        ('fuel-unrefined','fuel',100,NULL,NULL,
         'fuel_ton','transaction',NULL),
        ('life-support-stateroom','life_support',2000,NULL,NULL,
         'stateroom','month',NULL),
        ('life-support-low-berth','life_support',100,NULL,NULL,
         'low_berth','month',NULL),
        ('berthing-first-six-days','berthing',100,NULL,NULL,
         'ship','six_days',NULL),
        ('berthing-additional-day','berthing',100,NULL,NULL,
         'ship','day',NULL),
        ('maintenance-annual','maintenance',NULL,1,1000,
         'cash_price','year',NULL),
        ('repair-supplies','repair_supply',10000,NULL,NULL,
         'repair_supply_ton','transaction',NULL)
) source(
    operating_cost_code,cost_kind,amount_minor,
    rate_numerator,rate_denominator,rate_basis,
    billing_period,term_periods
)
JOIN src_locator locator ON locator.heading_path=CASE
    WHEN source.cost_kind='mortgage'
        THEN 'Off-World Travel > Starship Expenses'
    WHEN source.cost_kind='life_support'
        THEN 'Off-World Travel > Life Support'
    WHEN source.cost_kind='berthing'
        THEN 'Off-World Travel > Port Fees'
    WHEN source.cost_kind IN ('maintenance','repair_supply')
        THEN 'Off-World Travel > Routine Maintenance'
    ELSE 'Off-World Travel > Fuel'
END;

CREATE TABLE rule_ship_maintenance_degradation (
    natural_roll_minimum smallint NOT NULL,
    natural_roll_maximum smallint NOT NULL,
    system_hits smallint NOT NULL CHECK (system_hits>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (natural_roll_minimum,natural_roll_maximum),
    CHECK (natural_roll_minimum<=natural_roll_maximum)
);

INSERT INTO rule_ship_maintenance_degradation
SELECT source.minimum_roll,source.maximum_roll,source.system_hits,
       locator.source_locator_id
FROM (
    VALUES (1,3,1),(4,5,2),(6,6,3)
) source(minimum_roll,maximum_roll,system_hits)
JOIN src_locator locator
  ON locator.heading_path='Off-World Travel > Routine Maintenance';
