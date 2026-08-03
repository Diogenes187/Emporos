ALTER TABLE cmd_actor_task_receipt
 ADD COLUMN law_level smallint CHECK(law_level IS NULL OR law_level>=0),
 ADD COLUMN base_time_frame_rule_id bigint REFERENCES rule_time_frame(rule_id),
 ADD COLUMN time_frame_steps smallint NOT NULL DEFAULT 0 CHECK(time_frame_steps BETWEEN -2 AND 2),
 ADD COLUMN resolved_time_frame_rule_id bigint REFERENCES rule_time_frame(rule_id),
 ADD COLUMN task_time_roll smallint CHECK(task_time_roll BETWEEN 1 AND 6),
 ADD COLUMN task_time_quantity smallint CHECK(task_time_quantity BETWEEN 1 AND 6),
 ADD COLUMN task_time_unit text CHECK(task_time_unit IN ('second','round','minute','kilosecond','hour','day','week','month','quarter')),
 ADD COLUMN pace_modifier smallint NOT NULL DEFAULT 0 CHECK(pace_modifier=time_frame_steps),
 ADD COLUMN simultaneous_action_count smallint NOT NULL DEFAULT 1 CHECK(simultaneous_action_count>=1),
 ADD COLUMN simultaneous_action_modifier smallint NOT NULL DEFAULT 0
   CHECK(simultaneous_action_modifier=-2*(simultaneous_action_count-1)),
 ADD CHECK((base_time_frame_rule_id IS NULL AND resolved_time_frame_rule_id IS NULL
             AND task_time_roll IS NULL AND task_time_quantity IS NULL AND task_time_unit IS NULL
             AND time_frame_steps=0)
        OR (base_time_frame_rule_id IS NOT NULL AND resolved_time_frame_rule_id IS NOT NULL
             AND task_time_roll IS NOT NULL AND task_time_quantity=task_time_roll
             AND task_time_unit IS NOT NULL));

-- Earlier receipts folded fatigue into the circumstance snapshot. Separate the
-- two concepts before enforcing the complete arithmetic invariant.
UPDATE cmd_actor_task_receipt
 SET circumstance_modifier=circumstance_modifier-fatigue_modifier
 WHERE fatigue_modifier<>0;

COMMENT ON COLUMN cmd_actor_task_receipt.time_frame_steps IS
 'Published row shift: negative is faster, positive is slower; limited to two rows.';
COMMENT ON COLUMN cmd_actor_task_receipt.task_time_quantity IS
 'Source-safe 1D6 quantity in task_time_unit; months and quarters are not converted to invented seconds.';
