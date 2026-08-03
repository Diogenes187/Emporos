CREATE OR REPLACE FUNCTION senc_apply_next_missile_location_hit(p_attempt bigint,p_missile smallint) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE f senc_missile_damage_final_receipt%ROWTYPE;g record;s record;loc rule_space_combat_hit_location%ROWTYPE;grp smallint;hitno smallint;route text;rolled text;applied text;effect text;rid bigint;remaining integer;
 state_before smallint;state_after smallint;overflow text;new_status text;attack_dm smallint:=0;sensor_dm smallint:=0;instance_value smallint:=1;secondary boolean:=false;
BEGIN SELECT * INTO STRICT f FROM senc_missile_damage_final_receipt WHERE missile_impact_attempt_id=p_attempt AND missile_order=p_missile FOR UPDATE;
 SELECT groups.group_order,count(h.missile_damage_location_hit_receipt_id)::smallint+1 INTO grp,hitno FROM senc_missile_damage_location_group_roll groups LEFT JOIN senc_missile_damage_location_hit_receipt h
 ON h.missile_impact_attempt_id=groups.missile_impact_attempt_id AND h.missile_order=groups.missile_order AND h.group_order=groups.group_order
 WHERE groups.missile_impact_attempt_id=p_attempt AND groups.missile_order=p_missile GROUP BY groups.group_order,groups.hit_multiplicity HAVING count(h.missile_damage_location_hit_receipt_id)<groups.hit_multiplicity ORDER BY groups.group_order LIMIT 1;
 IF grp IS NULL THEN RAISE EXCEPTION 'All missile location hits are already applied' USING ERRCODE='23514';END IF;
 SELECT * INTO STRICT g FROM senc_missile_damage_location_group_roll WHERE missile_impact_attempt_id=p_attempt AND missile_order=p_missile AND group_order=grp;
 SELECT ship.*,class.hull_tons INTO STRICT s FROM senc_missile_damage_attempt a JOIN ship_ship ship ON ship.ship_id=a.target_ship_id JOIN ship_class class USING(ship_class_rule_id)
 WHERE a.missile_impact_attempt_id=p_attempt AND a.missile_order=p_missile FOR UPDATE OF ship;
 SELECT * INTO STRICT loc FROM rule_space_combat_hit_location WHERE roll_total=g.roll_total;
 IF s.hull_tons<100 THEN route:='small-craft';rolled:=loc.small_craft_location;ELSIF s.hull_current>0 THEN route:='external';rolled:=loc.external_vessel_location;ELSE route:='internal';rolled:=loc.internal_vessel_location;END IF;applied:=rolled;
 IF applied='hull' AND s.hull_current=0 THEN applied:=loc.internal_vessel_location;route:='internal';END IF;
 IF applied='armor' AND s.armor_current=0 THEN applied:='hull';IF s.hull_current=0 THEN applied:=loc.internal_vessel_location;route:='internal';END IF;END IF;
 IF applied IN('turret','bay','j-drive','m-drive','power-plant','sensors','bridge','fuel','hold') THEN
  SELECT hit_count INTO state_before FROM senc_ship_system_damage_state WHERE ship_id=s.ship_id AND system_code=applied AND system_instance=instance_value FOR UPDATE;
  state_before:=coalesce(state_before,0);
  IF state_before>=3 THEN SELECT overflow_location_code INTO STRICT overflow FROM rule_space_combat_location_effect e JOIN rule_rule r ON r.rule_id=e.hit_location_rule_id WHERE r.rule_code='combat.space.hit-locations' AND location_code=applied AND hit_ordinal=4;applied:=overflow;state_after:=state_before;
  ELSE state_after:=state_before+1;SELECT effect_code,attack_dm,sensor_dm INTO STRICT effect,attack_dm,sensor_dm FROM rule_space_combat_location_effect e JOIN rule_rule r ON r.rule_id=e.hit_location_rule_id WHERE r.rule_code='combat.space.hit-locations' AND location_code=applied AND hit_ordinal=state_after;END IF;
 END IF;
 IF effect IS NULL THEN effect:=CASE applied WHEN 'hull' THEN 'reduce-hull' WHEN 'structure' THEN 'reduce-structure' WHEN 'armor' THEN 'reduce-armor' WHEN 'crew' THEN 'roll-crew-damage' ELSE 'system-hit' END;END IF;
 secondary:=effect IN('roll-crew-damage','crew-normal-hit','crew-radiation-hit','minor-leak-1d6-tons-hour','destroy-1d6-times-10-percent');
 UPDATE ship_ship SET hull_current=CASE WHEN applied='hull' THEN greatest(0,hull_current-1) ELSE hull_current END,structure_current=CASE WHEN applied='structure' THEN greatest(0,structure_current-1) ELSE structure_current END,
  armor_current=CASE WHEN applied='armor' THEN greatest(0,armor_current-1) ELSE armor_current END,concurrency_version=concurrency_version+1,lifecycle_status=CASE WHEN applied='structure' AND structure_current<=1 THEN 'destroyed' ELSE lifecycle_status END,
  ended_at=CASE WHEN applied='structure' AND structure_current<=1 THEN coalesce(ended_at,clock_timestamp()) ELSE ended_at END WHERE ship_id=s.ship_id;
 IF state_before IS NOT NULL AND state_after>state_before THEN new_status:=CASE state_after WHEN 1 THEN 'damaged' WHEN 2 THEN 'disabled' ELSE 'destroyed' END;
  INSERT INTO senc_ship_system_damage_state(ship_id,campaign_id,system_code,system_instance,hit_count,system_status,attack_dm,sensor_dm) VALUES(s.ship_id,s.campaign_id,rolled,instance_value,state_after,new_status,attack_dm,sensor_dm)
  ON CONFLICT(ship_id,system_code,system_instance) DO UPDATE SET hit_count=EXCLUDED.hit_count,system_status=EXCLUDED.system_status,attack_dm=CASE WHEN EXCLUDED.hit_count=1 THEN EXCLUDED.attack_dm ELSE senc_ship_system_damage_state.attack_dm END,
   sensor_dm=CASE WHEN EXCLUDED.hit_count=1 THEN EXCLUDED.sensor_dm ELSE senc_ship_system_damage_state.sensor_dm END,concurrency_version=senc_ship_system_damage_state.concurrency_version+1,updated_at=clock_timestamp();END IF;
 INSERT INTO senc_missile_damage_location_hit_receipt(missile_impact_attempt_id,missile_order,group_order,hit_order,target_ship_id,campaign_id,routing_column,rolled_location,applied_location,effect_code,hull_before,hull_after,structure_before,structure_after,armor_before,armor_after,ship_version_before,ship_version_after)
 VALUES(p_attempt,p_missile,grp,hitno,s.ship_id,s.campaign_id,route,rolled,applied,effect,s.hull_current,CASE WHEN applied='hull' THEN greatest(0,s.hull_current-1) ELSE s.hull_current END,s.structure_current,CASE WHEN applied='structure' THEN greatest(0,s.structure_current-1) ELSE s.structure_current END,s.armor_current,CASE WHEN applied='armor' THEN greatest(0,s.armor_current-1) ELSE s.armor_current END,s.concurrency_version,s.concurrency_version+1) RETURNING missile_damage_location_hit_receipt_id INTO rid;
 SELECT sum(hit_multiplicity)-count(h.missile_damage_location_hit_receipt_id) INTO remaining FROM senc_missile_damage_location_group_roll groups LEFT JOIN senc_missile_damage_location_hit_receipt h USING(missile_impact_attempt_id,missile_order,group_order) WHERE groups.missile_impact_attempt_id=p_attempt AND groups.missile_order=p_missile;
 IF remaining=0 THEN UPDATE senc_missile_damage_final_receipt SET damage_status='applied' WHERE missile_impact_attempt_id=p_attempt AND missile_order=p_missile;END IF;RETURN rid;END $$;
