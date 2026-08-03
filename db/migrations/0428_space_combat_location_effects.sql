CREATE TABLE rule_space_combat_location_effect (
    hit_location_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),
    location_code text NOT NULL,
    hit_ordinal smallint NOT NULL CHECK (hit_ordinal BETWEEN 1 AND 4),
    effect_code text NOT NULL,
    attack_dm smallint NOT NULL DEFAULT 0,
    sensor_dm smallint NOT NULL DEFAULT 0,
    thrust_factor numeric(4,3),
    overflow_location_code text,
    PRIMARY KEY (hit_location_rule_id,location_code,hit_ordinal),
    CHECK (location_code IN (
        'hull','structure','armor','turret','bay','j-drive','m-drive',
        'power-plant','sensors','bridge','fuel','hold','crew'
    )),
    CHECK (overflow_location_code IS NULL OR overflow_location_code IN ('hull','structure')),
    CHECK (thrust_factor IS NULL OR thrust_factor BETWEEN 0 AND 1)
);

WITH r AS (
    SELECT rule_id FROM rule_rule WHERE rule_code='combat.space.hit-locations'
), effects(location_code,hit_ordinal,effect_code,attack_dm,sensor_dm,thrust_factor,overflow_location_code) AS (
    VALUES
    ('hull',1,'reduce-hull',0,0,NULL,NULL),
    ('hull',2,'reduce-hull',0,0,NULL,NULL),
    ('hull',3,'reduce-hull',0,0,NULL,NULL),
    ('hull',4,'route-same-row-internal',0,0,NULL,NULL),
    ('structure',1,'reduce-structure',0,0,NULL,NULL),
    ('structure',2,'reduce-structure',0,0,NULL,NULL),
    ('structure',3,'reduce-structure',0,0,NULL,NULL),
    ('structure',4,'reduce-structure',0,0,NULL,NULL),
    ('armor',1,'reduce-armor',0,0,NULL,NULL),
    ('armor',2,'reduce-armor',0,0,NULL,NULL),
    ('armor',3,'reduce-armor',0,0,NULL,NULL),
    ('armor',4,'overflow',0,0,NULL,'hull'),
    ('turret',1,'tracking-damaged',-2,0,NULL,NULL),
    ('turret',2,'disabled',0,0,NULL,NULL),
    ('turret',3,'destroyed',0,0,NULL,NULL),
    ('turret',4,'overflow',0,0,NULL,'hull'),
    ('bay',1,'targeting-damaged',-2,0,NULL,NULL),
    ('bay',2,'disabled',0,0,NULL,NULL),
    ('bay',3,'destroyed',0,0,NULL,NULL),
    ('bay',4,'overflow',0,0,NULL,'structure'),
    ('j-drive',1,'engineering-dm',0,0,NULL,NULL),
    ('j-drive',2,'disabled',0,0,NULL,NULL),
    ('j-drive',3,'destroyed',0,0,NULL,NULL),
    ('j-drive',4,'overflow',0,0,NULL,'structure'),
    ('m-drive',1,'reduce-thrust-one',0,0,NULL,NULL),
    ('m-drive',2,'halve-thrust',0,0,0.500,NULL),
    ('m-drive',3,'disabled',0,0,0.000,NULL),
    ('m-drive',4,'overflow',0,0,NULL,'hull'),
    ('power-plant',1,'damaged',0,0,NULL,NULL),
    ('power-plant',2,'crew-radiation-hit',0,0,NULL,NULL),
    ('power-plant',3,'destroyed-disable-ship',0,0,NULL,NULL),
    ('power-plant',4,'overflow',0,0,NULL,'structure'),
    ('sensors',1,'sensor-comms-dm',0,-2,NULL,NULL),
    ('sensors',2,'disabled',0,0,NULL,NULL),
    ('sensors',3,'destroyed',0,0,NULL,NULL),
    ('sensors',4,'overflow',0,0,NULL,'hull'),
    ('bridge',1,'crew-normal-hit',0,0,NULL,NULL),
    ('bridge',2,'disabled',-2,0,NULL,NULL),
    ('bridge',3,'destroyed',0,0,NULL,NULL),
    ('bridge',4,'overflow',0,0,NULL,'structure'),
    ('fuel',1,'minor-leak-1d6-tons-hour',0,0,NULL,NULL),
    ('fuel',2,'destroy-1d6-times-10-percent',0,0,NULL,NULL),
    ('fuel',3,'tank-destroyed',0,0,NULL,NULL),
    ('fuel',4,'overflow',0,0,NULL,'structure'),
    ('hold',1,'destroy-1d6-times-10-percent',0,0,NULL,NULL),
    ('hold',2,'destroy-1d6-times-10-percent',0,0,NULL,NULL),
    ('hold',3,'hold-and-contents-destroyed',0,0,NULL,NULL),
    ('hold',4,'overflow',0,0,NULL,'structure'),
    ('crew',1,'roll-crew-damage',0,0,NULL,NULL),
    ('crew',2,'roll-crew-damage',0,0,NULL,NULL),
    ('crew',3,'roll-crew-damage',0,0,NULL,NULL),
    ('crew',4,'roll-crew-damage',0,0,NULL,NULL)
)
INSERT INTO rule_space_combat_location_effect
SELECT r.rule_id,e.* FROM r CROSS JOIN effects e;

CREATE FUNCTION rule_reject_space_combat_location_effect_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Published space combat location effects are immutable';
END $$;

CREATE TRIGGER rule_space_combat_location_effect_immutable
BEFORE UPDATE OR DELETE ON rule_space_combat_location_effect
FOR EACH ROW EXECUTE FUNCTION rule_reject_space_combat_location_effect_mutation();
