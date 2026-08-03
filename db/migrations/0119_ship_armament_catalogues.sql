ALTER TABLE ship_weapon_definition
    DROP CONSTRAINT ship_weapon_definition_weapon_kind_check;

ALTER TABLE ship_weapon_definition
    ALTER COLUMN damage_dice_count DROP NOT NULL,
    ALTER COLUMN damage_die_sides DROP NOT NULL,
    ADD CONSTRAINT ship_weapon_definition_weapon_kind_check CHECK (
        weapon_kind IN (
            'laser','missile','sandcaster','particle',
            'meson','fusion','plasma','other'
        )
    ),
    ADD COLUMN mount_kind text CHECK (
        mount_kind IS NULL OR mount_kind IN ('turret','bay')
    ),
    ADD COLUMN minimum_tech_level smallint CHECK (
        minimum_tech_level IS NULL OR minimum_tech_level>=0
    ),
    ADD COLUMN optimum_range_code text REFERENCES
        rule_space_range_band(range_band_code),
    ADD COLUMN special_range boolean NOT NULL DEFAULT false,
    ADD COLUMN unit_cost_minor bigint CHECK (
        unit_cost_minor IS NULL OR unit_cost_minor>=0
    ),
    ADD COLUMN attack_modifier smallint NOT NULL DEFAULT 0,
    ADD COLUMN radiation_hit_count smallint NOT NULL DEFAULT 0 CHECK (
        radiation_hit_count>=0
    ),
    ADD COLUMN ignores_armor boolean NOT NULL DEFAULT false,
    ADD COLUMN defensive_reduction_dice smallint NOT NULL DEFAULT 0 CHECK (
        defensive_reduction_dice>=0
    ),
    ADD COLUMN special_effect_code text CHECK (
        special_effect_code IS NULL
        OR special_effect_code ~
           '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    ADD COLUMN calculation_status text NOT NULL DEFAULT 'published' CHECK (
        calculation_status IN ('published','source_unspecified')
    ),
    ADD CONSTRAINT ship_weapon_damage_pair_check CHECK (
        (damage_dice_count IS NULL)=(damage_die_sides IS NULL)
    ),
    ADD CONSTRAINT ship_weapon_damage_or_effect_check CHECK (
        damage_dice_count IS NOT NULL
        OR special_effect_code IS NOT NULL
    );

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,'ship.weapon.'||source.weapon_code,
       source.weapon_name,'ship','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('missile-rack','Missile Rack'),
        ('pulse-laser','Pulse Laser'),
        ('beam-laser','Beam Laser'),
        ('sandcaster','Sandcaster'),
        ('particle-beam-turret','Particle Beam Turret'),
        ('missile-bank','Missile Bank'),
        ('particle-beam-bay','Particle Beam Bay'),
        ('meson-gun-bay','Meson Gun Bay'),
        ('fusion-gun-bay','Fusion Gun Bay')
) source(weapon_code,weapon_name)
WHERE package.package_code='cepheus-engine';

INSERT INTO ship_weapon_definition (
    weapon_rule_id,weapon_code,weapon_kind,
    damage_dice_count,damage_die_sides,damage_modifier,
    ammunition_per_attack,source_locator_id,mount_kind,
    minimum_tech_level,optimum_range_code,special_range,
    unit_cost_minor,attack_modifier,radiation_hit_count,
    ignores_armor,defensive_reduction_dice,
    special_effect_code,calculation_status
)
SELECT rule.rule_id,source.weapon_code,source.weapon_kind,
       source.damage_dice,source.damage_sides,source.damage_modifier,
       source.ammunition,locator.source_locator_id,source.mount_kind,
       source.minimum_tl,source.optimum_range,source.special_range,
       source.unit_cost,source.attack_modifier,
       source.radiation_hits,source.ignores_armor,
       source.defensive_dice,source.special_effect,
       source.calculation_status
