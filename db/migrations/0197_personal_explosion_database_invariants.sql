CREATE FUNCTION enc_guard_personal_explosion_target()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE current_status text;
BEGIN
    SELECT explosion_status INTO STRICT current_status
      FROM enc_personal_explosion
     WHERE explosion_id=COALESCE(NEW.explosion_id,OLD.explosion_id);
    IF TG_OP IN ('INSERT','DELETE') AND EXISTS (
        SELECT 1 FROM cmd_personal_explosion_declaration_receipt
         WHERE explosion_id=COALESCE(NEW.explosion_id,OLD.explosion_id)
    ) THEN
        RAISE EXCEPTION 'Declared explosion roster is immutable';
    END IF;
    IF TG_OP='UPDATE' AND (
        current_status<>'awaiting_reactions'
        OR (NEW.explosion_id,NEW.actor_id,NEW.target_order,NEW.armor_rule_id)
           IS DISTINCT FROM
           (OLD.explosion_id,OLD.actor_id,OLD.target_order,OLD.armor_rule_id)
        OR OLD.reaction_declared
        OR NOT NEW.reaction_declared
    ) THEN
        RAISE EXCEPTION 'Only the first pending reaction declaration is mutable';
    END IF;
    IF TG_OP='DELETE' THEN RETURN OLD; END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER enc_personal_explosion_target_guard
BEFORE INSERT OR UPDATE OR DELETE ON enc_personal_explosion_target
FOR EACH ROW EXECUTE FUNCTION enc_guard_personal_explosion_target();

CREATE FUNCTION cmd_validate_personal_explosion_declaration()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.target_count<>(SELECT count(*)
        FROM enc_personal_explosion_target
        WHERE explosion_id=NEW.explosion_id) THEN
        RAISE EXCEPTION 'Explosion declaration target count does not match roster';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_explosion_declaration_validate
BEFORE INSERT ON cmd_personal_explosion_declaration_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_explosion_declaration();

CREATE FUNCTION cmd_validate_personal_explosion_resolution()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE expected_damage integer;
BEGIN
    IF NEW.target_count<>(SELECT count(*)
        FROM enc_personal_explosion_target
        WHERE explosion_id=NEW.explosion_id)
       OR EXISTS (
        SELECT 1 FROM enc_personal_explosion_target
        WHERE explosion_id=NEW.explosion_id AND NOT reaction_declared
       ) THEN
        RAISE EXCEPTION 'Explosion resolution requires every frozen reaction';
    END IF;
    SELECT COALESCE(sum(draw.result),0)+explosion.flat_damage
      INTO STRICT expected_damage
      FROM enc_personal_explosion explosion
      LEFT JOIN cmd_random_draw draw
        ON draw.command_id=NEW.command_id
       AND draw.draw_group='explosion_damage'
     WHERE explosion.explosion_id=NEW.explosion_id
     GROUP BY explosion.flat_damage;
    IF NEW.shared_rolled_damage<>expected_damage THEN
        RAISE EXCEPTION 'Shared explosion damage does not match recorded dice';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_explosion_resolution_validate
BEFORE INSERT ON cmd_personal_explosion_resolution_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_explosion_resolution();

CREATE FUNCTION cmd_validate_personal_explosion_target_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.damage_instance_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM health_damage_instance damage
         WHERE damage.damage_instance_id=NEW.damage_instance_id
           AND damage.explosion_command_id=NEW.command_id
           AND damage.target_actor_id=NEW.actor_id
           AND damage.penetrating_damage=NEW.penetrating_damage
    ) THEN
        RAISE EXCEPTION 'Explosion target receipt damage link is inconsistent';
    END IF;
    IF NOT EXISTS (
        SELECT 1
          FROM cmd_personal_explosion_resolution_receipt resolution
          JOIN enc_personal_explosion_target target
            ON target.explosion_id=resolution.explosion_id
         WHERE resolution.command_id=NEW.command_id
           AND target.actor_id=NEW.actor_id
           AND target.target_order=NEW.target_order
           AND target.armor_rule_id=NEW.armor_rule_id
           AND target.reaction_kind=NEW.reaction_kind
    ) THEN
        RAISE EXCEPTION 'Explosion target receipt does not match frozen roster';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_explosion_target_receipt_validate
BEFORE INSERT ON cmd_personal_explosion_target_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_validate_personal_explosion_target_receipt();

COMMENT ON FUNCTION enc_guard_personal_explosion_target() IS
    'Freezes roster identity after declaration while permitting one reaction.';
