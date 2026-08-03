INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        (
            'Personal Combat > Vehicles in Personal Combat',
            'Cepheus Engine, Vehicles in Personal Combat'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Closed and Open Vehicles',
            'Cepheus Engine, Closed and Open Vehicles'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicle-Mounted Weapons',
            'Cepheus Engine, Vehicle-Mounted Weapons'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Collisions',
            'Cepheus Engine, Collisions'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions',
            'Cepheus Engine, Vehicular Actions'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Evasive Action',
            'Cepheus Engine, Evasive Action'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Maneuvering',
            'Cepheus Engine, Maneuvering'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Ram',
            'Cepheus Engine, Ram'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Stunt',
            'Cepheus Engine, Stunt'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Weave',
            'Cepheus Engine, Weave'
        )
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/book1/personal-combat.md';

WITH source(rule_code,rule_name) AS (
    VALUES
        (
            'vehicle.combat.procedure',
            'Vehicles in Personal Combat'
        ),
        (
            'vehicle.combat.occupant-protection',
            'Vehicle Occupant Protection'
        ),
        (
            'vehicle.combat.weapon-arcs',
            'Vehicle-Mounted Weapon Arcs'
        ),
        (
            'vehicle.combat.collision',
            'Vehicle Collision'
        ),
        (
            'vehicle.combat.action.evasive',
            'Evasive Action'
        ),
        (
            'vehicle.combat.action.maneuver',
            'Maneuvering'
        ),
        (
            'vehicle.combat.action.ram',
            'Ram'
        ),
        (
            'vehicle.combat.action.stunt',
            'Stunt'
        ),
        (
            'vehicle.combat.action.weave',
            'Weave'
        )
)
INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,source.rule_code,
       source.rule_name,'vehicle','approved'
FROM source
CROSS JOIN sys_content_package package
WHERE package.package_code='cepheus-engine';

CREATE TABLE rule_vehicle_personal_combat (
    combat_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    moves_on_driver_initiative boolean NOT NULL,
    facing_must_be_tracked boolean NOT NULL,
    normal_control_action_kind text NOT NULL CHECK (
        normal_control_action_kind='minor'
    ),
    complex_control_action_kind text NOT NULL CHECK (
        complex_control_action_kind='significant'
    ),
    vehicle_target_attack_dm smallint NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_personal_combat
SELECT rule.rule_id,true,true,'minor','significant',1,
       locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.combat.procedure';

CREATE TABLE rule_vehicle_occupant_protection (
    protection_code text PRIMARY KEY CHECK (
        protection_code IN (
            'open','closed-civilian','closed-military'
        )
    ),
    vehicle_configuration text NOT NULL CHECK (
        vehicle_configuration IN ('open','closed')
    ),
    military_design boolean,
    cover_kind text NOT NULL CHECK (
        cover_kind IN ('none','soft','hard')
    ),
    cover_fraction numeric NOT NULL CHECK (
        cover_fraction BETWEEN 0 AND 1
    ),
    firing_occupants_per_arc smallint CHECK (
        firing_occupants_per_arc>0
    ),
    occupants_may_attack_any_direction boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (
            vehicle_configuration='open'
            AND military_design IS NULL
            AND cover_kind='none'
            AND cover_fraction=0
            AND firing_occupants_per_arc IS NULL
            AND occupants_may_attack_any_direction
        )
        OR (
            vehicle_configuration='closed'
            AND military_design IS NOT NULL
            AND cover_kind<>'none'
            AND cover_fraction>0
            AND firing_occupants_per_arc IS NOT NULL
            AND NOT occupants_may_attack_any_direction
        )
    )
);

INSERT INTO rule_vehicle_occupant_protection
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        (
            'open','open',NULL::boolean,'none',
            0::numeric,NULL::smallint,true
        ),
        (
            'closed-civilian','closed',false,'soft',
            0.5::numeric,2::smallint,false
        ),
        (
            'closed-military','closed',true,'hard',
            1::numeric,1::smallint,false
        )
) source(
    protection_code,vehicle_configuration,military_design,
    cover_kind,cover_fraction,firing_occupants_per_arc,
    occupants_may_attack_any_direction
)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Closed and Open Vehicles'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_weapon_arc (
    arc_code text PRIMARY KEY CHECK (
        arc_code IN ('front-fixed','turret')
    ),
    arc_degrees smallint NOT NULL CHECK (
        arc_degrees BETWEEN 1 AND 360
    ),
    unrestricted_direction boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    CHECK (
        (unrestricted_direction AND arc_degrees=360)
        OR (NOT unrestricted_direction AND arc_degrees<360)
    )
);