FROM (
    VALUES
        ('missile-rack','missile',NULL::smallint,NULL::smallint,
         0::smallint,1::smallint,'turret',6::smallint,NULL::text,
         true,750000::bigint,0::smallint,0::smallint,false,
         0::smallint,'missile-delivery','published'),
        ('pulse-laser','laser',2,6,0,0,'turret',7,'short',
         false,500000,-2,0,false,0,NULL::text,'published'),
        ('beam-laser','laser',NULL,NULL,0,0,'turret',NULL,NULL,
         false,NULL,0,0,false,0,
         'source-omits-construction-statistics','source_unspecified'),
        ('sandcaster','sandcaster',NULL,NULL,0,1,'turret',7,NULL,
         true,250000,0,0,false,1,'beam-defense','published'),
        ('particle-beam-turret','particle',3,6,0,0,'turret',8,'long',
         false,4000000,0,1,false,0,NULL,'published'),
        ('missile-bank','missile',NULL,NULL,0,12,'bay',6,NULL,
         true,12000000,0,0,false,0,'missile-flight-12','published'),
        ('particle-beam-bay','particle',6,6,0,0,'bay',8,'long',
         false,20000000,0,1,false,0,NULL,'published'),
        ('meson-gun-bay','meson',5,6,0,0,'bay',11,'long',
         false,50000000,0,1,true,0,NULL,'published'),
        ('fusion-gun-bay','fusion',5,6,0,0,'bay',12,'medium',
         false,8000000,0,0,false,0,NULL,'published')
) source(
    weapon_code,weapon_kind,damage_dice,damage_sides,
    damage_modifier,ammunition,mount_kind,minimum_tl,
    optimum_range,special_range,unit_cost,attack_modifier,
    radiation_hits,ignores_armor,defensive_dice,
    special_effect,calculation_status
)
JOIN rule_rule rule
  ON rule.rule_code='ship.weapon.'||source.weapon_code
JOIN src_locator locator
  ON locator.heading_path=CASE
      WHEN source.mount_kind='bay' THEN
          'Ship Design and Construction > Armaments > Bays'
      ELSE
          'Ship Design and Construction > Armaments > Turrets'
  END;

CREATE TABLE rule_ship_weapon_mount (
    mount_code text PRIMARY KEY CHECK (
        mount_code IN (
            'single-turret','double-turret','triple-turret',
            'pop-up-turret','fixed-mount','bay'
        )
    ),
    mount_kind text NOT NULL CHECK (
        mount_kind IN ('turret','bay')
    ),
    minimum_tech_level smallint CHECK (minimum_tech_level>=0),
    weapon_capacity smallint NOT NULL CHECK (weapon_capacity>0),
    allocated_tons numeric NOT NULL CHECK (allocated_tons>=0),
    fire_control_tons numeric NOT NULL CHECK (fire_control_tons>=0),
    hardpoints_used smallint NOT NULL CHECK (hardpoints_used>0),
    fixed_cost_minor bigint CHECK (fixed_cost_minor>=0),
    cost_additive_minor bigint CHECK (cost_additive_minor>=0),
    cost_multiplier numeric CHECK (cost_multiplier>0),
    concealed boolean NOT NULL DEFAULT false,
    fixed_direction boolean NOT NULL DEFAULT false,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        num_nonnulls(
            fixed_cost_minor,cost_additive_minor,cost_multiplier
        )=1
    )
);

