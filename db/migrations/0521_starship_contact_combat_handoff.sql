INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Starship Encounters > Encounter Range',
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Encounter Range' ELSE 'Cepheus Engine v9.1, Encounter Range' END
FROM src_artifact a JOIN src_work w USING(source_work_id)
WHERE (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book3/starship-encounters.md')
 OR (w.work_code='cepheus-engine.ogn' AND a.source_uri='https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-starship-encounters/')
ON CONFLICT DO NOTHING;
WITH p AS(SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'encounter.starship-combat-handoff','Starship Contact Combat Handoff','encounter','approved',
 'An established ship-class contact may initialize a forming space-combat engagement at the contact range once both campaign ship instances are identified.' FROM p;
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='encounter.starship-combat-handoff' AND l.heading_path='Starship Encounters > Encounter Range'
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE cmd_starship_combat_handoff_receipt(
 starship_combat_handoff_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,encounter_id bigint NOT NULL UNIQUE REFERENCES enc_starship_contact,
 campaign_id bigint NOT NULL REFERENCES camp_campaign,engagement_id bigint NOT NULL UNIQUE REFERENCES senc_engagement,
 player_ship_id bigint NOT NULL,contact_ship_id bigint NOT NULL,player_force_id bigint NOT NULL,contact_force_id bigint NOT NULL,
 player_vessel_id bigint NOT NULL,contact_vessel_id bigint NOT NULL,initial_range_code text NOT NULL REFERENCES rule_space_range_band,
 resolved_result_code text NOT NULL REFERENCES rule_starship_encounter_result,source_command_id bigint REFERENCES cmd_command,initialized_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(player_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),FOREIGN KEY(contact_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id),
 FOREIGN KEY(player_force_id,engagement_id,campaign_id) REFERENCES senc_force(force_id,engagement_id,campaign_id),FOREIGN KEY(contact_force_id,engagement_id,campaign_id) REFERENCES senc_force(force_id,engagement_id,campaign_id),
 FOREIGN KEY(player_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),FOREIGN KEY(contact_vessel_id,engagement_id,campaign_id) REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 CHECK(player_ship_id<>contact_ship_id),CHECK(player_force_id<>contact_force_id),CHECK(player_vessel_id<>contact_vessel_id)
);

CREATE FUNCTION enc_initialize_starship_contact_combat(p_encounter_id bigint,p_player_ship_id bigint,p_contact_ship_id bigint,p_source_command_id bigint DEFAULT NULL) RETURNS bigint LANGUAGE plpgsql AS $$
DECLARE contact record;player ship_ship%ROWTYPE;target ship_ship%ROWTYPE;engagement bigint;player_force bigint;contact_force bigint;player_vessel bigint;contact_vessel bigint;
BEGIN
 SELECT e.campaign_id,c.final_range,c.contact_status,res.final_result_code,res.result_kind,res.ship_class_rule_id INTO STRICT contact
 FROM enc_encounter e JOIN enc_starship_contact c USING(encounter_id) JOIN enc_starship_contact_resolution res USING(encounter_id)
 WHERE e.encounter_id=p_encounter_id FOR UPDATE OF e,c;
 IF contact.contact_status<>'established' OR contact.result_kind<>'ship-class' OR contact.final_range IS NULL THEN RAISE EXCEPTION 'Starship contact is not a concrete established ship-class contact' USING ERRCODE='23514';END IF;
 SELECT * INTO STRICT player FROM ship_ship WHERE ship_id=p_player_ship_id FOR UPDATE;SELECT * INTO STRICT target FROM ship_ship WHERE ship_id=p_contact_ship_id FOR UPDATE;
 IF player.campaign_id<>contact.campaign_id OR target.campaign_id<>contact.campaign_id OR target.ship_class_rule_id<>contact.ship_class_rule_id OR player.lifecycle_status<>'active' OR target.lifecycle_status<>'active' THEN RAISE EXCEPTION 'Combat handoff ship scope, class, or lifecycle is invalid' USING ERRCODE='23514';END IF;
 INSERT INTO senc_engagement(encounter_id,campaign_id,procedure_code) VALUES(p_encounter_id,contact.campaign_id,'cepheus-standard') RETURNING engagement_id INTO engagement;
 INSERT INTO senc_force(engagement_id,campaign_id,side_code,force_name) VALUES(engagement,contact.campaign_id,'player','Player Vessel') RETURNING force_id INTO player_force;
 INSERT INTO senc_force(engagement_id,campaign_id,side_code,force_name) VALUES(engagement,contact.campaign_id,'contact','Encounter Contact') RETURNING force_id INTO contact_force;
 INSERT INTO senc_vessel(engagement_id,campaign_id,force_id,ship_id,thrust_current) VALUES(engagement,contact.campaign_id,player_force,p_player_ship_id,(SELECT maneuver_rating FROM ship_class WHERE ship_class_rule_id=player.ship_class_rule_id)) RETURNING senc_vessel_id INTO player_vessel;
 INSERT INTO senc_vessel(engagement_id,campaign_id,force_id,ship_id,thrust_current) VALUES(engagement,contact.campaign_id,contact_force,p_contact_ship_id,(SELECT maneuver_rating FROM ship_class WHERE ship_class_rule_id=target.ship_class_rule_id)) RETURNING senc_vessel_id INTO contact_vessel;
 INSERT INTO senc_vessel_range(engagement_id,campaign_id,first_vessel_id,second_vessel_id,range_band_code) VALUES(engagement,contact.campaign_id,least(player_vessel,contact_vessel),greatest(player_vessel,contact_vessel),contact.final_range);
 INSERT INTO cmd_starship_combat_handoff_receipt(encounter_id,campaign_id,engagement_id,player_ship_id,contact_ship_id,player_force_id,contact_force_id,player_vessel_id,contact_vessel_id,initial_range_code,resolved_result_code,source_command_id)
 VALUES(p_encounter_id,contact.campaign_id,engagement,p_player_ship_id,p_contact_ship_id,player_force,contact_force,player_vessel,contact_vessel,contact.final_range,contact.final_result_code,p_source_command_id);
 RETURN engagement;
END $$;
CREATE TRIGGER cmd_starship_combat_handoff_immutable BEFORE UPDATE OR DELETE ON cmd_starship_combat_handoff_receipt FOR EACH ROW EXECUTE FUNCTION enc_reject_starship_subtype_mutation();
