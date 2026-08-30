ALTER TABLE camp_campaign_setting
 ADD COLUMN starting_world_location_id bigint,
 ADD COLUMN current_world_location_id bigint;

ALTER TABLE camp_campaign_setting
 ADD CONSTRAINT camp_campaign_setting_starting_world_fk
  FOREIGN KEY(starting_world_location_id,campaign_id)
  REFERENCES loc_location(location_id,campaign_id),
 ADD CONSTRAINT camp_campaign_setting_current_world_fk
  FOREIGN KEY(current_world_location_id,campaign_id)
  REFERENCES loc_location(location_id,campaign_id);

ALTER TABLE actor_actor
 ADD COLUMN homeworld_location_id bigint,
 ADD CONSTRAINT actor_actor_homeworld_fk
  FOREIGN KEY(homeworld_location_id,campaign_id)
  REFERENCES loc_location(location_id,campaign_id);

WITH first_world AS (
 SELECT DISTINCT ON (system.campaign_id)
        system.campaign_id,body.location_id
 FROM loc_star_system system
 JOIN loc_celestial_body body
   ON body.system_location_id=system.location_id
  AND body.campaign_id=system.campaign_id
  AND body.body_kind='planet'
 JOIN loc_world_profile profile
   ON profile.location_id=body.location_id
  AND profile.campaign_id=body.campaign_id
 ORDER BY system.campaign_id,system.hex_column,system.hex_row,body.orbit_order
)
UPDATE camp_campaign_setting setting
SET starting_world_location_id=world.location_id,
    current_world_location_id=world.location_id
FROM first_world world
WHERE world.campaign_id=setting.campaign_id
  AND setting.starting_world_location_id IS NULL;

COMMENT ON COLUMN camp_campaign_setting.starting_world_location_id IS
 'The main world where campaign play began; distinct from a keyed adventure location.';
COMMENT ON COLUMN camp_campaign_setting.current_world_location_id IS
 'The campaign party current main world; ships retain their own authoritative locations.';
COMMENT ON COLUMN actor_actor.homeworld_location_id IS
 'Optional character background homeworld; it does not imply current location.';
