INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Crew and Passengers',
         'Cepheus Engine VDS, Vehicle Crew and Passengers'),
        ('Vehicle Design > Vehicle Crew and Passengers > Life Support',
         'Cepheus Engine VDS, Vehicle Life Support'),
        ('Vehicle Design > Additional Vehicle Components',
         'Cepheus Engine VDS, Additional Vehicle Components')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/vds/vehicle-design.md';

ALTER TABLE vehicle_component_definition
    ADD COLUMN space_basis text NOT NULL DEFAULT 'fixed' CHECK (
        space_basis IN (
            'fixed','per_person','per_people_group',
            'per_chassis_space','per_chassis_ton','per_patient',
            'per_refrigerated_space','per_vessel_ton',
            'per_researcher_bonus','remaining_capacity','included',
            'source_unspecified'
        )
    ),
    ADD COLUMN cost_basis text NOT NULL DEFAULT 'fixed' CHECK (
        cost_basis IN (
            'fixed','per_space','per_person','per_chassis_space',
            'per_chassis_ton','included','source_unspecified'
        )
    ),
    ADD COLUMN capacity_kind text CHECK (
        capacity_kind IS NULL OR capacity_kind IN (
            'person','crew','additional_person','prisoner',
            'researcher','cargo_space','liquid_gas_space','lift_kg'
        )
    ),
    ADD COLUMN capacity_per_unit numeric CHECK (
        capacity_per_unit IS NULL OR capacity_per_unit>0
    ),
    ADD COLUMN effect_code text CHECK (
        effect_code IS NULL
        OR effect_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    ADD COLUMN calculation_status text NOT NULL DEFAULT 'published' CHECK (
        calculation_status IN (
            'published','formula','included','source_unspecified'
        )
    );

WITH source(component_code,component_name) AS (
    VALUES
        ('accommodation.bunk-military','Military Bunk'),
        ('accommodation.control-cabin-basic','Basic Control Cabin'),
        ('accommodation.control-cabin-extended','Extended Control Cabin'),
        ('accommodation.control-cabin-standard','Standard Control Cabin'),
        ('accommodation.low-berth','Vehicle Low Berth'),
        ('accommodation.stateroom-economy','Economy Stateroom'),
        ('accommodation.stateroom-elite','Elite Stateroom'),
        ('accommodation.stateroom-standard','Standard Stateroom'),
        ('accommodation.cockpit-basic','Basic Cockpit'),
        ('accommodation.cockpit-extended','Extended Cockpit'),
        ('accommodation.seat-cramped','Cramped Seat'),
        ('accommodation.seat-standard','Standard Seat'),
        ('life-support.basic','Basic Vehicle Life Support'),
        ('life-support.extended','Extended Vehicle Life Support')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.component.'||source.component_code,
       source.component_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

WITH source(
    component_code,component_kind,minimum_tl,unit_spaces,unit_cost,
    capacity_kind,capacity_per_unit,effect_code,heading_path
) AS (
    VALUES
        ('accommodation.bunk-military','passenger_space',NULL::smallint,24::numeric,100000::bigint,
         'additional_person',1::numeric,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.control-cabin-basic','crew_space',NULL,36,10000,
         'crew',1,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.control-cabin-extended','passenger_space',NULL,18,5000,
         'additional_person',1,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.control-cabin-standard','crew_space',NULL,72,20000,
         'person',3,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.low-berth','passenger_space',NULL,6,50000,
         'person',1,'hibernation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.stateroom-economy','passenger_space',NULL,24,250000,
         'person',1,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.stateroom-elite','passenger_space',NULL,72,750000,
         'person',2,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.stateroom-standard','passenger_space',NULL,48,500000,
         'person',2,'long-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.cockpit-basic','crew_space',NULL,2,1000,
         'crew',1,'short-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.cockpit-extended','crew_space',NULL,4,2000,
         'crew',2,'short-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.seat-cramped','passenger_space',NULL,4,2000,
         'person',3,'short-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('accommodation.seat-standard','passenger_space',NULL,2,1000,
         'person',1,'short-accommodation',
         'Vehicle Design > Vehicle Crew and Passengers'),
        ('life-support.basic','environmental_protection',4,3,10500,
         'person',20,'life-support-10-days',
         'Vehicle Design > Vehicle Crew and Passengers > Life Support'),
        ('life-support.extended','environmental_protection',7,3,52500,
         'person',5,'life-support-90-days',
         'Vehicle Design > Vehicle Crew and Passengers > Life Support')
)
INSERT INTO vehicle_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_spaces,unit_cost_minor,
    source_locator_id,capacity_kind,capacity_per_unit,effect_code
)
SELECT rule.rule_id,source.component_code,source.component_kind,
       source.minimum_tl,source.unit_spaces,source.unit_cost,
       locator.source_locator_id,source.capacity_kind,
       source.capacity_per_unit,source.effect_code
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.component.'||source.component_code
JOIN src_locator locator USING (heading_path);

CREATE TABLE rule_vehicle_accommodation (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    accommodation_code text NOT NULL UNIQUE CHECK (
        accommodation_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    duration_code text NOT NULL CHECK (
        duration_code IN ('short','long')
    ),
    maximum_occupants smallint NOT NULL CHECK (maximum_occupants>0),
    crew_capacity smallint NOT NULL DEFAULT 0 CHECK (crew_capacity>=0),
    additional_person_capacity smallint NOT NULL DEFAULT 0 CHECK (
        additional_person_capacity>=0
    ),
    comfortable_occupants smallint CHECK (comfortable_occupants>0),
    cramped_occupants smallint CHECK (cramped_occupants>0),
    military_only boolean NOT NULL DEFAULT false,
    hibernation_berth boolean NOT NULL DEFAULT false,
    includes_fresher boolean NOT NULL DEFAULT false,
    CHECK (
        crew_capacity<=maximum_occupants
        AND additional_person_capacity<=maximum_occupants
        AND COALESCE(comfortable_occupants,0)<=maximum_occupants
        AND COALESCE(cramped_occupants,0)<=maximum_occupants
    )
);

INSERT INTO rule_vehicle_accommodation
SELECT component.component_rule_id,source.*
FROM (
    VALUES
        ('bunk-military','long',1,0,1,NULL::smallint,1,true,false,false),
        ('control-cabin-basic','long',1,1,0,NULL,NULL,false,false,false),
        ('control-cabin-extended','long',1,0,1,NULL,NULL,false,false,false),
        ('control-cabin-standard','long',3,2,1,NULL,NULL,false,false,false),
        ('low-berth','long',1,0,1,NULL,NULL,false,true,false),
        ('stateroom-economy','long',1,0,1,NULL,1,false,false,true),
        ('stateroom-elite','long',2,0,2,2,NULL,false,false,true),
        ('stateroom-standard','long',2,0,2,1,2,false,false,true),
        ('cockpit-basic','short',1,1,0,NULL,NULL,false,false,false),
        ('cockpit-extended','short',2,2,0,NULL,NULL,false,false,false),
        ('seat-cramped','short',3,0,3,NULL,3,false,false,false),
        ('seat-standard','short',1,0,1,NULL,NULL,false,false,false)
) source(
    accommodation_code,duration_code,maximum_occupants,
    crew_capacity,additional_person_capacity,
    comfortable_occupants,cramped_occupants,
    military_only,hibernation_berth,includes_fresher
)
JOIN vehicle_component_definition component
  ON component.component_code=
     'accommodation.'||source.accommodation_code;

CREATE TABLE rule_vehicle_life_support (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    life_support_code text NOT NULL UNIQUE,
    supported_people_per_unit smallint NOT NULL CHECK (
        supported_people_per_unit>0
    ),
    spaces_per_unit numeric NOT NULL CHECK (spaces_per_unit>0),
    price_per_space_minor bigint NOT NULL CHECK (
        price_per_space_minor>=0
    ),
    duration_days smallint NOT NULL CHECK (duration_days>0)
);

INSERT INTO rule_vehicle_life_support
SELECT component.component_rule_id,source.*
FROM (
    VALUES
        ('basic',20,3::numeric,3500::bigint,10),
        ('extended',5,3,17500,90)
) source(
    life_support_code,supported_people_per_unit,spaces_per_unit,
    price_per_space_minor,duration_days
)
JOIN vehicle_component_definition component
  ON component.component_code='life-support.'||
     source.life_support_code;

CREATE TABLE rule_vehicle_life_support_inclusion (
    condition_code text PRIMARY KEY CHECK (
        condition_code IN (
            'submersible','hostile-environmental-protection'
        )
    ),
    component_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_life_support(component_rule_id),
    included_spaces numeric NOT NULL CHECK (included_spaces>0),
    included_cost_minor bigint NOT NULL CHECK (
        included_cost_minor>=0
    )
);

INSERT INTO rule_vehicle_life_support_inclusion
SELECT source.condition_code,component.component_rule_id,3,0
FROM (
    VALUES
        ('submersible'),('hostile-environmental-protection')
) source(condition_code)
JOIN vehicle_component_definition component
  ON component.component_code='life-support.basic';

CREATE TABLE rule_vehicle_sailing_crew_formula (
    formula_code text PRIMARY KEY,
    tech_level_subtrahend smallint NOT NULL,
    minimum_crew_per_tonnage_group smallint NOT NULL CHECK (
        minimum_crew_per_tonnage_group>0
    ),
    displacement_tons_per_group numeric NOT NULL CHECK (
        displacement_tons_per_group>0
    ),
    small_vessel_maximum_tons numeric NOT NULL CHECK (
        small_vessel_maximum_tons>0
    ),
    small_vessel_crew_multiplier numeric NOT NULL CHECK (
        small_vessel_crew_multiplier>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_sailing_crew_formula
SELECT 'standard',10,1,4,2,0.5,locator.source_locator_id
FROM src_locator locator
WHERE locator.heading_path=
      'Vehicle Design > Vehicle Crew and Passengers';

WITH source(component_code,component_name) AS (
    VALUES
        ('additional.cargo-hold','Vehicle Cargo Hold'),
        ('additional.cargo-trailer','Cargo Trailer'),
        ('additional.wet-bar','Wet Bar'),
        ('additional.detention-cell','Vehicle Detention Cell'),
        ('additional.floats-pontoons','Floats/Pontoons'),
        ('additional.folding-wings-rotors','Folding Wings/Rotors'),
        ('additional.galley-mini','Mini-Galley'),
        ('additional.galley-full','Full Galley'),
        ('additional.crane-heavy','Heavy Crane'),
        ('additional.crane-light','Light Crane'),
        ('additional.crane-medium','Medium Crane'),
        ('additional.fire-extinguishers','Fire Extinguishers'),
        ('additional.liquid-cannon','Liquid Cannon'),
        ('additional.cutting-equipment','Cutting Equipment'),
        ('additional.digging-equipment','Digging Equipment'),
        ('additional.ejection-seat','Ejection Seat'),
        ('additional.entertainment-system','Entertainment System'),
        ('additional.manipulator-arms','Manipulator Arms'),
        ('additional.operating-theater','Operating Theater'),
        ('additional.refrigeration','Refrigeration'),
        ('additional.sampler-atmosphere','Atmosphere Sampler'),
        ('additional.sampler-geology','Geology Sampler'),
        ('additional.sampler-hydrology','Hydrology Sampler'),
        ('additional.airlock','Vehicle Airlock'),
        ('additional.hot-tub-pool','Hot Tub/Pool'),
        ('additional.fresher','Fresher'),
        ('additional.general-purpose-lab','General Purpose Lab'),
        ('additional.cargo-arm','Cargo Arm'),
        ('additional.holding-tank','Holding Tank'),
        ('additional.refueling-station','Refueling Station'),
        ('additional.research-lab-space','Research Lab Space'),
        ('additional.holo-suite','Holo-Suite'),
        ('additional.autodoc','Vehicle Autodoc'),
        ('additional.emergency-low-berth','Emergency Low Berth'),
        ('additional.nuclear-damper','Vehicle Nuclear Damper')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.component.'||source.component_code,
       source.component_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

WITH source(
    component_code,component_kind,minimum_tl,unit_spaces,unit_cost,
    space_basis,cost_basis,capacity_kind,capacity_per_unit,
    effect_code,calculation_status
) AS (
    VALUES
        ('additional.cargo-hold','cargo',1,0::numeric,0::bigint,
         'remaining_capacity','included','cargo_space',1::numeric,
         'cargo-capacity','included'),
        ('additional.cargo-trailer','cargo',1,0,0,
         'source_unspecified','source_unspecified','cargo_space',NULL,
         'towed-cargo','formula'),
        ('additional.wet-bar','passenger_space',2,1.5,2000,
         'fixed','fixed',NULL,NULL,'hospitality','published'),
        ('additional.detention-cell','passenger_space',3,12,125000,
         'fixed','fixed','prisoner',1,'secure-confinement','published'),
        ('additional.floats-pontoons','other',3,0,0,
         'per_chassis_space','per_chassis_space',NULL,NULL,
         'water-landing','formula'),
        ('additional.folding-wings-rotors','other',3,0,0,
         'included','per_chassis_space',NULL,NULL,
         'compact-storage','formula'),
        ('additional.galley-mini','passenger_space',3,6,1000,
         'fixed','fixed','person',5,'food-service','published'),
        ('additional.galley-full','passenger_space',3,18,2000,
         'per_people_group','per_person','person',NULL,
         'food-service','formula'),
        ('additional.crane-heavy','other',4,24,100000,
         'fixed','fixed','lift_kg',10000,'material-handling','published'),
        ('additional.crane-light','other',4,3,2500,
         'fixed','fixed','lift_kg',400,'material-handling','published'),
        ('additional.crane-medium','other',4,12,40000,
         'fixed','fixed','lift_kg',2000,'material-handling','published'),
        ('additional.fire-extinguishers','other',4,0,500,
         'fixed','fixed',NULL,NULL,'internal-fire-suppression','published'),
        ('additional.liquid-cannon','other',4,3,2000,
         'fixed','fixed',NULL,NULL,'liquid-projector','published'),
        ('additional.cutting-equipment','other',5,15,10000,
         'fixed','fixed',NULL,NULL,'external-cutting','published'),
        ('additional.digging-equipment','other',5,30,25000,
         'fixed','fixed',NULL,NULL,'external-excavation','published'),
        ('additional.ejection-seat','crew_space',5,2,5000,
         'fixed','fixed','person',1,'emergency-egress','published'),
        ('additional.entertainment-system','passenger_space',5,0,200,
         'fixed','fixed',NULL,NULL,'entertainment','published'),
        ('additional.manipulator-arms','other',5,0,10000,
         'fixed','fixed',NULL,NULL,'remote-manipulation','formula'),
        ('additional.operating-theater','passenger_space',5,12,0,
         'per_patient','per_space','person',NULL,
         'medical-treatment','formula'),
        ('additional.refrigeration','cargo',5,0,0,
         'per_refrigerated_space','per_space','cargo_space',NULL,
         'refrigerated-capacity','formula'),
        ('additional.sampler-atmosphere','sensors',5,9,10000,
         'fixed','fixed',NULL,NULL,'atmosphere-sampling','published'),
        ('additional.sampler-geology','sensors',5,45,100000,
         'fixed','fixed',NULL,NULL,'geology-sampling','published'),
        ('additional.sampler-hydrology','sensors',5,15,10000,
         'fixed','fixed',NULL,NULL,'hydrology-sampling','published'),
        ('additional.airlock','environmental_protection',6,12,200000,
         'fixed','fixed',NULL,NULL,'sealed-egress','published'),
        ('additional.hot-tub-pool','passenger_space',6,1,3000,
         'per_person','per_space','person',1,'recreation','formula'),
        ('additional.fresher','passenger_space',7,6,1500,
         'fixed','fixed','person',NULL,'sanitation','published'),
        ('additional.general-purpose-lab','other',7,6,10000,
         'per_person','fixed','researcher',1,
         'equipped-research','formula'),
        ('additional.cargo-arm','other',8,1,50000,
         'fixed','fixed','lift_kg',NULL,'cargo-manipulation','published'),
        ('additional.holding-tank','cargo',8,1,1500,
         'per_person','per_space','liquid_gas_space',1,
         'fluid-storage','formula'),
        ('additional.refueling-station','fuel',9,12,0,
         'per_vessel_ton','per_space',NULL,NULL,
         'hydrogen-production','formula'),
        ('additional.research-lab-space','other',9,3,10000,
         'per_researcher_bonus','fixed','researcher',1,
         'skill-research','formula'),
        ('additional.holo-suite','passenger_space',10,3,15000,
         'fixed','fixed',NULL,NULL,'holographic-projection','published'),
        ('additional.autodoc','other',12,6,40000,
         'fixed','fixed','person',1,'automated-treatment','published'),
        ('additional.emergency-low-berth','passenger_space',12,12,100000,
         'fixed','fixed','person',4,'emergency-survival','published'),
        ('additional.nuclear-damper','environmental_protection',12,12,500000,
         'fixed','fixed',NULL,NULL,'nuclear-force-projection','published')
)
INSERT INTO vehicle_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_spaces,unit_cost_minor,
    source_locator_id,space_basis,cost_basis,
    capacity_kind,capacity_per_unit,effect_code,calculation_status
)
SELECT rule.rule_id,source.component_code,source.component_kind,
       source.minimum_tl,source.unit_spaces,source.unit_cost,
       locator.source_locator_id,source.space_basis,source.cost_basis,
       source.capacity_kind,source.capacity_per_unit,
       source.effect_code,source.calculation_status
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.component.'||source.component_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Additional Vehicle Components';

CREATE TABLE rule_vehicle_component_formula (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    quantity_basis text NOT NULL CHECK (
        quantity_basis IN (
            'chassis_spaces','people_served','person_capacity',
            'patient_capacity','refrigerated_spaces',
            'allocated_spaces','vessel_tons',
            'researcher_skill_levels'
        )
    ),
    base_spaces numeric NOT NULL DEFAULT 0 CHECK (base_spaces>=0),
    spaces_per_increment numeric NOT NULL DEFAULT 0 CHECK (
        spaces_per_increment>=0
    ),
    basis_units_per_increment numeric NOT NULL DEFAULT 1 CHECK (
        basis_units_per_increment>0
    ),
    increment_rounding text NOT NULL DEFAULT 'exact' CHECK (
        increment_rounding IN ('exact','ceiling')
    ),
    base_cost_minor bigint NOT NULL DEFAULT 0 CHECK (
        base_cost_minor>=0
    ),
    cost_per_basis_unit_minor numeric NOT NULL DEFAULT 0 CHECK (
        cost_per_basis_unit_minor>=0
    ),
    cost_per_allocated_space_minor numeric NOT NULL DEFAULT 0 CHECK (
        cost_per_allocated_space_minor>=0
    )
);

INSERT INTO rule_vehicle_component_formula
SELECT component.component_rule_id,source.quantity_basis,
       source.base_spaces,source.spaces_per_increment,
       source.basis_units_per_increment,source.increment_rounding,
       source.base_cost_minor,source.cost_per_basis_unit_minor,
       source.cost_per_allocated_space_minor
FROM (
    VALUES
        ('floats-pontoons','chassis_spaces',0::numeric,1::numeric,12::numeric,'ceiling',0::bigint,20.833333333333::numeric,0::numeric),
        ('folding-wings-rotors','chassis_spaces',0,0,12,'exact',0,50,0),
        ('galley-full','people_served',18,3,10,'ceiling',2000,500,0),
        ('hot-tub-pool','person_capacity',0,1,1,'exact',0,0,3000),
        ('operating-theater','patient_capacity',12,9,1,'exact',0,0,1500),
        ('refrigeration','refrigerated_spaces',0,1,10,'ceiling',0,0,250),
        ('holding-tank','allocated_spaces',0,1,1,'exact',0,0,1500),
        ('refueling-station','vessel_tons',12,1,50,'ceiling',0,0,15000),
        ('research-lab-space','researcher_skill_levels',0,3,1,'exact',0,10000,0)
) source(
    component_suffix,quantity_basis,base_spaces,
    spaces_per_increment,basis_units_per_increment,
    increment_rounding,base_cost_minor,
    cost_per_basis_unit_minor,cost_per_allocated_space_minor
)
JOIN vehicle_component_definition component
  ON component.component_code='additional.'||
     source.component_suffix;

CREATE TABLE rule_vehicle_cargo_trailer_rule (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    agility_dm smallint NOT NULL,
    small_vehicle_maximum_tons numeric NOT NULL CHECK (
        small_vehicle_maximum_tons>0
    ),
    small_vehicle_additional_agility_dm smallint NOT NULL,
    towing_speed_rounding_kph smallint NOT NULL CHECK (
        towing_speed_rounding_kph>0
    )
);

INSERT INTO rule_vehicle_cargo_trailer_rule
SELECT component_rule_id,-1,2,-1,10
FROM vehicle_component_definition
WHERE component_code='additional.cargo-trailer';

CREATE TABLE rule_vehicle_cargo_trailer_model (
    trailer_code text PRIMARY KEY,
    component_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_cargo_trailer_rule(component_rule_id),
    displacement_tons numeric NOT NULL UNIQUE CHECK (
        displacement_tons>0
    ),
    capacity_spaces smallint NOT NULL UNIQUE CHECK (capacity_spaces>0),
    price_minor bigint NOT NULL CHECK (price_minor>=0),
    description_code text NOT NULL
);

INSERT INTO rule_vehicle_cargo_trailer_model
SELECT source.trailer_code,component.component_rule_id,
       source.displacement_tons,source.capacity_spaces,
       source.price_minor,source.description_code
FROM (
    VALUES
        ('quarter-ton',0.25::numeric,3::smallint,1450::bigint,'light'),
        ('half-ton',0.5,6,1700,'moving-standard'),
        ('one-ton',1,12,2200,'moving-large'),
        ('two-ton',2,24,3200,'light-duty-standard'),
        ('four-ton',4,48,5700,'light-duty-large'),
        ('eight-ton',8,96,12000,'commercial-standard')
) source(
    trailer_code,displacement_tons,capacity_spaces,
    price_minor,description_code
)
JOIN vehicle_component_definition component
  ON component.component_code='additional.cargo-trailer';

CREATE TABLE rule_vehicle_crane (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    crane_class text NOT NULL UNIQUE CHECK (
        crane_class IN ('light','medium','heavy')
    ),
    lift_capacity_kg integer NOT NULL CHECK (lift_capacity_kg>0),
    rescue_equipment boolean NOT NULL DEFAULT false
);

INSERT INTO rule_vehicle_crane
SELECT component.component_rule_id,source.crane_class,
       source.lift_capacity_kg,source.rescue_equipment
FROM (
    VALUES
        ('light',400,true),('medium',2000,false),('heavy',10000,false)
) source(crane_class,lift_capacity_kg,rescue_equipment)
JOIN vehicle_component_definition component
  ON component.component_code='additional.crane-'||
     source.crane_class;

CREATE TABLE rule_vehicle_galley (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    galley_class text NOT NULL UNIQUE CHECK (
        galley_class IN ('mini','full')
    ),
    base_people_served smallint CHECK (base_people_served>0)
);

INSERT INTO rule_vehicle_galley
SELECT component.component_rule_id,source.galley_class,
       source.base_people_served
FROM (
    VALUES
        ('mini',5::smallint),('full',NULL::smallint)
) source(galley_class,base_people_served)
JOIN vehicle_component_definition component
  ON component.component_code='additional.galley-'||
     source.galley_class;

CREATE TABLE rule_vehicle_mobility_component (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    base_speed_multiplier numeric CHECK (
        base_speed_multiplier>0 AND base_speed_multiplier<=1
    ),
    agility_dm smallint,
    stored_size_multiplier numeric CHECK (
        stored_size_multiplier>0 AND stored_size_multiplier<=1
    ),
    removable boolean NOT NULL DEFAULT false,
    CHECK (
        base_speed_multiplier IS NOT NULL
        OR agility_dm IS NOT NULL
        OR stored_size_multiplier IS NOT NULL
    )
);

INSERT INTO rule_vehicle_mobility_component
SELECT component.component_rule_id,source.base_speed_multiplier,
       source.agility_dm,source.stored_size_multiplier,
       source.removable
FROM (
    VALUES
        ('floats-pontoons',0.9::numeric,-1::smallint,NULL::numeric,true),
        ('folding-wings-rotors',NULL::numeric,NULL::smallint,0.75::numeric,false)
) source(
    component_suffix,base_speed_multiplier,agility_dm,
    stored_size_multiplier,removable
)
JOIN vehicle_component_definition component
  ON component.component_code='additional.'||
     source.component_suffix;

CREATE TABLE rule_vehicle_manipulator_arm (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    base_strength smallint NOT NULL CHECK (base_strength>=0),
    base_dexterity smallint NOT NULL CHECK (base_dexterity>=0),
    price_per_added_attribute_point_minor bigint NOT NULL CHECK (
        price_per_added_attribute_point_minor>=0
    )
);

INSERT INTO rule_vehicle_manipulator_arm
SELECT component_rule_id,2,1,5000
FROM vehicle_component_definition
WHERE component_code='additional.manipulator-arms';

CREATE TABLE rule_vehicle_manipulator_limit (
    minimum_tech_level smallint PRIMARY KEY CHECK (
        minimum_tech_level>=0
    ),
    maximum_strength smallint NOT NULL CHECK (maximum_strength>0),
    maximum_dexterity smallint NOT NULL CHECK (maximum_dexterity>0),
    component_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_manipulator_arm(component_rule_id)
);

INSERT INTO rule_vehicle_manipulator_limit
SELECT source.*,component.component_rule_id
FROM (
    VALUES
        (5::smallint,6::smallint,4::smallint),
        (8,12,8),(11,18,12),(14,24,16)
) source(minimum_tech_level,maximum_strength,maximum_dexterity)
JOIN vehicle_component_definition component
  ON component.component_code='additional.manipulator-arms';

CREATE TABLE rule_vehicle_cargo_arm (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    strength_score smallint NOT NULL CHECK (strength_score>=0),
    dexterity_score smallint NOT NULL CHECK (dexterity_score>=0)
);

INSERT INTO rule_vehicle_cargo_arm
SELECT component_rule_id,30,0
FROM vehicle_component_definition
WHERE component_code='additional.cargo-arm';

CREATE TABLE rule_vehicle_liquid_cannon (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    ammunition_spaces_per_minute numeric NOT NULL CHECK (
        ammunition_spaces_per_minute>0
    ),
    maximum_range_band_rule_id bigint NOT NULL REFERENCES
        combat_range_band(rule_id)
);

INSERT INTO rule_vehicle_liquid_cannon
SELECT component.component_rule_id,3,range_rule.rule_id
FROM vehicle_component_definition component
JOIN rule_rule range_rule
  ON range_rule.rule_code='combat.range.medium'
WHERE component.component_code='additional.liquid-cannon';

CREATE TABLE rule_vehicle_operating_theater (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    mobile_operation_minimum_tech_level smallint NOT NULL CHECK (
        mobile_operation_minimum_tech_level>=0
    )
);

INSERT INTO rule_vehicle_operating_theater
SELECT component_rule_id,10
FROM vehicle_component_definition
WHERE component_code='additional.operating-theater';

CREATE TABLE rule_vehicle_refueling_rate (
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    chassis_spaces_refueled_per_hour smallint NOT NULL CHECK (
        chassis_spaces_refueled_per_hour>0
    ),
    PRIMARY KEY (component_rule_id,minimum_tech_level)
);

INSERT INTO rule_vehicle_refueling_rate
SELECT component.component_rule_id,source.*
FROM (
    VALUES
        (9::smallint,3::smallint),(12,12)
) source(minimum_tech_level,chassis_spaces_refueled_per_hour)
JOIN vehicle_component_definition component
  ON component.component_code='additional.refueling-station';

CREATE TABLE rule_vehicle_sampler_bonus (
    component_rule_id bigint NOT NULL REFERENCES
        vehicle_component_definition(component_rule_id),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    skill_dm smallint NOT NULL CHECK (skill_dm>0),
    PRIMARY KEY (component_rule_id,minimum_tech_level)
);

INSERT INTO rule_vehicle_sampler_bonus
SELECT component.component_rule_id,source.minimum_tl,source.skill_dm
FROM (
    VALUES
        ('geology',10::smallint,1::smallint),
        ('geology',14,2),
        ('hydrology',10,1),
        ('hydrology',14,2)
) source(sampler_code,minimum_tl,skill_dm)
JOIN vehicle_component_definition component
  ON component.component_code='additional.sampler-'||
     source.sampler_code;

CREATE TABLE rule_vehicle_emergency_low_berth (
    component_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_component_definition(component_rule_id),
    survival_capacity smallint NOT NULL CHECK (survival_capacity>0),
    passenger_transport_permitted boolean NOT NULL,
    capacity_source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_emergency_low_berth
SELECT component.component_rule_id,4,false,locator.source_locator_id
FROM vehicle_component_definition component
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Crew > Accommodation'
WHERE component.component_code='additional.emergency-low-berth';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       component.source_locator_id,'direct',true
FROM rule_rule rule
JOIN vehicle_component_definition component
  ON component.component_rule_id=rule.rule_id
WHERE rule.rule_code LIKE 'vehicle.component.accommodation.%'
   OR rule.rule_code LIKE 'vehicle.component.life-support.%'
   OR rule.rule_code LIKE 'vehicle.component.additional.%';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       berth.capacity_source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN rule_vehicle_emergency_low_berth berth
  ON berth.component_rule_id=rule.rule_id;

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
       'A corrected printing, publisher errata, or a corroborating authorized source with an explicit replacement value.',
       source.engine_disposition
FROM (
    VALUES
        (
            'vehicle.components.wet-bar-table',
            'source_conflict','high','wet-bar',
            'Wet Bar summary-row corruption',
            'The component prose specifies 1.5 Spaces and Cr2,000, while the summary table prints 1 Space and a malformed price cell of "5 Cr2,000".',
            'Table: 1 Space; "5 Cr2,000"',
            'Prose: 1.5 Spaces; Cr2,000',
            'Should the Wet Bar use the coherent prose values of 1.5 Spaces and Cr2,000?',
            'preserve_rule'
        ),
        (
            'vehicle.components.folding-wings-summary-omission',
            'source_omission','medium','folding-wings-rotors',
            'Folding Wings/Rotors omitted from summary table',
            'Folding Wings/Rotors has a complete component rule in the prose but no row in the Additional Vehicle Components summary table.',
            'No summary-table row',
            'Prose rule retained',
            'Should Folding Wings/Rotors be added to the component summary table?',
            'preserve_rule'
        ),
        (
            'vehicle.components.emergency-low-berth-capacity',
            'source_omission','medium','emergency-low-berth',
            'Vehicle Emergency Low Berth capacity omitted',
            'The vehicle rule says the berth can hold people but gives no number; the identically sized and priced core ship-design Emergency Low Berth holds four persons.',
            'Vehicle capacity unspecified',
            'Four-person survival capacity',
            'Is the vehicle Emergency Low Berth intended to use the core four-person survival capacity?',
            'preserve_rule'
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
     'Vehicle Design > Additional Vehicle Components'
WHERE issue.issue_code IN (
    'vehicle.components.wet-bar-table',
    'vehicle.components.folding-wings-summary-omission',
    'vehicle.components.emergency-low-berth-capacity'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Ship Crew > Accommodation'
WHERE issue.issue_code=
      'vehicle.components.emergency-low-berth-capacity';
