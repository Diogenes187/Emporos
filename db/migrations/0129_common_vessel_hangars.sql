CREATE TABLE rule_ship_hangar_carried_class (
    hangar_option_code text NOT NULL REFERENCES
        rule_ship_hangar_option(hangar_option_code),
    carried_class_rule_id bigint NOT NULL REFERENCES
        ship_class(ship_class_rule_id),
    PRIMARY KEY (hangar_option_code,carried_class_rule_id)
);

INSERT INTO rule_ship_hangar_carried_class (
    hangar_option_code,carried_class_rule_id
)
SELECT source.hangar_option_code,class.ship_class_rule_id
FROM (
    VALUES
        ('fighter','fighter'),('cutter','cutter'),
        ('life-boat','launch'),('ships-boat','ships-boat')
) source(hangar_option_code,class_code)
JOIN ship_class class
  ON class.class_code=source.class_code;

CREATE OR REPLACE FUNCTION ship_validate_carried_craft()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    option_code text;
    installation_count_value smallint;
    units_per_installation_value smallint;
BEGIN
    SELECT hangar.hangar_option_code,hangar.installation_count,
           option.units_per_installation
    INTO option_code,installation_count_value,
         units_per_installation_value
    FROM ship_class_hangar_option hangar
    JOIN rule_ship_hangar_option option
      ON option.hangar_option_code=hangar.hangar_option_code
    WHERE hangar.ship_class_rule_id=NEW.carrier_class_rule_id
      AND hangar.hangar_identifier=NEW.hangar_identifier;

    IF NOT EXISTS (
           SELECT 1
           FROM rule_ship_hangar_carried_class allowed
           WHERE allowed.hangar_option_code=option_code
             AND allowed.carried_class_rule_id=NEW.carried_class_rule_id
       )
       OR NEW.craft_count<>
          installation_count_value*units_per_installation_value THEN
        RAISE EXCEPTION
            'Carried craft conflicts with hangar type or capacity'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER ship_carried_craft_valid
BEFORE INSERT OR UPDATE ON ship_class_carried_craft
FOR EACH ROW EXECUTE FUNCTION ship_validate_carried_craft();

INSERT INTO ship_class_hangar_option (
    ship_class_rule_id,hangar_identifier,hangar_option_code,
    installation_count,basis_quantity,allocated_tons,
    installation_cost_minor
)
SELECT class.ship_class_rule_id,source.hangar_identifier,
       source.hangar_option_code,source.installation_count,
       source.basis_quantity,source.allocated_tons,
       source.installation_cost_minor
FROM (
    VALUES
        ('asteroid-miner','crew-escape-pods','escape-pods',1,3::numeric,1.5::numeric,300000::bigint),
        ('asteroid-miner','mining-drone-set','mining-drones',1,1,10,2000000),
        ('destroyer','crew-escape-pods','escape-pods',1,23,11.5,2300000),
        ('destroyer','ships-boat-hangar','ships-boat',1,1,39,7800000),
        ('dreadnought','crew-escape-pods','escape-pods',1,223,111.5,22300000),
        ('dreadnought','fighter-hangars','fighter',20,1,260,52000000),
        ('dreadnought','cutter-hangars','cutter',2,1,130,26000000),
        ('heavy-cruiser','crew-escape-pods','escape-pods',1,79,39.5,7900000),
        ('heavy-cruiser','fighter-hangars','fighter',12,1,156,31200000),
        ('heavy-cruiser','cutter-hangars','cutter',2,1,130,26000000),
        ('light-cruiser','crew-escape-pods','escape-pods',1,43,21.5,4300000),
        ('light-cruiser','fighter-hangars','fighter',4,1,52,10400000),
        ('light-cruiser','ships-boat-hangar','ships-boat',1,1,39,7800000),
        ('patrol-frigate','fighter-hangars','fighter',2,1,26,5200000),
        ('raider','fighter-hangars','fighter',2,1,26,5200000),
        ('raider','ships-boat-hangar','ships-boat',1,1,39,7800000),
        ('research-vessel','launch-hangars','life-boat',2,1,52,10400000),
        ('research-vessel','probe-drone-sets','probe-drones',3,1,3,600000),
        ('survey-vessel','launch-hangars','life-boat',2,1,52,10400000),
        ('survey-vessel','probe-drone-sets','probe-drones',4,1,4,800000),
        ('system-monitor','crew-escape-pods','escape-pods',1,45,22.5,4500000),
        ('system-monitor','fighter-hangars','fighter',8,1,104,20800000),
        ('system-monitor','ships-boat-hangar','ships-boat',1,1,39,7800000)
) source(
    class_code,hangar_identifier,hangar_option_code,
    installation_count,basis_quantity,allocated_tons,
    installation_cost_minor
)
JOIN ship_class class
  ON class.class_code=source.class_code;

INSERT INTO ship_class_carried_craft (
    carrier_class_rule_id,hangar_identifier,
    carried_class_rule_id,craft_count,source_locator_id
)
SELECT carrier.ship_class_rule_id,source.hangar_identifier,
       carried.ship_class_rule_id,source.craft_count,
       carrier.source_locator_id
FROM (
    VALUES
        ('destroyer','ships-boat-hangar','ships-boat',1),
        ('dreadnought','fighter-hangars','fighter',20),
        ('dreadnought','cutter-hangars','cutter',2),
        ('heavy-cruiser','fighter-hangars','fighter',12),
        ('heavy-cruiser','cutter-hangars','cutter',2),
        ('light-cruiser','fighter-hangars','fighter',4),
        ('light-cruiser','ships-boat-hangar','ships-boat',1),
        ('patrol-frigate','fighter-hangars','fighter',2),
        ('raider','fighter-hangars','fighter',2),
        ('raider','ships-boat-hangar','ships-boat',1),
        ('research-vessel','launch-hangars','launch',2),
        ('survey-vessel','launch-hangars','launch',2),
        ('system-monitor','fighter-hangars','fighter',8),
        ('system-monitor','ships-boat-hangar','ships-boat',1)
) source(
    carrier_code,hangar_identifier,carried_code,craft_count
)
JOIN ship_class carrier
  ON carrier.class_code=source.carrier_code
JOIN ship_class carried
  ON carried.class_code=source.carried_code;
