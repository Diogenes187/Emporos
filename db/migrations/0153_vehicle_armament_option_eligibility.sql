DELETE FROM rule_vehicle_armament_option_weapon_family family
USING rule_vehicle_armament_option option
WHERE option.option_rule_id=family.option_rule_id
  AND (
      family.weapon_family_code='any-turret-weapon'
      OR (
          option.option_code='missile-guidance-system'
          AND family.weapon_family_code='missile'
      )
  );

ALTER TABLE rule_vehicle_armament_option_weapon_family
    DROP CONSTRAINT
        rule_vehicle_armament_option_weapon_fa_weapon_family_code_check,
    ADD CONSTRAINT
        rule_vehicle_armament_option_weapon_family_code_fkey
        FOREIGN KEY (weapon_family_code)
        REFERENCES rule_vehicle_weapon_family(weapon_family_code);

CREATE TABLE rule_vehicle_armament_option_scope (
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_armament_option(option_rule_id),
    eligibility_scope_code text NOT NULL CHECK (
        eligibility_scope_code IN (
            'any-turret-weapon','missile-equipped-vehicle'
        )
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (option_rule_id,eligibility_scope_code)
);

INSERT INTO rule_vehicle_armament_option_scope
SELECT option.option_rule_id,source.eligibility_scope_code,
       locator.source_locator_id
FROM (
    VALUES
        ('heavy-turret-weapon','any-turret-weapon'),
        ('light-turret-weapon','any-turret-weapon'),
        ('missile-guidance-system','missile-equipped-vehicle')
) source(option_code,eligibility_scope_code)
JOIN rule_vehicle_armament_option option USING (option_code)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Armament Options'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';
