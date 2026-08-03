INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Ship Design and Construction > Ship Crew > Accommodation',
         'Cepheus Engine v9.1, Ship Design: Crew Accommodation'),
        ('Ship Design and Construction > Vehicle and Drone Hangar',
         'Cepheus Engine v9.1, Ship Design: Hangars'),
        ('Ship Design and Construction > Armaments > Turrets',
         'Cepheus Engine v9.1, Ship Design: Turrets'),
        ('Ship Design and Construction > Armaments > Missiles',
         'Cepheus Engine v9.1, Ship Design: Missiles'),
        ('Ship Design and Construction > Armaments > Bays',
         'Cepheus Engine v9.1, Ship Design: Bays'),
        ('Ship Design and Construction > Armaments > Screens',
         'Cepheus Engine v9.1, Ship Design: Screens')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
      'src/book2/ship-design-and-construction.md';

ALTER TABLE ship_component_definition
    DROP CONSTRAINT ship_component_definition_component_kind_check;

ALTER TABLE ship_component_definition
    ADD CONSTRAINT ship_component_definition_component_kind_check CHECK (
        component_kind IN (
            'bridge','computer','sensor','jump_drive','maneuver_drive',
            'power_plant','fuel_tank','stateroom','low_berth',
            'emergency_low_berth','barracks','cargo_hold','weapon_mount',
            'fuel_processor','fuel_scoop','armory','briefing_room',
            'detention_cell','laboratory','launch_tube','library',
            'luxury','ship_locker','vault','hangar','drone',
            'escape_pod','airlock','other'
        )
    ),
    ADD COLUMN tonnage_basis text NOT NULL DEFAULT 'fixed' CHECK (
        tonnage_basis IN (
            'fixed','per_person','per_component_ton',
            'largest_craft_multiplier','remaining_hull',
            'hull_percent','included','source_unspecified'
        )
    ),
    ADD COLUMN tonnage_factor numeric CHECK (tonnage_factor>=0),
    ADD COLUMN cost_basis text NOT NULL DEFAULT 'fixed' CHECK (
        cost_basis IN (
            'fixed','per_person','per_component_ton','included',
            'source_unspecified'
        )
    ),
    ADD COLUMN capacity_kind text CHECK (
        capacity_kind IS NULL OR capacity_kind IN (
            'person','prisoner','scientist','cargo_ton',
            'steward_equivalent','contained_ton','processed_ton_per_day',
            'launches_per_round','crew_supported','marine_supported'
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

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'ship.component.'||source.component_code,
       source.component_name,'ship','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('stateroom','Stateroom'),
        ('low-berth','Low Passage Berth'),
        ('emergency-low-berth','Emergency Low Berth'),
        ('barracks','Barracks'),
        ('armory','Armory'),
        ('briefing-room','Briefing Room'),
        ('cargo-hold','Cargo Hold'),
        ('detention-cell','Detention Cell'),
        ('fuel-scoop','Fuel Scoop'),
        ('fuel-processor','Fuel Processor'),
        ('laboratory','Laboratory'),
        ('launch-tube','Launch Tube'),
        ('library','Library'),
        ('luxuries','Luxuries'),
        ('ships-locker','Ship''s Locker'),
        ('vault','Vault')
) source(component_code,component_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO ship_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_tons,unit_cost_minor,
    source_locator_id,tonnage_basis,tonnage_factor,cost_basis,
    capacity_kind,capacity_per_unit,effect_code,calculation_status
)
SELECT rule.rule_id,source.component_code,source.component_kind,
       source.minimum_tl,source.unit_tons,source.unit_cost,
       locator.source_locator_id,source.tonnage_basis,
       source.tonnage_factor,source.cost_basis,
       source.capacity_kind,source.capacity_per_unit,
       source.effect_code,source.calculation_status
FROM (
    VALUES
        ('stateroom','stateroom',NULL::smallint,4::numeric,
         500000::bigint,'fixed',1::numeric,'fixed',
         'person',1::numeric,'life-support','published'),
        ('low-berth','low_berth',NULL,0.5,50000,
         'fixed',1,'fixed','person',1,'low-passage','published'),
        ('emergency-low-berth','emergency_low_berth',NULL,1,100000,
         'fixed',1,'fixed','person',4,'emergency-survival','published'),
        ('barracks','barracks',NULL,2,100000,
         'per_person',2,'per_person','person',1,
         'boarding-accommodation','formula'),
        ('armory','armory',NULL,2,500000,
         'fixed',1,'fixed','crew_supported',50,
         'military-equipment','published'),
        ('briefing-room','briefing_room',NULL,0,0,
         'source_unspecified',NULL::numeric,'source_unspecified',
         NULL::text,NULL::numeric,'tactics-dm-1','source_unspecified'),
        ('cargo-hold','cargo_hold',NULL,0,0,
         'remaining_hull',1,'included','cargo_ton',1,
         'cargo-capacity','included'),
        ('detention-cell','detention_cell',NULL,2,250000,
         'fixed',1,'fixed','prisoner',1,
         'secure-confinement','published'),
        ('fuel-scoop','fuel_scoop',NULL,0,1000000,
         'fixed',0,'fixed',NULL,NULL,
         'unrefined-fuel-collection','published'),
        ('fuel-processor','fuel_processor',NULL,1,50000,
         'per_component_ton',1,'per_component_ton',
         'processed_ton_per_day',20,'fuel-refining','formula'),
        ('laboratory','laboratory',NULL,4,1000000,
         'per_person',4,'per_person','scientist',1,
         'research-space','formula'),
        ('launch-tube','launch_tube',NULL,0,0,
         'largest_craft_multiplier',25,'per_component_ton',
         'launches_per_round',10,'rapid-launch-recovery','formula'),
        ('library','library',NULL,4,4000000,
         'fixed',1,'fixed',NULL,NULL,
         'jump-training-week','published'),
        ('luxuries','luxury',NULL,1,100000,
         'per_component_ton',1,'per_component_ton',
         'steward_equivalent',1,'passenger-service','formula'),
        ('ships-locker','ship_locker',NULL,0,0,
         'included',0,'included',NULL,NULL,
         'standard-equipment','included'),
        ('vault','vault',NULL,12,6000000,
         'fixed',1,'fixed','contained_ton',6,
         'vault-hull-structure-4','published')
) source(
    component_code,component_kind,minimum_tl,unit_tons,unit_cost,
    tonnage_basis,tonnage_factor,cost_basis,capacity_kind,
    capacity_per_unit,effect_code,calculation_status
)
JOIN rule_rule rule
  ON rule.rule_code='ship.component.'||source.component_code
JOIN src_locator locator
  ON locator.heading_path=CASE
      WHEN source.component_code IN (
          'stateroom','low-berth','emergency-low-berth','barracks'
      ) THEN
          'Ship Design and Construction > Ship Crew > Accommodation'
      ELSE
          'Ship Design and Construction > Additional Ship Components'
  END;

CREATE TABLE rule_ship_armory_capacity (
    component_rule_id bigint NOT NULL REFERENCES
        ship_component_definition(component_rule_id),
    capacity_kind text NOT NULL CHECK (
        capacity_kind IN ('crew_supported','marine_supported')
    ),
    capacity_count smallint NOT NULL CHECK (capacity_count>0),
    PRIMARY KEY (component_rule_id,capacity_kind)
);

INSERT INTO rule_ship_armory_capacity
SELECT definition.component_rule_id,source.*
FROM ship_component_definition definition
CROSS JOIN (
    VALUES
        ('crew_supported',50::smallint),
        ('marine_supported',10::smallint)
) source(capacity_kind,capacity_count)
WHERE definition.component_code='armory';

CREATE TABLE rule_ship_hangar_option (
    hangar_option_code text PRIMARY KEY CHECK (
        hangar_option_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    installed_tons numeric CHECK (installed_tons>0),
    tons_per_person numeric CHECK (tons_per_person>0),
    hull_percent numeric CHECK (hull_percent>0),
    installation_cost_minor bigint CHECK (
        installation_cost_minor>=0
    ),
    cost_minor_per_ton bigint CHECK (cost_minor_per_ton>=0),
    units_per_installation smallint NOT NULL DEFAULT 1 CHECK (
        units_per_installation>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        num_nonnulls(installed_tons,tons_per_person,hull_percent)=1
    ),
    CHECK (
        num_nonnulls(
            installation_cost_minor,cost_minor_per_ton
        )=1
    )
);

INSERT INTO rule_ship_hangar_option
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('atv',13::numeric,NULL::numeric,NULL::numeric,
         2600000::bigint,NULL::bigint,1::smallint),
        ('air-raft',5,NULL,NULL,1000000,NULL,1),
        ('cutter',65,NULL,NULL,13000000,NULL,1),
        ('escape-pods',NULL,0.5,NULL,NULL,200000,1),
        ('life-boat',26,NULL,NULL,5200000,NULL,1),
        ('mining-drones',10,NULL,NULL,2000000,NULL,1),
        ('pinnace',52,NULL,NULL,10400000,NULL,1),
        ('probe-drones',1,NULL,NULL,200000,NULL,5),
        ('repair-drones',NULL,NULL,0.01,NULL,200000,1),
        ('ships-boat',39,NULL,NULL,7800000,NULL,1),
        ('shuttle',122.5,NULL,NULL,24500000,NULL,1)
) source(
    hangar_option_code,installed_tons,tons_per_person,hull_percent,
    installation_cost_minor,cost_minor_per_ton,
    units_per_installation
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Vehicle and Drone Hangar';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       definition.source_locator_id,'fills_source_gap',true
FROM rule_rule rule
JOIN ship_component_definition definition
  ON definition.component_rule_id=rule.rule_id
WHERE rule.rule_code LIKE 'ship.component.%';
