ALTER TABLE vehicle_class_weapon_point_summary
    ADD COLUMN calculated_used_weapon_points smallint CHECK (
        calculated_used_weapon_points>0
    ),
    ADD COLUMN used_reconciliation_status text CHECK (
        used_reconciliation_status IN ('matches','source-conflict')
    );

UPDATE vehicle_class_weapon_point_summary summary
SET calculated_used_weapon_points=summary.published_used_weapon_points,
    used_reconciliation_status='matches';

ALTER TABLE vehicle_class_weapon_point_summary
    ALTER COLUMN calculated_used_weapon_points SET NOT NULL,
    ALTER COLUMN used_reconciliation_status SET NOT NULL,
    ADD CHECK (
        (
            used_reconciliation_status='matches'
            AND calculated_used_weapon_points=
                published_used_weapon_points
        )
        OR
        (
            used_reconciliation_status='source-conflict'
            AND calculated_used_weapon_points<>
                published_used_weapon_points
        )
    );

ALTER TABLE vehicle_class_armament_mount
    DROP CONSTRAINT vehicle_class_armament_mount_check,
    ADD COLUMN ordnance_bay_rule_id bigint REFERENCES
        rule_vehicle_ordnance_bay(bay_rule_id),
    ADD CONSTRAINT vehicle_class_armament_mount_type_check CHECK (
        num_nonnulls(
            weapon_mount_rule_id,turret_rule_id,
            ordnance_bay_rule_id
        )=1
    );

