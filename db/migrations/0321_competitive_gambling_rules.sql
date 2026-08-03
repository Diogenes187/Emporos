CREATE TABLE rule_competitive_gambling (
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 all_players_make_normal_check boolean NOT NULL CHECK(all_players_make_normal_check),
 cheating_requires_extra_check boolean NOT NULL CHECK(cheating_requires_extra_check),
 successful_other_player_catches_cheater boolean NOT NULL CHECK(successful_other_player_catches_cheater),
 one_uncaught_cheater_takes_pot boolean NOT NULL CHECK(one_uncaught_cheater_takes_pot),
 multiple_uncaught_cheaters_use_highest_cheat_total boolean NOT NULL CHECK(multiple_uncaught_cheaters_use_highest_cheat_total),
 ordinary_winner_uses_highest_normal_total boolean NOT NULL CHECK(ordinary_winner_uses_highest_normal_total),
 ties_require_referee_resolution boolean NOT NULL CHECK(ties_require_referee_resolution)
);
COMMENT ON TABLE rule_competitive_gambling IS 'CE-SKILL-004 paired-source competitive Gambling and Raymond-approved detection/winner hierarchy.';
