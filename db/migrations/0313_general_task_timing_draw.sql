DO $$ DECLARE d text; BEGIN
 SELECT pg_get_constraintdef(oid) INTO STRICT d FROM pg_constraint
 WHERE conrelid='cmd_random_draw'::regclass
   AND conname='cmd_random_draw_draw_group_check';
 ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
 EXECUTE format('ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check %s',
   replace(d,'CHECK (','CHECK (draw_group=''task_time'' OR '));
END $$;
