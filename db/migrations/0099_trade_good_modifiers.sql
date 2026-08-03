ALTER TABLE rule_trade_good_modifier
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);

WITH source(good_code,purchase_modifiers,sale_modifiers) AS (
    VALUES
        ('advanced-electronics','{"Ht":2,"In":3}'::jsonb,'{"Ni":2,"Po":1}'::jsonb),
        ('advanced-manufactured-goods','{"In":3,"Ri":2}'::jsonb,'{"Ag":1,"Ni":2}'::jsonb),
        ('agricultural-equipment','{"In":3,"Ri":2}'::jsonb,'{"Ag":2,"Ga":1}'::jsonb),
        ('animal-products','{"Ag":2,"Ga":3}'::jsonb,'{"Hi":2,"Ri":1}'::jsonb),
        ('collectibles','{"In":2,"Ri":3}'::jsonb,'{"Hi":2,"Ni":1}'::jsonb),
        ('computers-parts','{"Ht":3,"In":2}'::jsonb,'{"Na":1,"Ni":2}'::jsonb),
        ('crystals-gems','{"Ni":3,"Na":2}'::jsonb,'{"In":1,"Ri":2}'::jsonb),
        ('cybernetic-parts','{"Ht":3,"Ri":2}'::jsonb,'{"Na":1,"Ni":2}'::jsonb),
        ('food-service-equipment','{"In":3,"Na":2}'::jsonb,'{"Ag":1,"Ni":2}'::jsonb),
        ('furniture','{"Ag":2,"Ga":3}'::jsonb,'{"Hi":1,"Ri":2}'::jsonb),
        ('gambling-equipment','{"Hi":2,"Ri":3}'::jsonb,'{"Na":2,"Ni":1}'::jsonb),
        ('grav-vehicles','{"Ht":3,"Ri":2}'::jsonb,'{"Ni":2,"Po":1}'::jsonb),
        ('grocery-products','{"Ag":3,"Ga":2}'::jsonb,'{"Hi":1,"Ri":2}'::jsonb),
        ('household-appliances','{"Hi":2,"In":3}'::jsonb,'{"Na":1,"Ni":2}'::jsonb),
        ('industrial-supplies','{"In":3,"Ri":2}'::jsonb,'{"Na":1,"Ni":2}'::jsonb),
        ('liquor-intoxicants','{"Ag":3,"Ga":2}'::jsonb,'{"In":1,"Ri":2}'::jsonb),
        ('luxury-goods','{"Ag":2,"Ga":3}'::jsonb,'{"In":1,"Ri":2}'::jsonb),
        ('manufacturing-equipment','{"In":3,"Ri":2}'::jsonb,'{"Na":1,"Ni":2}'::jsonb),
        ('medical-equipment','{"Ht":2,"Ri":3}'::jsonb,'{"Hi":1,"In":2}'::jsonb),
        ('petrochemicals','{"Na":2,"Ni":3}'::jsonb,'{"Ag":1,"In":2}'::jsonb),
        ('pharmaceuticals','{"Ht":3,"Wa":2}'::jsonb,'{"In":2,"Ri":1}'::jsonb),
        ('polymers','{"In":2,"Ri":3}'::jsonb,'{"Ni":2,"Va":1}'::jsonb),
        ('precious-metals','{"As":3,"Ic":2}'::jsonb,'{"In":1,"Ri":2}'::jsonb),
        ('radioactives','{"As":2,"Ni":3}'::jsonb,'{"In":2,"Ht":1}'::jsonb),
        ('robots-drones','{"Ht":3,"In":2}'::jsonb,'{"Ni":1,"Ri":2}'::jsonb),
        ('scientific-equipment','{"Ht":3,"Ri":2}'::jsonb,'{"Hi":2,"Ni":1}'::jsonb),
        ('survival-gear','{"Ga":3,"Ri":2}'::jsonb,'{"Fl":2,"Va":1}'::jsonb),
        ('textiles','{"Ag":3,"Ni":2}'::jsonb,'{"Na":1,"Ri":2}'::jsonb),
        ('uncommon-raw-materials','{"Ag":3,"Ni":2}'::jsonb,'{"In":2,"Na":1}'::jsonb),
        ('uncommon-unrefined-ores','{"As":2,"Va":1}'::jsonb,'{"In":2,"Na":1}'::jsonb),
        ('illicit-luxury-goods','{"Ag":2,"Ga":3}'::jsonb,'{"In":4,"Ri":6}'::jsonb),
        ('illicit-pharmaceuticals','{"Ht":3,"Wa":2}'::jsonb,'{"In":6,"Ri":4}'::jsonb),
        ('medical-research-material','{"Ht":2,"Ri":3}'::jsonb,'{"In":6,"Na":4}'::jsonb),
        ('military-equipment','{"Ht":3,"In":2}'::jsonb,'{"Hi":6,"Ni":4}'::jsonb),
        ('personal-weapons-armor','{"In":3,"Ri":2}'::jsonb,'{"Ni":6,"Po":4}'::jsonb)
),
expanded AS (
    SELECT good_code,'purchase'::text AS transaction_side,
           modifier.key AS trade_code,
           modifier.value::text::smallint AS dice_modifier
    FROM source
    CROSS JOIN LATERAL jsonb_each(purchase_modifiers) modifier
    UNION ALL
    SELECT good_code,'sale',
           modifier.key,
           modifier.value::text::smallint
    FROM source
    CROSS JOIN LATERAL jsonb_each(sale_modifiers) modifier
)
INSERT INTO rule_trade_good_modifier(
    trade_good_rule_id,trade_code_rule_id,transaction_side,
    dice_modifier,source_locator_id
)
SELECT good.trade_good_rule_id,code.trade_code_rule_id,
       expanded.transaction_side,expanded.dice_modifier,
       locator.source_locator_id
FROM expanded
JOIN rule_trade_good good USING (good_code)
JOIN loc_trade_code code ON code.trade_code=expanded.trade_code
CROSS JOIN LATERAL (
    SELECT source_locator_id
    FROM src_locator
    WHERE heading_path=
        'Trade and Commerce > Determine Goods Available'
    ORDER BY source_locator_id
    LIMIT 1
) locator;

ALTER TABLE rule_trade_good_modifier
    ALTER COLUMN source_locator_id SET NOT NULL;
