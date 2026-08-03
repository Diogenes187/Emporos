INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT source_work_id,'repository_file','src/book2/space-combat.md',
       '0839018902355215fb8148f0b4ce1b1f8e011080',
       36818,
       'c058b6f6a481e7a85ca33056aea4f20ec5f0928ca749a3f16b42cf401450f8c2',
       'text/markdown','governing'
FROM src_work
WHERE work_code='cepheus-engine.github-v9.1';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Space Combat > Range','Cepheus Engine v9.1, Space Combat: Range'),
        ('Space Combat > Crew Positions','Cepheus Engine v9.1, Space Combat: Crew Positions'),
        ('Space Combat > The Space Combat Turn','Cepheus Engine v9.1, Space Combat: Turn'),
        ('Space Combat > Actions','Cepheus Engine v9.1, Space Combat: Actions'),
        ('Space Combat > Damage','Cepheus Engine v9.1, Space Combat: Damage')
) source(heading_path,display_citation)
WHERE artifact.source_uri='src/book2/space-combat.md';

CREATE TABLE rule_space_combat_procedure (
    procedure_code text PRIMARY KEY,
    turn_seconds integer NOT NULL CHECK (turn_seconds>0),
    initiative_dice_count smallint NOT NULL CHECK (
        initiative_dice_count>0
    ),
    initiative_die_sides smallint NOT NULL CHECK (
        initiative_die_sides>1
    ),
    higher_thrust_modifier smallint NOT NULL,
    significant_actions_per_crew smallint NOT NULL CHECK (
        significant_actions_per_crew>0
    ),
    minor_actions_with_significant smallint NOT NULL CHECK (
        minor_actions_with_significant>=0
    ),
    minor_actions_without_significant smallint NOT NULL CHECK (
        minor_actions_without_significant>
        minor_actions_with_significant
    ),
    initiative_rerolled_each_round boolean NOT NULL,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_space_combat_procedure
SELECT 'cepheus-standard',1000,2,6,1,1,1,3,false,
       source_locator_id
FROM src_locator
WHERE heading_path='Space Combat > The Space Combat Turn';

CREATE TABLE rule_space_range_band (
    range_band_code text PRIMARY KEY CHECK (
        range_band_code IN (
            'distant','very_long','long','medium',
            'short','close','adjacent','docked'
        )
    ),
    display_order smallint NOT NULL UNIQUE CHECK (display_order>0),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_space_range_band
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('docked',1),('adjacent',2),('close',3),('short',4),
        ('medium',5),('long',6),('very_long',7),('distant',8)
) source(range_band_code,display_order)
JOIN src_locator locator ON locator.heading_path='Space Combat > Range';

CREATE TABLE rule_space_combat_action (
    action_code text PRIMARY KEY CHECK (
        action_code ~ '^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$'
    ),
    action_name text NOT NULL UNIQUE CHECK (btrim(action_name)<>''),
    action_kind text NOT NULL CHECK (
        action_kind IN ('minor','significant','reaction','variable')
    ),
    crew_role text NOT NULL CHECK (btrim(crew_role)<>''),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id)
);

INSERT INTO rule_space_combat_action
SELECT source.*,locator.source_locator_id
FROM (
    VALUES
        ('change-positions','Change Positions','minor','anyone'),
        ('personal-action','Personal Action','minor','anyone'),
        ('reload-weapons','Reload Weapons System','significant','anyone'),
        ('miscellaneous','Miscellaneous','variable','anyone'),
        ('coordinate-crew','Coordinate Crew','significant','captain'),
        ('increase-initiative','Increase Initiative','significant','captain'),
        ('boarding-action','Boarding Action','significant','security_or_marine'),
        ('repair-system','Repair Damaged System','significant','damage_control'),
        ('fire-sand','Fire Sand','reaction','gunner'),
        ('point-defense','Point Defense','reaction','gunner'),
        ('trigger-screens','Trigger Screens','reaction','gunner'),
        ('attack','Attack','significant','gunner'),
        ('calculate-jump','Calculate Jump Plot','significant','navigator'),
        ('range-check','Range Check','significant','navigator'),
        ('adjust-speed','Adjust Speed','minor','pilot'),
        ('maintain-course','Maintain Course','minor','pilot'),
        ('dodge','Dodge Incoming Fire','reaction','pilot'),
        ('avoid-collision','Avoid Collision','significant','pilot'),
        ('break-pursuit','Break Pursuit','significant','pilot'),
        ('dock','Dock With Another Vessel','significant','pilot'),
        ('evasive-maneuvers','Evasive Maneuvers','significant','pilot'),
        ('line-up-shot','Line Up The Shot','significant','pilot'),
        ('pursuit','Pursuit','significant','pilot'),
        ('ram','Ram','significant','pilot'),
        ('electronic-warfare','Electronic Warfare','significant','sensors_operator'),
        ('intercept-comms','Intercept Enemy Communications','significant','sensors_operator'),
        ('maintain-comms','Maintain Communications','significant','sensors_operator'),
        ('sensor-targeting','Sensor Targeting','significant','sensors_operator')
) source(action_code,action_name,action_kind,crew_role)
JOIN src_locator locator ON locator.heading_path='Space Combat > Actions';

