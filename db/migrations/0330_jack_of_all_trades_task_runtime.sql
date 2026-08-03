ALTER TABLE cmd_actor_task_receipt
 ADD COLUMN base_skill_modifier smallint,
 ADD COLUMN jack_of_all_trades_level smallint CHECK(jack_of_all_trades_level IS NULL OR jack_of_all_trades_level>=0),
 ADD COLUMN jack_of_all_trades_reduction smallint NOT NULL DEFAULT 0 CHECK(jack_of_all_trades_reduction>=0),
 ADD CHECK((base_skill_modifier IS NULL AND jack_of_all_trades_level IS NULL AND jack_of_all_trades_reduction=0)
        OR (base_skill_modifier IS NOT NULL AND skill_modifier=least(0,base_skill_modifier+jack_of_all_trades_reduction)
            AND jack_of_all_trades_reduction=least(-least(base_skill_modifier,0),COALESCE(jack_of_all_trades_level,0))));
COMMENT ON COLUMN cmd_actor_task_receipt.base_skill_modifier IS 'Raw trained level or published untrained modifier before Jack of All Trades.';
