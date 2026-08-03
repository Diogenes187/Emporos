CREATE TABLE venc_attack (
    vehicle_attack_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    vehicle_crew_turn_id bigint NOT NULL,
    vehicle_combat_round_id bigint NOT NULL,
    vehicle_engagement_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    attacker_vehicle_id bigint NOT NULL,
    target_vehicle_id bigint NOT NULL,
    class_armament_mount_id bigint NOT NULL,
    weapon_slot_order smallint NOT NULL CHECK (
        weapon_slot_order>0
    ),
    weapon_rule_id bigint NOT NULL REFERENCES
        rule_vehicle_weapon_definition(weapon_rule_id),
    fire_arc_code text NOT NULL REFERENCES
        rule_vehicle_weapon_arc(arc_code),
    range_profile_code text NOT NULL REFERENCES
        rule_vehicle_weapon_range_profile(range_profile_code),
    target_range_code text NOT NULL REFERENCES
        rule_vehicle_weapon_target_range(target_range_code),
    difficulty_rule_id bigint NOT NULL REFERENCES
        rule_difficulty(rule_id),
    attack_roll integer NOT NULL,
    attack_total integer NOT NULL,
    target_number integer NOT NULL,
    effect integer NOT NULL,
    hit boolean NOT NULL,
    rolled_damage integer NOT NULL CHECK (rolled_damage>=0),
    effect_damage integer NOT NULL CHECK (effect_damage>=0),
    raw_damage integer NOT NULL CHECK (raw_damage>=0),
    armor_rating_used smallint NOT NULL CHECK (
        armor_rating_used>=0
    ),
    penetrating_damage integer NOT NULL CHECK (
        penetrating_damage>=0
    ),
    damage_band_code text NOT NULL REFERENCES
        rule_vehicle_damage_band(damage_band_code),
    source_command_id bigint REFERENCES cmd_command(command_id),
    first_attack_draw_order smallint CHECK (
        first_attack_draw_order>0
    ),
    attack_draw_count smallint NOT NULL DEFAULT 0 CHECK (
        attack_draw_count>=0
    ),
    first_damage_draw_order smallint CHECK (
        first_damage_draw_order>0
    ),
    damage_draw_count smallint NOT NULL DEFAULT 0 CHECK (
        damage_draw_count>=0
    ),
    finalized boolean NOT NULL DEFAULT false,
    declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finalized_at timestamptz,
    FOREIGN KEY (
        vehicle_crew_turn_id,vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ) REFERENCES venc_crew_turn(
        vehicle_crew_turn_id,vehicle_combat_round_id,
        vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        attacker_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        target_vehicle_id,vehicle_engagement_id,campaign_id
    ) REFERENCES venc_vehicle(
        venc_vehicle_id,vehicle_engagement_id,campaign_id
    ),
    FOREIGN KEY (
        class_armament_mount_id,weapon_slot_order
    ) REFERENCES vehicle_class_armament_weapon(
        class_armament_mount_id,slot_order
    ),
    UNIQUE (vehicle_attack_id,vehicle_engagement_id,campaign_id),
    CHECK (attacker_vehicle_id<>target_vehicle_id),
    CHECK (effect=attack_total-target_number),
    CHECK (hit=(attack_total>=target_number)),
    CHECK (
        (hit AND raw_damage=rolled_damage+effect_damage)
        OR (
            NOT hit AND rolled_damage=0
            AND effect_damage=0 AND raw_damage=0
        )
    ),
    CHECK (
        penetrating_damage=
        greatest(raw_damage-armor_rating_used,0)
    ),
    CHECK (
        (
            source_command_id IS NULL
            AND first_attack_draw_order IS NULL
            AND attack_draw_count=0
            AND first_damage_draw_order IS NULL
            AND damage_draw_count=0
        )
        OR (
            source_command_id IS NOT NULL
            AND first_attack_draw_order IS NOT NULL
            AND attack_draw_count>0
            AND (
                (
                    hit
                    AND first_damage_draw_order IS NOT NULL
                    AND damage_draw_count>0
                )
                OR (
                    NOT hit
                    AND first_damage_draw_order IS NULL
                    AND damage_draw_count=0
                )
            )
        )
    ),
    CHECK (
        (finalized AND finalized_at IS NOT NULL)
        OR (NOT finalized AND finalized_at IS NULL)
    )
);

