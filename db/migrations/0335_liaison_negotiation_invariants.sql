CREATE FUNCTION cmd_validate_liaison_negotiation_participant() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE task cmd_actor_task_receipt%ROWTYPE;
BEGIN
 SELECT * INTO STRICT task FROM cmd_actor_task_receipt WHERE command_id=NEW.task_command_id;
 IF task.actor_id<>NEW.actor_id OR task.characteristic_rule_id<>NEW.characteristic_rule_id
    OR task.skill_rule_id<>(SELECT skill_rule_id FROM rule_liaison_negotiation)
    OR task.check_total<>NEW.check_total THEN
  RAISE EXCEPTION 'Liaison negotiation participant snapshot mismatch';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER cmd_liaison_negotiation_participant_valid BEFORE INSERT ON cmd_liaison_negotiation_participant FOR EACH ROW EXECUTE FUNCTION cmd_validate_liaison_negotiation_participant();

CREATE FUNCTION cmd_validate_liaison_negotiation_aggregate() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE actual_count integer; actual_winners integer; n camp_liaison_negotiation%ROWTYPE;
BEGIN
 SELECT count(*),count(*) FILTER(WHERE gained_advantage) INTO actual_count,actual_winners
  FROM cmd_liaison_negotiation_participant WHERE command_id=NEW.command_id;
 SELECT * INTO STRICT n FROM camp_liaison_negotiation WHERE negotiation_id=NEW.negotiation_id;
 IF actual_count<>NEW.participant_count
    OR actual_winners<>(CASE WHEN n.negotiation_status='resolved' THEN 1 ELSE 0 END)
    OR NEW.tied_at_winning_total<>(n.negotiation_status='tied')
    OR EXISTS(SELECT 1 FROM cmd_liaison_negotiation_participant p
              WHERE p.command_id=NEW.command_id
                AND (p.gained_advantage<>(p.check_total=NEW.winning_total AND NOT NEW.tied_at_winning_total)))
    OR (n.winner_actor_id IS NOT NULL AND NOT EXISTS(
         SELECT 1 FROM cmd_liaison_negotiation_participant p
          WHERE p.command_id=NEW.command_id AND p.actor_id=n.winner_actor_id AND p.gained_advantage)) THEN
  RAISE EXCEPTION 'Liaison negotiation aggregate mismatch';
 END IF;
 RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER cmd_liaison_negotiation_aggregate_valid
 AFTER INSERT ON cmd_liaison_negotiation_receipt DEFERRABLE INITIALLY DEFERRED
 FOR EACH ROW EXECUTE FUNCTION cmd_validate_liaison_negotiation_aggregate();

CREATE FUNCTION cmd_validate_liaison_negotiation_campaign() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.winner_actor_id IS NOT NULL AND NOT EXISTS(
  SELECT 1 FROM actor_actor WHERE actor_id=NEW.winner_actor_id AND campaign_id=NEW.campaign_id) THEN
  RAISE EXCEPTION 'Liaison negotiation winner belongs to another campaign';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER camp_liaison_negotiation_valid BEFORE INSERT ON camp_liaison_negotiation FOR EACH ROW EXECUTE FUNCTION cmd_validate_liaison_negotiation_campaign();
