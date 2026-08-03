CREATE TABLE rule_space_combat_crew_damage_band (
    hit_location_rule_id bigint NOT NULL REFERENCES rule_rule(rule_id),
    damage_kind text NOT NULL CHECK (damage_kind IN ('normal','radiation')),
    roll_range int4range NOT NULL,
    target_scope text NOT NULL CHECK (target_scope IN ('none','one-random','all')),
    damage_dice_count smallint NOT NULL CHECK (damage_dice_count IN (0,2,4)),
    damage_die_sides smallint CHECK (damage_die_sides=6),
    radiation_multiplier_rads smallint,
    outcome_code text NOT NULL,
    PRIMARY KEY (hit_location_rule_id,damage_kind,roll_range),
    CHECK (NOT isempty(roll_range) AND lower_inc(roll_range) AND NOT upper_inc(roll_range)),
    CHECK ((damage_dice_count=0)=(damage_die_sides IS NULL)),
    CHECK ((damage_kind='radiation')=(radiation_multiplier_rads=10)),
    CHECK (damage_dice_count>0 OR target_scope='none')
);

WITH r AS (SELECT rule_id FROM rule_rule WHERE rule_code='combat.space.hit-locations'),
bands(damage_kind,roll_range,target_scope,dice_count,die_sides,multiplier,outcome_code) AS (
 VALUES
 ('normal',int4range(2,5,'[)'),'none',0,NULL,NULL,'lucky-escape'),
 ('normal',int4range(5,9,'[)'),'one-random',2,6,NULL,'one-crew-2d6'),
 ('normal',int4range(9,11,'[)'),'one-random',4,6,NULL,'one-crew-4d6'),
 ('normal',int4range(11,12,'[)'),'all',2,6,NULL,'all-crew-2d6'),
 ('normal',int4range(12,13,'[)'),'all',4,6,NULL,'all-crew-4d6'),
 ('radiation',int4range(2,5,'[)'),'none',0,NULL,10,'lucky-escape'),
 ('radiation',int4range(5,9,'[)'),'one-random',2,6,10,'one-crew-2d6-times-10-rads'),
 ('radiation',int4range(9,11,'[)'),'one-random',4,6,10,'one-crew-4d6-times-10-rads'),
 ('radiation',int4range(11,12,'[)'),'all',2,6,10,'all-crew-2d6-times-10-rads'),
 ('radiation',int4range(12,13,'[)'),'all',4,6,10,'all-crew-4d6-times-10-rads')
)
INSERT INTO rule_space_combat_crew_damage_band
SELECT r.rule_id,b.* FROM r CROSS JOIN bands b;

ALTER TABLE rule_space_combat_crew_damage_band ADD CONSTRAINT rule_space_combat_crew_damage_no_overlap
EXCLUDE USING gist (hit_location_rule_id WITH =,damage_kind WITH =,roll_range WITH &&);

CREATE FUNCTION rule_reject_space_combat_crew_damage_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Published space combat crew damage bands are immutable'; END $$;
CREATE TRIGGER rule_space_combat_crew_damage_immutable
BEFORE UPDATE OR DELETE ON rule_space_combat_crew_damage_band
FOR EACH ROW EXECUTE FUNCTION rule_reject_space_combat_crew_damage_mutation();
