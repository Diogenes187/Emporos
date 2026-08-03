INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Configuration',
         'Cepheus Engine VDS, Vehicle Configuration'),
        ('Vehicle Design > Vehicle Configuration Options',
         'Cepheus Engine VDS, Vehicle Configuration Options'),
        ('Vehicle Design > Vehicle Drive Options',
         'Cepheus Engine VDS, Vehicle Drive Options')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/vds/vehicle-design.md';

WITH source(rule_code,rule_name) AS (
    VALUES
        ('vehicle.configuration.closed','Closed Vehicle Configuration'),
        ('vehicle.configuration.open','Open Vehicle Configuration'),
        ('vehicle.configuration-option.corrosive-environmental-protection',
         'Corrosive Environmental Protection System'),
        ('vehicle.configuration-option.hostile-environmental-protection',
         'Hostile Environmental Protection System'),
        ('vehicle.configuration-option.hydrofoils','Hydrofoils'),
        ('vehicle.configuration-option.insidious-environmental-protection',
         'Insidious Environmental Protection System'),
        ('vehicle.configuration-option.open-cargo-bed','Open Cargo Bed'),
        ('vehicle.configuration-option.open-frame','Open Frame'),
        ('vehicle.configuration-option.self-sealing','Self-Sealing Chassis'),
        ('vehicle.configuration-option.streamlined','Streamlined Vehicle'),
        ('vehicle.configuration-option.submersible','Submersible'),
        ('vehicle.configuration-option.vacuum-environmental-protection',
         'Vacuum Environmental Protection System'),
        ('vehicle.configuration-option.wave-piercing-hull',
         'Wave-Piercing Hull'),
        ('vehicle.drive-option.additional-drive-system',
         'Additional Drive System'),
        ('vehicle.drive-option.decreased-agility','Decreased Agility'),
        ('vehicle.drive-option.decreased-fuel-efficiency',
         'Decreased Fuel Efficiency'),
        ('vehicle.drive-option.extra-legs','Extra Legs'),
        ('vehicle.drive-option.extra-pair-of-wheels',
         'Extra Pair of Wheels'),
        ('vehicle.drive-option.increased-agility','Increased Agility'),
        ('vehicle.drive-option.increased-fuel-efficiency',
         'Increased Fuel Efficiency'),
        ('vehicle.drive-option.jump-jets','Jump Jets'),
        ('vehicle.drive-option.off-road-capability',
         'Off-Road Capability'),
        ('vehicle.drive-option.tilt-rotors-jets','Tilt Rotors/Jets')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_configuration (
    configuration_rule_id bigint PRIMARY KEY REFERENCES
        rule_rule(rule_id),
    configuration_code text NOT NULL UNIQUE CHECK (
        configuration_code IN ('closed','open')
    ),
    chassis_price_multiplier numeric NOT NULL CHECK (
        chassis_price_multiplier>0
    ),
    sealed_or_airtight boolean NOT NULL,
    unrestricted_attack_direction boolean NOT NULL
);

INSERT INTO rule_vehicle_configuration
SELECT rule.rule_id,source.*
FROM (
    VALUES
        ('closed',1::numeric,false,false),
        ('open',0.9::numeric,false,true)
) source(
    configuration_code,chassis_price_multiplier,
    sealed_or_airtight,unrestricted_attack_direction
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.configuration.'||
     source.configuration_code;

ALTER TABLE vehicle_class
    ADD CONSTRAINT vehicle_class_configuration_fkey
    FOREIGN KEY (configuration)
    REFERENCES rule_vehicle_configuration(configuration_code);

CREATE TABLE rule_vehicle_configuration_cover (
    configuration_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration(configuration_rule_id),
    vehicle_use_code text NOT NULL CHECK (
        vehicle_use_code IN ('civilian','military')
    ),
    cover_code text NOT NULL CHECK (
        cover_code IN ('none','half-soft','full-hard')
    ),
    shooters_per_arc smallint CHECK (shooters_per_arc>0),
    all_occupants_may_attack boolean NOT NULL,
    PRIMARY KEY (configuration_rule_id,vehicle_use_code),
    CHECK (
        (cover_code='none' AND shooters_per_arc IS NULL
         AND all_occupants_may_attack)
        OR
        (cover_code<>'none' AND shooters_per_arc IS NOT NULL
         AND NOT all_occupants_may_attack)
    )
);

INSERT INTO rule_vehicle_configuration_cover
SELECT configuration.configuration_rule_id,
       source.vehicle_use_code,source.cover_code,
       source.shooters_per_arc,source.all_occupants_may_attack
FROM (
    VALUES
        ('closed','civilian','half-soft',2::smallint,false),
        ('closed','military','full-hard',1,false),
        ('open','civilian','none',NULL::smallint,true),
        ('open','military','none',NULL::smallint,true)
) source(
    configuration_code,vehicle_use_code,cover_code,
    shooters_per_arc,all_occupants_may_attack
)
JOIN rule_vehicle_configuration configuration USING (
    configuration_code
);

CREATE TABLE rule_vehicle_design_category (
    category_code text PRIMARY KEY CHECK (
        category_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    category_name text NOT NULL UNIQUE
);

INSERT INTO rule_vehicle_design_category VALUES
    ('aircraft','Aircraft'),
    ('airplane','Airplane'),
    ('jet','Jet'),
    ('hypersonic','Hypersonic'),
    ('aquatic','Aquatic Vessel'),
    ('aquatic-surface','Aquatic Surface Vessel'),
    ('thrust-based','Thrust-Based Vehicle'),
    ('ground','Ground Vehicle'),
    ('hovercraft','Hovercraft'),
    ('walker','Walker'),
    ('wheeled','Wheeled Vehicle');

CREATE TABLE rule_vehicle_propulsion_category (
    propulsion_code text NOT NULL REFERENCES
        rule_vehicle_propulsion_type(propulsion_code),
    speed_variant text NOT NULL CHECK (btrim(speed_variant)<>''),
    category_code text NOT NULL REFERENCES
        rule_vehicle_design_category(category_code),
    PRIMARY KEY (propulsion_code,category_code,speed_variant)
);

INSERT INTO rule_vehicle_propulsion_category VALUES
    ('sails-non-powered','any','aquatic'),
    ('sails-non-powered','any','aquatic-surface'),
    ('sails-non-powered','any','thrust-based'),
    ('wheels-non-powered','any','ground'),
    ('wheels-non-powered','any','wheeled'),
    ('rails','any','ground'),
    ('screw-propeller','any','aquatic'),
    ('screw-propeller','any','aquatic-surface'),
    ('screw-propeller','any','thrust-based'),
    ('airship','any','aircraft'),
    ('airship','any','thrust-based'),
    ('rotor','horizontal','aircraft'),
    ('rotor','horizontal','airplane'),
    ('rotor','horizontal','thrust-based'),
    ('rotor','vertical','aircraft'),
    ('rotor','vertical','thrust-based'),
    ('tracks','any','ground'),
    ('jet','any','aircraft'),
    ('jet','any','jet'),
    ('jet','any','thrust-based'),
    ('mole','any','ground'),
    ('air-cushion','any','ground'),
    ('air-cushion','any','hovercraft'),
    ('air-cushion','any','thrust-based'),
    ('hypersonic','any','aircraft'),
    ('hypersonic','any','hypersonic'),
    ('hypersonic','any','thrust-based'),
    ('legs','any','ground'),
    ('legs','any','walker'),
    ('wheels','any','ground'),
    ('wheels','any','wheeled'),
    ('grav','any','thrust-based'),
    ('advanced-grav','any','thrust-based'),
    ('extreme-grav','any','thrust-based');

CREATE TABLE rule_vehicle_configuration_option (
    option_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE CHECK (
        option_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    minimum_tech_level smallint CHECK (minimum_tech_level>=0),
    required_configuration_code text REFERENCES
        rule_vehicle_configuration(configuration_code),
    space_basis text NOT NULL CHECK (
        space_basis IN (
            'none','fixed','chassis-percent',
            'remaining-spaces-per-depth-doubling'
        )
    ),
    space_value numeric NOT NULL CHECK (space_value>=0),
    space_rounding text NOT NULL CHECK (
        space_rounding IN (
            'exact','ceiling','source-unspecified'
        )
    ),
    price_basis text NOT NULL CHECK (
        price_basis IN (
            'chassis-price-increase-percent',
            'chassis-price-reduction-percent',
            'chassis-price-percent','per-chassis-space',
            'per-chassis-ton','included'
        )
    ),
    price_value numeric NOT NULL CHECK (price_value>=0),
    base_speed_multiplier numeric CHECK (
        base_speed_multiplier>0
    ),
    construction_only boolean NOT NULL DEFAULT false,
    requires_life_support boolean NOT NULL DEFAULT false,
    calculation_status text NOT NULL DEFAULT 'published' CHECK (
        calculation_status IN ('published','adjudicated')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

WITH source(
    option_code,minimum_tl,required_configuration,
    space_basis,space_value,space_rounding,
    price_basis,price_value,base_speed_multiplier,
    construction_only,requires_life_support,calculation_status
) AS (
    VALUES
        ('corrosive-environmental-protection',9::smallint,'closed',
         'fixed',6::numeric,'exact','per-chassis-space',10000::numeric,
         NULL::numeric,false,true,'published'),
        ('hostile-environmental-protection',7,'closed',
         'fixed',3,'exact','per-chassis-space',5000,
         NULL,false,false,'published'),
        ('hydrofoils',NULL::smallint,NULL::text,
         'none',0,'exact','chassis-price-increase-percent',300,
         3,false,false,'published'),
        ('insidious-environmental-protection',9,'closed',
         'fixed',6,'exact','per-chassis-space',50000,
         NULL,false,true,'published'),
        ('open-cargo-bed',NULL,NULL,
         'none',0,'exact','chassis-price-reduction-percent',20,
         NULL,false,false,'published'),
        ('open-frame',NULL,NULL,
         'none',0,'exact','chassis-price-reduction-percent',20,
         NULL,false,false,'adjudicated'),
        ('self-sealing',9,NULL,
         'none',0,'exact','per-chassis-ton',10000,
         NULL,false,false,'published'),
        ('streamlined',NULL,'closed',
         'none',0,'exact','chassis-price-increase-percent',300,
         5,true,false,'published'),
        ('submersible',NULL,NULL,
         'none',0,'exact','chassis-price-increase-percent',500,
         NULL,false,false,'published'),
        ('vacuum-environmental-protection',6,'closed',
         'fixed',3,'exact','per-chassis-space',10000,
         NULL,false,true,'published'),
        ('wave-piercing-hull',NULL,NULL,
         'chassis-percent',5,'ceiling','chassis-price-percent',200,
         1.1,false,false,'published')
)
INSERT INTO rule_vehicle_configuration_option (
    option_rule_id,option_code,minimum_tech_level,
    required_configuration_code,space_basis,space_value,
    space_rounding,price_basis,price_value,
    base_speed_multiplier,construction_only,
    requires_life_support,calculation_status,source_locator_id
)
SELECT rule.rule_id,source.option_code,source.minimum_tl,
       source.required_configuration,source.space_basis,
       source.space_value,source.space_rounding,
       source.price_basis,source.price_value,
       source.base_speed_multiplier,source.construction_only,
       source.requires_life_support,source.calculation_status,
       locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.configuration-option.'||
     source.option_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Configuration Options';

CREATE TABLE rule_vehicle_configuration_option_category (
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    category_code text NOT NULL REFERENCES
        rule_vehicle_design_category(category_code),
    applicability text NOT NULL CHECK (
        applicability IN ('allowed','prohibited')
    ),
    PRIMARY KEY (option_rule_id,category_code)
);

INSERT INTO rule_vehicle_configuration_option_category
SELECT option.option_rule_id,source.category_code,
       source.applicability
FROM (
    VALUES
        ('hydrofoils','aquatic-surface','allowed'),
        ('open-cargo-bed','airplane','prohibited'),
        ('open-cargo-bed','jet','prohibited'),
        ('open-cargo-bed','hypersonic','prohibited'),
        ('open-frame','airplane','prohibited'),
        ('open-frame','jet','prohibited'),
        ('open-frame','hypersonic','prohibited'),
        ('streamlined','thrust-based','allowed'),
        ('submersible','aquatic','allowed'),
        ('wave-piercing-hull','aquatic-surface','allowed')
) source(option_code,category_code,applicability)
JOIN rule_vehicle_configuration_option option USING (option_code);

CREATE TABLE rule_vehicle_configuration_price_combination (
    configuration_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration(configuration_rule_id),
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    combined_chassis_price_reduction_percent numeric NOT NULL CHECK (
        combined_chassis_price_reduction_percent BETWEEN 0 AND 100
    ),
    replaces_individual_reductions boolean NOT NULL,
    calculation_status text NOT NULL CHECK (
        calculation_status IN ('published','adjudicated')
    ),
    PRIMARY KEY (configuration_rule_id,option_rule_id)
);

INSERT INTO rule_vehicle_configuration_price_combination
SELECT configuration.configuration_rule_id,option.option_rule_id,
       25,true,source.calculation_status
FROM (
    VALUES
        ('open-cargo-bed','published'),
        ('open-frame','adjudicated')
) source(option_code,calculation_status)
JOIN rule_vehicle_configuration configuration
  ON configuration.configuration_code='open'
JOIN rule_vehicle_configuration_option option USING (option_code);

CREATE TABLE rule_vehicle_environmental_hazard (
    hazard_code text PRIMARY KEY CHECK (
        hazard_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    hazard_name text NOT NULL UNIQUE
);

INSERT INTO rule_vehicle_environmental_hazard VALUES
    ('vacuum','Vacuum'),
    ('corrosive','Corrosive Environment'),
    ('insidious-atmosphere','Insidious Atmosphere'),
    ('extreme-heat','Extreme Heat'),
    ('extreme-cold','Extreme Cold'),
    ('radiation','Radiation'),
    ('poison','Poison'),
    ('bacteriological','Bacteriological Threat');

CREATE TABLE rule_vehicle_environmental_protection (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    protected_duration_days smallint CHECK (
        protected_duration_days>0
    ),
    hull_structure_damage_per_day_after_duration smallint CHECK (
        hull_structure_damage_per_day_after_duration>0
    ),
    CHECK (
        (
            protected_duration_days IS NULL
            AND hull_structure_damage_per_day_after_duration IS NULL
        )
        OR
        (
            protected_duration_days IS NOT NULL
            AND hull_structure_damage_per_day_after_duration IS NOT NULL
        )
    )
);

INSERT INTO rule_vehicle_environmental_protection
SELECT option.option_rule_id,source.protected_duration_days,
       source.damage_per_day
FROM (
    VALUES
        ('corrosive-environmental-protection',NULL::smallint,NULL::smallint),
        ('hostile-environmental-protection',NULL,NULL),
        ('insidious-environmental-protection',5,1),
        ('vacuum-environmental-protection',NULL,NULL)
) source(option_code,protected_duration_days,damage_per_day)
JOIN rule_vehicle_configuration_option option USING (option_code);

CREATE TABLE rule_vehicle_environmental_protection_hazard (
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_environmental_protection(option_rule_id),
    hazard_code text NOT NULL REFERENCES
        rule_vehicle_environmental_hazard(hazard_code),
    PRIMARY KEY (option_rule_id,hazard_code)
);

INSERT INTO rule_vehicle_environmental_protection_hazard
SELECT option.option_rule_id,source.hazard_code
FROM (
    VALUES
        ('corrosive-environmental-protection','corrosive'),
        ('corrosive-environmental-protection','extreme-heat'),
        ('corrosive-environmental-protection','extreme-cold'),
        ('corrosive-environmental-protection','radiation'),
        ('corrosive-environmental-protection','poison'),
        ('corrosive-environmental-protection','bacteriological'),
        ('hostile-environmental-protection','extreme-heat'),
        ('hostile-environmental-protection','extreme-cold'),
        ('hostile-environmental-protection','radiation'),
        ('hostile-environmental-protection','poison'),
        ('hostile-environmental-protection','bacteriological'),
        ('insidious-environmental-protection','insidious-atmosphere'),
        ('insidious-environmental-protection','extreme-heat'),
        ('insidious-environmental-protection','extreme-cold'),
        ('insidious-environmental-protection','radiation'),
        ('insidious-environmental-protection','poison'),
        ('insidious-environmental-protection','bacteriological'),
        ('vacuum-environmental-protection','vacuum'),
        ('vacuum-environmental-protection','extreme-heat'),
        ('vacuum-environmental-protection','extreme-cold'),
        ('vacuum-environmental-protection','radiation'),
        ('vacuum-environmental-protection','poison'),
        ('vacuum-environmental-protection','bacteriological')
) source(option_code,hazard_code)
JOIN rule_vehicle_configuration_option option USING (option_code);

CREATE TABLE rule_vehicle_configuration_option_inclusion (
    parent_option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    included_option_rule_id bigint REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    included_component_rule_id bigint REFERENCES
        vehicle_component_definition(component_rule_id),
    included_spaces numeric NOT NULL CHECK (included_spaces>=0),
    included_cost_minor bigint NOT NULL CHECK (
        included_cost_minor>=0
    ),
    CHECK (
        num_nonnulls(
            included_option_rule_id,included_component_rule_id
        )=1
    ),
    UNIQUE (
        parent_option_rule_id,included_option_rule_id,
        included_component_rule_id
    )
);

INSERT INTO rule_vehicle_configuration_option_inclusion (
    parent_option_rule_id,included_option_rule_id,
    included_component_rule_id,included_spaces,included_cost_minor
)
SELECT parent.option_rule_id,included.option_rule_id,NULL,3,0
FROM rule_vehicle_configuration_option parent
JOIN rule_vehicle_configuration_option included
  ON included.option_code='hostile-environmental-protection'
WHERE parent.option_code='submersible';

INSERT INTO rule_vehicle_configuration_option_inclusion (
    parent_option_rule_id,included_option_rule_id,
    included_component_rule_id,included_spaces,included_cost_minor
)
SELECT parent.option_rule_id,NULL,component.component_rule_id,3,0
FROM rule_vehicle_configuration_option parent
JOIN vehicle_component_definition component
  ON component.component_code='life-support.basic'
WHERE parent.option_code='submersible';

CREATE TABLE rule_vehicle_submersible_depth (
    minimum_tech_level smallint PRIMARY KEY CHECK (
        minimum_tech_level>=0
    ),
    maximum_tech_level smallint CHECK (
        maximum_tech_level>=minimum_tech_level
    ),
    safe_dive_depth_metres integer NOT NULL CHECK (
        safe_dive_depth_metres>0
    ),
    crush_depth_metres integer NOT NULL CHECK (
        crush_depth_metres>safe_dive_depth_metres
    ),
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_configuration_option(option_rule_id)
);

INSERT INTO rule_vehicle_submersible_depth
SELECT source.*,option.option_rule_id
FROM (
    VALUES
        (4::smallint,5::smallint,50,150),
        (6,8,200,600),
        (9,11,600,1800),
        (12,14,2000,6000),
        (15,16,4000,12000),
        (17,NULL::smallint,8000,24000)
) source(
    minimum_tech_level,maximum_tech_level,
    safe_dive_depth_metres,crush_depth_metres
)
JOIN rule_vehicle_configuration_option option
  ON option.option_code='submersible';

CREATE TABLE rule_vehicle_submersible_world_adjustment (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    baseline_world_size smallint NOT NULL CHECK (
        baseline_world_size>=0
    ),
    depth_percent_per_size_difference numeric NOT NULL CHECK (
        depth_percent_per_size_difference>0
    ),
    larger_world_depth_direction text NOT NULL CHECK (
        larger_world_depth_direction IN ('increase','decrease')
    )
);

INSERT INTO rule_vehicle_submersible_world_adjustment
SELECT option_rule_id,8,10,'decrease'
FROM rule_vehicle_configuration_option
WHERE option_code='submersible';

CREATE TABLE rule_vehicle_submersible_depth_upgrade (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_configuration_option(option_rule_id),
    depth_multiplier_per_step numeric NOT NULL CHECK (
        depth_multiplier_per_step>1
    ),
    remaining_space_multiplier_per_step numeric NOT NULL CHECK (
        remaining_space_multiplier_per_step>0
        AND remaining_space_multiplier_per_step<1
    ),
    chassis_price_increase_percent_per_step numeric NOT NULL CHECK (
        chassis_price_increase_percent_per_step>0
    ),
    space_rounding text NOT NULL CHECK (
        space_rounding IN (
            'floor','ceiling','nearest','source-unspecified'
        )
    )
);

INSERT INTO rule_vehicle_submersible_depth_upgrade
SELECT option_rule_id,2,0.5,100,'source-unspecified'
FROM rule_vehicle_configuration_option
WHERE option_code='submersible';

CREATE TABLE rule_vehicle_drive_option (
    option_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    option_code text NOT NULL UNIQUE CHECK (
        option_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_drive_option
SELECT rule.rule_id,source.option_code,locator.source_locator_id
FROM (
    VALUES
        ('additional-drive-system'),
        ('decreased-agility'),
        ('decreased-fuel-efficiency'),
        ('extra-legs'),
        ('extra-pair-of-wheels'),
        ('increased-agility'),
        ('increased-fuel-efficiency'),
        ('jump-jets'),
        ('off-road-capability'),
        ('tilt-rotors-jets')
) source(option_code)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.drive-option.'||source.option_code
JOIN src_locator locator
  ON locator.heading_path='Vehicle Design > Vehicle Drive Options';

CREATE TABLE rule_vehicle_drive_option_category (
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    category_code text NOT NULL REFERENCES
        rule_vehicle_design_category(category_code),
    PRIMARY KEY (option_rule_id,category_code)
);

INSERT INTO rule_vehicle_drive_option_category
SELECT option.option_rule_id,source.category_code
FROM (
    VALUES
        ('extra-legs','walker'),
        ('extra-pair-of-wheels','wheeled'),
        ('jump-jets','ground'),
        ('jump-jets','hovercraft'),
        ('off-road-capability','ground'),
        ('tilt-rotors-jets','aircraft')
) source(option_code,category_code)
JOIN rule_vehicle_drive_option option USING (option_code);

CREATE TABLE rule_vehicle_drive_adjustment_option (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    agility_dm_per_step smallint,
    maximum_steps smallint CHECK (maximum_steps>0),
    fuel_consumption_multiplier numeric CHECK (
        fuel_consumption_multiplier>0
    ),
    chassis_price_adjustment_percent_per_step numeric NOT NULL,
    CHECK (
        agility_dm_per_step IS NOT NULL
        OR fuel_consumption_multiplier IS NOT NULL
    )
);

INSERT INTO rule_vehicle_drive_adjustment_option
SELECT option.option_rule_id,source.agility_dm_per_step,
       source.maximum_steps,source.fuel_multiplier,
       source.price_adjustment
FROM (
    VALUES
        ('decreased-agility',-1::smallint,2::smallint,NULL::numeric,-25::numeric),
        ('decreased-fuel-efficiency',NULL::smallint,NULL::smallint,1.25::numeric,-10::numeric),
        ('increased-agility',1::smallint,3::smallint,NULL::numeric,50::numeric),
        ('increased-fuel-efficiency',NULL::smallint,NULL::smallint,0.9::numeric,20::numeric)
) source(
    option_code,agility_dm_per_step,maximum_steps,
    fuel_multiplier,price_adjustment
)
JOIN rule_vehicle_drive_option option USING (option_code);

CREATE TABLE rule_vehicle_secondary_drive_option (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    secondary_performance_offset smallint NOT NULL CHECK (
        secondary_performance_offset<0
    ),
    agility_dm smallint NOT NULL CHECK (agility_dm<0),
    purchase_second_propulsion_drive boolean NOT NULL
);

INSERT INTO rule_vehicle_secondary_drive_option
SELECT option_rule_id,-1,-1,true
FROM rule_vehicle_drive_option
WHERE option_code='additional-drive-system';

CREATE TABLE rule_vehicle_extra_contact_element (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    element_code text NOT NULL UNIQUE CHECK (
        element_code IN ('leg','wheel-pair')
    ),
    drive_price_percent_per_element numeric NOT NULL CHECK (
        drive_price_percent_per_element>0
    ),
    drive_space_percent_per_element numeric NOT NULL CHECK (
        drive_space_percent_per_element>0
    ),
    elements_per_terrain_penalty_reduction smallint NOT NULL CHECK (
        elements_per_terrain_penalty_reduction>0
    ),
    terrain_penalty_reduction smallint NOT NULL CHECK (
        terrain_penalty_reduction>0
    ),
    standard_element_count smallint NOT NULL CHECK (
        standard_element_count>0
    ),
    small_vehicle_element_count smallint,
    small_vehicle_maximum_tons numeric,
    attack_dm_threshold_element_count smallint,
    attack_dm smallint,
    CHECK (
        num_nonnulls(
            small_vehicle_element_count,small_vehicle_maximum_tons
        ) IN (0,2)
    ),
    CHECK (
        num_nonnulls(
            attack_dm_threshold_element_count,attack_dm
        ) IN (0,2)
    )
);

INSERT INTO rule_vehicle_extra_contact_element
SELECT option.option_rule_id,source.element_code,
       source.drive_price_percent_per_element,
       source.drive_space_percent_per_element,
       source.elements_per_terrain_penalty_reduction,
       source.terrain_penalty_reduction,
       source.standard_element_count,
       source.small_vehicle_element_count,
       source.small_vehicle_maximum_tons,
       source.attack_dm_threshold_element_count,
       source.attack_dm
FROM (
    VALUES
        ('extra-legs','leg',25::numeric,5::numeric,2::smallint,1::smallint,
         2::smallint,NULL::smallint,NULL::numeric,4::smallint,1::smallint),
        ('extra-pair-of-wheels','wheel-pair',25,25,1,1,
         2,1,0.5,NULL::smallint,NULL::smallint)
) source(
    option_code,element_code,drive_price_percent_per_element,
    drive_space_percent_per_element,
    elements_per_terrain_penalty_reduction,
    terrain_penalty_reduction,standard_element_count,
    small_vehicle_element_count,small_vehicle_maximum_tons,
    attack_dm_threshold_element_count,attack_dm
)
JOIN rule_vehicle_drive_option option USING (option_code);

CREATE TABLE rule_vehicle_jump_jet_option (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    selected_drive_basis text NOT NULL CHECK (
        selected_drive_basis='thrust'
    ),
    minimum_drive_performance smallint NOT NULL CHECK (
        minimum_drive_performance>0
    ),
    drive_space_multiplier numeric NOT NULL CHECK (
        drive_space_multiplier>0
    ),
    drive_price_multiplier numeric NOT NULL CHECK (
        drive_price_multiplier>0
    ),
    flight_speed_multiplier numeric NOT NULL CHECK (
        flight_speed_multiplier>0
    ),
    fuel_consumption_multiplier numeric NOT NULL CHECK (
        fuel_consumption_multiplier>0
    ),
    maximum_altitude_metres integer NOT NULL CHECK (
        maximum_altitude_metres>0
    )
);

INSERT INTO rule_vehicle_jump_jet_option
SELECT option_rule_id,'thrust',1,0.75,0.75,0.25,5,100
FROM rule_vehicle_drive_option
WHERE option_code='jump-jets';

CREATE TABLE rule_vehicle_off_road_option (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    contact_drive_price_percent numeric NOT NULL CHECK (
        contact_drive_price_percent>0
    ),
    base_speed_multiplier numeric NOT NULL CHECK (
        base_speed_multiplier>0
    ),
    normal_off_road_agility_penalty_negated smallint NOT NULL CHECK (
        normal_off_road_agility_penalty_negated>0
    ),
    rough_terrain_agility_dm smallint NOT NULL CHECK (
        rough_terrain_agility_dm<0
    ),
    off_road_speed_reduction_negated boolean NOT NULL
);

INSERT INTO rule_vehicle_off_road_option
SELECT option_rule_id,50,0.9,2,-2,true
FROM rule_vehicle_drive_option
WHERE option_code='off-road-capability';

CREATE TABLE rule_vehicle_tilt_rotor_jet_option (
    option_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_drive_option(option_rule_id),
    thrust_drive_price_multiplier numeric NOT NULL CHECK (
        thrust_drive_price_multiplier>0
    ),
    vertical_takeoff boolean NOT NULL,
    hover_capable boolean NOT NULL
);

INSERT INTO rule_vehicle_tilt_rotor_jet_option
SELECT option_rule_id,3,true,true
FROM rule_vehicle_drive_option
WHERE option_code='tilt-rotors-jets';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code LIKE 'vehicle.configuration-option.%'
               THEN configuration_option.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.drive-option.%'
               THEN drive_option.source_locator_id
           ELSE configuration_locator.source_locator_id
       END,
       'direct',true
FROM rule_rule rule
LEFT JOIN rule_vehicle_configuration_option configuration_option
  ON configuration_option.option_rule_id=rule.rule_id
LEFT JOIN rule_vehicle_drive_option drive_option
  ON drive_option.option_rule_id=rule.rule_id
LEFT JOIN src_locator configuration_locator
  ON configuration_locator.heading_path=
     'Vehicle Design > Vehicle Configuration'
 AND rule.rule_code LIKE 'vehicle.configuration.%'
WHERE rule.rule_code LIKE 'vehicle.configuration.%'
   OR rule.rule_code LIKE 'vehicle.configuration-option.%'
   OR rule.rule_code LIKE 'vehicle.drive-option.%';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
SELECT source.issue_code,'vehicle.catalogue',source.issue_type,
       source.review_priority,source.subject_code,source.title,
       source.problem_statement,source.published_value,
       source.calculated_value,source.reviewer_question,
       'A corrected printing, publisher errata, or a corroborating authorized source with an explicit replacement rule.',
       source.engine_disposition
FROM (
    VALUES
        (
            'vehicle.configuration.open-frame-copy-error',
            'source_conflict','high','open-frame',
            'Open Frame paragraph names Open Cargo Bed',
            'The Open Frame paragraph gives its 20% reduction, but its prohibition and combined Open-configuration rule repeatedly name Open Cargo Bed instead of Open Frame.',
            'Open Frame heading; Open Cargo Bed conditions',
            'Open Frame uses the parallel aircraft prohibition and combined 25% reduction',
            'Should the Open Frame paragraph name Open Frame in its aircraft prohibition and Open-configuration combination?',
            'preserve_rule'
        ),
        (
            'vehicle.configuration.submersible-ballast-rounding',
            'source_omission','medium','submersible',
            'Submersible ballast rounding direction unspecified',
            'Each depth doubling removes half the remaining spaces, but the instruction says only "rounded off" and does not specify floor, ceiling, or nearest rounding.',
            'Half remaining spaces, rounded off',
            'Rounding method source-unspecified',
            'Should submersible ballast space loss round down, round up, or to the nearest Space?',
            'source_gap_pending'
        )
) source(
    issue_code,issue_type,review_priority,subject_code,title,
    problem_statement,published_value,calculated_value,
    reviewer_question,engine_disposition
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Configuration Options'
WHERE issue.issue_code LIKE 'vehicle.configuration.%';