INSERT INTO rule_vehicle_weapon_arc
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('front-fixed',90::smallint,false),
        ('turret',360::smallint,true)
) source(arc_code,arc_degrees,unrestricted_direction)
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle-Mounted Weapons'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_collision (
    collision_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    speed_increment_kph smallint NOT NULL CHECK (
        speed_increment_kph>0
    ),
    damage_dice_per_increment smallint NOT NULL CHECK (
        damage_dice_per_increment>0
    ),
    damage_die_sides smallint NOT NULL CHECK (
        damage_die_sides>1
    ),
    increment_rounding text NOT NULL CHECK (
        increment_rounding='ceiling'
    ),
    struck_target_takes_full_damage boolean NOT NULL,
    solid_target_damages_ramming_vehicle boolean NOT NULL,
    unsecured_occupant_damage_fraction numeric NOT NULL CHECK (
        unsecured_occupant_damage_fraction BETWEEN 0 AND 1
    ),
    unsecured_throw_metres_per_increment numeric NOT NULL CHECK (
        unsecured_throw_metres_per_increment>=0
    ),
    secured_occupant_damage_fraction numeric NOT NULL CHECK (
        secured_occupant_damage_fraction BETWEEN 0 AND 1
    ),
    secured_occupants_are_thrown boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_vehicle_collision
SELECT rule.rule_id,10,1,6,'ceiling',true,true,1,3,0.25,
       false,locator.source_locator_id
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Collisions'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1'
WHERE rule.rule_code='vehicle.combat.collision';

