CREATE VIEW vehicle_class_catalogue_completeness AS
WITH facts AS (
    SELECT class.vehicle_class_rule_id,class.class_code,
           class.standard_design,
           class.source_locator_id IS NOT NULL
               AS has_source_locator,
           EXISTS (
               SELECT 1
               FROM src_record_provenance provenance
               WHERE provenance.rule_id=
                     class.vehicle_class_rule_id
           ) AS has_rule_provenance,
           total.construction_receipt_id IS NOT NULL
               AS has_current_receipt,
           coalesce(receipt.finalized,false)
               AS receipt_finalized,
           EXISTS (
               SELECT 1
               FROM vehicle_class_construction_line line
               WHERE line.construction_receipt_id=
                     total.construction_receipt_id
           ) AS has_receipt_lines,
           EXISTS (
               SELECT 1
               FROM vehicle_class_construction_line line
               WHERE line.construction_receipt_id=
                     total.construction_receipt_id
                 AND line.space_role='capacity'
           ) AS has_capacity_line,
           coalesce((
               SELECT sum(line.published_spaces)
               FROM vehicle_class_construction_line line
               WHERE line.construction_receipt_id=
                     total.construction_receipt_id
                 AND line.line_kind='cargo'
           ),0)=class.cargo_spaces AS has_published_cargo,
           (
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_propulsion propulsion
                   WHERE propulsion.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
               OR EXISTS (
                   SELECT 1
                   FROM vehicle_class_ship_scale_propulsion propulsion
                   WHERE propulsion.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
           ) AS has_propulsion_selection,
           EXISTS (
               SELECT 1
               FROM vehicle_class_component component
               WHERE component.vehicle_class_rule_id=
                     class.vehicle_class_rule_id
           ) AS has_component_selections,
           (
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_construction_line line
                   WHERE line.construction_receipt_id=
                         total.construction_receipt_id
                     AND line.line_kind='fuel'
               )=EXISTS (
                   SELECT 1
                   FROM vehicle_class_fuel_tank tank
                   WHERE tank.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
               AND
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_construction_line line
                   WHERE line.construction_receipt_id=
                         total.construction_receipt_id
                     AND line.line_kind='autopilot'
               )=EXISTS (
                   SELECT 1
                   FROM vehicle_class_autopilot autopilot
                   WHERE autopilot.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
               AND
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_construction_line line
                   WHERE line.construction_receipt_id=
                         total.construction_receipt_id
                     AND line.line_kind='computer_option'
               )=EXISTS (
                   SELECT 1
                   FROM vehicle_class_computer_option option
                   WHERE option.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
               AND
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_construction_line line
                   WHERE line.construction_receipt_id=
                         total.construction_receipt_id
                     AND line.line_kind='configuration_option'
               )=EXISTS (
                   SELECT 1
                   FROM vehicle_class_configuration_option option
                   WHERE option.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
               AND
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_construction_line line
                   WHERE line.construction_receipt_id=
                         total.construction_receipt_id
                     AND line.line_kind='drive_option'
               )=EXISTS (
                   SELECT 1
                   FROM vehicle_class_drive_option option
                   WHERE option.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
               AND
               EXISTS (
                   SELECT 1
                   FROM vehicle_class_construction_line line
                   WHERE line.construction_receipt_id=
                         total.construction_receipt_id
                     AND line.line_kind='weapon'
               )=EXISTS (
                   SELECT 1
                   FROM vehicle_class_armament_mount mount
                   JOIN vehicle_class_armament_weapon weapon
                     USING (class_armament_mount_id)
                   WHERE mount.vehicle_class_rule_id=
                         class.vehicle_class_rule_id
               )
           ) AS optional_selections_match_receipt,
           total.receipt_status,
           total.reconciliation_status,
           coalesce((
               SELECT count(*)
               FROM vehicle_class_construction_variance variance
               WHERE variance.construction_receipt_id=
                     total.construction_receipt_id
           ),0) AS retained_variance_count,
           coalesce((
               SELECT count(*)
               FROM src_issue issue
               WHERE issue.domain_code='vehicle.catalogue'
                 AND issue.subject_code=class.class_code
           ),0) AS registered_issue_count
    FROM vehicle_class class
    LEFT JOIN vehicle_class_construction_total total
      ON total.vehicle_class_rule_id=
         class.vehicle_class_rule_id
    LEFT JOIN vehicle_class_construction_receipt receipt
      ON receipt.construction_receipt_id=
         total.construction_receipt_id
)
SELECT facts.*,
       (
           facts.standard_design
           AND facts.has_source_locator
           AND facts.has_rule_provenance
           AND facts.has_current_receipt
           AND facts.receipt_finalized
           AND facts.has_receipt_lines
           AND facts.has_capacity_line
           AND facts.has_published_cargo
           AND facts.has_propulsion_selection
           AND facts.has_component_selections
           AND facts.optional_selections_match_receipt
       ) AS is_relationally_complete
FROM facts;
