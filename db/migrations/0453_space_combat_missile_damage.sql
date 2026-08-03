CREATE TABLE senc_missile_damage_attempt(
 missile_impact_attempt_id bigint NOT NULL,missile_order smallint NOT NULL,target_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,
 missile_code text NOT NULL REFERENCES rule_ship_missile(missile_code),damage_dice_count smallint NOT NULL CHECK(damage_dice_count>0),
 damage_die_sides smallint NOT NULL CHECK(damage_die_sides>1),armor_snapshot smallint NOT NULL CHECK(armor_snapshot>=0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),PRIMARY KEY(missile_impact_attempt_id,missile_order),
 FOREIGN KEY(missile_impact_attempt_id,missile_order) REFERENCES senc_missile_impact_roll(missile_impact_attempt_id,missile_order),
 FOREIGN KEY(target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id));
CREATE TABLE senc_missile_damage_die(
 missile_impact_attempt_id bigint NOT NULL,missile_order smallint NOT NULL,die_order smallint NOT NULL CHECK(die_order>0),result smallint NOT NULL CHECK(result>0),
 PRIMARY KEY(missile_impact_attempt_id,missile_order,die_order),FOREIGN KEY(missile_impact_attempt_id,missile_order) REFERENCES senc_missile_damage_attempt(missile_impact_attempt_id,missile_order));
CREATE TABLE senc_missile_damage_final_receipt(
 missile_impact_attempt_id bigint NOT NULL,missile_order smallint NOT NULL,rolled_damage smallint NOT NULL CHECK(rolled_damage>0),
 post_armor_damage smallint NOT NULL CHECK(post_armor_damage>=0),single_hit_groups smallint NOT NULL CHECK(single_hit_groups>=0),
 double_hit_groups smallint NOT NULL CHECK(double_hit_groups>=0),triple_hit_groups smallint NOT NULL CHECK(triple_hit_groups>=0),
 damage_status text NOT NULL DEFAULT 'queued' CHECK(damage_status IN('queued','applied')),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(missile_impact_attempt_id,missile_order),FOREIGN KEY(missile_impact_attempt_id,missile_order) REFERENCES senc_missile_damage_attempt(missile_impact_attempt_id,missile_order));

CREATE FUNCTION senc_validate_missile_damage_attempt() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE impact record; missile rule_ship_missile%ROWTYPE; target record; expected_armor integer;
BEGIN
 SELECT roll.hit,launch.missile_code,attempt.campaign_id,salvo.target_vessel_id INTO STRICT impact FROM senc_missile_impact_roll roll
 JOIN senc_missile_impact_attempt attempt USING(missile_impact_attempt_id) JOIN senc_missile_salvo salvo USING(missile_salvo_id)
 JOIN senc_missile_launch_receipt launch ON launch.missile_launch_receipt_id=salvo.launch_receipt_id
 WHERE roll.missile_impact_attempt_id=NEW.missile_impact_attempt_id AND roll.missile_order=NEW.missile_order;
 SELECT * INTO STRICT missile FROM rule_ship_missile WHERE missile_code=impact.missile_code;
 SELECT ship.ship_id,ship.campaign_id,ship.armor_current INTO STRICT target FROM senc_vessel vessel JOIN ship_ship ship USING(ship_id) WHERE vessel.senc_vessel_id=impact.target_vessel_id;
 expected_armor:=target.armor_current;
 IF NOT impact.hit OR NEW.target_ship_id<>target.ship_id OR NEW.campaign_id<>impact.campaign_id OR target.campaign_id<>impact.campaign_id
  OR NEW.missile_code<>impact.missile_code OR NEW.damage_dice_count<>missile.damage_dice_count OR NEW.damage_die_sides<>missile.damage_die_sides
  OR NEW.armor_snapshot<>expected_armor THEN RAISE EXCEPTION 'Missile damage attempt must snapshot one confirmed hit, its profile, target, and current armor' USING ERRCODE='23514'; END IF; RETURN NEW;
