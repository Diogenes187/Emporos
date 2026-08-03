INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Common Watercraft > TL9 Destroyer',
         'Cepheus Engine VDS, Common Watercraft: TL9 Destroyer'),
        ('Common Watercraft > TL5 Motor Boat',
         'Cepheus Engine VDS, Common Watercraft: TL5 Motor Boat'),
        ('Common Watercraft > TL4 Steamship',
         'Cepheus Engine VDS, Common Watercraft: TL4 Steamship'),
        ('Common Watercraft > TL6 Submersible',
         'Cepheus Engine VDS, Common Watercraft: TL6 Submersible')
) source(heading_path,display_citation)
JOIN src_work work
  ON work.source_work_id=artifact.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE artifact.source_uri='src/vds/common-watercraft.md';

ALTER TABLE vehicle_class
    ALTER COLUMN chassis_code DROP NOT NULL;

CREATE TABLE vehicle_class_ship_scale_hull (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class(vehicle_class_rule_id),
    ship_hull_code text NOT NULL REFERENCES
        rule_ship_hull_design(hull_code),
    published_base_spaces numeric NOT NULL CHECK (
        published_base_spaces>0
    ),
    published_base_cost_minor bigint NOT NULL CHECK (
        published_base_cost_minor>0
    ),
    space_combat_hull_points smallint NOT NULL CHECK (
        space_combat_hull_points>0
    ),
    space_combat_structure_points smallint NOT NULL CHECK (
        space_combat_structure_points>0
    ),
    calculation_status text NOT NULL CHECK (
        calculation_status IN ('matches','published_override')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

CREATE TABLE vehicle_class_ship_scale_power_plant (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class_ship_scale_hull(vehicle_class_rule_id),
    craft_scale text NOT NULL,
    drive_code text NOT NULL,
    power_plant_code text NOT NULL REFERENCES
        rule_vehicle_power_plant_type(power_plant_code),
    published_spaces numeric NOT NULL CHECK (published_spaces>0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    calculation_status text NOT NULL CHECK (
        calculation_status='published_override'
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    FOREIGN KEY (craft_scale,drive_code)
        REFERENCES rule_ship_drive_design(craft_scale,drive_code)
);

CREATE TABLE vehicle_class_ship_scale_propulsion (
    vehicle_class_rule_id bigint PRIMARY KEY REFERENCES
        vehicle_class_ship_scale_hull(vehicle_class_rule_id),
    propulsion_code text NOT NULL REFERENCES
        rule_vehicle_propulsion_type(propulsion_code),
    craft_scale text NOT NULL,
    drive_code text NOT NULL,
    published_spaces numeric NOT NULL CHECK (published_spaces>0),
    published_cost_minor bigint NOT NULL CHECK (
        published_cost_minor>0
    ),
    performance smallint NOT NULL CHECK (
        performance BETWEEN 1 AND 6
    ),
    reported_top_speed numeric NOT NULL CHECK (
        reported_top_speed>0
    ),
    reported_cruise_speed numeric NOT NULL CHECK (
        reported_cruise_speed>0
    ),
    reported_speed_unit text NOT NULL CHECK (
        reported_speed_unit='kilometre_per_hour'
    ),
    reported_agility_dm smallint NOT NULL,
    calculation_status text NOT NULL CHECK (
        calculation_status='published_override'
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    FOREIGN KEY (craft_scale,drive_code)
        REFERENCES rule_ship_drive_design(craft_scale,drive_code)
);

CREATE OR REPLACE FUNCTION vehicle_validate_class_capacity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    chassis_spaces numeric;
    armor_base smallint;
    armor_maximum smallint;
    armor_tech_level smallint;
BEGIN
    IF NEW.chassis_code IS NOT NULL THEN
        SELECT spaces INTO chassis_spaces
        FROM rule_vehicle_chassis
        WHERE chassis_code=NEW.chassis_code;
    ELSE
        SELECT published_base_spaces INTO chassis_spaces
        FROM vehicle_class_ship_scale_hull
        WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    END IF;
    IF chassis_spaces IS NOT NULL
       AND NEW.allocated_spaces+NEW.cargo_spaces>chassis_spaces THEN
        RAISE EXCEPTION 'Vehicle design exceeds chassis spaces'
            USING ERRCODE='23514';
    END IF;
    IF NEW.armor_code IS NOT NULL THEN
        SELECT base_armor,maximum_armor,minimum_tech_level
        INTO armor_base,armor_maximum,armor_tech_level
        FROM rule_vehicle_armor
        WHERE armor_code=NEW.armor_code;
        IF NEW.armor_rating<armor_base
           OR NEW.armor_rating>armor_maximum
           OR NEW.minimum_tech_level<armor_tech_level THEN
            RAISE EXCEPTION
                'Vehicle armor is invalid for material or tech level'
                USING ERRCODE='23514';
        END IF;
    ELSIF NEW.armor_rating<>0 THEN
        RAISE EXCEPTION 'Vehicle armor rating requires armor material'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION vehicle_validate_ship_scale_hull()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_row vehicle_class%ROWTYPE;
    hull_row rule_ship_hull_design%ROWTYPE;
BEGIN
    SELECT * INTO class_row
    FROM vehicle_class
    WHERE vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    SELECT * INTO hull_row
    FROM rule_ship_hull_design
    WHERE hull_code=NEW.ship_hull_code;
    IF class_row.chassis_code IS NOT NULL
       OR NEW.published_base_spaces<>hull_row.hull_tons*12
       OR class_row.construction_hours<>
          hull_row.construction_weeks*7*24
       OR class_row.hull_points<>floor(hull_row.hull_tons/5)
       OR class_row.structure_points<>floor(hull_row.hull_tons/5)
       OR NEW.space_combat_hull_points<>
          floor(hull_row.hull_tons/50)
       OR NEW.space_combat_structure_points<>
          floor(hull_row.hull_tons/50)
       OR class_row.allocated_spaces+class_row.cargo_spaces>
          NEW.published_base_spaces
       OR (
           NEW.calculation_status='matches'
           AND NEW.published_base_cost_minor<>
               hull_row.base_cost_minor
       ) THEN
        RAISE EXCEPTION
            'Ship-scale vehicle hull conflicts with its class or hull table'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_ship_scale_hull_valid
BEFORE INSERT OR UPDATE ON vehicle_class_ship_scale_hull
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_ship_scale_hull();

CREATE OR REPLACE FUNCTION vehicle_validate_hull_authority()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_rule_id bigint;
    selected_chassis text;
    ship_hull_count integer;
BEGIN
    target_rule_id=coalesce(
        NEW.vehicle_class_rule_id,OLD.vehicle_class_rule_id
    );
    SELECT chassis_code INTO selected_chassis
    FROM vehicle_class
    WHERE vehicle_class_rule_id=target_rule_id;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    SELECT count(*) INTO ship_hull_count
    FROM vehicle_class_ship_scale_hull
    WHERE vehicle_class_rule_id=target_rule_id;
    IF (
        selected_chassis IS NULL
        AND ship_hull_count<>1
    ) OR (
        selected_chassis IS NOT NULL
        AND ship_hull_count<>0
    ) THEN
        RAISE EXCEPTION
            'Vehicle class must have exactly one chassis authority'
            USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER vehicle_class_hull_authority_valid
AFTER INSERT OR UPDATE OF chassis_code ON vehicle_class
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_hull_authority();

CREATE CONSTRAINT TRIGGER vehicle_ship_hull_authority_valid
AFTER INSERT OR UPDATE OR DELETE ON vehicle_class_ship_scale_hull
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_hull_authority();

CREATE OR REPLACE FUNCTION vehicle_validate_ship_scale_drive()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    class_tech smallint;
    class_scale text;
    plant_tech smallint;
    propulsion_tech smallint;
BEGIN
    SELECT class.minimum_tech_level,hull.craft_scale
    INTO class_tech,class_scale
    FROM vehicle_class class
    JOIN vehicle_class_ship_scale_hull selection
      USING (vehicle_class_rule_id)
    JOIN rule_ship_hull_design hull
      ON hull.hull_code=selection.ship_hull_code
    WHERE class.vehicle_class_rule_id=NEW.vehicle_class_rule_id;
    IF TG_TABLE_NAME=
       'vehicle_class_ship_scale_power_plant' THEN
        SELECT minimum_tech_level INTO plant_tech
        FROM rule_vehicle_power_plant_type
        WHERE power_plant_code=NEW.power_plant_code;
        IF NEW.craft_scale<>class_scale
           OR class_tech<plant_tech THEN
            RAISE EXCEPTION
                'Ship-scale vehicle power plant conflicts with class'
                USING ERRCODE='23514';
        END IF;
    ELSE
        SELECT minimum_tech_level INTO propulsion_tech
        FROM rule_vehicle_propulsion_type
        WHERE propulsion_code=NEW.propulsion_code;
        IF NEW.craft_scale<>class_scale
           OR class_tech<propulsion_tech
           OR NOT EXISTS (
               SELECT 1
               FROM rule_vehicle_propulsion_speed
               WHERE propulsion_code=NEW.propulsion_code
                 AND speed_variant='standard'
                 AND performance=NEW.performance
                 AND base_speed=NEW.reported_top_speed
                 AND speed_unit=NEW.reported_speed_unit
           ) THEN
            RAISE EXCEPTION
                'Ship-scale vehicle propulsion conflicts with class'
                USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER vehicle_ship_scale_power_plant_valid
BEFORE INSERT OR UPDATE
ON vehicle_class_ship_scale_power_plant
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_ship_scale_drive();

CREATE TRIGGER vehicle_ship_scale_propulsion_valid
BEFORE INSERT OR UPDATE
ON vehicle_class_ship_scale_propulsion
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_ship_scale_drive();

CREATE OR REPLACE FUNCTION vehicle_validate_ship_scale_completeness()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    target_rule_id bigint;
    ship_hull_count integer;
    power_plant_count integer;
    propulsion_count integer;
BEGIN
    target_rule_id=coalesce(
        NEW.vehicle_class_rule_id,OLD.vehicle_class_rule_id
    );
    SELECT count(*) INTO ship_hull_count
    FROM vehicle_class_ship_scale_hull
    WHERE vehicle_class_rule_id=target_rule_id;
    IF ship_hull_count=0 THEN
        RETURN NULL;
    END IF;
    SELECT count(*) INTO power_plant_count
    FROM vehicle_class_ship_scale_power_plant
    WHERE vehicle_class_rule_id=target_rule_id;
    SELECT count(*) INTO propulsion_count
    FROM vehicle_class_ship_scale_propulsion
    WHERE vehicle_class_rule_id=target_rule_id;
    IF power_plant_count<>1 OR propulsion_count<>1 THEN
        RAISE EXCEPTION
            'Ship-scale vehicle requires one power plant and propulsion'
            USING ERRCODE='23514';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER vehicle_ship_hull_complete
AFTER INSERT OR UPDATE OR DELETE ON vehicle_class_ship_scale_hull
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_ship_scale_completeness();

CREATE CONSTRAINT TRIGGER vehicle_ship_power_complete
AFTER INSERT OR UPDATE OR DELETE
ON vehicle_class_ship_scale_power_plant
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_ship_scale_completeness();

CREATE CONSTRAINT TRIGGER vehicle_ship_propulsion_complete
AFTER INSERT OR UPDATE OR DELETE
ON vehicle_class_ship_scale_propulsion
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION vehicle_validate_ship_scale_completeness();

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'vehicle.class.'||source.class_code,
       source.class_name,'vehicle','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('destroyer-watercraft','Destroyer'),
        ('motor-boat','Motor Boat'),
        ('steamship','Steamship'),
        ('submersible','Submersible')
) source(class_code,class_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO vehicle_class (
    vehicle_class_rule_id,class_code,chassis_code,
    minimum_tech_level,configuration,standard_design,
    armor_code,armor_rating,hull_points,structure_points,
    allocated_spaces,cargo_spaces,construction_cost_minor,
    construction_hours,source_locator_id
)
SELECT rule.rule_id,source.class_code,NULL,
       source.tech_level,'closed',true,
       source.armor_code,source.armor_rating,
       source.hull_points,source.structure_points,
       source.allocated_spaces,source.cargo_spaces,
       source.construction_cost_minor,source.construction_hours,
       locator.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft',9,'titanium-steel',6,160,160,
         8752.62::numeric,847.38::numeric,51521940::bigint,15456,
         'Common Watercraft > TL9 Destroyer'),
        ('motor-boat',5,'iron',2,12,12,
         447.15,272.85,2698450,5376,
         'Common Watercraft > TL5 Motor Boat'),
        ('steamship',4,'iron',2,40,40,
         1883.4,516.6,5730030,7392,
         'Common Watercraft > TL4 Steamship'),
        ('submersible',6,'iron',2,20,20,
         659.73,540.27,31194670,6048,
         'Common Watercraft > TL6 Submersible')
) source(
    class_code,tech_level,armor_code,armor_rating,
    hull_points,structure_points,allocated_spaces,cargo_spaces,
    construction_cost_minor,construction_hours,heading_path
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.class.'||source.class_code
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

INSERT INTO vehicle_class_ship_scale_hull (
    vehicle_class_rule_id,ship_hull_code,
    published_base_spaces,published_base_cost_minor,
    space_combat_hull_points,space_combat_structure_points,
    calculation_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,source.ship_hull_code,
       source.base_spaces,source.base_cost,
       source.space_hull,source.space_structure,
       'published_override',class.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft','8',9600::numeric,
         20000000::bigint,16::smallint,16::smallint),
        ('motor-boat','sB',720,400000,1,1),
        ('steamship','2',2400,2000000,4,4),
        ('submersible','1',1200,3000000,2,2)
) source(
    class_code,ship_hull_code,base_spaces,base_cost,
    space_hull,space_structure
)
JOIN vehicle_class class USING (class_code);

INSERT INTO vehicle_class_ship_scale_power_plant (
    vehicle_class_rule_id,craft_scale,drive_code,
    power_plant_code,published_spaces,published_cost_minor,
    calculation_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,source.craft_scale,
       source.drive_code,source.power_plant_code,
       source.spaces,source.cost_minor,
       'published_override',class.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft','starship','K',
         'early-fusion',338.4::numeric,480000::bigint),
        ('motor-boat','small_craft','sC',
         'internal-combustion',116.64,1200),
        ('steamship','starship','B',
         'external-combustion',1134,19200),
        ('submersible','starship','C',
         'fission',86.4,96000)
) source(
    class_code,craft_scale,drive_code,power_plant_code,
    spaces,cost_minor
)
JOIN vehicle_class class USING (class_code);

INSERT INTO vehicle_class_ship_scale_propulsion (
    vehicle_class_rule_id,propulsion_code,craft_scale,
    drive_code,published_spaces,published_cost_minor,
    performance,reported_top_speed,reported_cruise_speed,
    reported_speed_unit,reported_agility_dm,
    calculation_status,source_locator_id
)
SELECT class.vehicle_class_rule_id,'screw-propeller',
       source.craft_scale,source.drive_code,
       source.spaces,source.cost_minor,source.performance,
       source.top_speed,source.cruise_speed,
       'kilometre_per_hour',source.agility_dm,
       'published_override',class.source_locator_id
FROM (
    VALUES
        ('destroyer-watercraft','starship','K',
         205.2::numeric,1000000::bigint,3::smallint,
         60::numeric,45::numeric,-3::smallint),
        ('motor-boat','small_craft','sC',
         16.2,75000,5,100,75,-2),
        ('steamship','starship','B',
         32.4,200000,2,40,30,-5),
        ('submersible','starship','C',
         21.6,100000,2,40,30,-5)
) source(
    class_code,craft_scale,drive_code,spaces,cost_minor,
    performance,top_speed,cruise_speed,agility_dm
)
JOIN vehicle_class class USING (class_code);

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       class.source_locator_id,'fills_source_gap',true
FROM rule_rule rule
JOIN vehicle_class class
  ON class.vehicle_class_rule_id=rule.rule_id
WHERE rule.rule_code IN (
    'vehicle.class.destroyer-watercraft',
    'vehicle.class.motor-boat',
    'vehicle.class.steamship',
    'vehicle.class.submersible'
);

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES (
    'vehicle.class.destroyer-design-table-copy',
    'vehicle.catalogue','source_conflict','high',
    'destroyer-watercraft',
    'Destroyer construction table contains copied aircraft values',
    'The Destroyer construction table stops during its armament allocation and then gives 17.22 cargo spaces, a total cost of 817894.22 credits, and a discounted cost of 736110 credits. Those are the Twin Engine Jet values and conflict with the Destroyer narrative cargo and final price.',
    'Table repeats Twin Engine Jet cargo and totals',
    'Narrative retains 70.615 tons cargo and KCr51,521.940 final cost',
    'Can a complete corrected Destroyer construction table be supplied?',
    'Publisher errata or a complete authorized itemized Destroyer worksheet.',
    'preserve_published'
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
WHERE issue.issue_code=
      'vehicle.class.destroyer-design-table-copy';
