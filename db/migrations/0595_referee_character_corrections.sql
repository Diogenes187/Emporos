INSERT INTO cmd_command_type VALUES
 ('correct_character_state','Audited referee correction of authoritative character state')
ON CONFLICT(command_type) DO NOTHING;
INSERT INTO cmd_domain_event_type VALUES
 ('character_state_corrected','Referee corrected authoritative character state')
ON CONFLICT(event_type) DO NOTHING;

CREATE TABLE cmd_character_correction_receipt(
 command_id bigint PRIMARY KEY REFERENCES cmd_command(command_id),
 campaign_id bigint NOT NULL REFERENCES camp_campaign(campaign_id),
 actor_id bigint NOT NULL,
 correction_kind text NOT NULL CHECK(correction_kind IN('skill','characteristic','finance','location')),
 target_rule_id bigint REFERENCES rule_rule(rule_id),
 finance_field text CHECK(finance_field IN('cash_credits','debt_credits','medical_debt_credits','anagathic_debt_credits')),
 prior_value bigint,
 resulting_value bigint,
 prior_maximum bigint,
 resulting_maximum bigint,
 prior_location_id bigint,
 resulting_location_id bigint,
 reason text NOT NULL CHECK(btrim(reason)<>''),
 corrected_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(actor_id,campaign_id) REFERENCES actor_actor(actor_id,campaign_id),
 FOREIGN KEY(prior_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id),
 FOREIGN KEY(resulting_location_id,campaign_id) REFERENCES loc_location(location_id,campaign_id),
 CHECK(
  (correction_kind='skill' AND target_rule_id IS NOT NULL AND finance_field IS NULL AND resulting_value IS NOT NULL AND resulting_location_id IS NULL)
  OR (correction_kind='characteristic' AND target_rule_id IS NOT NULL AND finance_field IS NULL AND resulting_value IS NOT NULL AND resulting_maximum IS NOT NULL AND resulting_location_id IS NULL)
  OR (correction_kind='finance' AND target_rule_id IS NULL AND finance_field IS NOT NULL AND resulting_value IS NOT NULL AND resulting_location_id IS NULL)
  OR (correction_kind='location' AND target_rule_id IS NULL AND finance_field IS NULL AND resulting_value IS NULL AND resulting_location_id IS NOT NULL)
 )
);
CREATE INDEX cmd_character_correction_actor_recent
 ON cmd_character_correction_receipt(actor_id,corrected_at DESC);

COMMENT ON TABLE cmd_character_correction_receipt IS
 'Immutable before/after receipts for explicit owner/referee corrections; original mechanical receipts remain unchanged.';
