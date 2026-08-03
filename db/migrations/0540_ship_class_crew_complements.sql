-- Emporos derives playable stations from each published crew complement because
-- the inherited catalogue records crew totals but contains no position rows.
WITH complement AS(
 SELECT ship_class_rule_id,GREATEST(1,characteristic_value::integer) AS crew
 FROM ship_class_characteristic WHERE characteristic_code='crew'
), roles AS(
 SELECT complement.ship_class_rule_id,definition.crew_position_rule_id,source.position_count,source.required
 FROM complement CROSS JOIN LATERAL(VALUES
  ('master',1,true),('pilot',CASE WHEN crew>=2 THEN 1 ELSE 0 END,true),
  ('engineer',CASE WHEN crew>=3 THEN 1 ELSE 0 END,true),('navigator',CASE WHEN crew>=4 THEN 1 ELSE 0 END,true),
  ('steward',CASE WHEN crew>=5 THEN 1 ELSE 0 END,false),('medic',CASE WHEN crew>=6 THEN 1 ELSE 0 END,false),
  ('gunner',GREATEST(crew-6,0),false)
 ) source(position_code,position_count,required)
 JOIN ship_crew_position_definition definition USING(position_code)
 WHERE source.position_count>0
)
INSERT INTO ship_class_crew_position(ship_class_rule_id,crew_position_rule_id,position_count,required)
SELECT ship_class_rule_id,crew_position_rule_id,position_count,required FROM roles
ON CONFLICT(ship_class_rule_id,crew_position_rule_id) DO NOTHING;

INSERT INTO ship_crew_position(ship_id,campaign_id,crew_position_rule_id,position_identifier)
SELECT ship.ship_id,ship.campaign_id,template.crew_position_rule_id,
 definition.position_code||'-'||lpad(series::text,2,'0')
FROM ship_ship ship JOIN ship_class_crew_position template USING(ship_class_rule_id)
JOIN ship_crew_position_definition definition USING(crew_position_rule_id)
CROSS JOIN LATERAL generate_series(1,template.position_count) series
ON CONFLICT(ship_id,position_identifier) DO NOTHING;