CREATE TABLE senc_engagement (
    engagement_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    encounter_id bigint NOT NULL UNIQUE,
    campaign_id bigint NOT NULL,
    procedure_code text NOT NULL REFERENCES
        rule_space_combat_procedure(procedure_code),
    engagement_status text NOT NULL DEFAULT 'forming' CHECK (
        engagement_status IN (
            'forming','active','resolved','escaped','aborted'
        )
    ),
    current_round integer CHECK (current_round>0),
    started_at timestamptz,
    ended_at timestamptz,
    FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    UNIQUE (engagement_id,campaign_id),
    CHECK (
        (engagement_status='forming'
         AND started_at IS NULL AND ended_at IS NULL)
        OR (engagement_status='active'
            AND started_at IS NOT NULL AND ended_at IS NULL)
        OR (engagement_status IN ('resolved','escaped','aborted')
            AND ended_at IS NOT NULL)
    )
);

CREATE TABLE senc_force (
    force_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    side_code text NOT NULL CHECK (btrim(side_code)<>''),
    force_name text NOT NULL CHECK (btrim(force_name)<>''),
    FOREIGN KEY (engagement_id,campaign_id)
        REFERENCES senc_engagement(engagement_id,campaign_id),
    UNIQUE (force_id,engagement_id,campaign_id),
    UNIQUE (engagement_id,side_code)
);

CREATE TABLE senc_vessel (
    senc_vessel_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    force_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    initiative_current integer,
    speed_current numeric NOT NULL DEFAULT 0 CHECK (speed_current>=0),
    thrust_current smallint NOT NULL DEFAULT 0 CHECK (thrust_current>=0),
    vessel_status text NOT NULL DEFAULT 'engaged' CHECK (
        vessel_status IN (
            'engaged','disabled','destroyed','escaped','surrendered'
        )
    ),
    joined_round integer CHECK (joined_round>0),
    ended_round integer CHECK (ended_round>0),
    FOREIGN KEY (force_id,engagement_id,campaign_id)
        REFERENCES senc_force(force_id,engagement_id,campaign_id),
    FOREIGN KEY (ship_id,campaign_id)
        REFERENCES ship_ship(ship_id,campaign_id),
    UNIQUE (senc_vessel_id,engagement_id,campaign_id),
    UNIQUE (engagement_id,ship_id),
    CHECK (ended_round IS NULL OR ended_round>=joined_round)
);

