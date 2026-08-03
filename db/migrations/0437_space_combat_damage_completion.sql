CREATE TABLE senc_mount_damage_application_receipt(
 mount_attack_declaration_id bigint PRIMARY KEY REFERENCES senc_mount_damage_final_receipt(mount_attack_declaration_id),
 expected_hit_count smallint NOT NULL CHECK(expected_hit_count>0),applied_hit_count smallint NOT NULL CHECK(applied_hit_count=expected_hit_count),
 required_secondary_count smallint NOT NULL CHECK(required_secondary_count>=0),resolved_secondary_count smallint NOT NULL CHECK(resolved_secondary_count=required_secondary_count),
 target_ship_id bigint NOT NULL,campaign_id bigint NOT NULL,target_ship_version_after bigint NOT NULL CHECK(target_ship_version_after>0),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),FOREIGN KEY(target_ship_id,campaign_id) REFERENCES ship_ship(ship_id,campaign_id)
);
CREATE OR REPLACE FUNCTION senc_reject_staged_damage_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_TABLE_NAME='senc_mount_damage_final_receipt' AND TG_OP='UPDATE'
  AND OLD.damage_status='queued' AND NEW.damage_status='applied'
  AND (to_jsonb(NEW)-'damage_status')=(to_jsonb(OLD)-'damage_status')
  AND EXISTS(SELECT 1 FROM senc_mount_damage_application_receipt WHERE mount_attack_declaration_id=OLD.mount_attack_declaration_id) THEN RETURN NEW;
 END IF;
 RAISE EXCEPTION 'Staged weapon damage receipts and dice are immutable';
END $$;
CREATE FUNCTION senc_finalize_mount_damage_application() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected integer; applied integer; required integer; resolved integer; target record;
BEGIN
 SELECT sum(hit_multiplicity) INTO expected FROM senc_damage_location_group_roll WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT count(*),count(*) FILTER(WHERE secondary_resolution_required) INTO applied,required FROM senc_damage_location_hit_receipt WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 SELECT count(*) INTO resolved FROM senc_damage_location_hit_receipt hit LEFT JOIN senc_crew_damage_application_receipt crew
  ON crew.damage_location_hit_receipt_id=hit.damage_location_hit_receipt_id
 WHERE hit.mount_attack_declaration_id=NEW.mount_attack_declaration_id AND hit.secondary_resolution_required
  AND ((hit.effect_code IN('roll-crew-damage','crew-normal-hit','crew-radiation-hit') AND crew.damage_location_hit_receipt_id IS NOT NULL));
 SELECT ship.ship_id,ship.campaign_id,ship.concurrency_version INTO STRICT target FROM senc_mount_attack_declaration declaration
 JOIN senc_vessel vessel ON vessel.senc_vessel_id=declaration.target_vessel_id JOIN ship_ship ship ON ship.ship_id=vessel.ship_id
 WHERE declaration.mount_attack_declaration_id=NEW.mount_attack_declaration_id FOR UPDATE OF ship;
 IF NEW.expected_hit_count<>expected OR NEW.applied_hit_count<>applied OR applied<>expected OR NEW.required_secondary_count<>required
  OR NEW.resolved_secondary_count<>resolved OR resolved<>required OR NEW.target_ship_id<>target.ship_id OR NEW.campaign_id<>target.campaign_id
  OR NEW.target_ship_version_after<>target.concurrency_version THEN
  RAISE EXCEPTION 'Mount damage application requires every ordered hit and secondary consequence' USING ERRCODE='23514'; END IF;
 UPDATE senc_mount_damage_final_receipt SET damage_status='applied' WHERE mount_attack_declaration_id=NEW.mount_attack_declaration_id;
 RETURN NEW;
END $$;
CREATE TRIGGER senc_mount_damage_application_valid AFTER INSERT ON senc_mount_damage_application_receipt FOR EACH ROW EXECUTE FUNCTION senc_finalize_mount_damage_application();
CREATE FUNCTION senc_reject_mount_damage_application_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Mount damage application receipts are immutable'; END $$;
CREATE TRIGGER senc_mount_damage_application_immutable BEFORE UPDATE OR DELETE ON senc_mount_damage_application_receipt FOR EACH ROW EXECUTE FUNCTION senc_reject_mount_damage_application_mutation();
