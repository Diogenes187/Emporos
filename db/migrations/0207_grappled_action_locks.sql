CREATE FUNCTION cmd_reject_grappled_actor_action()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM enc_personal_grapple_active_actor
    WHERE actor_id=NEW.actor_id
 ) THEN
   RAISE EXCEPTION
     'A grappled combatant may only make opposed Natural Weapons checks';
 END IF;
 RETURN NEW;
END;
$$;

CREATE TRIGGER cmd_personal_action_grapple_lock
BEFORE INSERT ON cmd_personal_action_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_personal_reaction_grapple_lock
BEFORE INSERT ON cmd_personal_reaction_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_personal_aim_grapple_lock
BEFORE INSERT ON cmd_personal_aim_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_personal_stance_grapple_lock
BEFORE INSERT ON cmd_personal_stance_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_personal_cover_grapple_lock
BEFORE INSERT ON cmd_personal_cover_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_personal_move_grapple_lock
BEFORE INSERT ON cmd_personal_move_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_personal_kill_aim_grapple_lock
BEFORE INSERT ON cmd_personal_kill_aim_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_weapon_reload_grapple_lock
BEFORE INSERT ON cmd_weapon_reload_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_psionic_activation_grapple_lock
BEFORE INSERT ON cmd_psionic_activation_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();
CREATE TRIGGER cmd_psionic_recovery_grapple_lock
BEFORE INSERT ON cmd_psionic_recovery_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_actor_action();

CREATE FUNCTION cmd_reject_grappled_commander_action()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM enc_personal_grapple_active_actor
    WHERE actor_id=NEW.commander_actor_id
 ) THEN
   RAISE EXCEPTION
     'A grappled combatant cannot issue battlefield communication';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_communication_grapple_lock
BEFORE INSERT ON cmd_personal_communication_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_commander_action();
CREATE TRIGGER cmd_personal_initiative_support_grapple_lock
BEFORE INSERT ON cmd_personal_initiative_support_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_commander_action();

CREATE FUNCTION cmd_reject_grappled_attack_declaration()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF EXISTS (
   SELECT 1
     FROM enc_personal_attack attack
     JOIN enc_personal_grapple_active_actor active
       ON active.actor_id=attack.attacker_actor_id
    WHERE attack.personal_attack_id=NEW.personal_attack_id
 ) THEN
   RAISE EXCEPTION
     'A grappled combatant cannot declare an ordinary attack';
 END IF;
 RETURN NEW;
END;
$$;
CREATE TRIGGER cmd_personal_attack_declaration_grapple_lock
BEFORE INSERT ON cmd_personal_attack_declaration_receipt
FOR EACH ROW EXECUTE FUNCTION cmd_reject_grappled_attack_declaration();