END $$;
CREATE TRIGGER senc_missile_damage_attempt_valid BEFORE INSERT ON senc_missile_damage_attempt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_damage_attempt();
CREATE FUNCTION senc_validate_missile_damage_die() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE a senc_missile_damage_attempt%ROWTYPE; BEGIN
 SELECT * INTO STRICT a FROM senc_missile_damage_attempt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order FOR UPDATE;
 IF EXISTS(SELECT 1 FROM senc_missile_damage_final_receipt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order)
  OR NEW.die_order>a.damage_dice_count OR NEW.result>a.damage_die_sides THEN RAISE EXCEPTION 'Missile damage die exceeds its unfinalized profile' USING ERRCODE='23514'; END IF; RETURN NEW; END $$;
CREATE TRIGGER senc_missile_damage_die_valid BEFORE INSERT ON senc_missile_damage_die FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_damage_die();
CREATE FUNCTION senc_validate_missile_damage_final() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE a senc_missile_damage_attempt%ROWTYPE;n integer;total integer;singles integer;doubles integer;triples integer;excess integer;net integer;
BEGIN SELECT * INTO STRICT a FROM senc_missile_damage_attempt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order FOR UPDATE;
 SELECT count(*),coalesce(sum(result),0) INTO n,total FROM senc_missile_damage_die WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order;
 net:=greatest(0,total-a.armor_snapshot);
 IF net<=44 THEN SELECT single_hit_groups,double_hit_groups,triple_hit_groups INTO singles,doubles,triples FROM rule_space_combat_damage_band WHERE damage_range @> net;
 ELSE excess:=net-44;singles:=floor(excess/3);doubles:=floor(excess/6);triples:=2;END IF;
 IF n<>a.damage_dice_count OR NEW.rolled_damage<>total OR NEW.post_armor_damage<>net OR NEW.single_hit_groups<>singles OR NEW.double_hit_groups<>doubles OR NEW.triple_hit_groups<>triples
 THEN RAISE EXCEPTION 'Missile damage final receipt fails independent dice, armor, or damage-band recomputation' USING ERRCODE='23514'; END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_damage_final_valid BEFORE INSERT ON senc_missile_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_damage_final();

CREATE TABLE senc_missile_damage_location_group_roll(
 missile_impact_attempt_id bigint NOT NULL,missile_order smallint NOT NULL,group_order smallint NOT NULL CHECK(group_order>0),hit_multiplicity smallint NOT NULL CHECK(hit_multiplicity BETWEEN 1 AND 3),
 first_die smallint NOT NULL CHECK(first_die BETWEEN 1 AND 6),second_die smallint NOT NULL CHECK(second_die BETWEEN 1 AND 6),roll_total smallint NOT NULL CHECK(roll_total=first_die+second_die),
 PRIMARY KEY(missile_impact_attempt_id,missile_order,group_order),FOREIGN KEY(missile_impact_attempt_id,missile_order) REFERENCES senc_missile_damage_final_receipt(missile_impact_attempt_id,missile_order));
CREATE FUNCTION senc_validate_missile_location_group() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE f senc_missile_damage_final_receipt%ROWTYPE;existing integer;BEGIN
 SELECT * INTO STRICT f FROM senc_missile_damage_final_receipt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order FOR UPDATE;
 SELECT count(*) INTO existing FROM senc_missile_damage_location_group_roll WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order AND hit_multiplicity=NEW.hit_multiplicity;
 IF f.damage_status<>'queued' OR existing>=(CASE NEW.hit_multiplicity WHEN 1 THEN f.single_hit_groups WHEN 2 THEN f.double_hit_groups ELSE f.triple_hit_groups END)
  OR NEW.group_order<>(SELECT count(*)+1 FROM senc_missile_damage_location_group_roll WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order)
 THEN RAISE EXCEPTION 'Missile location group exceeds its independent damage-band sequence' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_missile_location_group_valid BEFORE INSERT ON senc_missile_damage_location_group_roll FOR EACH ROW EXECUTE FUNCTION senc_validate_missile_location_group();

