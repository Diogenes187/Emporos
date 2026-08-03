INSERT INTO src_artifact(
    source_work_id,artifact_kind,source_uri,source_revision,checksum_sha256,
    media_type,local_role,captured_at
)
SELECT source_work_id,'web_page',
       'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-space-combat/',
       'concordance-2026-08-01',
       'fe749015527a02df2f4447d733c7cd3cb8556b4006a99627830fc5236f25b3bc',
       'text/html','governing',clock_timestamp()
FROM src_work WHERE work_code='cepheus-engine.ogn'
ON CONFLICT DO NOTHING;

INSERT INTO src_locator(
    source_work_id,source_artifact_id,locator_type,heading_path,
    display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
       'Space Combat > Initiative',
       CASE work.work_code
         WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: Initiative'
         ELSE 'Cepheus Engine v9.1, Space Combat: Initiative'
       END
FROM src_artifact artifact
JOIN src_work work USING(source_work_id)
WHERE (work.work_code='cepheus-engine.ogn'
       AND artifact.source_uri LIKE '%cepheus-engine-space-combat/')
   OR (work.work_code='cepheus-engine.github-v9.1'
       AND artifact.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (
    SELECT content_package_id FROM sys_content_package
    WHERE package_code='cepheus-engine'
)
INSERT INTO rule_rule(
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT content_package_id,'combat.space.initiative',
       'Space Combat Initiative','combat','approved',
       'Initial vessel initiative, hostile Thrust comparison, Tactics scope, and awareness.'
FROM package;

CREATE TABLE rule_space_combat_initiative (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    dice_count smallint NOT NULL CHECK (dice_count=2),
    die_sides smallint NOT NULL CHECK (die_sides=6),
    awareness_fixed_total smallint NOT NULL CHECK (awareness_fixed_total=12),
    awareness_uses_pilot_dexterity boolean NOT NULL,
    compare_highest_hostile_thrust boolean NOT NULL,
    higher_thrust_modifier smallint NOT NULL CHECK (higher_thrust_modifier=1),
    vessel_tactics_scope boolean NOT NULL,
    fleet_tactics_scope boolean NOT NULL,
    tactics_scopes_stack boolean NOT NULL
);

INSERT INTO rule_space_combat_initiative
SELECT rule_id,2,6,12,true,true,1,true,true,false
FROM rule_rule WHERE rule_code='combat.space.initiative';

INSERT INTO rule_interpretation(
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule_id,'agreed_interpretation','CE-SC-001',
       'Higher Thrust compares with the fastest hostile vessel; vessel and fleet Tactics scopes do not stack; awareness uses the assigned pilot Dexterity DM.'
FROM rule_rule WHERE rule_code='combat.space.initiative';

INSERT INTO src_record_provenance(
    rule_id,content_package_id,source_locator_id,provenance_class,
    is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code WHEN 'cepheus-engine.ogn' THEN 'direct'
            ELSE 'corroborating' END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule
CROSS JOIN src_locator locator
JOIN src_work work USING(source_work_id)
WHERE rule.rule_code='combat.space.initiative'
  AND locator.heading_path='Space Combat > Initiative'
  AND work.work_code IN ('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_tactics_initiative_receipt (
    tactics_initiative_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    force_id bigint NOT NULL,
    senc_vessel_id bigint,
    captain_assignment_id bigint NOT NULL,
    captain_ship_id bigint NOT NULL,
    task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
    tactics_effect smallint NOT NULL,
    scope_kind text NOT NULL CHECK (scope_kind IN ('vessel','fleet')),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (force_id,engagement_id,campaign_id)
        REFERENCES senc_force(force_id,engagement_id,campaign_id),
    FOREIGN KEY (senc_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
    FOREIGN KEY (captain_assignment_id,captain_ship_id,campaign_id)
        REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
    CHECK ((scope_kind='fleet' AND senc_vessel_id IS NULL)
        OR (scope_kind='vessel' AND senc_vessel_id IS NOT NULL))
);

CREATE UNIQUE INDEX senc_one_fleet_tactics_receipt
    ON senc_tactics_initiative_receipt(engagement_id,force_id)
    WHERE scope_kind='fleet';
CREATE UNIQUE INDEX senc_one_vessel_tactics_receipt
    ON senc_tactics_initiative_receipt(engagement_id,senc_vessel_id)
    WHERE scope_kind='vessel';

CREATE TABLE senc_vessel_initiative_receipt (
    vessel_initiative_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    senc_vessel_id bigint NOT NULL,
    force_id bigint NOT NULL,
    ship_id bigint NOT NULL,
    aware_at_start boolean NOT NULL,
    die_one smallint CHECK (die_one BETWEEN 1 AND 6),
    die_two smallint CHECK (die_two BETWEEN 1 AND 6),
    base_total smallint NOT NULL CHECK (base_total BETWEEN 2 AND 12),
    pilot_assignment_id bigint,
    pilot_dexterity_value smallint,
    pilot_dexterity_modifier smallint NOT NULL,
    vessel_thrust_snapshot smallint NOT NULL CHECK (vessel_thrust_snapshot>=0),
    highest_hostile_thrust_snapshot smallint NOT NULL CHECK (highest_hostile_thrust_snapshot>=0),
    higher_thrust_modifier smallint NOT NULL CHECK (higher_thrust_modifier IN (0,1)),
    tactics_initiative_receipt_id bigint REFERENCES senc_tactics_initiative_receipt,
    tactics_effect smallint NOT NULL,
    initiative_total integer NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    FOREIGN KEY (senc_vessel_id,engagement_id,campaign_id)
        REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
    FOREIGN KEY (force_id,engagement_id,campaign_id)
        REFERENCES senc_force(force_id,engagement_id,campaign_id),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    FOREIGN KEY (pilot_assignment_id,ship_id,campaign_id)
        REFERENCES ship_crew_assignment(crew_assignment_id,ship_id,campaign_id),
    UNIQUE (engagement_id,senc_vessel_id),
    CHECK ((aware_at_start AND die_one IS NULL AND die_two IS NULL
            AND base_total=12 AND pilot_assignment_id IS NOT NULL
            AND pilot_dexterity_value IS NOT NULL)
        OR (NOT aware_at_start AND die_one IS NOT NULL AND die_two IS NOT NULL
            AND base_total=die_one+die_two AND pilot_assignment_id IS NULL
            AND pilot_dexterity_value IS NULL
            AND pilot_dexterity_modifier=0)),
    CHECK (initiative_total=base_total+pilot_dexterity_modifier
          +higher_thrust_modifier+tactics_effect)
);

CREATE FUNCTION senc_validate_tactics_initiative_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    position text;
    duty text;
    vessel_force bigint;
    task_actor bigint;
    captain_actor bigint;
    task_effect smallint;
BEGIN
    SELECT definition.position_code,assignment.duty_status,assignment.actor_id
    INTO position,duty,captain_actor
    FROM ship_crew_assignment assignment
    JOIN ship_crew_position position_state USING(ship_crew_position_id)
    JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
    WHERE assignment.crew_assignment_id=NEW.captain_assignment_id;
    SELECT actor_id,effect INTO task_actor,task_effect
    FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
    IF position<>'master' OR duty<>'active' OR task_actor<>captain_actor
       OR task_effect<>NEW.tactics_effect THEN
        RAISE EXCEPTION 'Initiative Tactics receipt requires the active ship master and matching task Effect'
            USING ERRCODE='23514';
    END IF;
    SELECT force_id INTO vessel_force FROM senc_vessel
    WHERE senc_vessel_id=NEW.senc_vessel_id;
    IF NEW.scope_kind='vessel' AND vessel_force<>NEW.force_id THEN
        RAISE EXCEPTION 'Vessel Tactics scope must remain within its force'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER senc_tactics_initiative_valid
BEFORE INSERT OR UPDATE ON senc_tactics_initiative_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_tactics_initiative_receipt();

CREATE FUNCTION senc_validate_vessel_initiative_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    vessel senc_vessel%ROWTYPE;
    hostile_max smallint;
    expected_tactics smallint:=0;
    tactics_scope text;
    tactics_force bigint;
    tactics_vessel bigint;
    pilot_position text;
    pilot_duty text;
    pilot_actor bigint;
    dex_rule bigint;
    dex_value smallint;
    dex_modifier smallint;
BEGIN
    SELECT * INTO STRICT vessel FROM senc_vessel
    WHERE senc_vessel_id=NEW.senc_vessel_id;
    SELECT max(hostile.thrust_current) INTO hostile_max
    FROM senc_vessel hostile
    WHERE hostile.engagement_id=NEW.engagement_id
      AND hostile.force_id<>vessel.force_id
      AND hostile.vessel_status='engaged';
    IF vessel.engagement_id<>NEW.engagement_id
       OR vessel.campaign_id<>NEW.campaign_id
       OR vessel.force_id<>NEW.force_id OR vessel.ship_id<>NEW.ship_id
       OR hostile_max IS NULL
       OR NEW.vessel_thrust_snapshot<>vessel.thrust_current
       OR NEW.highest_hostile_thrust_snapshot<>hostile_max
       OR NEW.higher_thrust_modifier<>(
          CASE WHEN vessel.thrust_current>hostile_max THEN 1 ELSE 0 END
       ) THEN
        RAISE EXCEPTION 'Vessel initiative hostile-Thrust snapshot is inconsistent'
            USING ERRCODE='23514';
    END IF;
    IF NEW.tactics_initiative_receipt_id IS NOT NULL THEN
        SELECT tactics_effect,scope_kind,force_id,senc_vessel_id
        INTO expected_tactics,tactics_scope,tactics_force,tactics_vessel
        FROM senc_tactics_initiative_receipt
        WHERE tactics_initiative_receipt_id=NEW.tactics_initiative_receipt_id;
        IF tactics_force<>NEW.force_id
           OR (tactics_scope='vessel' AND tactics_vessel<>NEW.senc_vessel_id) THEN
            RAISE EXCEPTION 'Initiative Tactics scope is inconsistent'
                USING ERRCODE='23514';
        END IF;
    END IF;
    IF NEW.tactics_effect<>expected_tactics THEN
        RAISE EXCEPTION 'Initiative Tactics Effect snapshot is inconsistent'
            USING ERRCODE='23514';
    END IF;
    IF NEW.aware_at_start THEN
        SELECT definition.position_code,assignment.duty_status,assignment.actor_id
        INTO pilot_position,pilot_duty,pilot_actor
        FROM ship_crew_assignment assignment
        JOIN ship_crew_position position_state USING(ship_crew_position_id)
        JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
        WHERE assignment.crew_assignment_id=NEW.pilot_assignment_id;
        SELECT rule_id INTO STRICT dex_rule FROM rule_rule
        WHERE rule_code='characteristic.dexterity';
        SELECT current_value INTO dex_value FROM actor_characteristic
        WHERE actor_id=pilot_actor AND characteristic_rule_id=dex_rule;
        SELECT modifier INTO dex_modifier
        FROM rule_characteristic_modifier_band
        WHERE characteristic_rule_id=dex_rule
          AND score_range @> dex_value;
        IF pilot_position<>'pilot' OR pilot_duty<>'active'
           OR dex_value IS NULL OR NEW.pilot_dexterity_value<>dex_value
           OR NEW.pilot_dexterity_modifier<>dex_modifier THEN
            RAISE EXCEPTION 'Aware initiative requires the active pilot Dexterity snapshot'
                USING ERRCODE='23514';
        END IF;
    END IF;
    UPDATE senc_vessel SET initiative_current=NEW.initiative_total
    WHERE senc_vessel_id=NEW.senc_vessel_id;
    RETURN NEW;
END $$;

CREATE TRIGGER senc_vessel_initiative_valid
BEFORE INSERT ON senc_vessel_initiative_receipt
FOR EACH ROW EXECUTE FUNCTION senc_validate_vessel_initiative_receipt();

CREATE FUNCTION senc_reject_initiative_receipt_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Space combat initiative receipts are immutable';
END $$;
CREATE TRIGGER senc_tactics_initiative_immutable
BEFORE UPDATE OR DELETE ON senc_tactics_initiative_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_initiative_receipt_mutation();
CREATE TRIGGER senc_vessel_initiative_immutable
BEFORE UPDATE OR DELETE ON senc_vessel_initiative_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_initiative_receipt_mutation();
