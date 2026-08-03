CREATE OR REPLACE FUNCTION cmd_validate_firing_into_combat_receipt()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE attack enc_personal_attack%ROWTYPE;
DECLARE resolved cmd_attack_receipt%ROWTYPE;
DECLARE nearest smallint;
DECLARE nearest_count smallint;
DECLARE selected_order smallint;
DECLARE scatter cmd_random_draw%ROWTYPE;
DECLARE tie_draw cmd_random_draw%ROWTYPE;
BEGIN
 SELECT * INTO STRICT attack FROM enc_personal_attack
  WHERE personal_attack_id=NEW.personal_attack_id;
 SELECT * INTO STRICT resolved FROM cmd_attack_receipt
  WHERE command_id=NEW.command_id;
 SELECT min(proximity_tier) INTO nearest
   FROM enc_personal_firing_into_combat_target
  WHERE personal_attack_id=NEW.personal_attack_id;
 SELECT count(*) INTO nearest_count
   FROM enc_personal_firing_into_combat_target
  WHERE personal_attack_id=NEW.personal_attack_id
    AND proximity_tier=nearest;
 IF NEW.scatter_roll IS NOT NULL THEN
   SELECT * INTO STRICT scatter FROM cmd_random_draw
    WHERE command_id=NEW.command_id
      AND draw_group='combat_scatter' AND draw_order=1;
 END IF;
 IF NEW.tie_selection_draw IS NOT NULL THEN
   SELECT * INTO STRICT tie_draw FROM cmd_random_draw
    WHERE command_id=NEW.command_id
      AND draw_group='combat_nearest_tie' AND draw_order=1;
 END IF;
 IF NEW.selected_target_actor_id IS NOT NULL THEN
   SELECT target_order INTO STRICT selected_order
     FROM enc_personal_firing_into_combat_target
    WHERE personal_attack_id=NEW.personal_attack_id
      AND target_actor_id=NEW.selected_target_actor_id
      AND proximity_tier=nearest;
 END IF;
 IF NOT attack.firing_into_combat
    OR resolved.personal_attack_id<>attack.personal_attack_id
    OR NEW.original_target_actor_id<>attack.target_actor_id
    OR NEW.original_effect<>resolved.effect
    OR NEW.original_attack_hit<>(resolved.attack_total>=resolved.target_number)
    OR (NEW.redirected AND (
        NOT resolved.hit
        OR resolved.target_actor_id IS DISTINCT FROM NEW.selected_target_actor_id
        OR NEW.nearest_tier<>nearest
        OR NEW.nearest_tie_count<>nearest_count
        OR NEW.kill_aim_damage_excluded<>attack.kill_aim_damage_bonus))
    OR (NOT NEW.redirected AND (
        resolved.target_actor_id IS DISTINCT FROM attack.target_actor_id
        OR NEW.kill_aim_damage_excluded<>0))
    OR (NEW.scatter_roll IS NOT NULL AND (
        scatter.die_sides<>6 OR scatter.result<>NEW.scatter_roll))
    OR (NEW.tie_selection_draw IS NOT NULL AND (
        tie_draw.die_sides<>nearest_count
        OR tie_draw.result<>NEW.tie_selection_draw))
    OR (NEW.redirected AND nearest_count=1
        AND NEW.tie_selection_draw IS NOT NULL)
    OR (NEW.redirected AND nearest_count>1 AND (
        NEW.tie_selection_draw IS NULL
        OR selected_order<>(
          SELECT target_order
            FROM enc_personal_firing_into_combat_target
           WHERE personal_attack_id=NEW.personal_attack_id
             AND proximity_tier=nearest
           ORDER BY target_order
           OFFSET NEW.tie_selection_draw-1 LIMIT 1)))
 THEN
   RAISE EXCEPTION 'Firing into Combat receipt does not match frozen facts';
 END IF;
 RETURN NEW;
END;
$$;
