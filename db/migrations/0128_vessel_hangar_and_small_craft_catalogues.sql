ALTER TABLE rule_ship_hangar_option
    ADD COLUMN derivation_status text NOT NULL DEFAULT 'published' CHECK (
        derivation_status IN ('published','formula','source_unspecified')
    );

INSERT INTO rule_ship_hangar_option (
    hangar_option_code,installed_tons,tons_per_person,hull_percent,
    installation_cost_minor,cost_minor_per_ton,
    units_per_installation,source_locator_id,
    derivation_status
)
SELECT 'fighter',13,NULL,NULL,2600000,NULL,1,
       source_locator_id,'formula'
FROM src_locator
WHERE heading_path='Ship Design and Construction > Vehicle and Drone Hangar';

ALTER TABLE ship_component_definition
    DROP CONSTRAINT ship_component_definition_cost_basis_check,
    ADD CONSTRAINT ship_component_definition_cost_basis_check CHECK (
        cost_basis IN (
            'fixed','per_person','per_component_ton','included',
            'per_20_hull_tons','source_unspecified'
        )
    );

ALTER TABLE ship_class_source_assertion
    DROP CONSTRAINT ship_class_source_assertion_assertion_status_check,
    ADD CONSTRAINT ship_class_source_assertion_assertion_status_check CHECK (
        assertion_status IN (
            'accepted','reconciled','unresolved_conflict',
            'source_unspecified'
        )
    );

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,'ship.component.'||source.component_code,
       source.component_name,'ship','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('one-person-cockpit','One-Person Cockpit'),
        ('two-person-cockpit','Two-Person Cockpit'),
        ('one-person-control-cabin','One-Person Control Cabin'),
        ('two-person-control-cabin','Two-Person Control Cabin'),
        ('cutter-module-berth','Cutter Module Berth'),
        ('smelter','Smelter')
) source(component_code,component_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO ship_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_tons,unit_cost_minor,
    source_locator_id,tonnage_basis,tonnage_factor,cost_basis,
    capacity_kind,capacity_per_unit,effect_code,calculation_status
)
SELECT rule.rule_id,source.component_code,'other',
       source.minimum_tl,source.unit_tons,source.unit_cost,
       locator.source_locator_id,source.tonnage_basis,
       source.tonnage_factor,source.cost_basis,
       source.capacity_kind,source.capacity_per_unit,
       source.effect_code,source.calculation_status
FROM (
    VALUES
        ('one-person-cockpit',NULL::smallint,1.5::numeric,100000::bigint,
         'fixed',1::numeric,'per_20_hull_tons','person',1::numeric,
         'small-craft-control','published',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('two-person-cockpit',NULL,3,100000,'fixed',1,
         'per_20_hull_tons','person',2,'small-craft-control','published',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('one-person-control-cabin',NULL,3,100000,'fixed',1,
         'per_20_hull_tons','person',1,'small-craft-control','published',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('two-person-control-cabin',NULL,6,100000,'fixed',1,
         'per_20_hull_tons','person',3,'small-craft-control','published',
         'Ship Design and Construction > Small Craft Cockpits and Control Cabins'),
        ('cutter-module-berth',NULL,30,0,'fixed',1,'included',
         'contained_ton',30,'cutter-module-interface','published',
         'Common Vessels > TL9 Cutter'),
        ('smelter',NULL,0,0,'source_unspecified',NULL,
         'source_unspecified',NULL,NULL,'ore-smelting',
         'source_unspecified','Common Vessels > TL9 Asteroid Miner')
) source(
    component_code,minimum_tl,unit_tons,unit_cost,
    tonnage_basis,tonnage_factor,cost_basis,capacity_kind,
    capacity_per_unit,effect_code,calculation_status,heading_path
)
JOIN rule_rule rule
  ON rule.rule_code='ship.component.'||source.component_code
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO ship_class_source_assertion (
    ship_class_rule_id,field_code,published_value,canonical_value,
    assertion_status,rationale,source_locator_id
)
SELECT ship_class_rule_id,'smelter-specification','smelter',NULL,
       'source_unspecified',
       'The paired common-vessel publications name the smelter but provide no tonnage, cost, capacity, or construction rule; ship-design tables and the prior implementation provide no missing profile.',
       source_locator_id
FROM ship_class
WHERE class_code='asteroid-miner';

CREATE TABLE ship_class_carried_craft (
    carrier_class_rule_id bigint NOT NULL,
    hangar_identifier text NOT NULL,
    carried_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    craft_count smallint NOT NULL CHECK (craft_count>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (
        carrier_class_rule_id,hangar_identifier,carried_class_rule_id
    ),
    FOREIGN KEY (carrier_class_rule_id,hangar_identifier)
        REFERENCES ship_class_hangar_option(
            ship_class_rule_id,hangar_identifier
        ),
    CHECK (carrier_class_rule_id<>carried_class_rule_id)
);

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       component.source_locator_id,
       CASE WHEN component.calculation_status='source_unspecified'
            THEN 'interpretation' ELSE 'direct' END,
       true
FROM rule_rule rule
JOIN ship_component_definition component
  ON component.component_rule_id=rule.rule_id
WHERE rule.rule_code IN (
    'ship.component.one-person-cockpit',
    'ship.component.two-person-cockpit',
    'ship.component.one-person-control-cabin',
    'ship.component.two-person-control-cabin',
    'ship.component.cutter-module-berth',
    'ship.component.smelter'
);
