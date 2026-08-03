DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',replace(d,'CHECK (','CHECK (command_type=''resolve_competitive_gambling'' OR '));
END $$;
CREATE TABLE camp_competitive_gambling_game (
 game_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE,
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 venue_reference text NOT NULL CHECK(btrim(venue_reference)<>''),
 game_reference text NOT NULL CHECK(btrim(game_reference)<>''),
 pot_reference text NOT NULL CHECK(btrim(pot_reference)<>''),
 game_status text NOT NULL CHECK(game_status IN ('resolved','tied','no_eligible_winner')),
 resolution_basis text NOT NULL CHECK(resolution_basis IN ('normal','cheating','tie','none')),
 winner_actor_id bigint REFERENCES actor_actor(actor_id),
 source_command_id bigint NOT NULL UNIQUE REFERENCES cmd_command(command_id),
 CHECK((game_status='resolved')=(winner_actor_id IS NOT NULL))
);
CREATE TABLE cmd_competitive_gambling_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 game_id bigint NOT NULL UNIQUE REFERENCES camp_competitive_gambling_game(game_id),
 rule_id bigint NOT NULL REFERENCES rule_competitive_gambling(rule_id),
 referee_reference text NOT NULL CHECK(btrim(referee_reference)<>''),
 participant_count smallint NOT NULL CHECK(participant_count>=2),
 cheating_count smallint NOT NULL CHECK(cheating_count BETWEEN 0 AND participant_count),
 uncaught_cheater_count smallint NOT NULL CHECK(uncaught_cheater_count BETWEEN 0 AND cheating_count),
 winning_score smallint,
 tied_at_winning_score boolean NOT NULL
);
CREATE TABLE cmd_competitive_gambling_participant (
 command_id bigint NOT NULL REFERENCES cmd_competitive_gambling_receipt(command_id),
 participant_order smallint NOT NULL CHECK(participant_order>0),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 normal_task_command_id bigint NOT NULL UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 normal_total smallint NOT NULL,
 normal_succeeded boolean NOT NULL,
 cheating_declared boolean NOT NULL,
 cheat_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 cheat_total smallint,
 caught_cheating boolean NOT NULL,
 eligible_for_pot boolean NOT NULL,
 won_pot boolean NOT NULL,
 PRIMARY KEY(command_id,participant_order), UNIQUE(command_id,actor_id),
 CHECK(cheating_declared=(cheat_task_command_id IS NOT NULL AND cheat_total IS NOT NULL)),
 CHECK(NOT caught_cheating OR cheating_declared),
 CHECK(eligible_for_pot=NOT caught_cheating),
 CHECK(NOT won_pot OR eligible_for_pot)
);
CREATE FUNCTION cmd_reject_competitive_gambling_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Competitive gambling receipts are immutable'; END $$;
CREATE TRIGGER cmd_competitive_gambling_receipt_immutable BEFORE UPDATE OR DELETE ON cmd_competitive_gambling_receipt FOR EACH ROW EXECUTE FUNCTION cmd_reject_competitive_gambling_mutation();
CREATE TRIGGER cmd_competitive_gambling_participant_immutable BEFORE UPDATE OR DELETE ON cmd_competitive_gambling_participant FOR EACH ROW EXECUTE FUNCTION cmd_reject_competitive_gambling_mutation();
