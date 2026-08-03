ALTER TABLE rule_vehicle_turret
    RENAME COLUMN price_per_total_space_minor
    TO price_per_base_space_minor;

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL15 G/Carrier',
         'Cepheus Engine VDS, TL15 G/Carrier'),
        ('src/vds/common-grav-vehicles.md',
         'Common Grav Vehicles > TL9 Grav Tank',
         'Cepheus Engine VDS, TL9 Grav Tank'),
        ('src/vds/common-ground-vehicles.md',
         'Common Ground Vehicles > TL12 AFV, Tracked',
         'Cepheus Engine VDS, TL12 AFV, Tracked')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

CREATE TABLE vehicle_class_weapon_point_summary (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class(vehicle_class_rule_id),
    published_available_weapon_points smallint NOT NULL CHECK (
        published_available_weapon_points>0
    ),
    calculated_available_weapon_points smallint NOT NULL CHECK (
        calculated_available_weapon_points>0
    ),
    published_used_weapon_points smallint NOT NULL CHECK (
        published_used_weapon_points>0
    ),
    reconciliation_status text NOT NULL CHECK (
        reconciliation_status IN ('matches','source-conflict')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        published_used_weapon_points<=
        published_available_weapon_points
    ),
    CHECK (
        (reconciliation_status='matches'
         AND published_available_weapon_points=
             calculated_available_weapon_points)
        OR
        (reconciliation_status='source-conflict'
         AND published_available_weapon_points<>
             calculated_available_weapon_points)
    )
);

WITH source(
    class_code,published_available,published_used,
    reconciliation_status,heading_path
) AS (
    VALUES
        ('g-carrier',1::smallint,1::smallint,'matches',
         'Common Grav Vehicles > TL15 G/Carrier'),
        ('grav-tank',1,1,'matches',
         'Common Grav Vehicles > TL9 Grav Tank'),
        ('afv-tracked',1,1,'source-conflict',
         'Common Ground Vehicles > TL12 AFV, Tracked')
)
INSERT INTO vehicle_class_weapon_point_summary
SELECT class.vehicle_class_rule_id,source.published_available,
       greatest(
           1,
           floor(
               chassis.displacement_tons/
               formula.displacement_tons_per_weapon_point
           )::smallint
       ),
       source.published_used,source.reconciliation_status,
       locator.source_locator_id
FROM source
JOIN vehicle_class class USING (class_code)
JOIN rule_vehicle_chassis chassis USING (chassis_code)
CROSS JOIN rule_vehicle_weapon_point_formula formula
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE formula.formula_code='standard';

