CREATE TABLE rule_personal_armor_catalogue (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    ordinary_simultaneous_armor_limit integer NOT NULL CHECK (
        ordinary_simultaneous_armor_limit=1
    ),
    source_noted_layering_exceptions boolean NOT NULL CHECK (
        source_noted_layering_exceptions
    ),
    layered_damage_resolution text NOT NULL CHECK (
        layered_damage_resolution='outside-in'
    ),
    exceptional_effect_minimum_damage integer NOT NULL CHECK (
        exceptional_effect_minimum_damage=1
    ),
    exceptional_effect_threshold integer NOT NULL CHECK (
        exceptional_effect_threshold=6
    )
);

ALTER TABLE inv_armor_definition
    ADD COLUMN catalogue_display_order integer CHECK (
        catalogue_display_order>0
    ),
    ADD COLUMN laser_rating_explicit boolean NOT NULL DEFAULT false,
    ADD CONSTRAINT inv_armor_explicit_laser_rating_check CHECK (
        NOT laser_rating_explicit OR laser_armor_rating IS NOT NULL
    );

CREATE UNIQUE INDEX inv_armor_catalogue_display_order_unique
ON inv_armor_definition(catalogue_display_order)
WHERE catalogue_display_order IS NOT NULL;

COMMENT ON TABLE rule_personal_armor_catalogue IS
    'CE-EQUIP-001 governing personal armor catalogue and layering baseline.';
