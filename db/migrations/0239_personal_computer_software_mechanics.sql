CREATE TABLE rule_personal_database_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    search_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    searchable_by_agent boolean NOT NULL CHECK (searchable_by_agent)
);

CREATE TABLE rule_personal_interface_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    missing_interface_difficulty_rule_id bigint NOT NULL REFERENCES
        rule_difficulty(rule_id),
    displays_data boolean NOT NULL CHECK (displays_data)
);

CREATE TABLE rule_personal_security_difficulty (
    software_rule_id bigint NOT NULL REFERENCES
        rule_personal_software_family(rule_id),
    rating integer NOT NULL CHECK (rating BETWEEN 0 AND 3),
    difficulty_rule_id bigint NOT NULL REFERENCES rule_difficulty(rule_id),
    PRIMARY KEY (software_rule_id,rating),
    UNIQUE (software_rule_id,difficulty_rule_id)
);

CREATE TABLE rule_personal_translator_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    specialized_expert_system boolean NOT NULL CHECK (
        specialized_expert_system),
    language_skills_only boolean NOT NULL CHECK (language_skills_only),
    minimum_realtime_rating integer NOT NULL CHECK (
        minimum_realtime_rating=1),
    rating_zero_near_realtime boolean NOT NULL CHECK (
        rating_zero_near_realtime)
);

CREATE TABLE rule_personal_intrusion_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    hacking_dm_equals_rating boolean NOT NULL CHECK (
        hacking_dm_equals_rating),
    often_illegal boolean NOT NULL CHECK (often_illegal)
);

CREATE TABLE rule_personal_intelligent_interface_capability (
    software_rule_id bigint NOT NULL REFERENCES
        rule_personal_software_family(rule_id),
    rating integer NOT NULL CHECK (rating BETWEEN 1 AND 3),
    autonomy_class text NOT NULL CHECK (
        autonomy_class IN ('low-autonomous','high-autonomous','true-ai')),
    voice_control boolean NOT NULL CHECK (voice_control),
    intelligent_display boolean NOT NULL CHECK (intelligent_display),
    self_initiating boolean NOT NULL,
    self_learning boolean NOT NULL,
    creative_thought boolean NOT NULL,
    PRIMARY KEY (software_rule_id,rating),
    CHECK (self_initiating=(rating>=2)),
    CHECK (self_learning=(rating>=2)),
    CHECK (creative_thought=(rating=3))
);

CREATE TABLE rule_personal_expert_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    required_interface_rule_id bigint NOT NULL REFERENCES
        rule_personal_software_family(rule_id),
    granted_skill_level_offset integer NOT NULL CHECK (
        granted_skill_level_offset=-1),
    existing_higher_skill_dm integer NOT NULL CHECK (
        existing_higher_skill_dm=1)
);

CREATE TABLE rule_personal_expert_allowed_characteristic (
    expert_software_rule_id bigint NOT NULL REFERENCES
        rule_personal_expert_mechanic(software_rule_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    PRIMARY KEY (expert_software_rule_id,characteristic_rule_id)
);

CREATE TABLE rule_personal_agent_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    computer_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
    computer_skill_equals_rating boolean NOT NULL CHECK (
        computer_skill_equals_rating),
    carries_out_assigned_tasks boolean NOT NULL CHECK (
        carries_out_assigned_tasks),
    expert_component_rule_id bigint NOT NULL REFERENCES
        rule_personal_software_family(rule_id),
    intellect_component_rule_id bigint NOT NULL REFERENCES
        rule_personal_software_family(rule_id)
);

CREATE TABLE rule_personal_intellect_mechanic (
    software_rule_id bigint PRIMARY KEY REFERENCES
        rule_personal_software_family(rule_id),
    improved_agent boolean NOT NULL CHECK (improved_agent),
    can_use_expert_systems boolean NOT NULL CHECK (can_use_expert_systems),
    simultaneous_skills_equal_rating boolean NOT NULL CHECK (
        simultaneous_skills_equal_rating)
);

COMMENT ON TABLE rule_personal_expert_mechanic IS
    'CE-EQUIP-008 exact Expert skill substitution and higher-skill bonus.';