CREATE TABLE vehicle_class_armament_mount (
    class_armament_mount_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class_weapon_point_summary(vehicle_class_rule_id),
    mount_sequence smallint NOT NULL CHECK (mount_sequence>0),
    quantity smallint NOT NULL CHECK (quantity>0),
    weapon_mount_rule_id bigint REFERENCES
        rule_vehicle_weapon_mount(mount_rule_id),
    turret_rule_id bigint REFERENCES
        rule_vehicle_turret(turret_rule_id),
    weapon_points_each smallint NOT NULL CHECK (
        weapon_points_each>0
    ),
    published_mount_spaces_each numeric NOT NULL CHECK (
        published_mount_spaces_each>=0
    ),
    published_mount_cost_each_minor bigint NOT NULL CHECK (
        published_mount_cost_each_minor>=0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (vehicle_class_rule_id,mount_sequence),
    CHECK (
        num_nonnulls(weapon_mount_rule_id,turret_rule_id)=1
    )
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_armament_mount()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    available_points smallint;
    other_points integer;
    class_tech smallint;
    mount_tech smallint;
BEGIN
    SELECT summary.published_available_weapon_points,
           class.minimum_tech_level
    INTO available_points,class_tech
    FROM vehicle_class_weapon_point_summary summary
    JOIN vehicle_class class USING (vehicle_class_rule_id)
    WHERE summary.vehicle_class_rule_id=NEW.vehicle_class_rule_id;

    SELECT coalesce(
               sum(mount.quantity*mount.weapon_points_each),0
           )
    INTO other_points
    FROM vehicle_class_armament_mount mount
    WHERE mount.vehicle_class_rule_id=NEW.vehicle_class_rule_id
      AND mount.class_armament_mount_id<>
          coalesce(NEW.class_armament_mount_id,0);

    IF other_points+NEW.quantity*NEW.weapon_points_each>
       available_points THEN
        RAISE EXCEPTION
            'Vehicle class armaments exceed published weapon points'
            USING ERRCODE='23514';
    END IF;

    IF NEW.weapon_mount_rule_id IS NOT NULL THEN
        SELECT minimum_tech_level INTO mount_tech
        FROM rule_vehicle_weapon_mount
        WHERE mount_rule_id=NEW.weapon_mount_rule_id;
        IF class_tech<mount_tech THEN
            RAISE EXCEPTION
                'Vehicle class tech level is below weapon mount tech level'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_armament_mount_valid
BEFORE INSERT OR UPDATE ON vehicle_class_armament_mount
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_class_armament_mount();

WITH source(
    class_code,mount_sequence,quantity,mount_code,turret_code,
    weapon_points_each,published_spaces,published_cost,
    heading_path
) AS (
    VALUES
        ('g-carrier',1::smallint,1::smallint,
         'ring-powered',NULL::text,1::smallint,0::numeric,
         2150::bigint,'Common Grav Vehicles > TL15 G/Carrier'),
        ('grav-tank',1,1,NULL,'small',1,0.5,4000,
         'Common Grav Vehicles > TL9 Grav Tank'),
        ('afv-tracked',1,1,NULL,'small',1,0.5,4000,
         'Common Ground Vehicles > TL12 AFV, Tracked')
)
INSERT INTO vehicle_class_armament_mount (
    vehicle_class_rule_id,mount_sequence,quantity,
    weapon_mount_rule_id,turret_rule_id,weapon_points_each,
    published_mount_spaces_each,published_mount_cost_each_minor,
    source_locator_id
)
SELECT class.vehicle_class_rule_id,source.mount_sequence,
       source.quantity,weapon_mount.mount_rule_id,
       turret.turret_rule_id,source.weapon_points_each,
       source.published_spaces,source.published_cost,
       locator.source_locator_id
FROM source
JOIN vehicle_class class USING (class_code)
LEFT JOIN rule_vehicle_weapon_mount weapon_mount
  ON weapon_mount.mount_code=source.mount_code
LEFT JOIN rule_vehicle_turret turret
  ON turret.turret_code=source.turret_code
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE vehicle_class_armament_weapon (
    class_armament_mount_id bigint NOT NULL REFERENCES
        vehicle_class_armament_mount(class_armament_mount_id)
        ON DELETE CASCADE,
    slot_order smallint NOT NULL CHECK (slot_order>0),
    weapon_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_weapon_definition(weapon_rule_id),
    quantity_per_mount smallint NOT NULL CHECK (
        quantity_per_mount>0
    ),
    published_weapon_spaces_each numeric NOT NULL CHECK (
        published_weapon_spaces_each>0
    ),
    published_weapon_cost_each_minor bigint NOT NULL CHECK (
        published_weapon_cost_each_minor>0
    ),
    reconciliation_status text NOT NULL CHECK (
        reconciliation_status IN ('matches','source-conflict')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (class_armament_mount_id,slot_order)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_armament_weapon()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    weapon_tech smallint;
    weapon_spaces numeric;
    weapon_cost bigint;
    maximum_spaces numeric;
BEGIN
    SELECT class.minimum_tech_level,
           weapon.minimum_tech_level,
           weapon.unit_spaces,
           weapon.unit_cost_minor,
           mount_definition.maximum_weapon_spaces
    INTO class_tech,weapon_tech,weapon_spaces,
         weapon_cost,maximum_spaces
    FROM vehicle_class_armament_mount mount
    JOIN vehicle_class class USING (vehicle_class_rule_id)
    JOIN rule_vehicle_weapon_definition weapon
      ON weapon.weapon_rule_id=NEW.weapon_rule_id
    LEFT JOIN rule_vehicle_weapon_mount mount_definition
      ON mount_definition.mount_rule_id=
         mount.weapon_mount_rule_id
    WHERE mount.class_armament_mount_id=
          NEW.class_armament_mount_id;

    IF class_tech<weapon_tech
       OR (
           maximum_spaces IS NOT NULL
           AND weapon_spaces>maximum_spaces
       )
       OR (
           NEW.reconciliation_status='matches'
           AND (
               NEW.published_weapon_spaces_each<>weapon_spaces
               OR NEW.published_weapon_cost_each_minor<>weapon_cost
           )
       )
       OR (
           NEW.reconciliation_status='source-conflict'
           AND NEW.published_weapon_spaces_each=weapon_spaces
           AND NEW.published_weapon_cost_each_minor=weapon_cost
       ) THEN
        RAISE EXCEPTION
            'Vehicle class weapon selection violates catalogue data'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_armament_weapon_valid
BEFORE INSERT OR UPDATE ON vehicle_class_armament_weapon
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_class_armament_weapon();

WITH source(
    class_code,weapon_code,published_spaces,published_cost,
    heading_path
) AS (
    VALUES
        ('g-carrier','fusion-gun-tl-15',3::numeric,
         200000::bigint,'Common Grav Vehicles > TL15 G/Carrier'),
        ('grav-tank','beam-laser-tl-9',3,100000,
         'Common Grav Vehicles > TL9 Grav Tank'),
        ('afv-tracked','beam-laser-tl-11',3,120000,
         'Common Ground Vehicles > TL12 AFV, Tracked')
)
INSERT INTO vehicle_class_armament_weapon
SELECT mount.class_armament_mount_id,1,
       weapon.weapon_rule_id,1,source.published_spaces,
       source.published_cost,'matches',locator.source_locator_id
FROM source
JOIN vehicle_class class USING (class_code)
JOIN vehicle_class_armament_mount mount
  ON mount.vehicle_class_rule_id=class.vehicle_class_rule_id
 AND mount.mount_sequence=1
JOIN rule_vehicle_weapon_definition weapon USING (weapon_code)
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE vehicle_class_armament_gun_shield (
    class_armament_mount_id bigint PRIMARY KEY REFERENCES
        vehicle_class_armament_mount(class_armament_mount_id)
        ON DELETE CASCADE,
    option_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_gun_shield(option_rule_id),
    published_armor_rating smallint NOT NULL CHECK (
        published_armor_rating>0
    ),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_gun_shield()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    selected_mount_rule_id bigint;
    expected_cost bigint;
BEGIN
    SELECT mount.weapon_mount_rule_id,
           shield.cost_per_armor_point_minor*
           NEW.published_armor_rating
    INTO selected_mount_rule_id,expected_cost
    FROM vehicle_class_armament_mount mount
    CROSS JOIN rule_vehicle_gun_shield shield
    WHERE mount.class_armament_mount_id=
          NEW.class_armament_mount_id
      AND shield.option_rule_id=NEW.option_rule_id;

    IF NOT EXISTS (
        SELECT 1
        FROM rule_vehicle_gun_shield_mount permitted
        WHERE permitted.option_rule_id=NEW.option_rule_id
          AND permitted.mount_rule_id=selected_mount_rule_id
    )
       OR NEW.published_cost_minor<>expected_cost THEN
        RAISE EXCEPTION
            'Vehicle class gun shield violates mount or price rule'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_gun_shield_valid
BEFORE INSERT OR UPDATE ON vehicle_class_armament_gun_shield
FOR EACH ROW EXECUTE FUNCTION
    vehicle_validate_class_gun_shield();

INSERT INTO vehicle_class_armament_gun_shield
SELECT mount.class_armament_mount_id,shield.option_rule_id,
       7,1400,locator.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_armament_mount mount
  ON mount.vehicle_class_rule_id=class.vehicle_class_rule_id
CROSS JOIN rule_vehicle_gun_shield shield
JOIN src_locator locator
  ON locator.heading_path=
     'Common Grav Vehicles > TL15 G/Carrier'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE class.class_code='g-carrier'
  AND mount.mount_sequence=1;

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES (
    'vehicle.class.afv-weapon-points',
    'vehicle.catalogue','source_conflict','high',
    'afv-tracked',
    'Tracked AFV publishes one weapon point for a ten-ton chassis',
    'The Tracked AFV profile says its ten-ton chassis has one weapon point, while the VDS weapon-point rule grants one per five tons and explicitly gives ten tons as two weapon points.',
    'One weapon point',
    'Two weapon points',
    'Should the Tracked AFV have two available weapon points, or is its chassis tonnage or the general allocation rule different?',
    'A corrected printing, publisher errata, or another authorized Tracked AFV profile resolving the conflict.',
    'preserve_published'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Common Ground Vehicles > TL12 AFV, Tracked'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code='vehicle.class.afv-weapon-points';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor retains the same VDS profile but has no independent vehicle weapon-point or standard-design calculator capable of resolving this conflict.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='engine/skills.py'
WHERE issue.issue_code='vehicle.class.afv-weapon-points';
