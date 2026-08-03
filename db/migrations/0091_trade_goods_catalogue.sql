INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status
)
SELECT package.content_package_id,
       'trade.good.'||source.good_code,
       source.name,'trade','approved'
FROM sys_content_package package
CROSS JOIN (
    VALUES
        ('basic-consumables','Basic Consumable Goods'),
        ('basic-electronics','Basic Electronics'),
        ('basic-machine-parts','Basic Machine Parts'),
        ('basic-manufactured-goods','Basic Manufactured Goods'),
        ('basic-raw-materials','Basic Raw Materials'),
        ('basic-unrefined-ore','Basic Unrefined Ore'),
        ('advanced-electronics','Advanced Electronics'),
        ('advanced-manufactured-goods','Advanced Manufactured Goods'),
        ('agricultural-equipment','Agricultural Equipment'),
        ('animal-products','Animal Products'),
        ('collectibles','Collectibles'),
        ('computers-parts','Computers & Computer Parts'),
        ('crystals-gems','Crystals & Gems'),
        ('cybernetic-parts','Cybernetic Parts'),
        ('food-service-equipment','Food Service Equipment'),
        ('furniture','Furniture'),
        ('gambling-equipment','Gambling Devices & Equipment'),
        ('grav-vehicles','Grav Vehicles'),
        ('grocery-products','Grocery Products'),
        ('household-appliances','Household Appliances'),
        ('industrial-supplies','Industrial Supplies'),
        ('liquor-intoxicants','Liquor & Other Intoxicants'),
        ('luxury-goods','Luxury Goods'),
        ('manufacturing-equipment','Manufacturing Equipment'),
        ('medical-equipment','Medical Equipment'),
        ('petrochemicals','Petrochemicals'),
        ('pharmaceuticals','Pharmaceuticals'),
        ('polymers','Polymers'),
        ('precious-metals','Precious Metals'),
        ('radioactives','Radioactives'),
        ('robots-drones','Robots & Drones'),
        ('scientific-equipment','Scientific Equipment'),
        ('survival-gear','Survival Gear'),
        ('textiles','Textiles'),
        ('uncommon-raw-materials','Uncommon Raw Materials'),
        ('uncommon-unrefined-ores','Uncommon Unrefined Ores'),
        ('illicit-luxury-goods','Illicit Luxury Goods'),
        ('illicit-pharmaceuticals','Illicit Pharmaceuticals'),
        ('medical-research-material','Medical Research Material'),
        ('military-equipment','Military Equipment'),
        ('personal-weapons-armor','Personal Weapons & Armor'),
        ('unusual-cargo','Unusual Cargo')
) source(good_code,name)
WHERE package.package_code='cepheus-engine';

INSERT INTO rule_trade_good (
    trade_good_rule_id,good_code,d66_result,good_kind,
    base_price_credits,availability_dice_count,
    availability_die_sides,availability_multiplier,
    black_market_only
)
SELECT rule.rule_id,source.good_code,source.d66_result,
       source.good_kind,source.base_price,source.dice_count,
       source.die_sides,source.multiplier,source.black_market_only
FROM rule_rule rule
JOIN (
    VALUES
        ('basic-consumables',NULL::smallint,'common',1000,2,6,5,false),
        ('basic-electronics',NULL,'common',25000,2,6,5,false),
        ('basic-machine-parts',NULL,'common',10000,2,6,5,false),
        ('basic-manufactured-goods',NULL,'common',20000,2,6,5,false),
        ('basic-raw-materials',NULL,'common',5000,2,6,5,false),
        ('basic-unrefined-ore',NULL,'common',2000,2,6,5,false),
        ('advanced-electronics',11,'trade',100000,1,6,5,false),
        ('advanced-manufactured-goods',12,'trade',200000,1,6,5,false),
        ('agricultural-equipment',13,'trade',150000,1,6,1,false),
        ('animal-products',14,'trade',1500,4,6,5,false),
        ('collectibles',15,'trade',50000,1,6,1,false),
        ('computers-parts',16,'trade',150000,2,6,1,false),
        ('crystals-gems',21,'trade',20000,1,6,5,false),
        ('cybernetic-parts',22,'trade',250000,1,6,5,false),
        ('food-service-equipment',23,'trade',4000,2,6,1,false),
        ('furniture',24,'trade',5000,4,6,1,false),
        ('gambling-equipment',25,'trade',4000,1,6,1,false),
        ('grav-vehicles',26,'trade',160000,1,6,1,false),
        ('grocery-products',31,'trade',6000,1,6,5,false),
        ('household-appliances',32,'trade',12000,4,6,1,false),
        ('industrial-supplies',33,'trade',75000,2,6,1,false),
        ('liquor-intoxicants',34,'trade',15000,1,6,5,false),
        ('luxury-goods',35,'trade',150000,1,6,1,false),
        ('manufacturing-equipment',36,'trade',750000,1,6,5,false),
        ('medical-equipment',41,'trade',50000,1,6,5,false),
        ('petrochemicals',42,'trade',10000,2,6,5,false),
        ('pharmaceuticals',43,'trade',100000,1,6,1,false),
        ('polymers',44,'trade',7000,4,6,5,false),
        ('precious-metals',45,'trade',50000,1,6,1,false),
        ('radioactives',46,'trade',1000000,1,6,1,false),
        ('robots-drones',51,'trade',500000,1,6,5,false),
        ('scientific-equipment',52,'trade',50000,1,6,5,false),
        ('survival-gear',53,'trade',4000,2,6,1,false),
        ('textiles',54,'trade',3000,3,6,5,false),
        ('uncommon-raw-materials',55,'trade',50000,2,6,5,false),
        ('uncommon-unrefined-ores',56,'trade',20000,2,6,5,false),
        ('illicit-luxury-goods',61,'trade',150000,1,6,1,true),
        ('illicit-pharmaceuticals',62,'trade',100000,1,6,1,true),
        ('medical-research-material',63,'trade',50000,1,6,5,true),
        ('military-equipment',64,'trade',150000,2,6,1,true),
        ('personal-weapons-armor',65,'trade',30000,2,6,1,true),
        ('unusual-cargo',66,'unusual',NULL,NULL,NULL,NULL,false)
) source(
    good_code,d66_result,good_kind,base_price,dice_count,
    die_sides,multiplier,black_market_only
)
  ON rule.rule_code='trade.good.'||source.good_code;
