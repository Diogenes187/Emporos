INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Armaments > Ordinance Bays',
         'Cepheus Engine VDS, Ordinance Bays'),
        ('Vehicle Design > Vehicle Armaments > Missiles',
         'Cepheus Engine VDS, Vehicular Missiles'),
        ('Vehicle Design > Vehicle Armaments > Anti-Missile Systems',
         'Cepheus Engine VDS, Anti-Missile Systems')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/vds/vehicle-design.md';

WITH source(rule_code,rule_name) AS (
    VALUES
        ('vehicle.ordnance-bay.dedicated',
         'Dedicated Ordnance Bay'),
        ('vehicle.ordnance-bay.general-purpose',
         'General Purpose Ordnance Bay'),
        ('vehicle.ordnance.bomb-he-standard',
         'Bomb, High Explosive, Standard'),
        ('vehicle.ordnance.torpedo-he-standard',
         'Torpedo, High Explosive, Standard'),
        ('vehicle.ordnance.bomb-he-heavy',
         'Bomb, High Explosive, Heavy'),
        ('vehicle.ordnance.torpedo-he-heavy',
         'Torpedo, High Explosive, Heavy'),
        ('vehicle.ordnance.bomb-nuclear-heavy',
         'Bomb, Nuclear, Heavy'),
        ('vehicle.ordnance.bomb-nuclear-standard',
         'Bomb, Nuclear, Standard'),
        ('vehicle.ordnance.torpedo-nuclear-heavy',
         'Torpedo, Nuclear, Heavy'),
        ('vehicle.ordnance.torpedo-nuclear-standard',
         'Torpedo, Nuclear, Standard'),
        ('vehicle.ordnance.bomb-antimatter-heavy',
         'Bomb, Antimatter, Heavy'),
        ('vehicle.ordnance.bomb-antimatter-standard',
         'Bomb, Antimatter, Standard'),
        ('vehicle.ordnance.torpedo-antimatter-heavy',
         'Torpedo, Antimatter, Heavy'),
        ('vehicle.ordnance.torpedo-antimatter-standard',
         'Torpedo, Antimatter, Standard'),
        ('vehicle.missile.standard-he-unguided',
         'Standard HE, Unguided Missile'),
        ('vehicle.missile.standard-he-remote-guided',
         'Standard HE, Remote-Guided Missile'),
        ('vehicle.missile.standard-he-heat-seeking',
         'Standard HE, Heat-Seeking Missile'),
        ('vehicle.missile.nuclear-radar-guided',
         'Nuclear, Radar-Guided Missile'),
        ('vehicle.missile.standard-he-radar-guided',
         'Standard HE, Radar-Guided Missile'),
        ('vehicle.missile.nuclear-smart-computer-guided',
         'Nuclear, Smart Computer-Guided Missile'),
        ('vehicle.missile.standard-he-smart-computer-guided',
         'Standard HE, Smart Computer-Guided Missile'),
        ('vehicle.missile.nuclear-nas-guided',
         'Nuclear, NAS-Guided Missile'),
        ('vehicle.missile.standard-he-nas-guided',
         'Standard HE, NAS-Guided Missile'),
        ('vehicle.missile.antimatter-smart-ai-guided',
         'Antimatter, Smart AI-Guided Missile'),
        ('vehicle.anti-missile.general',
         'Anti-Missile Resolution'),
        ('vehicle.anti-missile-system.smoke-dischargers',
         'Smoke Dischargers'),
        ('vehicle.anti-missile-system.chaff-dispensers',
         'Chaff Dispensers'),
        ('vehicle.anti-missile-system.flares','Flares'),
        ('vehicle.anti-missile-system.decoys','Decoys'),
        ('vehicle.anti-missile-system.explosive-belt',
         'Explosive Belt'),
        ('vehicle.anti-missile-system.minigun','Minigun'),
        ('vehicle.anti-missile-system.prismatic-aerosols',
         'Prismatic Aerosols'),
        ('vehicle.anti-missile-system.laser','Laser'),
        ('vehicle.anti-missile-system.vrf-gauss','VRF Gauss')
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_ordnance_bay (
    bay_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    bay_code text NOT NULL UNIQUE CHECK (
        bay_code IN ('dedicated','general-purpose')
    ),
    cost_per_capacity_space_minor bigint NOT NULL CHECK (
        cost_per_capacity_space_minor>0
    ),
    single_ordnance_type_only boolean NOT NULL,
    reloadable boolean NOT NULL,
    rate_of_fire_basis text NOT NULL CHECK (
        rate_of_fire_basis IN (
            'ordnance-count',
            'one-missile-or-torpedo-or-half-bomb-capacity'
        )
    ),
    missile_launches_per_round smallint CHECK (
        missile_launches_per_round>0
    ),
    torpedo_launches_per_round smallint CHECK (
        torpedo_launches_per_round>0
    ),
    bomb_capacity_fraction_per_round numeric CHECK (
        bomb_capacity_fraction_per_round>0
        AND bomb_capacity_fraction_per_round<=1
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (bay_code='dedicated'
         AND single_ordnance_type_only
         AND missile_launches_per_round IS NULL
         AND torpedo_launches_per_round IS NULL
         AND bomb_capacity_fraction_per_round IS NULL)
        OR
        (bay_code='general-purpose'
         AND NOT single_ordnance_type_only
         AND missile_launches_per_round IS NOT NULL
         AND torpedo_launches_per_round IS NOT NULL
         AND bomb_capacity_fraction_per_round IS NOT NULL)
    )
);

INSERT INTO rule_vehicle_ordnance_bay
SELECT rule.rule_id,source.bay_code,source.cost_per_space,
       source.single_type,true,source.rof_basis,
       source.missiles,source.torpedoes,source.bomb_fraction,
       locator.source_locator_id
FROM (
    VALUES
        ('dedicated',5000::bigint,true,
         'ordnance-count',NULL::smallint,NULL::smallint,
         NULL::numeric),
        ('general-purpose',10000,false,
         'one-missile-or-torpedo-or-half-bomb-capacity',
         1,1,0.5)
) source(
    bay_code,cost_per_space,single_type,rof_basis,
    missiles,torpedoes,bomb_fraction
)
JOIN rule_rule rule
  ON rule.rule_code='vehicle.ordnance-bay.'||source.bay_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Ordinance Bays'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_ordnance_bay_weapon_point_formula (
    formula_code text PRIMARY KEY,
    bay_spaces_per_weapon_point numeric NOT NULL CHECK (
        bay_spaces_per_weapon_point>0
    ),
    minimum_weapon_points smallint NOT NULL CHECK (
        minimum_weapon_points>0
    ),
    allocation_rounding text NOT NULL CHECK (
        allocation_rounding IN ('floor','ceiling')
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_ordnance_bay_weapon_point_formula
SELECT 'standard',60,1,'ceiling',locator.source_locator_id
FROM src_locator locator
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE locator.heading_path=
      'Vehicle Design > Vehicle Armaments > Ordinance Bays';

CREATE TABLE rule_vehicle_ordnance_definition (
    ordnance_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    ordnance_code text NOT NULL UNIQUE CHECK (
        ordnance_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    ordnance_kind text NOT NULL CHECK (
        ordnance_kind IN ('bomb','torpedo')
    ),
    warhead_kind text NOT NULL CHECK (
        warhead_kind IN (
            'high-explosive','nuclear','antimatter'
        )
    ),
    yield_class text NOT NULL CHECK (
        yield_class IN ('standard','heavy')
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    unit_spaces numeric NOT NULL CHECK (unit_spaces>0),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>0),
    range_profile_code text REFERENCES
        rule_vehicle_weapon_range_profile(range_profile_code),
    published_range_token text NOT NULL CHECK (
        btrim(published_range_token)<>''
    ),
    range_status text NOT NULL CHECK (
        range_status IN ('published','source-malformed')
    ),
    damage_dice_count smallint NOT NULL CHECK (
        damage_dice_count>0
    ),
    damage_die_sides smallint NOT NULL CHECK (
        damage_die_sides>1
    ),
    radiation_dice_count smallint CHECK (
        radiation_dice_count>0
    ),
    radiation_die_sides smallint CHECK (
        radiation_die_sides>1
    ),
    radiation_multiplier smallint CHECK (
        radiation_multiplier>0
    ),
    radiation_unit_status text NOT NULL CHECK (
        radiation_unit_status IN (
            'not-applicable','published-rads','source-omitted'
        )
    ),
    treated_as_aquatic_missile boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (range_status='published'
         AND range_profile_code IS NOT NULL)
        OR
        (range_status='source-malformed'
         AND range_profile_code IS NULL)
    ),
    CHECK (
        (radiation_dice_count IS NULL)=
        (radiation_die_sides IS NULL)
        AND
        (radiation_dice_count IS NULL)=
        (radiation_multiplier IS NULL)
    ),
    CHECK (
        (radiation_unit_status='not-applicable'
         AND radiation_dice_count IS NULL)
        OR
        (radiation_unit_status<>'not-applicable'
         AND radiation_dice_count IS NOT NULL)
    )
);

WITH source(
    ordnance_code,ordnance_kind,warhead_kind,yield_class,
    minimum_tl,unit_spaces,unit_cost,range_profile,
    published_range,range_status,damage_dice,
    radiation_dice,radiation_multiplier,radiation_status
) AS (
    VALUES
        ('bomb-he-standard','bomb','high-explosive','standard',
         4::smallint,3::numeric,1200::bigint,'very-distant',
         'ranged (v distant)','published',12::smallint,
         NULL::smallint,NULL::smallint,'not-applicable'),
        ('torpedo-he-standard','torpedo','high-explosive','standard',
         4,12,2400,'very-distant','ranged (v distant)',
         'published',12,NULL,NULL,'not-applicable'),
        ('bomb-he-heavy','bomb','high-explosive','heavy',
         5,6,4000,'very-distant','ranged (v distant)',
         'published',14,NULL,NULL,'not-applicable'),
        ('torpedo-he-heavy','torpedo','high-explosive','heavy',
         5,24,8000,'very-distant','ranged (v distant)',
         'published',14,NULL,NULL,'not-applicable'),
        ('bomb-nuclear-heavy','bomb','nuclear','heavy',
         6,6,8000,'very-distant','ranged (v distant)',
         'published',28,2,10,'published-rads'),
        ('bomb-nuclear-standard','bomb','nuclear','standard',
         6,3,2400,'very-distant','ranged (v distant)',
         'published',24,2,10,'published-rads'),
        ('torpedo-nuclear-heavy','torpedo','nuclear','heavy',
         6,24,16000,NULL,'ranged (v','source-malformed',
         28,2,10,'source-omitted'),
        ('torpedo-nuclear-standard','torpedo','nuclear','standard',
         6,12,4800,'very-distant','ranged (v distant)',
         'published',24,2,10,'published-rads'),
        ('bomb-antimatter-heavy','bomb','antimatter','heavy',
         17,6,24000,'extreme','ranged (extreme)',
         'published',42,4,10,'published-rads'),
        ('bomb-antimatter-standard','bomb','antimatter','standard',
         17,3,7200,'extreme','ranged (extreme)',
         'published',36,4,10,'published-rads'),
        ('torpedo-antimatter-heavy','torpedo','antimatter','heavy',
         17,24,48000,'extreme','ranged (extreme)',
         'published',42,4,10,'published-rads'),
        ('torpedo-antimatter-standard','torpedo','antimatter',
         'standard',17,12,14400,'extreme','ranged (extreme)',
         'published',36,4,10,'published-rads')
)
INSERT INTO rule_vehicle_ordnance_definition
SELECT rule.rule_id,source.ordnance_code,
       source.ordnance_kind,source.warhead_kind,
       source.yield_class,source.minimum_tl,
       source.unit_spaces,source.unit_cost,
       source.range_profile,source.published_range,
       source.range_status,source.damage_dice,6,
       source.radiation_dice,
       CASE WHEN source.radiation_dice IS NULL
            THEN NULL ELSE 6 END,
       source.radiation_multiplier,source.radiation_status,
       source.ordnance_kind='torpedo',locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.ordnance.'||source.ordnance_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Ordinance Bays'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_missile_guidance (
    guidance_code text PRIMARY KEY CHECK (
        guidance_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    guidance_name text NOT NULL UNIQUE,
    smart_guidance boolean NOT NULL,
    appears_in_missile_catalogue boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_missile_guidance
SELECT source.guidance_code,source.guidance_name,
       source.smart_guidance,source.in_catalogue,
       locator.source_locator_id
FROM (
    VALUES
        ('unguided','Unguided',false,true),
        ('remote-guided','Remote-Guided',false,true),
        ('heat-seeking','Heat-Seeking',false,true),
        ('radar-guided','Radar-Guided',false,true),
        ('smart-computer-guided','Smart Computer-Guided',true,true),
        ('nas-guided','NAS-Guided',false,true),
        ('smart-ai-guided','Smart AI-Guided',true,true),
        ('laser-guided','Laser-Guided',false,false)
) source(
    guidance_code,guidance_name,smart_guidance,in_catalogue
)
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Missiles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_missile (
    missile_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    missile_code text NOT NULL UNIQUE CHECK (
        missile_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    warhead_kind text NOT NULL CHECK (
        warhead_kind IN (
            'standard-high-explosive','nuclear','antimatter'
        )
    ),
    guidance_code text NOT NULL REFERENCES
        rule_vehicle_missile_guidance(guidance_code),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    unit_spaces numeric NOT NULL CHECK (unit_spaces>0),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>0),
    range_profile_code text NOT NULL REFERENCES
        rule_vehicle_weapon_range_profile(range_profile_code),
    damage_dice_count smallint NOT NULL CHECK (
        damage_dice_count>0
    ),
    damage_die_sides smallint NOT NULL CHECK (
        damage_die_sides>1
    ),
    radiation_hit_count smallint NOT NULL CHECK (
        radiation_hit_count>=0
    ),
    fixed_attack_target smallint CHECK (fixed_attack_target>0),
    may_repeat_missed_attack boolean NOT NULL,
    radiation_rule_status text NOT NULL CHECK (
        radiation_rule_status IN (
            'not-applicable','published','prose-table-conflict'
        )
    ),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (guidance_code LIKE 'smart-%'
         AND fixed_attack_target IS NOT NULL
         AND may_repeat_missed_attack)
        OR
        (guidance_code NOT LIKE 'smart-%'
         AND fixed_attack_target IS NULL
         AND NOT may_repeat_missed_attack)
    )
);

WITH source(
    missile_code,warhead_kind,guidance_code,minimum_tl,
    unit_cost,range_profile,damage_dice,radiation_hits,
    radiation_status
) AS (
    VALUES
        ('standard-he-unguided','standard-high-explosive',
         'unguided',3::smallint,750::bigint,'very-long',
         5::smallint,0::smallint,'not-applicable'),
        ('standard-he-remote-guided','standard-high-explosive',
         'remote-guided',3,750,'very-long',5,0,'not-applicable'),
        ('standard-he-heat-seeking','standard-high-explosive',
         'heat-seeking',4,1000,'very-long',6,0,'not-applicable'),
        ('nuclear-radar-guided','nuclear','radar-guided',
         6,3750,'very-long',12,1,'published'),
        ('standard-he-radar-guided','standard-high-explosive',
         'radar-guided',6,1250,'distant',6,0,'not-applicable'),
        ('nuclear-smart-computer-guided','nuclear',
         'smart-computer-guided',7,5000,'distant',16,1,'published'),
        ('standard-he-smart-computer-guided',
         'standard-high-explosive','smart-computer-guided',
         7,2500,'very-distant',8,0,'not-applicable'),
        ('nuclear-nas-guided','nuclear','nas-guided',
         12,2500,'very-long',13,0,'prose-table-conflict'),
        ('standard-he-nas-guided','standard-high-explosive',
         'nas-guided',12,2500,'distant',11,0,'not-applicable'),
        ('antimatter-smart-ai-guided','antimatter',
         'smart-ai-guided',17,10000,'extreme',20,1,'published')
)
INSERT INTO rule_vehicle_missile
SELECT rule.rule_id,source.missile_code,source.warhead_kind,
       source.guidance_code,source.minimum_tl,1,
       source.unit_cost,source.range_profile,source.damage_dice,6,
       source.radiation_hits,
       CASE WHEN source.guidance_code LIKE 'smart-%'
            THEN 8 ELSE NULL END,
       source.guidance_code LIKE 'smart-%',
       source.radiation_status,locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code='vehicle.missile.'||source.missile_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Missiles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_anti_missile_resolution (
    resolution_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    base_target_number smallint NOT NULL CHECK (base_target_number>0),
    additional_target_dm smallint NOT NULL CHECK (
        additional_target_dm<0
    ),
    negates_missiles boolean NOT NULL,
    negates_rockets boolean NOT NULL,
    negates_launched_grenades boolean NOT NULL,
    negates_mortar_rounds boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_anti_missile_resolution
SELECT rule.rule_id,8,-1,true,true,true,true,
       locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Anti-Missile Systems'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.anti-missile.general';

CREATE TABLE rule_vehicle_anti_missile_system (
    system_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    system_code text NOT NULL UNIQUE CHECK (
        system_code ~
        '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    minimum_tech_level smallint NOT NULL CHECK (
        minimum_tech_level>=0
    ),
    interception_dm smallint,
    laser_damage_reduction_dice smallint CHECK (
        laser_damage_reduction_dice>0
    ),
    laser_damage_reduction_die_sides smallint CHECK (
        laser_damage_reduction_die_sides>1
    ),
    unit_spaces numeric CHECK (unit_spaces>0),
    unit_cost_minor bigint NOT NULL CHECK (unit_cost_minor>0),
    minimum_effective_range_code text REFERENCES
        rule_vehicle_weapon_target_range(target_range_code),
    uses_before_reload smallint CHECK (uses_before_reload>0),
    reload_cost_minor bigint CHECK (reload_cost_minor>0),
    applies_to_all_supported_threats boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        interception_dm IS NOT NULL
        OR laser_damage_reduction_dice IS NOT NULL
    ),
    CHECK (
        (laser_damage_reduction_dice IS NULL)=
        (laser_damage_reduction_die_sides IS NULL)
    ),
    CHECK (
        (uses_before_reload IS NULL)=
        (reload_cost_minor IS NULL)
    )
);

WITH source(
    system_code,minimum_tl,interception_dm,
    laser_reduction,unit_spaces,unit_cost,minimum_range,
    uses,reload_cost,all_threats
) AS (
    VALUES
        ('smoke-dischargers',3::smallint,2::smallint,
         NULL::smallint,1.5::numeric,1000::bigint,NULL::text,
         6::smallint,100::bigint,false),
        ('chaff-dispensers',4,2,NULL,1.5,1200,NULL,6,150,false),
        ('flares',6,2,NULL,1.5,2000,NULL,6,200,false),
        ('decoys',7,2,NULL,1.5,8000,NULL,6,1000,false),
        ('explosive-belt',8,0,NULL,NULL,15000,'short',10,800,true),
        ('minigun',8,0,NULL,9,200000,'medium',10,7000,true),
        ('prismatic-aerosols',9,2,2,1.5,4000,NULL,6,500,false),
        ('laser',10,1,NULL,12,250000,'medium',NULL,NULL,true),
        ('vrf-gauss',11,0,NULL,9,200000,'medium',15,20000,true)
)
INSERT INTO rule_vehicle_anti_missile_system
SELECT rule.rule_id,source.system_code,source.minimum_tl,
       source.interception_dm,source.laser_reduction,
       CASE WHEN source.laser_reduction IS NULL
            THEN NULL ELSE 6 END,
       source.unit_spaces,source.unit_cost,source.minimum_range,
       source.uses,source.reload_cost,source.all_threats,
       locator.source_locator_id
FROM source
JOIN rule_rule rule
  ON rule.rule_code=
     'vehicle.anti-missile-system.'||source.system_code
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Anti-Missile Systems'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_anti_missile_guidance_claim (
    system_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_anti_missile_system(system_rule_id),
    guidance_code text NOT NULL REFERENCES
        rule_vehicle_missile_guidance(guidance_code),
    claim_role text NOT NULL CHECK (
        claim_role IN ('primary-label','parenthetical-label')
    ),
    PRIMARY KEY (system_rule_id,guidance_code,claim_role)
);

INSERT INTO rule_vehicle_anti_missile_guidance_claim
SELECT system.system_rule_id,source.guidance_code,
       source.claim_role
FROM (
    VALUES
        ('smoke-dischargers','remote-guided','parenthetical-label'),
        ('chaff-dispensers','heat-seeking','parenthetical-label'),
        ('flares','radar-guided','parenthetical-label'),
        ('decoys','smart-computer-guided','primary-label'),
        ('decoys','smart-ai-guided','primary-label'),
        ('decoys','radar-guided','parenthetical-label'),
        ('prismatic-aerosols','laser-guided','primary-label')
) source(system_code,guidance_code,claim_role)
JOIN rule_vehicle_anti_missile_system system USING (system_code);

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code LIKE 'vehicle.ordnance%'
               THEN ordnance_locator.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.missile.%'
               THEN missile_locator.source_locator_id
           ELSE defense_locator.source_locator_id
       END,
       'direct',true
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.github-v9.1'
LEFT JOIN src_locator ordnance_locator
  ON ordnance_locator.source_work_id=work.source_work_id
 AND ordnance_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Ordinance Bays'
LEFT JOIN src_locator missile_locator
  ON missile_locator.source_work_id=work.source_work_id
 AND missile_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Missiles'
LEFT JOIN src_locator defense_locator
  ON defense_locator.source_work_id=work.source_work_id
 AND defense_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Anti-Missile Systems'
WHERE rule.rule_code LIKE 'vehicle.ordnance%'
   OR rule.rule_code LIKE 'vehicle.missile.%'
   OR rule.rule_code='vehicle.anti-missile.general'
   OR rule.rule_code LIKE 'vehicle.anti-missile-system.%';

INSERT INTO src_issue (
    issue_code,domain_code,issue_type,review_priority,
    subject_code,title,problem_statement,
    published_value,calculated_value,
    reviewer_question,requested_evidence,engine_disposition
)
VALUES
    (
        'vehicle.ordnance.heavy-nuclear-torpedo-row',
        'vehicle.catalogue','source_conflict','high',
        'torpedo-nuclear-heavy',
        'Heavy Nuclear Torpedo range and radiation unit are truncated',
        'The Heavy Nuclear Torpedo row ends its range at "ranged (v" and gives 2D6x10 without the radiation unit printed for every parallel nuclear or antimatter ordnance row.',
        'Range: ranged (v; Damage: 28D6 + 2D6x10',
        'Range and radiation unit source-malformed',
        'What range profile and radiation unit should the Heavy Nuclear Torpedo use?',
        'A corrected printing, publisher errata, or another authorized source with the complete row.',
        'source_gap_pending'
    ),
    (
        'vehicle.missile.nas-radiation-hit',
        'vehicle.catalogue','source_conflict','high',
        'nuclear-nas-guided',
        'NAS-Guided Nuclear Missile omits the required radiation hit',
        'The missile prose says both nuclear and antimatter missiles automatically inflict one radiation hit, but the NAS-Guided Nuclear Missile table row lists only 13D6.',
        'Nuclear missiles: 1 radiation hit; NAS row: 13D6',
        'Published table row retains zero radiation hits',
        'Should the NAS-Guided Nuclear Missile also inflict one automatic radiation hit?',
        'A corrected printing, publisher errata, or another authorized missile table resolving the prose-table conflict.',
        'preserve_published'
    ),
    (
        'vehicle.anti-missile.decoy-guidance-label',
        'vehicle.catalogue','source_conflict','medium',
        'decoys',
        'Decoy protection identifies smart missiles as radar-guided',
        'The Decoys row says it applies to smart missile attacks, then identifies those attacks parenthetically as radar-guided missiles even though the missile catalogue treats smart and radar guidance as distinct.',
        'DM+2 vs smart missile attacks (radar-guided missiles)',
        'Smart-guided and radar-guided claims retained separately',
        'Do Decoys protect against smart missiles, radar-guided missiles, or both?',
        'A corrected printing, publisher errata, or another authorized anti-missile table defining the intended guidance category.',
        'preserve_rule'
    );

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,
       CASE
           WHEN issue.issue_code LIKE 'vehicle.ordnance.%'
               THEN ordnance_locator.source_locator_id
           WHEN issue.issue_code LIKE 'vehicle.missile.%'
               THEN missile_locator.source_locator_id
           ELSE defense_locator.source_locator_id
       END,
       'primary'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-engine.github-v9.1'
LEFT JOIN src_locator ordnance_locator
  ON ordnance_locator.source_work_id=work.source_work_id
 AND ordnance_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Ordinance Bays'
LEFT JOIN src_locator missile_locator
  ON missile_locator.source_work_id=work.source_work_id
 AND missile_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Missiles'
LEFT JOIN src_locator defense_locator
  ON defense_locator.source_work_id=work.source_work_id
 AND defense_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Anti-Missile Systems'
WHERE issue.issue_code IN (
    'vehicle.ordnance.heavy-nuclear-torpedo-row',
    'vehicle.missile.nas-radiation-hit',
    'vehicle.anti-missile.decoy-guidance-label'
);
