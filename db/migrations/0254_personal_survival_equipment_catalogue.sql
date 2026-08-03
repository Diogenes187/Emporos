CREATE TABLE inv_personal_survival_equipment_definition (
    item_rule_id bigint PRIMARY KEY REFERENCES inv_item_definition(rule_id),
    survival_equipment_code text NOT NULL UNIQUE CHECK (
        survival_equipment_code IN (
            'cold-weather-clothing','filter-mask','swimming-equipment',
            'combination-mask','oxygen-tanks','respirator',
            'underwater-air-tanks','artificial-gill','environment-suit',
            'rescue-bubble','thruster-pack','portable-generator')),
    catalogue_mass_is_unquantified boolean NOT NULL,
    CHECK (
        catalogue_mass_is_unquantified =
        (survival_equipment_code IN (
            'filter-mask','combination-mask','respirator',
            'environment-suit')))
);

COMMENT ON TABLE inv_personal_survival_equipment_definition IS
    'CE-EQUIP-022 exact paired-source Survival Equipment catalogue.';
