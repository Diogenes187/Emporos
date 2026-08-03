CREATE TABLE inv_personal_sensory_aid_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    sensory_aid_code text NOT NULL UNIQUE CHECK (
        sensory_aid_code IN (
            'torch','lamp-oil','oil-lamp','binoculars','electric-torch',
            'cold-light-lantern','infrared-goggles',
            'light-intensifier-goggles')),
    catalogue_mass_is_unquantified boolean NOT NULL,
    CHECK (
        catalogue_mass_is_unquantified =
        (sensory_aid_code IN (
            'lamp-oil','infrared-goggles','light-intensifier-goggles')))
);

COMMENT ON TABLE inv_personal_sensory_aid_definition IS
    'CE-EQUIP-019 exact paired-source Sensory Aids catalogue.';
