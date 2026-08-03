ALTER TABLE rule_armor_environmental_protection
    DROP CONSTRAINT rule_armor_environmental_protection_check,
    ADD CONSTRAINT rule_armor_environmental_protection_value_check CHECK (
        (hazard_code='radiation'
         AND protection_kind='reduction'
         AND radiation_reduction_rads IS NOT NULL
         AND radiation_reduction_rads>0)
        OR
        (hazard_code<>'radiation'
         AND radiation_reduction_rads IS NULL)
    );

COMMENT ON CONSTRAINT rule_armor_environmental_protection_value_check
ON rule_armor_environmental_protection IS
    'Rejects SQL NULL explicitly for radiation-reduction mechanics.';
