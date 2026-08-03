CREATE TABLE rule_personal_explosion (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    shared_damage_roll boolean NOT NULL CHECK (shared_damage_roll),
    dodge_reduction_dice smallint NOT NULL CHECK (dodge_reduction_dice=1),
    dive_divisor smallint NOT NULL CHECK (dive_divisor=2),
    dive_rounding text NOT NULL CHECK (dive_rounding='down'),
    reduction_before_armor boolean NOT NULL CHECK (reduction_before_armor),
    dive_ends_prone boolean NOT NULL CHECK (dive_ends_prone),
    dive_loses_significant_actions smallint NOT NULL CHECK (
        dive_loses_significant_actions=1
    )
);

CREATE TABLE enc_personal_explosion (
    explosion_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    encounter_id bigint NOT NULL REFERENCES enc_personal_combat(encounter_id),
    round_number integer NOT NULL CHECK (round_number>0),
    source_reference text NOT NULL CHECK (btrim(source_reference)<>''),
    damage_dice smallint NOT NULL CHECK (damage_dice>0),
    damage_die_sides smallint NOT NULL CHECK (damage_die_sides>1),
    flat_damage integer NOT NULL DEFAULT 0 CHECK (flat_damage>=0),
    explosion_status text NOT NULL DEFAULT 'awaiting_reactions' CHECK (
        explosion_status IN ('awaiting_reactions','resolved','cancelled')
    ),
    UNIQUE (encounter_id,source_reference)
);

CREATE TABLE enc_personal_explosion_target (
    explosion_id bigint NOT NULL REFERENCES enc_personal_explosion(explosion_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_order smallint NOT NULL CHECK (target_order>0),
    armor_rule_id bigint NOT NULL REFERENCES inv_armor_definition(item_rule_id),
    reaction_declared boolean NOT NULL DEFAULT false,
    reaction_kind text CHECK (reaction_kind IN ('none','dodge','dive')),
    PRIMARY KEY (explosion_id,actor_id),
    UNIQUE (explosion_id,target_order),
    CHECK (reaction_declared=(reaction_kind IS NOT NULL))
);

CREATE TABLE cmd_personal_explosion_resolution_receipt (
    command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
    explosion_id bigint NOT NULL UNIQUE REFERENCES enc_personal_explosion(explosion_id),
    shared_rolled_damage integer NOT NULL CHECK (shared_rolled_damage>=0),
    target_count smallint NOT NULL CHECK (target_count>0)
);

ALTER TABLE health_damage_instance
    ADD COLUMN explosion_command_id bigint
        REFERENCES cmd_personal_explosion_resolution_receipt(command_id),
    ADD CONSTRAINT health_damage_instance_explosion_target_unique
        UNIQUE (explosion_command_id,target_actor_id);

ALTER TABLE health_damage_instance
    DROP CONSTRAINT health_damage_exactly_one_source_check,
    ADD CONSTRAINT health_damage_exactly_one_source_check CHECK (
        num_nonnulls(
            attack_command_id,environmental_command_id,
            explosion_command_id
        )=1
    );

CREATE TABLE cmd_personal_explosion_target_receipt (
    command_id bigint NOT NULL
        REFERENCES cmd_personal_explosion_resolution_receipt(command_id),
    actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    target_order smallint NOT NULL,
    armor_rule_id bigint NOT NULL REFERENCES inv_armor_definition(item_rule_id),
    reaction_kind text NOT NULL CHECK (
        reaction_kind IN ('none','dodge','dive')
    ),
    dodge_reduction integer NOT NULL CHECK (dodge_reduction>=0),
    damage_after_reaction integer NOT NULL CHECK (damage_after_reaction>=0),
    armor_rating integer NOT NULL CHECK (armor_rating>=0),
    penetrating_damage integer NOT NULL CHECK (penetrating_damage>=0),
    damage_instance_id bigint REFERENCES health_damage_instance(damage_instance_id),
    PRIMARY KEY (command_id,actor_id),
    UNIQUE (command_id,target_order),
    CHECK ((penetrating_damage>0)=(damage_instance_id IS NOT NULL))
);

ALTER TABLE enc_personal_combatant
    ADD COLUMN significant_action_losses_pending smallint NOT NULL DEFAULT 0
        CHECK (significant_action_losses_pending>=0);

COMMENT ON CONSTRAINT health_damage_exactly_one_source_check
    ON health_damage_instance IS
    'Every damage instance originates from exactly one attack or explosion.';
