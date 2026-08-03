DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint
 WHERE conrelid='cmd_command'::regclass AND conname='cmd_command_command_type_check';
 ALTER TABLE cmd_command DROP CONSTRAINT cmd_command_command_type_check;
 EXECUTE format('ALTER TABLE cmd_command ADD CONSTRAINT cmd_command_command_type_check %s',
   replace(d,'CHECK (','CHECK (command_type=''allocate_skill_training_week'' OR '));
END $$;

CREATE TABLE rule_gameplay_skill_training (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_total_counts_zero_levels boolean NOT NULL CHECK(NOT skill_total_counts_zero_levels),
 required_weeks_addend_kind text NOT NULL CHECK(required_weeks_addend_kind='desired_level'),
 minimum_new_level_zero_weeks smallint NOT NULL CHECK(minimum_new_level_zero_weeks=1),
 simultaneous_skills_per_week smallint NOT NULL CHECK(simultaneous_skills_per_week=1),
 forbidden_skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id)
);

CREATE TABLE camp_skill_training_project (
 training_project_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 starting_skill_level smallint CHECK(starting_skill_level IS NULL OR starting_skill_level>=0),
 desired_skill_level smallint NOT NULL CHECK(desired_skill_level>=0),
 skill_total_at_start integer NOT NULL CHECK(skill_total_at_start>=0),
 required_weeks smallint NOT NULL CHECK(required_weeks>=1),
 completed_weeks smallint NOT NULL DEFAULT 0 CHECK(completed_weeks>=0),
 training_status text NOT NULL DEFAULT 'active' CHECK(training_status IN ('active','completed')),
 started_campaign_week bigint NOT NULL,
 completed_campaign_week bigint,
 CHECK(desired_skill_level=COALESCE(starting_skill_level+1,0)),
 CHECK(completed_weeks<=required_weeks),
 CHECK((training_status='completed')=(completed_weeks=required_weeks)),
 CHECK((training_status='completed')=(completed_campaign_week IS NOT NULL))
);
CREATE UNIQUE INDEX camp_skill_training_one_active_per_actor
 ON camp_skill_training_project(actor_id) WHERE training_status='active';

CREATE TABLE cmd_skill_training_week_receipt (
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 training_project_id bigint NOT NULL REFERENCES camp_skill_training_project(training_project_id),
 actor_id bigint NOT NULL REFERENCES actor_actor(actor_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 campaign_week bigint NOT NULL,
 week_number smallint NOT NULL CHECK(week_number>=1),
 required_weeks smallint NOT NULL CHECK(required_weeks>=1),
 skill_level_before smallint,
 skill_level_after smallint,
 actor_version_before bigint NOT NULL,
 actor_version_after bigint NOT NULL CHECK(actor_version_after=actor_version_before+1),
 allocated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(actor_id,campaign_week),
 UNIQUE(training_project_id,week_number),
 CHECK((week_number<required_weeks AND skill_level_after IS NULL)
    OR (week_number=required_weeks AND skill_level_after IS NOT NULL))
);

COMMENT ON TABLE rule_gameplay_skill_training IS 'CE-SKILL-001 paired-source gameplay skill advancement, with Raymond-approved one-week minimum for a new level-zero skill.';
COMMENT ON TABLE cmd_skill_training_week_receipt IS 'Immutable campaign-week allocations; one actor may train only one skill in a given week.';
