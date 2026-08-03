INSERT INTO rule_interpretation(
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule_id,'agreed_interpretation','CE-SC-008',
 'Raymond approved applying the unqualified Hull overflow rule to small craft: when Hull is already 0, a further Hull result routes to the location in the same roll row of the Internal vessel column.'
FROM rule_rule WHERE rule_code='combat.space.hit-locations';

CREATE TABLE senc_ship_system_damage_state (
    ship_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    system_code text NOT NULL CHECK (system_code IN (
        'turret','bay','j-drive','m-drive','power-plant','sensors',
        'bridge','fuel','hold'
    )),
    system_instance smallint NOT NULL DEFAULT 1 CHECK (system_instance>0),
    hit_count smallint NOT NULL DEFAULT 0 CHECK (hit_count BETWEEN 0 AND 3),
    system_status text NOT NULL DEFAULT 'operational' CHECK (
        system_status IN ('operational','damaged','disabled','destroyed')
    ),
    attack_dm smallint NOT NULL DEFAULT 0 CHECK (attack_dm BETWEEN -2 AND 0),
    sensor_dm smallint NOT NULL DEFAULT 0 CHECK (sensor_dm BETWEEN -2 AND 0),
    concurrency_version bigint NOT NULL DEFAULT 1 CHECK (concurrency_version>0),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (ship_id,system_code,system_instance),
    FOREIGN KEY (ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
    CHECK ((hit_count=0)=(system_status='operational')),
    CHECK (system_code IN ('turret','bay') OR system_instance=1),
    CHECK (system_code IN ('turret','bay') OR attack_dm=0),
    CHECK (system_code='sensors' OR sensor_dm=0)
);

CREATE OR REPLACE FUNCTION senc_validate_ship_system_damage_state()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE class_id bigint; mount_total integer;
BEGIN
    SELECT ship_class_rule_id INTO STRICT class_id
    FROM ship_ship WHERE ship_id=NEW.ship_id AND campaign_id=NEW.campaign_id;
    IF NEW.system_code IN ('turret','bay') THEN
        SELECT coalesce(sum(selected.mount_count),0) INTO mount_total
        FROM ship_class_weapon_mount selected
        JOIN rule_ship_weapon_mount definition USING (mount_code)
        WHERE selected.ship_class_rule_id=class_id
          AND definition.mount_kind=NEW.system_code;
        IF NEW.system_instance>mount_total THEN
            RAISE EXCEPTION 'System damage instance does not identify an installed turret or bay'
                USING ERRCODE='23514';
        END IF;
    ELSIF NEW.system_code='j-drive'
          AND NOT EXISTS (
              SELECT 1 FROM ship_class_drive
              WHERE ship_class_rule_id=class_id AND drive_kind='jump'
          ) THEN
        RAISE EXCEPTION 'System damage state requires an installed jump drive'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER senc_ship_system_damage_state_valid
BEFORE INSERT OR UPDATE ON senc_ship_system_damage_state
FOR EACH ROW EXECUTE FUNCTION senc_validate_ship_system_damage_state();
