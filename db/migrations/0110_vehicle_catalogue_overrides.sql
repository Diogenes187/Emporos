ALTER TABLE vehicle_class_propulsion
    DROP CONSTRAINT vehicle_class_propulsion_calculation_status_check,
    ADD CONSTRAINT vehicle_class_propulsion_calculation_status_check
        CHECK (
            calculation_status IN (
                'matches','modified','published_override','source_conflict',
                'external'
            )
        );

UPDATE vehicle_class_propulsion propulsion
SET calculation_status='published_override'
FROM rule_rule rule
WHERE rule.rule_id=propulsion.vehicle_class_rule_id
  AND rule.rule_code='vehicle.class.ground-car';

