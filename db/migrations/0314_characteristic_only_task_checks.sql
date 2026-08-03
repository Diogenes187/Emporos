ALTER TABLE cmd_actor_task_receipt ALTER COLUMN skill_rule_id DROP NOT NULL;
ALTER TABLE cmd_actor_task_receipt ADD CHECK(
 (skill_rule_id IS NULL AND skill_modifier=0)
 OR skill_rule_id IS NOT NULL);
COMMENT ON COLUMN cmd_actor_task_receipt.skill_rule_id IS
 'Nullable only for source-directed characteristic-only checks such as the post-refusal Bribery Social Standing check.';