CREATE TABLE senc_missile_damage_location_hit_receipt(
 missile_damage_location_hit_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,missile_impact_attempt_id bigint NOT NULL,missile_order smallint NOT NULL,group_order smallint NOT NULL,hit_order smallint NOT NULL CHECK(hit_order BETWEEN 1 AND 3),
 target_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,routing_column text NOT NULL CHECK(routing_column IN('external','internal','small-craft')),rolled_location text NOT NULL,applied_location text NOT NULL,effect_code text NOT NULL,
 hull_before smallint NOT NULL,hull_after smallint NOT NULL,structure_before smallint NOT NULL,structure_after smallint NOT NULL,armor_before smallint NOT NULL,armor_after smallint NOT NULL,
 ship_version_before bigint NOT NULL,ship_version_after bigint NOT NULL CHECK(ship_version_after=ship_version_before+1),recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(missile_impact_attempt_id,missile_order,group_order,hit_order),FOREIGN KEY(missile_impact_attempt_id,missile_order,group_order) REFERENCES senc_missile_damage_location_group_roll(missile_impact_attempt_id,missile_order,group_order),
 FOREIGN KEY(target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id));

CREATE FUNCTION senc_apply_next_missile_location_hit(p_attempt bigint,p_missile smallint) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE f senc_missile_damage_final_receipt%ROWTYPE;g record;s record;loc rule_space_combat_hit_location%ROWTYPE;grp smallint;hitno smallint;route text;rolled text;applied text;effect text;rid bigint;remaining integer;
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
 effect:=CASE applied WHEN 'hull' THEN 'reduce-hull' WHEN 'structure' THEN 'reduce-structure' WHEN 'armor' THEN 'reduce-armor' WHEN 'crew' THEN 'roll-crew-damage' ELSE 'system-hit' END;
 UPDATE ship_ship SET hull_current=CASE WHEN applied='hull' THEN greatest(0,hull_current-1) ELSE hull_current END,structure_current=CASE WHEN applied='structure' THEN greatest(0,structure_current-1) ELSE structure_current END,
  armor_current=CASE WHEN applied='armor' THEN greatest(0,armor_current-1) ELSE armor_current END,concurrency_version=concurrency_version+1,
  lifecycle_status=CASE WHEN applied='structure' AND structure_current<=1 THEN 'destroyed' ELSE lifecycle_status END,ended_at=CASE WHEN applied='structure' AND structure_current<=1 THEN coalesce(ended_at,clock_timestamp()) ELSE ended_at END WHERE ship_id=s.ship_id;
 INSERT INTO senc_missile_damage_location_hit_receipt(missile_impact_attempt_id,missile_order,group_order,hit_order,target_ship_id,campaign_id,routing_column,rolled_location,applied_location,effect_code,hull_before,hull_after,structure_before,structure_after,armor_before,armor_after,ship_version_before,ship_version_after)
 VALUES(p_attempt,p_missile,grp,hitno,s.ship_id,s.campaign_id,route,rolled,applied,effect,s.hull_current,CASE WHEN applied='hull' THEN greatest(0,s.hull_current-1) ELSE s.hull_current END,s.structure_current,CASE WHEN applied='structure' THEN greatest(0,s.structure_current-1) ELSE s.structure_current END,s.armor_current,CASE WHEN applied='armor' THEN greatest(0,s.armor_current-1) ELSE s.armor_current END,s.concurrency_version,s.concurrency_version+1) RETURNING missile_damage_location_hit_receipt_id INTO rid;
 SELECT sum(hit_multiplicity)-count(h.missile_damage_location_hit_receipt_id) INTO remaining FROM senc_missile_damage_location_group_roll groups LEFT JOIN senc_missile_damage_location_hit_receipt h USING(missile_impact_attempt_id,missile_order,group_order) WHERE groups.missile_impact_attempt_id=p_attempt AND groups.missile_order=p_missile;
 IF remaining=0 THEN UPDATE senc_missile_damage_final_receipt SET damage_status='applied' WHERE missile_impact_attempt_id=p_attempt AND missile_order=p_missile;END IF;RETURN rid;END $$;