CREATE TABLE rule_vehicle_combat_action (
    action_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    action_code text NOT NULL UNIQUE CHECK (
        action_code IN (
            'evasive','maneuver','ram','stunt','weave'
        )
    ),
    action_kind text NOT NULL CHECK (
        action_kind='significant'
    ),
    check_requirement text NOT NULL CHECK (
        check_requirement IN (
            'none','vehicle-skill','vehicle-control'
        )
    ),
    collision_on_success boolean NOT NULL,
    affected_by_dodge boolean NOT NULL,
    affected_by_evasive_action boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

WITH source(
    rule_code,action_code,check_requirement,
    collision_on_success,affected_by_dodge,
    affected_by_evasive_action,heading_path
) AS (
    VALUES
        (
            'vehicle.combat.action.evasive','evasive',
            'vehicle-skill',false,false,false,
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Evasive Action'
        ),
        (
            'vehicle.combat.action.maneuver','maneuver',
            'none',false,false,false,
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Maneuvering'
        ),
        (
            'vehicle.combat.action.ram','ram',
            'vehicle-skill',true,true,true,
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Ram'
        ),
        (
            'vehicle.combat.action.stunt','stunt',
            'vehicle-control',false,false,false,
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Stunt'
        ),
        (
            'vehicle.combat.action.weave','weave',
            'vehicle-skill',false,false,false,
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Weave'
        )
)
INSERT INTO rule_vehicle_combat_action
SELECT rule.rule_id,source.action_code,'significant',
       source.check_requirement,source.collision_on_success,
       source.affected_by_dodge,
       source.affected_by_evasive_action,
       locator.source_locator_id
FROM source
JOIN rule_rule rule USING (rule_code)
JOIN src_locator locator
  ON locator.heading_path=source.heading_path
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.github-v9.1';

CREATE TABLE rule_vehicle_evasive_action (
    action_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    incoming_attack_dm_uses_negative_effect boolean NOT NULL,
    outgoing_attack_dm_uses_negative_effect boolean NOT NULL,
    applies_to_vehicle_attacks boolean NOT NULL,
    applies_to_occupant_attacks boolean NOT NULL,
    duration_basis text NOT NULL CHECK (
        duration_basis='until-next-driver-action'
    )
);

INSERT INTO rule_vehicle_evasive_action
SELECT action_rule_id,true,true,true,true,
       'until-next-driver-action'
FROM rule_vehicle_combat_action
WHERE action_code='evasive';

CREATE TABLE rule_vehicle_maneuver_action (
    action_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    avoids_obvious_obstacles boolean NOT NULL,
    changes_vehicle_relative_arc boolean NOT NULL,
    changes_single_target_arc boolean NOT NULL
);

INSERT INTO rule_vehicle_maneuver_action
SELECT action_rule_id,true,true,true
FROM rule_vehicle_combat_action
WHERE action_code='maneuver';

CREATE TABLE rule_vehicle_ram_action (
    action_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    referee_target_size_bonus_allowed boolean NOT NULL,
    referee_automatic_success_allowed boolean NOT NULL
);

INSERT INTO rule_vehicle_ram_action
SELECT action_rule_id,true,true
FROM rule_vehicle_combat_action
WHERE action_code='ram';

CREATE TABLE rule_vehicle_stunt_action (
    action_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    additional_fire_arcs smallint NOT NULL CHECK (
        additional_fire_arcs>=0
    ),
    additional_fire_arc_duration_rounds smallint NOT NULL CHECK (
        additional_fire_arc_duration_rounds>0
    ),
    maximum_maneuver_equivalents smallint NOT NULL CHECK (
        maximum_maneuver_equivalents>0
    ),
    may_start_task_chain boolean NOT NULL
);

INSERT INTO rule_vehicle_stunt_action
SELECT action_rule_id,1,1,3,true
FROM rule_vehicle_combat_action
WHERE action_code='stunt';

CREATE TABLE rule_vehicle_weave_action (
    action_rule_id bigint PRIMARY KEY REFERENCES
        rule_vehicle_combat_action(action_rule_id),
    minimum_weave_number smallint NOT NULL CHECK (
        minimum_weave_number>0
    ),
    speed_kph_per_maximum_weave_number smallint NOT NULL CHECK (
        speed_kph_per_maximum_weave_number>0
    ),
    maximum_rounding text NOT NULL CHECK (
        maximum_rounding='ceiling'
    ),
    check_dm_per_weave_number smallint NOT NULL CHECK (
        check_dm_per_weave_number<0
    ),
    failure_causes_collision boolean NOT NULL,
    pursuer_must_match_weave_number boolean NOT NULL,
    pursuer_may_break_off boolean NOT NULL
);

INSERT INTO rule_vehicle_weave_action
SELECT action_rule_id,1,20,'ceiling',-1,true,true,true
FROM rule_vehicle_combat_action
WHERE action_code='weave';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code='vehicle.combat.procedure'
               THEN procedure_locator.source_locator_id
           WHEN rule.rule_code=
                'vehicle.combat.occupant-protection'
               THEN protection_locator.source_locator_id
           WHEN rule.rule_code='vehicle.combat.weapon-arcs'
               THEN arc_locator.source_locator_id
           WHEN rule.rule_code='vehicle.combat.collision'
               THEN collision_locator.source_locator_id
           ELSE action_locator.source_locator_id
       END,
       'direct',true
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.github-v9.1'
LEFT JOIN src_locator procedure_locator
  ON procedure_locator.source_work_id=work.source_work_id
 AND procedure_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat'
LEFT JOIN src_locator protection_locator
  ON protection_locator.source_work_id=work.source_work_id
 AND protection_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Closed and Open Vehicles'
LEFT JOIN src_locator arc_locator
  ON arc_locator.source_work_id=work.source_work_id
 AND arc_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle-Mounted Weapons'
LEFT JOIN src_locator collision_locator
  ON collision_locator.source_work_id=work.source_work_id
 AND collision_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Collisions'
LEFT JOIN src_locator action_locator
  ON action_locator.source_work_id=work.source_work_id
 AND action_locator.heading_path=
     CASE rule.rule_code
         WHEN 'vehicle.combat.action.evasive'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Evasive Action'
         WHEN 'vehicle.combat.action.maneuver'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Maneuvering'
         WHEN 'vehicle.combat.action.ram'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Ram'
         WHEN 'vehicle.combat.action.stunt'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Stunt'
         WHEN 'vehicle.combat.action.weave'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Weave'
     END
WHERE rule.rule_code LIKE 'vehicle.combat.%';