INSERT INTO rule_ship_weapon_mount
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('single-turret','turret',7::smallint,1::smallint,
         1::numeric,1::numeric,1::smallint,200000::bigint,
         NULL::bigint,NULL::numeric,false,false),
        ('double-turret','turret',8,2,1,1,1,500000,
         NULL,NULL,false,false),
        ('triple-turret','turret',9,3,1,1,1,1000000,
         NULL,NULL,false,false),
        ('pop-up-turret','turret',10,3,2,1,1,NULL,
         1000000,NULL,true,false),
        ('fixed-mount','turret',NULL,3,0,0,1,NULL,
         NULL,0.5,false,true),
        ('bay','bay',NULL,1,50,1,1,0,
         NULL,NULL,false,false)
) source(
    mount_code,mount_kind,minimum_tech_level,weapon_capacity,
    allocated_tons,fire_control_tons,hardpoints_used,
    fixed_cost_minor,cost_additive_minor,cost_multiplier,
    concealed,fixed_direction
)
JOIN src_locator locator
  ON locator.heading_path=CASE
      WHEN source.mount_kind='bay' THEN
          'Ship Design and Construction > Armaments > Bays'
      ELSE
          'Ship Design and Construction > Armaments > Turrets'
  END;

CREATE TABLE rule_ship_missile (
    missile_code text PRIMARY KEY CHECK (
        missile_code IN ('standard','smart','nuclear')
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    damage_dice_count smallint NOT NULL CHECK (
        damage_dice_count>0
    ),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides>1),
    radiation_hit_count smallint NOT NULL DEFAULT 0 CHECK (
        radiation_hit_count>=0
    ),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>0),
    thrust smallint NOT NULL CHECK (thrust>0),
    endurance_turns smallint NOT NULL CHECK (endurance_turns>0),
    units_per_ton smallint NOT NULL CHECK (units_per_ton>0),
    fixed_attack_target integer,
    may_repeat_missed_attack boolean NOT NULL,
    radiation_dm_uses_target_armor boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_missile
SELECT source.missile_code,source.minimum_tech_level,
       source.damage_dice_count,source.damage_die_sides,
       source.radiation_hit_count,source.unit_cost_minor,
       10::smallint,4::smallint,12::smallint,
       source.fixed_target,source.repeat_attack,
       source.armor_radiation_dm,locator.source_locator_id
FROM (
    VALUES
        ('standard',6::smallint,1::smallint,6::smallint,
         0::smallint,1250::bigint,NULL::integer,false,false),
        ('smart',8,1,6,0,2500,8,true,false),
        ('nuclear',6,2,6,1,3750,NULL,false,true)
) source(
    missile_code,minimum_tech_level,damage_dice_count,
    damage_die_sides,radiation_hit_count,unit_cost_minor,
    fixed_target,repeat_attack,armor_radiation_dm
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Armaments > Missiles';

CREATE TABLE rule_ship_screen (
    screen_code text PRIMARY KEY CHECK (
        screen_code IN ('meson-screen','nuclear-damper')
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    allocated_tons numeric NOT NULL CHECK (allocated_tons>0),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>0),
    protected_weapon_kind text NOT NULL CHECK (
        protected_weapon_kind IN ('meson','fusion_and_nuclear')
    ),
    damage_reduction_dice smallint NOT NULL CHECK (
        damage_reduction_dice>0
    ),
    damage_reduction_die_sides smallint NOT NULL CHECK (
        damage_reduction_die_sides>1
    ),
    radiation_dm_per_active_screen smallint NOT NULL DEFAULT 0,
    removes_automatic_radiation boolean NOT NULL DEFAULT false,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_ship_screen
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('meson-screen',12::smallint,50::numeric,60000000::bigint,
         'meson',2::smallint,6::smallint,-2::smallint,false),
        ('nuclear-damper',12,50,50000000,
         'fusion_and_nuclear',2,6,0,true)
) source(
    screen_code,minimum_tech_level,allocated_tons,unit_cost_minor,
    protected_weapon_kind,damage_reduction_dice,
    damage_reduction_die_sides,radiation_dm_per_active_screen,
    removes_automatic_radiation
)
JOIN src_locator locator
  ON locator.heading_path=
     'Ship Design and Construction > Armaments > Screens';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       weapon.source_locator_id,'fills_source_gap',true
FROM rule_rule rule
JOIN ship_weapon_definition weapon
  ON weapon.weapon_rule_id=rule.rule_id
WHERE rule.rule_code LIKE 'ship.weapon.%';