CREATE TABLE vehicle_class_armament_missile (
    class_armament_mount_id bigint PRIMARY KEY REFERENCES
        vehicle_class_armament_mount(class_armament_mount_id)
        ON DELETE CASCADE,
    missile_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_missile(missile_rule_id),
    loaded_per_mount smallint NOT NULL CHECK (
        loaded_per_mount>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE TABLE vehicle_class_armament_ordnance (
    class_armament_mount_id bigint PRIMARY KEY REFERENCES
        vehicle_class_armament_mount(class_armament_mount_id)
        ON DELETE CASCADE,
    ordnance_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_ordnance_definition(ordnance_rule_id),
    loaded_per_bay smallint NOT NULL CHECK (loaded_per_bay>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE TABLE vehicle_class_weapon_ammunition_load (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    weapon_family_code text NOT NULL REFERENCES
        rule_vehicle_weapon_ammunition(weapon_family_code),
    round_count integer NOT NULL CHECK (round_count>0),
    allocated_spaces numeric NOT NULL CHECK (allocated_spaces>0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (vehicle_class_rule_id,weapon_family_code)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_ammunition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    ammunition rule_vehicle_weapon_ammunition%ROWTYPE;
    expected_spaces numeric;
    expected_cost numeric;
BEGIN
    SELECT definition.* INTO ammunition
    FROM rule_vehicle_weapon_ammunition definition
    WHERE definition.weapon_family_code=NEW.weapon_family_code;
    expected_spaces=ceil(
        NEW.round_count::numeric/ammunition.rounds_per_space
    );
    expected_cost=expected_spaces*ammunition.price_per_space_minor;
    IF NEW.allocated_spaces<>expected_spaces
       OR NEW.published_cost_minor<>expected_cost THEN
        RAISE EXCEPTION
            'Vehicle ammunition load conflicts with catalogue formula'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_ammunition_valid
BEFORE INSERT OR UPDATE ON vehicle_class_weapon_ammunition_load
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_ammunition();

CREATE TABLE vehicle_class_missile_load (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    missile_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_missile(missile_rule_id),
    missile_count integer NOT NULL CHECK (missile_count>0),
    allocated_spaces numeric NOT NULL CHECK (allocated_spaces>0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (vehicle_class_rule_id,missile_rule_id)
);

CREATE TABLE vehicle_class_ordnance_load (
    vehicle_class_rule_id bigint NOT NULL REFERENCES
        vehicle_class(vehicle_class_rule_id),
    ordnance_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_ordnance_definition(ordnance_rule_id),
    ordnance_count integer NOT NULL CHECK (ordnance_count>0),
    allocated_spaces numeric NOT NULL CHECK (allocated_spaces>0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    PRIMARY KEY (vehicle_class_rule_id,ordnance_rule_id)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_ordnance_load()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    unit_spaces numeric;
    unit_cost bigint;
    expected_count integer;
BEGIN
    IF TG_TABLE_NAME='vehicle_class_missile_load' THEN
        SELECT missile.unit_spaces,missile.unit_cost_minor
        INTO unit_spaces,unit_cost
        FROM rule_vehicle_missile missile
        WHERE missile.missile_rule_id=NEW.missile_rule_id;
        expected_count=NEW.missile_count;
    ELSE
        SELECT ordnance.unit_spaces,ordnance.unit_cost_minor
        INTO unit_spaces,unit_cost
        FROM rule_vehicle_ordnance_definition ordnance
        WHERE ordnance.ordnance_rule_id=NEW.ordnance_rule_id;
        expected_count=NEW.ordnance_count;
    END IF;
    IF NEW.allocated_spaces<>unit_spaces*expected_count
       OR NEW.published_cost_minor<>unit_cost*expected_count THEN
        RAISE EXCEPTION
            'Vehicle missile or ordnance load conflicts with catalogue'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_class_missile_load_valid
BEFORE INSERT OR UPDATE ON vehicle_class_missile_load
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_ordnance_load();

CREATE TRIGGER vehicle_class_ordnance_load_valid
BEFORE INSERT OR UPDATE ON vehicle_class_ordnance_load
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_class_ordnance_load();

INSERT INTO vehicle_class_weapon_point_summary (
    vehicle_class_rule_id,
    published_available_weapon_points,
    calculated_available_weapon_points,
    published_used_weapon_points,reconciliation_status,
    source_locator_id,effective_available_weapon_points,
    adjudication_basis,calculated_used_weapon_points,
    used_reconciliation_status
)
SELECT class.vehicle_class_rule_id,160,160,23,'matches',
       class.source_locator_id,160,'published-profile',22,
       'source-conflict'
FROM vehicle_class class
WHERE class.class_code='destroyer-watercraft';

WITH source(
    mount_sequence,quantity,mount_code,turret_code,bay_code,
    weapon_points_each,published_spaces,published_cost
) AS (
    VALUES
        (1::smallint,4::smallint,NULL::text,'small'::text,
         NULL::text,1::smallint,0.5::numeric,4000::bigint),
        (2,1,NULL,'small',NULL,4,0.5,4000),
        (3,8,NULL,'small',NULL,1,0.5,4000),
        (4,4,'fixed',NULL,NULL,1,0,0),
        (5,2,NULL,NULL,'dedicated',1,36,180000)
)
INSERT INTO vehicle_class_armament_mount (
    vehicle_class_rule_id,mount_sequence,quantity,
    weapon_mount_rule_id,turret_rule_id,
    ordnance_bay_rule_id,weapon_points_each,
    published_mount_spaces_each,published_mount_cost_each_minor,
    source_locator_id
)
SELECT class.vehicle_class_rule_id,source.mount_sequence,
       source.quantity,mount.mount_rule_id,turret.turret_rule_id,
       bay.bay_rule_id,source.weapon_points_each,
       source.published_spaces,source.published_cost,
       class.source_locator_id
FROM source
CROSS JOIN vehicle_class class
LEFT JOIN rule_vehicle_weapon_mount mount
  ON mount.mount_code=source.mount_code
LEFT JOIN rule_vehicle_turret turret
  ON turret.turret_code=source.turret_code
LEFT JOIN rule_vehicle_ordnance_bay bay
  ON bay.bay_code=source.bay_code
WHERE class.class_code='destroyer-watercraft';

WITH source(mount_sequence,weapon_code) AS (
    VALUES
        (1::smallint,'autocannon-tl-8'),
        (2,'mass-driver-tl-8'),
        (3,'rocket-artillery-tl-7'),
        (4,'missile-rack')
)
INSERT INTO vehicle_class_armament_weapon (
    class_armament_mount_id,slot_order,weapon_rule_id,
    quantity_per_mount,published_weapon_spaces_each,
    published_weapon_cost_each_minor,reconciliation_status,
    source_locator_id
)
SELECT mount.class_armament_mount_id,1,weapon.weapon_rule_id,
       1,weapon.unit_spaces,weapon.unit_cost_minor,'matches',
       class.source_locator_id
FROM source
JOIN vehicle_class class
  ON class.class_code='destroyer-watercraft'
JOIN vehicle_class_armament_mount mount
  ON mount.vehicle_class_rule_id=class.vehicle_class_rule_id
 AND mount.mount_sequence=source.mount_sequence
JOIN rule_vehicle_weapon_definition weapon
  ON weapon.weapon_code=source.weapon_code;

INSERT INTO vehicle_class_armament_missile (
    class_armament_mount_id,missile_rule_id,
    loaded_per_mount,source_locator_id
)
SELECT mount.class_armament_mount_id,missile.missile_rule_id,
       1,class.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_armament_mount mount
  ON mount.vehicle_class_rule_id=class.vehicle_class_rule_id
 AND mount.mount_sequence=4
JOIN rule_vehicle_missile missile
  ON missile.missile_code=
     'standard-he-smart-computer-guided'
WHERE class.class_code='destroyer-watercraft';

INSERT INTO vehicle_class_armament_ordnance (
    class_armament_mount_id,ordnance_rule_id,
    loaded_per_bay,source_locator_id
)
SELECT mount.class_armament_mount_id,ordnance.ordnance_rule_id,
       3,class.source_locator_id
FROM vehicle_class class
JOIN vehicle_class_armament_mount mount
  ON mount.vehicle_class_rule_id=class.vehicle_class_rule_id
 AND mount.mount_sequence=5
JOIN rule_vehicle_ordnance_definition ordnance
  ON ordnance.ordnance_code='torpedo-he-standard'
WHERE class.class_code='destroyer-watercraft';

INSERT INTO vehicle_class_weapon_ammunition_load (
    vehicle_class_rule_id,weapon_family_code,round_count,
    allocated_spaces,published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,source.weapon_family,
       source.round_count,source.spaces,source.cost_minor,
       class.source_locator_id
FROM (
    VALUES
        ('autocannon',1800,72::numeric,288000::bigint),
        ('mass-driver',300,150,1350000),
        ('rocket-artillery',900,300,1500000)
) source(weapon_family,round_count,spaces,cost_minor)
CROSS JOIN vehicle_class class
WHERE class.class_code='destroyer-watercraft';

INSERT INTO vehicle_class_missile_load (
    vehicle_class_rule_id,missile_rule_id,missile_count,
    allocated_spaces,published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,missile.missile_rule_id,
       900,900,2250000,class.source_locator_id
FROM vehicle_class class
JOIN rule_vehicle_missile missile
  ON missile.missile_code=
     'standard-he-smart-computer-guided'
WHERE class.class_code='destroyer-watercraft';

INSERT INTO vehicle_class_ordnance_load (
    vehicle_class_rule_id,ordnance_rule_id,ordnance_count,
    allocated_spaces,published_cost_minor,source_locator_id
)
SELECT class.vehicle_class_rule_id,ordnance.ordnance_rule_id,
       240,2880,576000,class.source_locator_id
FROM vehicle_class class
JOIN rule_vehicle_ordnance_definition ordnance
  ON ordnance.ordnance_code='torpedo-he-standard'
WHERE class.class_code='destroyer-watercraft';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES
(
    'vehicle.class.destroyer-used-weapon-points',
    'vehicle.catalogue','arithmetic_conflict','high',
    'destroyer-watercraft',
    'Destroyer armament reconstructs to 22 rather than 23 weapon points',
    'The published Destroyer says 23 weapon points are used. Four Autocannon turrets use 4, the Mass Driver turret uses 4, eight Rocket Artillery turrets use 8, four Missile Racks use 4, and two 36-space torpedo bays use 2, for a total of 22.',
    '23 weapon points used',
    '22 weapon points reconstructed from listed armament',
    'Is one listed mount, bay, or heavy-weapon designation intended to consume an additional weapon point?',
    'A corrected printing or complete authorized Destroyer armament worksheet.',
    'preserve_rule'
),
(
    'vehicle.class.destroyer-heavy-weapon-labels',
    'vehicle.catalogue','source_conflict','medium',
    'destroyer-watercraft',
    'Destroyer uses undefined Heavy weapon labels',
    'The profile names a Heavy Mass Driver TL8 and Heavy Rocket Artillery TL7, but the governing weapon catalogue defines only Mass Driver TL8 and Rocket Artillery TL7 at those tech levels.',
    'Heavy Mass Driver TL8 and Heavy Rocket Artillery TL7',
    'Mapped to the unique TL8 Mass Driver and TL7 Rocket Artillery entries',
    'Are the word Heavy labels descriptive, or are two weapon variants missing from the catalogue?',
    'A corrected printing or authorized weapon catalogue defining the Heavy variants.',
    'preserve_rule'
);

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'primary'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Common Watercraft > TL9 Destroyer'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE issue.issue_code IN (
    'vehicle.class.destroyer-used-weapon-points',
    'vehicle.class.destroyer-heavy-weapon-labels'
);