CREATE TABLE venc_attack_modifier (
    vehicle_attack_id bigint NOT NULL REFERENCES
        venc_attack(vehicle_attack_id),
    modifier_order smallint NOT NULL CHECK (modifier_order>0),
    modifier_code text NOT NULL CHECK (
        modifier_code IN (
            'skill','characteristic','weapon',
            'range-difficulty','vehicle-size',
            'target-movement','attacker-movement',
            'attacker-evasion','target-evasion',
            'circumstance'
        )
    ),
    modifier_value integer NOT NULL,
    source_kind text NOT NULL CHECK (
        source_kind IN (
            'actor','weapon','range-matrix','vehicle',
            'action-resolution','referee'
        )
    ),
    source_reference text CHECK (
        source_reference IS NULL
        OR btrim(source_reference)<>''
    ),
    PRIMARY KEY (vehicle_attack_id,modifier_order),
    UNIQUE (vehicle_attack_id,modifier_code)
);

CREATE TABLE venc_attack_damage_packet (
    vehicle_attack_id bigint NOT NULL REFERENCES
        venc_attack(vehicle_attack_id),
    packet_order smallint NOT NULL CHECK (packet_order>0),
    location_hit_count smallint NOT NULL CHECK (
        location_hit_count BETWEEN 1 AND 3
    ),
    packet_quantity smallint NOT NULL CHECK (packet_quantity>0),
    PRIMARY KEY (vehicle_attack_id,packet_order)
);

CREATE OR REPLACE FUNCTION venc_validate_attack_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    attacker_class bigint;
    mount_class bigint;
    selected_weapon bigint;
    weapon_range text;
    matrix_difficulty bigint;
BEGIN
    SELECT vehicle.vehicle_class_rule_id
    INTO attacker_class
    FROM venc_vehicle participant
    JOIN vehicle_vehicle vehicle
      ON vehicle.vehicle_id=participant.vehicle_id
     AND vehicle.campaign_id=participant.campaign_id
    WHERE participant.venc_vehicle_id=NEW.attacker_vehicle_id
      AND participant.vehicle_engagement_id=
          NEW.vehicle_engagement_id
      AND participant.campaign_id=NEW.campaign_id;

    SELECT mount.vehicle_class_rule_id,
           selection.weapon_rule_id,
           weapon.range_profile_code
    INTO mount_class,selected_weapon,weapon_range
    FROM vehicle_class_armament_weapon selection
    JOIN vehicle_class_armament_mount mount
      USING (class_armament_mount_id)
    JOIN rule_vehicle_weapon_definition weapon
      ON weapon.weapon_rule_id=selection.weapon_rule_id
    WHERE selection.class_armament_mount_id=
          NEW.class_armament_mount_id
      AND selection.slot_order=NEW.weapon_slot_order;

    SELECT difficulty_rule_id
    INTO matrix_difficulty
    FROM rule_vehicle_weapon_range_difficulty
    WHERE range_profile_code=NEW.range_profile_code
      AND target_range_code=NEW.target_range_code;

    IF attacker_class<>mount_class
       OR NEW.weapon_rule_id<>selected_weapon
       OR NEW.range_profile_code<>weapon_range
       OR NEW.difficulty_rule_id IS DISTINCT FROM
          matrix_difficulty THEN
        RAISE EXCEPTION
            'Vehicle attack weapon or range identity is inconsistent'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER venc_attack_identity_valid
BEFORE INSERT ON venc_attack
FOR EACH ROW EXECUTE FUNCTION venc_validate_attack_identity();

CREATE OR REPLACE FUNCTION venc_validate_attack_finalization()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    modifier_total integer;
    band_matches boolean;
    packet_mismatch boolean;