CREATE TABLE senc_vessel_range (
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    first_vessel_id bigint NOT NULL,
    second_vessel_id bigint NOT NULL,
    range_band_code text NOT NULL REFERENCES
        rule_space_range_band(range_band_code),
    range_version bigint NOT NULL DEFAULT 1 CHECK (range_version>0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (engagement_id,first_vessel_id,second_vessel_id),
    FOREIGN KEY (first_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        ),
    FOREIGN KEY (second_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        ),
    CHECK (first_vessel_id<second_vessel_id)
);

CREATE TABLE senc_round (
    space_combat_round_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    round_number integer NOT NULL CHECK (round_number>0),
    round_status text NOT NULL DEFAULT 'open' CHECK (
        round_status IN ('open','resolving_damage','completed','aborted')
    ),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (engagement_id,campaign_id)
        REFERENCES senc_engagement(engagement_id,campaign_id),
    UNIQUE (space_combat_round_id,engagement_id,campaign_id),
    UNIQUE (engagement_id,round_number),
    CHECK (
        (round_status IN ('open','resolving_damage') AND ended_at IS NULL)
        OR (round_status IN ('completed','aborted') AND ended_at IS NOT NULL)
    )
);

CREATE TABLE senc_crew_turn (
    crew_turn_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_combat_round_id bigint NOT NULL,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    senc_vessel_id bigint NOT NULL,
    crew_assignment_id bigint NOT NULL,
    initiative_at_action integer NOT NULL,
    significant_actions_used smallint NOT NULL DEFAULT 0 CHECK (
        significant_actions_used BETWEEN 0 AND 1
    ),
    minor_actions_used smallint NOT NULL DEFAULT 0 CHECK (
        minor_actions_used BETWEEN 0 AND 3
    ),
    turn_status text NOT NULL DEFAULT 'pending' CHECK (
        turn_status IN ('pending','acting','completed','forfeited')
    ),
    FOREIGN KEY (space_combat_round_id,engagement_id,campaign_id)
        REFERENCES senc_round(
            space_combat_round_id,engagement_id,campaign_id
        ),
    FOREIGN KEY (senc_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        ),
    FOREIGN KEY (crew_assignment_id)
        REFERENCES ship_crew_assignment(crew_assignment_id),
    UNIQUE (space_combat_round_id,crew_assignment_id),
    UNIQUE (crew_turn_id,space_combat_round_id,engagement_id,campaign_id),
    CHECK (
        significant_actions_used=0 OR minor_actions_used<=1
    )
);

CREATE TABLE senc_action (
    space_combat_action_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    crew_turn_id bigint NOT NULL,
    space_combat_round_id bigint NOT NULL,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    action_order smallint NOT NULL CHECK (action_order>0),
    action_code text NOT NULL REFERENCES
        rule_space_combat_action(action_code),
    target_vessel_id bigint,
    action_status text NOT NULL DEFAULT 'declared' CHECK (
        action_status IN (
            'declared','resolved','failed','cancelled','interrupted'
        )
    ),
    check_total integer,
    target_number integer,
    effect integer,
    source_command_id bigint REFERENCES cmd_command(command_id),
    declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at timestamptz,
    FOREIGN KEY (
        crew_turn_id,space_combat_round_id,engagement_id,campaign_id
    ) REFERENCES senc_crew_turn(
        crew_turn_id,space_combat_round_id,engagement_id,campaign_id
    ),
    FOREIGN KEY (target_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        ),
    UNIQUE (crew_turn_id,action_order),
    UNIQUE (space_combat_action_id,engagement_id,campaign_id),
    CHECK (
        (action_status='declared' AND resolved_at IS NULL)
        OR (action_status<>'declared' AND resolved_at IS NOT NULL)
    )
);

CREATE TABLE senc_reaction (
    reaction_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    triggering_action_id bigint NOT NULL,
    reacting_action_id bigint NOT NULL UNIQUE,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    reaction_order smallint NOT NULL CHECK (reaction_order>0),
    FOREIGN KEY (triggering_action_id,engagement_id,campaign_id)
        REFERENCES senc_action(
            space_combat_action_id,engagement_id,campaign_id
        ),
    FOREIGN KEY (reacting_action_id,engagement_id,campaign_id)
        REFERENCES senc_action(
            space_combat_action_id,engagement_id,campaign_id
        ),
    UNIQUE (triggering_action_id,reaction_order),
    CHECK (triggering_action_id<>reacting_action_id)
);

CREATE TABLE senc_attack (
    attack_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    space_combat_action_id bigint NOT NULL UNIQUE,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    attacker_vessel_id bigint NOT NULL,
    target_vessel_id bigint NOT NULL,
    weapon_rule_id bigint NOT NULL REFERENCES
        ship_weapon_definition(weapon_rule_id),
    attack_total integer NOT NULL,
    target_number integer NOT NULL,
    effect integer NOT NULL,
    hit boolean NOT NULL,
    rolled_damage integer NOT NULL CHECK (rolled_damage>=0),
    net_damage integer NOT NULL CHECK (net_damage>=0),
    FOREIGN KEY (space_combat_action_id,engagement_id,campaign_id)
        REFERENCES senc_action(
            space_combat_action_id,engagement_id,campaign_id
        ),
    FOREIGN KEY (attacker_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        ),
    FOREIGN KEY (target_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        ),
    UNIQUE (attack_id,engagement_id,campaign_id),
    CHECK (attacker_vessel_id<>target_vessel_id),
    CHECK ((hit AND rolled_damage>0) OR (NOT hit AND net_damage=0)),
    CHECK (net_damage<=rolled_damage)
);

CREATE TABLE senc_attack_damage (
    attack_id bigint NOT NULL,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    ship_damage_id bigint NOT NULL UNIQUE,
    allocation_order smallint NOT NULL CHECK (allocation_order>0),
    allocated_damage smallint NOT NULL CHECK (allocated_damage>0),
    FOREIGN KEY (attack_id,engagement_id,campaign_id)
        REFERENCES senc_attack(attack_id,engagement_id,campaign_id),
    FOREIGN KEY (ship_damage_id)
        REFERENCES ship_damage(ship_damage_id),
    PRIMARY KEY (attack_id,allocation_order)
);

CREATE TABLE senc_missile_salvo (
    missile_salvo_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    launch_attack_id bigint NOT NULL UNIQUE,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    target_vessel_id bigint NOT NULL,
    missile_count smallint NOT NULL CHECK (missile_count>0),
    smart_missiles boolean NOT NULL,
    launched_round integer NOT NULL CHECK (launched_round>0),
    impact_round integer NOT NULL CHECK (impact_round>launched_round),
    missiles_remaining smallint NOT NULL CHECK (
        missiles_remaining>=0 AND missiles_remaining<=missile_count
    ),
    salvo_status text NOT NULL DEFAULT 'in_flight' CHECK (
        salvo_status IN (
            'in_flight','impacted','destroyed','disabled','missed'
        )
    ),
    FOREIGN KEY (launch_attack_id,engagement_id,campaign_id)
        REFERENCES senc_attack(attack_id,engagement_id,campaign_id),
    FOREIGN KEY (target_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(
            senc_vessel_id,engagement_id,campaign_id
        )
);
