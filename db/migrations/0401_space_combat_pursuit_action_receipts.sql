CREATE TABLE senc_pursuit_action_receipt(
 pursuit_action_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 pursuit_id bigint NOT NULL,
 engagement_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 space_combat_round_id bigint NOT NULL,
 round_number integer NOT NULL CHECK(round_number>0),
 action_kind text NOT NULL CHECK(action_kind IN('establish','maintain','break')),
 acting_vessel_id bigint NOT NULL,
 opposing_vessel_id bigint NOT NULL,
 action_id bigint NOT NULL UNIQUE,
 acting_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 opposing_task_command_id bigint UNIQUE REFERENCES cmd_actor_task_receipt(command_id),
 acting_effect smallint,
 opposing_effect smallint,
 acting_characteristic_value smallint,
 opposing_characteristic_value smallint,
 acting_won boolean,
 range_band_snapshot text NOT NULL REFERENCES rule_space_range_band(range_band_code),
 acting_speed_snapshot numeric NOT NULL CHECK(acting_speed_snapshot>=0),
 opposing_speed_snapshot numeric NOT NULL CHECK(opposing_speed_snapshot>=0),
 attack_modifier_before smallint NOT NULL CHECK(attack_modifier_before BETWEEN 0 AND 4),
 attack_modifier_after smallint NOT NULL CHECK(attack_modifier_after BETWEEN 0 AND 4),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(pursuit_id,engagement_id,campaign_id)
  REFERENCES senc_pursuit(pursuit_id,engagement_id,campaign_id),
 FOREIGN KEY(space_combat_round_id,engagement_id,campaign_id)
  REFERENCES senc_round(space_combat_round_id,engagement_id,campaign_id),
 FOREIGN KEY(acting_vessel_id,engagement_id,campaign_id)
  REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(opposing_vessel_id,engagement_id,campaign_id)
  REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(action_id,engagement_id,campaign_id)
  REFERENCES senc_action(space_combat_action_id,engagement_id,campaign_id),
 UNIQUE(pursuit_id,round_number,action_kind),
 CHECK(acting_vessel_id<>opposing_vessel_id),
 CHECK((action_kind='maintain' AND acting_task_command_id IS NULL
   AND opposing_task_command_id IS NULL AND acting_effect IS NULL
   AND opposing_effect IS NULL AND acting_characteristic_value IS NULL
   AND opposing_characteristic_value IS NULL AND acting_won IS NULL)
  OR (action_kind IN('establish','break') AND acting_task_command_id IS NOT NULL
   AND opposing_task_command_id IS NOT NULL AND acting_effect IS NOT NULL
   AND opposing_effect IS NOT NULL AND acting_characteristic_value IS NOT NULL
   AND opposing_characteristic_value IS NOT NULL AND acting_won IS NOT NULL))
);
CREATE FUNCTION senc_reject_pursuit_action_receipt_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Pursuit action receipts are immutable'; END $$;
CREATE TRIGGER senc_pursuit_action_receipt_immutable
BEFORE UPDATE OR DELETE ON senc_pursuit_action_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_pursuit_action_receipt_mutation();