BEGIN
    IF NOT OLD.finalized AND NEW.finalized THEN
        SELECT coalesce(sum(modifier_value),0)
        INTO modifier_total
        FROM venc_attack_modifier
        WHERE vehicle_attack_id=NEW.vehicle_attack_id;

        SELECT NEW.penetrating_damage<@damage_range
        INTO band_matches
        FROM rule_vehicle_damage_band
        WHERE damage_band_code=NEW.damage_band_code;

        SELECT EXISTS (
            (
                SELECT packet_order,location_hit_count,
                       packet_quantity
                FROM rule_vehicle_damage_band_packet
                WHERE damage_band_code=NEW.damage_band_code
                EXCEPT
                SELECT packet_order,location_hit_count,
                       packet_quantity
                FROM venc_attack_damage_packet
                WHERE vehicle_attack_id=NEW.vehicle_attack_id
            )
            UNION ALL
            (
                SELECT packet_order,location_hit_count,
                       packet_quantity
                FROM venc_attack_damage_packet
                WHERE vehicle_attack_id=NEW.vehicle_attack_id
                EXCEPT
                SELECT packet_order,location_hit_count,
                       packet_quantity
                FROM rule_vehicle_damage_band_packet
                WHERE damage_band_code=NEW.damage_band_code
            )
        ) INTO packet_mismatch;

        IF NEW.attack_total<>NEW.attack_roll+modifier_total
           OR NOT coalesce(band_matches,false)
           OR packet_mismatch
           OR NEW.finalized_at IS NULL THEN
            RAISE EXCEPTION
                'Vehicle attack receipt does not reconcile'
                USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END IF;

    RAISE EXCEPTION 'Finalized vehicle attacks are immutable'
        USING ERRCODE='23514';
END;
$$;

CREATE TRIGGER venc_attack_finalization_valid
BEFORE UPDATE OR DELETE ON venc_attack
FOR EACH ROW EXECUTE FUNCTION
    venc_validate_attack_finalization();

CREATE OR REPLACE FUNCTION venc_attack_line_open()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    receipt_id bigint;
    receipt_finalized boolean;
BEGIN
    receipt_id:=CASE
        WHEN TG_OP='DELETE' THEN OLD.vehicle_attack_id
        ELSE NEW.vehicle_attack_id
    END;
    SELECT finalized INTO receipt_finalized
    FROM venc_attack
    WHERE vehicle_attack_id=receipt_id;
    IF receipt_finalized THEN
        RAISE EXCEPTION
            'Finalized vehicle attack lines are immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END;
$$;

CREATE TRIGGER venc_attack_modifier_open
BEFORE INSERT OR UPDATE OR DELETE ON venc_attack_modifier
FOR EACH ROW EXECUTE FUNCTION venc_attack_line_open();

CREATE TRIGGER venc_attack_packet_open
BEFORE INSERT OR UPDATE OR DELETE ON venc_attack_damage_packet
FOR EACH ROW EXECUTE FUNCTION venc_attack_line_open();

CREATE VIEW venc_attack_receipt_total AS
WITH modifier_total AS (
    SELECT vehicle_attack_id,sum(modifier_value) AS modifier_total
    FROM venc_attack_modifier
    GROUP BY vehicle_attack_id
),
packet_total AS (
    SELECT vehicle_attack_id,
           sum(location_hit_count*packet_quantity)
               AS location_hits
    FROM venc_attack_damage_packet
    GROUP BY vehicle_attack_id
)
SELECT attack.vehicle_attack_id,attack.vehicle_engagement_id,
       attack.campaign_id,attack.attacker_vehicle_id,
       attack.target_vehicle_id,attack.weapon_rule_id,
       attack.attack_roll,
       coalesce(modifier.modifier_total,0)
           AS modifier_total,
       attack.attack_total,attack.target_number,attack.effect,
       attack.hit,attack.raw_damage,attack.armor_rating_used,
       attack.penetrating_damage,attack.damage_band_code,
       coalesce(packet.location_hits,0) AS location_hits,
       attack.finalized
FROM venc_attack attack
LEFT JOIN modifier_total modifier
  USING (vehicle_attack_id)
LEFT JOIN packet_total packet
  USING (vehicle_attack_id);
