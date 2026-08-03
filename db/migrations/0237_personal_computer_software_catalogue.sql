CREATE TABLE rule_personal_software_catalogue (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    permits_lower_rating_use boolean NOT NULL CHECK (
        permits_lower_rating_use),
    minimum_usable_rating_is_family_minimum boolean NOT NULL CHECK (
        minimum_usable_rating_is_family_minimum),
    difficult_copy_above_rating integer NOT NULL CHECK (
        difficult_copy_above_rating=1),
    transfer_bandwidth_is_unquantified boolean NOT NULL CHECK (
        transfer_bandwidth_is_unquantified)
);

CREATE TABLE rule_personal_software_family (
    rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    software_code text NOT NULL UNIQUE CHECK (
        software_code IN (
            'database','interface','security','translator','intrusion',
            'intelligent-interface','expert','agent','intellect')),
    ranked boolean NOT NULL,
    minimum_published_rating integer CHECK (minimum_published_rating>=0),
    maximum_published_rating integer CHECK (
        maximum_published_rating>=minimum_published_rating),
    maximum_is_open_ended boolean NOT NULL,
    CHECK (
        (ranked AND minimum_published_rating IS NOT NULL
         AND maximum_published_rating IS NOT NULL)
        OR
        (NOT ranked AND minimum_published_rating IS NULL
         AND maximum_published_rating IS NULL
         AND NOT maximum_is_open_ended)),
    CHECK (
        NOT maximum_is_open_ended OR software_code='intellect')
);

CREATE TABLE rule_personal_software_profile (
    software_rule_id bigint NOT NULL REFERENCES
        rule_personal_software_family(rule_id),
    profile_order integer NOT NULL CHECK (profile_order>0),
    rating integer CHECK (rating>=0),
    rating_or_higher boolean NOT NULL,
    minimum_tech_level integer NOT NULL CHECK (minimum_tech_level>=0),
    cost_basis text NOT NULL CHECK (
        cost_basis IN (
            'fixed','included','range','unavailable','not-stated')),
    minimum_cost_credits bigint CHECK (minimum_cost_credits>=0),
    maximum_cost_credits bigint CHECK (maximum_cost_credits>=0),
    PRIMARY KEY (software_rule_id,profile_order),
    UNIQUE NULLS NOT DISTINCT (software_rule_id,rating),
    CHECK (NOT rating_or_higher OR rating IS NOT NULL),
    CHECK (
        (cost_basis='fixed'
         AND minimum_cost_credits=maximum_cost_credits)
        OR
        (cost_basis='included'
         AND minimum_cost_credits=0 AND maximum_cost_credits=0)
        OR
        (cost_basis='range'
         AND minimum_cost_credits IS NOT NULL
         AND maximum_cost_credits>=minimum_cost_credits)
        OR
        (cost_basis IN ('unavailable','not-stated')
         AND minimum_cost_credits IS NULL
         AND maximum_cost_credits IS NULL))
);

COMMENT ON TABLE rule_personal_software_profile IS
    'CE-EQUIP-007 exact published personal software rows and cost states.';
