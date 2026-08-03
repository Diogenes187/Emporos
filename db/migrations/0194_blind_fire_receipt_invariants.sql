ALTER TABLE cmd_personal_blind_fire_receipt
    ADD CONSTRAINT cmd_personal_blind_fire_selected_roster_fk
    FOREIGN KEY (personal_attack_id,selected_target_actor_id)
    REFERENCES enc_personal_blind_fire_target(
        personal_attack_id,target_actor_id
    );

CREATE FUNCTION cmd_validate_personal_blind_fire_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack_hit boolean;
DECLARE recorded_dice smallint;
DECLARE recorded_max smallint;
BEGIN
    SELECT hit INTO STRICT attack_hit FROM cmd_attack_receipt
    WHERE command_id=NEW.command_id;
    IF attack_hit<>(NEW.selected_target_actor_id IS NOT NULL) THEN
        RAISE EXCEPTION
            'Blind-fire target selection must exist exactly on a successful check';
    END IF;
    SELECT count(*),max(result) INTO recorded_dice,recorded_max
    FROM cmd_random_draw
    WHERE command_id=NEW.command_id AND draw_group='attack';
    IF recorded_dice<>3 OR recorded_max<>NEW.discarded_attack_die THEN
        RAISE EXCEPTION 'Blind-fire receipt must match three recorded attack dice';
    END IF;
    IF (SELECT skill_modifier FROM cmd_attack_receipt
        WHERE command_id=NEW.command_id)<>0 THEN
        RAISE EXCEPTION 'Blind fire must use effective weapon skill Level 0';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER cmd_personal_blind_fire_receipt_validate
BEFORE INSERT ON cmd_personal_blind_fire_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_blind_fire_receipt();

COMMENT ON CONSTRAINT cmd_personal_blind_fire_selected_roster_fk
    ON cmd_personal_blind_fire_receipt IS
    'Selected target must belong to the immutable declaration roster.';
