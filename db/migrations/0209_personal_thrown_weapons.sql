CREATE TABLE rule_personal_thrown_weapon (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    impact_adds_effect boolean NOT NULL CHECK (impact_adds_effect),
    payload_adds_effect boolean NOT NULL CHECK (NOT payload_adds_effect),
    miss_scatter_base_metres numeric NOT NULL CHECK (
        miss_scatter_base_metres=6
    ),
    scatter_distance_uses_effect boolean NOT NULL CHECK (
        scatter_distance_uses_effect
    ),
    scatter_distance_minimum_metres numeric NOT NULL CHECK (
        scatter_distance_minimum_metres=0
    ),
    scatter_direction_die_sides smallint NOT NULL CHECK (
        scatter_direction_die_sides=360
    )
);

CREATE TABLE inv_thrown_delivery_capability (
    item_rule_id bigint PRIMARY KEY
        REFERENCES inv_weapon_definition(item_rule_id),
    delivery_type text NOT NULL CHECK (
        delivery_type IN ('impact','payload')
    ),
    attack_profile_code text NOT NULL CHECK (
        attack_profile_code='thrown'
    ),
    effect_contributes_damage boolean NOT NULL,
    CHECK (
        (delivery_type='impact' AND effect_contributes_damage)
        OR (delivery_type='payload' AND NOT effect_contributes_damage)
    )
);

ALTER TABLE enc_personal_attack
    ADD COLUMN thrown_delivery_type text CHECK (
        thrown_delivery_type IN ('impact','payload')
    ),
    ADD COLUMN thrown_target_point_reference text CHECK (
        thrown_target_point_reference IS NULL
        OR btrim(thrown_target_point_reference)<>''
    ),
    ADD CONSTRAINT enc_personal_attack_thrown_snapshot_check CHECK (
        (
          attack_profile_code='thrown'
          AND thrown_delivery_type IS NOT NULL
          AND thrown_target_point_reference IS NOT NULL
        )
        OR (
          attack_profile_code<>'thrown'
          AND thrown_delivery_type IS NULL
          AND thrown_target_point_reference IS NULL
        )
    );

CREATE TABLE cmd_personal_thrown_weapon_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_attack_receipt(command_id),
    personal_attack_id bigint NOT NULL UNIQUE
        REFERENCES enc_personal_attack(personal_attack_id),
    delivery_type text NOT NULL CHECK (
        delivery_type IN ('impact','payload')
    ),
    attack_hit boolean NOT NULL,
    original_effect integer NOT NULL,
    target_point_reference text NOT NULL CHECK (
        btrim(target_point_reference)<>''
    ),
    scatter_direction_draw smallint,
    scatter_bearing_degrees smallint,
    scatter_distance_metres numeric NOT NULL CHECK (
        scatter_distance_metres>=0
    ),
    payload_delivery_required boolean NOT NULL,
    direct_damage_permitted boolean NOT NULL,
    CHECK (
        (
          attack_hit AND scatter_direction_draw IS NULL
          AND scatter_bearing_degrees IS NULL
          AND scatter_distance_metres=0
        )
        OR (
          NOT attack_hit
          AND scatter_direction_draw BETWEEN 1 AND 360
          AND scatter_bearing_degrees=scatter_direction_draw-1
        )
    ),
    CHECK (
        (
          delivery_type='impact' AND NOT payload_delivery_required
          AND direct_damage_permitted=attack_hit
        )
        OR (
          delivery_type='payload' AND payload_delivery_required
          AND NOT direct_damage_permitted
        )
    )
);

CREATE TABLE cmd_personal_thrown_payload_link (
    delivery_attack_command_id bigint PRIMARY KEY
        REFERENCES cmd_personal_thrown_weapon_receipt(command_id),
    payload_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
    target_point_reference text NOT NULL,
    scatter_bearing_degrees smallint,
    scatter_distance_metres numeric NOT NULL CHECK (
        scatter_distance_metres>=0
    )
);

ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack','damage','task','occurrence','encounter_type','initiative',
        'psionic_activation','psionic_timing','career_qualification',
        'career_draft','career_survival','career_mishap','career_injury',
        'career_injury_reduction','career_injury_crisis_cost',
        'career_commission','career_advancement','career_training',
        'career_aging','career_reenlistment','career_benefit',
        'career_benefit_ship_shares','career_aging_crisis_cost',
        'career_medical_employer','career_anagathic_cost',
        'career_anagathic_survival','environment_damage',
        'blind_target','explosion_damage','explosion_dodge',
        'combat_scatter','combat_nearest_tie',
        'grapple_challenger','grapple_opponent','grapple_throw_damage',
        'thrown_scatter_direction'
    )
);

CREATE FUNCTION cmd_reject_thrown_history_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Thrown-weapon delivery history is immutable'; END;
$$;
CREATE TRIGGER cmd_personal_thrown_weapon_receipt_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_thrown_weapon_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_thrown_history_mutation();
CREATE TRIGGER cmd_personal_thrown_payload_link_immutable
BEFORE UPDATE OR DELETE ON cmd_personal_thrown_payload_link
FOR EACH ROW EXECUTE FUNCTION cmd_reject_thrown_history_mutation();

COMMENT ON TABLE cmd_personal_thrown_weapon_receipt IS
    'CE-COMBAT-011 target reference plus auditable polar scatter offset.';
