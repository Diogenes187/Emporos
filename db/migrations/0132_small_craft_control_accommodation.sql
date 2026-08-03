INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',
       'Ship Design and Construction > Small Craft Cockpits and Control Cabins',
       'Cepheus Engine v9.1, Ship Design: Small Craft Cockpits and Control Cabins'
FROM src_artifact artifact
WHERE artifact.source_uri=
      'src/book2/ship-design-and-construction.md';

INSERT INTO ship_component_definition (
    component_rule_id,component_code,component_kind,
    minimum_tech_level,unit_tons,unit_cost_minor,
    source_locator_id,tonnage_basis,tonnage_factor,cost_basis,
    capacity_kind,capacity_per_unit,effect_code,calculation_status
)
SELECT rule.rule_id,source.component_code,'other',
       NULL,source.unit_tons,100000,
       locator.source_locator_id,'fixed',1,
       'per_20_hull_tons','person',source.person_capacity,
       'small-craft-control','published'
FROM (
    VALUES
        ('one-person-cockpit',1.5::numeric,1::numeric),
        ('two-person-cockpit',3,2),
        ('one-person-control-cabin',3,1),
        ('two-person-control-cabin',6,3)
) source(component_code,unit_tons,person_capacity)
JOIN rule_rule rule
  ON rule.rule_code='ship.component.'||source.component_code
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Small Craft Cockpits and Control Cabins'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO ship_class_component (
    ship_class_rule_id,component_rule_id,quantity,rating,
    allocated_tons,display_order,source_locator_id
)
SELECT class.ship_class_rule_id,component.component_rule_id,
       1,NULL,source.allocated_tons,
       (
           SELECT coalesce(max(existing.display_order),0)+1
           FROM ship_class_component existing
           WHERE existing.ship_class_rule_id=class.ship_class_rule_id
       ),
       class.source_locator_id
FROM (
    VALUES
        ('cutter','one-person-control-cabin',3::numeric),
        ('fighter','one-person-cockpit',1.5),
        ('launch','two-person-control-cabin',6),
        ('pinnace','one-person-control-cabin',3),
        ('ships-boat','one-person-control-cabin',3),
        ('shuttle','two-person-control-cabin',6)
) source(class_code,component_code,allocated_tons)
JOIN ship_class class
  ON class.class_code=source.class_code
JOIN ship_component_definition component
  ON component.component_code=source.component_code;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       component.source_locator_id,'direct',true
FROM rule_rule rule
JOIN ship_component_definition component
  ON component.component_rule_id=rule.rule_id
WHERE rule.rule_code IN (
    'ship.component.one-person-cockpit',
    'ship.component.two-person-cockpit',
    'ship.component.one-person-control-cabin',
    'ship.component.two-person-control-cabin'
);

CREATE OR REPLACE VIEW ship_class_catalogue_completeness AS
SELECT class.ship_class_rule_id,
       class.class_code,
       class.craft_scale,
       (hull.ship_class_rule_id IS NOT NULL) AS has_hull,
       (
           SELECT count(*)
           FROM ship_class_drive drive
           WHERE drive.ship_class_rule_id=class.ship_class_rule_id
       )=CASE
             WHEN class.craft_scale='small_craft' THEN 2
             WHEN class.jump_rating=0 THEN 2
             ELSE 3
         END AS has_required_drives,
       (computer.ship_class_rule_id IS NOT NULL) AS has_computer,
       (electronics.ship_class_rule_id IS NOT NULL) AS has_electronics,
       EXISTS (
           SELECT 1
           FROM ship_class_component selected
           JOIN ship_component_definition component
             ON component.component_rule_id=selected.component_rule_id
           WHERE selected.ship_class_rule_id=class.ship_class_rule_id
             AND component.component_code='cargo-hold'
             AND selected.allocated_tons=class.cargo_capacity_tons
       ) AS has_published_cargo,
       EXISTS (
           SELECT 1
           FROM ship_class_component selected
           JOIN ship_component_definition component
             ON component.component_rule_id=selected.component_rule_id
           WHERE selected.ship_class_rule_id=class.ship_class_rule_id
             AND (
                 (
                     class.craft_scale='starship'
                     AND component.component_code='stateroom'
                 )
                 OR
                 (
                     class.craft_scale='small_craft'
                     AND component.component_code IN (
                         'one-person-cockpit','two-person-cockpit',
                         'one-person-control-cabin',
                         'two-person-control-cabin'
                     )
                 )
             )
       ) AS has_control_accommodation,
       (armament.ship_class_rule_id IS NOT NULL)
           AS has_armament_declaration,
       (
           SELECT count(*)
           FROM ship_class_source_assertion assertion
           WHERE assertion.ship_class_rule_id=class.ship_class_rule_id
             AND assertion.assertion_status IN (
                 'unresolved_conflict','source_unspecified'
             )
       ) AS unresolved_source_assertions,
       (
           hull.ship_class_rule_id IS NOT NULL
           AND computer.ship_class_rule_id IS NOT NULL
           AND electronics.ship_class_rule_id IS NOT NULL
           AND armament.ship_class_rule_id IS NOT NULL
           AND (
               SELECT count(*)
               FROM ship_class_drive drive
               WHERE drive.ship_class_rule_id=class.ship_class_rule_id
           )=CASE
                 WHEN class.craft_scale='small_craft' THEN 2
                 WHEN class.jump_rating=0 THEN 2
                 ELSE 3
             END
           AND EXISTS (
               SELECT 1
               FROM ship_class_component selected
               JOIN ship_component_definition component
                 ON component.component_rule_id=selected.component_rule_id
               WHERE selected.ship_class_rule_id=class.ship_class_rule_id
                 AND component.component_code='cargo-hold'
                 AND selected.allocated_tons=class.cargo_capacity_tons
           )
           AND EXISTS (
               SELECT 1
               FROM ship_class_component selected
               JOIN ship_component_definition component
                 ON component.component_rule_id=selected.component_rule_id
               WHERE selected.ship_class_rule_id=class.ship_class_rule_id
                 AND (
                     (
                         class.craft_scale='starship'
                         AND component.component_code='stateroom'
                     )
                     OR
                     (
                         class.craft_scale='small_craft'
                         AND component.component_code IN (
                             'one-person-cockpit','two-person-cockpit',
                             'one-person-control-cabin',
                             'two-person-control-cabin'
                         )
                     )
                 )
           )
       ) AS is_structurally_complete
FROM ship_class class
LEFT JOIN ship_class_design_hull hull
  ON hull.ship_class_rule_id=class.ship_class_rule_id
LEFT JOIN ship_class_computer computer
  ON computer.ship_class_rule_id=class.ship_class_rule_id
LEFT JOIN ship_class_electronics electronics
  ON electronics.ship_class_rule_id=class.ship_class_rule_id
LEFT JOIN ship_class_armament_declaration armament
  ON armament.ship_class_rule_id=class.ship_class_rule_id;
