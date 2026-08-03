CREATE TABLE cmd_species_bad_first_impression_receipt (
    command_id bigint NOT NULL REFERENCES cmd_command(command_id),
    encounter_id bigint NOT NULL REFERENCES enc_encounter(encounter_id),
    reacting_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    bad_impression_actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
    prior_attitude_rule_id bigint REFERENCES rule_attitude(rule_id),
    source_attitude_rule_id bigint NOT NULL REFERENCES rule_attitude(rule_id),
    PRIMARY KEY (command_id,reacting_actor_id,bad_impression_actor_id),
    CHECK (reacting_actor_id <> bad_impression_actor_id)
);

COMMENT ON TABLE cmd_species_bad_first_impression_receipt IS
    'Audits cross-species Unfriendly starting attitudes caused when an encounter participant is added.';