CREATE TABLE senc_nuclear_missile_radiation_hit_receipt(
 missile_impact_attempt_id bigint NOT NULL,missile_order smallint NOT NULL,target_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,armor_dm smallint NOT NULL CHECK(armor_dm<=0),
 die_one smallint NOT NULL CHECK(die_one BETWEEN 1 AND 6),die_two smallint NOT NULL CHECK(die_two BETWEEN 1 AND 6),unmodified_roll smallint NOT NULL CHECK(unmodified_roll=die_one+die_two),modified_roll smallint NOT NULL CHECK(modified_roll=unmodified_roll+armor_dm),
 target_scope text NOT NULL CHECK(target_scope IN('none','one-random','all')),damage_dice_count smallint NOT NULL CHECK(damage_dice_count IN(0,2,4)),outcome_code text NOT NULL,recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(missile_impact_attempt_id,missile_order),FOREIGN KEY(missile_impact_attempt_id,missile_order) REFERENCES senc_missile_damage_final_receipt(missile_impact_attempt_id,missile_order),FOREIGN KEY(target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id));
CREATE FUNCTION senc_validate_nuclear_missile_radiation() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE a senc_missile_damage_attempt%ROWTYPE;expected record;bounded integer;BEGIN
 SELECT * INTO STRICT a FROM senc_missile_damage_attempt WHERE missile_impact_attempt_id=NEW.missile_impact_attempt_id AND missile_order=NEW.missile_order FOR UPDATE;
 bounded:=greatest(2,least(12,NEW.modified_roll));
 SELECT band.* INTO STRICT expected FROM rule_space_combat_crew_damage_band band JOIN rule_rule r ON r.rule_id=band.hit_location_rule_id WHERE r.rule_code='combat.space.hit-locations' AND band.damage_kind='radiation' AND band.roll_range @> bounded;
 IF a.missile_code<>'nuclear' OR NEW.target_ship_id<>a.target_ship_id OR NEW.campaign_id<>a.campaign_id OR NEW.armor_dm<>-a.armor_snapshot
  OR NEW.target_scope<>expected.target_scope OR NEW.damage_dice_count<>expected.damage_dice_count OR NEW.outcome_code<>expected.outcome_code
 THEN RAISE EXCEPTION 'Nuclear missile radiation hit must apply target armor as a negative crew-hit DM' USING ERRCODE='23514';END IF;RETURN NEW;END $$;
CREATE TRIGGER senc_nuclear_missile_radiation_valid BEFORE INSERT ON senc_nuclear_missile_radiation_hit_receipt FOR EACH ROW EXECUTE FUNCTION senc_validate_nuclear_missile_radiation();

CREATE FUNCTION senc_reject_missile_damage_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
 IF TG_TABLE_NAME='senc_missile_damage_final_receipt' AND TG_OP='UPDATE' AND OLD.damage_status='queued' AND NEW.damage_status='applied' AND (to_jsonb(OLD)-'damage_status')=(to_jsonb(NEW)-'damage_status') THEN RETURN NEW;END IF;
 RAISE EXCEPTION 'Missile damage dice and receipts are immutable';END $$;
CREATE TRIGGER senc_missile_damage_attempt_immutable BEFORE UPDATE OR DELETE ON senc_missile_damage_attempt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_damage_mutation();
CREATE TRIGGER senc_missile_damage_die_immutable BEFORE UPDATE OR DELETE ON senc_missile_damage_die FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_damage_mutation();
CREATE TRIGGER senc_missile_damage_final_immutable BEFORE UPDATE OR DELETE ON senc_missile_damage_final_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_damage_mutation();
CREATE TRIGGER senc_missile_location_group_immutable BEFORE UPDATE OR DELETE ON senc_missile_damage_location_group_roll FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_damage_mutation();
CREATE TRIGGER senc_missile_location_hit_immutable BEFORE UPDATE OR DELETE ON senc_missile_damage_location_hit_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_damage_mutation();
CREATE TRIGGER senc_nuclear_missile_radiation_immutable BEFORE UPDATE OR DELETE ON senc_nuclear_missile_radiation_hit_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_missile_damage_mutation();
