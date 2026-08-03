CREATE TABLE inv_personal_device_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    device_code text NOT NULL UNIQUE CHECK (
        device_code IN (
            'magnetic-compass','wrist-watch','radiation-counter',
            'metal-detector','hand-calculator','inertial-locator',
            'electromagnetic-probe','hand-computer-fixed',
            'holographic-projector','densitometer','bioscanner',
            'neural-activity-sensor')),
    catalogue_mass_is_unquantified boolean NOT NULL,
    CHECK (
        catalogue_mass_is_unquantified =
        (device_code IN (
            'magnetic-compass','wrist-watch','electromagnetic-probe')))
);

COMMENT ON TABLE inv_personal_device_definition IS
    'CE-EQUIP-013 exact paired-source Personal Devices catalogue.';
