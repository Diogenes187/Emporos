CREATE TABLE rule_armor_degradation (
    armor_rule_id bigint NOT NULL REFERENCES
        inv_armor_definition(item_rule_id),
    damage_type text NOT NULL CHECK (damage_type='laser'),
    armor_rating_loss_per_hit integer NOT NULL CHECK (
        armor_rating_loss_per_hit>0
    ),
    minimum_armor_rating integer NOT NULL CHECK (
        minimum_armor_rating>=0
    ),
    PRIMARY KEY (armor_rule_id,damage_type)
);

CREATE TABLE rule_armor_layer_exception (
    armor_rule_id bigint PRIMARY KEY REFERENCES
        inv_armor_definition(item_rule_id),
    may_layer_with_other_armor boolean NOT NULL CHECK (
        may_layer_with_other_armor
    ),
    maximum_total_layers integer NOT NULL CHECK (
        maximum_total_layers=2
    ),
    layer_position_choice boolean NOT NULL CHECK (layer_position_choice)
);

CREATE TABLE rule_armor_characteristic_modifier (
    armor_rule_id bigint NOT NULL REFERENCES
        inv_armor_definition(item_rule_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    modifier integer NOT NULL,
    modifies_damage_tracking boolean NOT NULL CHECK (
        NOT modifies_damage_tracking
    ),
    PRIMARY KEY (armor_rule_id,characteristic_rule_id)
);

CREATE TABLE rule_armor_computer_system (
    armor_rule_id bigint PRIMARY KEY REFERENCES
        inv_armor_definition(item_rule_id),
    computer_model integer NOT NULL CHECK (computer_model=2),
    expert_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    expert_program_level integer NOT NULL CHECK (expert_program_level=2)
);

CREATE TABLE rule_armor_life_support (
    armor_rule_id bigint PRIMARY KEY REFERENCES
        inv_armor_definition(item_rule_id),
    duration_seconds integer NOT NULL CHECK (duration_seconds=21600),
    supplies_breathable_atmosphere boolean NOT NULL CHECK (
        supplies_breathable_atmosphere
    )
);

CREATE TABLE rule_environmental_hazard (
    hazard_code text PRIMARY KEY CHECK (
        hazard_code IN (
            'hard-vacuum','temperature-extremes','low-pressure',
            'radiation','flame','high-pressure',
            'toxic-corrosive-atmosphere','nbc'
        )
    )
);

CREATE TABLE rule_armor_environmental_protection (
    armor_rule_id bigint NOT NULL REFERENCES
        inv_armor_definition(item_rule_id),
    hazard_code text NOT NULL REFERENCES
        rule_environmental_hazard(hazard_code),
    protection_kind text NOT NULL CHECK (
        protection_kind IN ('standard','full','impervious','reduction')
    ),
    radiation_reduction_rads integer,
    PRIMARY KEY (armor_rule_id,hazard_code),
    CHECK (
        (hazard_code='radiation'
         AND protection_kind='reduction'
         AND radiation_reduction_rads>0)
        OR
        (hazard_code<>'radiation'
         AND radiation_reduction_rads IS NULL)
    )
);

CREATE TABLE rule_armor_capability_inheritance (
    armor_rule_id bigint PRIMARY KEY REFERENCES
        inv_armor_definition(item_rule_id),
    inherited_armor_rule_id bigint NOT NULL REFERENCES
        inv_armor_definition(item_rule_id),
    CHECK (armor_rule_id<>inherited_armor_rule_id)
);

CREATE VIEW rule_armor_effective_environmental_protection AS
WITH RECURSIVE ancestry(armor_rule_id,source_armor_rule_id) AS (
    SELECT item_rule_id,item_rule_id FROM inv_armor_definition
    UNION ALL
    SELECT ancestry.armor_rule_id,inheritance.inherited_armor_rule_id
    FROM ancestry
    JOIN rule_armor_capability_inheritance inheritance
      ON inheritance.armor_rule_id=ancestry.source_armor_rule_id
)
SELECT ancestry.armor_rule_id,protection.hazard_code,
       protection.protection_kind,protection.radiation_reduction_rads,
       ancestry.source_armor_rule_id
FROM ancestry
JOIN rule_armor_environmental_protection protection
  ON protection.armor_rule_id=ancestry.source_armor_rule_id;

CREATE TABLE src_armor_mechanic_provenance (
    armor_rule_id bigint NOT NULL REFERENCES
        inv_armor_definition(item_rule_id),
    mechanic_code text NOT NULL CHECK (btrim(mechanic_code)<>''),
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    import_candidate_id bigint NOT NULL,
    provenance_class text NOT NULL CHECK (
        provenance_class IN ('direct','corroborating')
    ),
    is_primary_citation boolean NOT NULL,
    PRIMARY KEY (
        armor_rule_id,mechanic_code,source_locator_id,import_candidate_id
    ),
    FOREIGN KEY (import_candidate_id,source_locator_id)
        REFERENCES src_import_candidate(
            import_candidate_id,source_locator_id)
);

CREATE UNIQUE INDEX src_armor_mechanic_one_primary
ON src_armor_mechanic_provenance(armor_rule_id,mechanic_code)
WHERE is_primary_citation;

COMMENT ON TABLE rule_armor_degradation IS
    'CE-EQUIP-002 typed armor degradation mechanics.';
COMMENT ON VIEW rule_armor_effective_environmental_protection IS
    'Direct and explicitly inherited personal armor protections.';
