CREATE TABLE rule_starship_encounter_effect(
 effect_code text PRIMARY KEY,sensor_skill_code text,sensor_modifier smallint,avoidance_skill_code text,
 damage_dice_per_thrust smallint CHECK(damage_dice_per_thrust>0),may_trigger_second_encounter boolean NOT NULL DEFAULT false,
 uses_trade_goods_generation boolean NOT NULL DEFAULT false,
 CHECK((sensor_skill_code IS NULL)=(sensor_modifier IS NULL)),
 CHECK((avoidance_skill_code IS NULL)=(damage_dice_per_thrust IS NULL))
);
INSERT INTO rule_starship_encounter_effect VALUES
 ('comet-sensor-interference','comms',-2,NULL,NULL,false,false),
 ('collision-debris',NULL,NULL,'piloting',1,false,false),
 ('dust-cloud-interference','comms',-2,NULL,NULL,true,false),
 ('jettisoned-cargo',NULL,NULL,NULL,NULL,false,true);
ALTER TABLE rule_starship_encounter_result ADD CONSTRAINT rule_starship_encounter_result_effect_fk FOREIGN KEY(effect_code) REFERENCES rule_starship_encounter_effect(effect_code);

CREATE OR REPLACE VIEW enc_starship_contact_resolution AS
SELECT c.encounter_id,c.category_rule_id,cat.category_code,r.draw_count,r.final_result_code,result.result_name,result.result_kind,
 result.ship_class_rule_id,ship.class_code,result.effect_code,effect.sensor_skill_code,effect.sensor_modifier,effect.avoidance_skill_code,
 effect.damage_dice_per_thrust,effect.may_trigger_second_encounter,effect.uses_trade_goods_generation
FROM enc_starship_contact c LEFT JOIN cmd_starship_subtype_resolution_receipt r USING(encounter_id)
LEFT JOIN rule_starship_encounter_category cat ON cat.rule_id=c.category_rule_id
LEFT JOIN rule_starship_encounter_result result ON result.result_code=r.final_result_code
LEFT JOIN ship_class ship ON ship.ship_class_rule_id=result.ship_class_rule_id
LEFT JOIN rule_starship_encounter_effect effect ON effect.effect_code=result.effect_code;
