INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading',v.heading,
       CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Space Combat: '||v.label
       ELSE 'Cepheus Engine v9.1, Space Combat: '||v.label END
FROM src_artifact a JOIN src_work w USING(source_work_id)
CROSS JOIN (VALUES
 ('Space Combat > Significant Actions > Pursuit','Pursuit'),
 ('Space Combat > Significant Actions > Break Pursuit','Break Pursuit')
) v(heading,label)
WHERE (w.work_code='cepheus-engine.ogn' AND a.source_uri LIKE '%cepheus-engine-space-combat/')
   OR (w.work_code='cepheus-engine.github-v9.1' AND a.source_uri='src/book2/space-combat.md')
ON CONFLICT DO NOTHING;

WITH package AS (SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine')
INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status,description)
SELECT content_package_id,'combat.space.pursuit','Space Combat Pursuit','combat','approved',
       'Pairwise pursuit establishment, maintenance, attack advantage, and termination.'
FROM package;

CREATE TABLE rule_space_combat_pursuit(
 rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
 skill_rule_id bigint NOT NULL REFERENCES rule_skill(rule_id),
 establishment_range_codes text[] NOT NULL,
 equal_speed_required boolean NOT NULL,
 maintenance_requires_significant_action boolean NOT NULL,
 maintenance_requires_check boolean NOT NULL,
 first_turn_attack_modifier smallint NOT NULL CHECK(first_turn_attack_modifier=0),
 attack_modifier_per_later_turn smallint NOT NULL CHECK(attack_modifier_per_later_turn=1),
 maximum_attack_modifier smallint NOT NULL CHECK(maximum_attack_modifier=4),
 automatic_break_minimum_range_order smallint NOT NULL,
 automatic_break_speed_advantage numeric NOT NULL CHECK(automatic_break_speed_advantage=7),
 immediate_automatic_break boolean NOT NULL,
 reestablishment_required_after_break boolean NOT NULL
);
INSERT INTO rule_space_combat_pursuit
SELECT pursuit.rule_id,pilot.rule_id,ARRAY['close','short'],true,true,false,0,1,4,
       (SELECT display_order FROM rule_space_range_band WHERE range_band_code='medium'),7,true,true
FROM rule_rule pursuit CROSS JOIN rule_rule pilot
WHERE pursuit.rule_code='combat.space.pursuit' AND pilot.rule_code='skill.piloting';

INSERT INTO rule_interpretation(rule_id,interpretation_type,decision_register_entry,rationale)
SELECT rule_id,'agreed_interpretation','CE-SC-003',
 'Range at Medium or greater, or a target speed advantage of 7+, ends pursuit immediately; later attacks lose the bonus and reestablishment requires a new action.'
FROM rule_rule WHERE rule_code='combat.space.pursuit';

INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,
 CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'direct' ELSE 'corroborating' END,
 w.work_code='cepheus-engine.ogn'
FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='combat.space.pursuit'
 AND l.heading_path IN('Space Combat > Significant Actions > Pursuit','Space Combat > Significant Actions > Break Pursuit')
 AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1');

CREATE TABLE senc_pursuit(
 pursuit_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 engagement_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 pursuing_vessel_id bigint NOT NULL,
 target_vessel_id bigint NOT NULL,
 pursuit_status text NOT NULL CHECK(pursuit_status IN('active','broken')),
 established_round integer NOT NULL CHECK(established_round>0),
 last_maintained_round integer NOT NULL CHECK(last_maintained_round>=established_round),
 consecutive_maintained_turns smallint NOT NULL CHECK(consecutive_maintained_turns>0),
 attack_modifier smallint NOT NULL CHECK(attack_modifier BETWEEN 0 AND 4),
 ended_round integer CHECK(ended_round>=established_round),
 ended_reason text CHECK(ended_reason IN('break-action','range','speed','not-maintained','vessel-ended')),
 FOREIGN KEY(pursuing_vessel_id,engagement_id,campaign_id)
  REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 FOREIGN KEY(target_vessel_id,engagement_id,campaign_id)
  REFERENCES senc_vessel(senc_vessel_id,engagement_id,campaign_id),
 UNIQUE(pursuit_id,engagement_id,campaign_id),
 CHECK(pursuing_vessel_id<>target_vessel_id),
 CHECK(attack_modifier=least(greatest(consecutive_maintained_turns-1,0),4)),
 CHECK((pursuit_status='active' AND ended_round IS NULL AND ended_reason IS NULL)
    OR (pursuit_status='broken' AND ended_round IS NOT NULL AND ended_reason IS NOT NULL))
);
CREATE UNIQUE INDEX senc_one_active_pursuit_pair
 ON senc_pursuit(engagement_id,pursuing_vessel_id,target_vessel_id)
 WHERE pursuit_status='active';

CREATE TABLE senc_pursuit_transition_receipt(
 pursuit_transition_receipt_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 pursuit_id bigint NOT NULL,
 engagement_id bigint NOT NULL,
 campaign_id bigint NOT NULL,
 round_number integer NOT NULL CHECK(round_number>0),
 transition_kind text NOT NULL CHECK(transition_kind IN('established','maintained','broken')),
 reason text NOT NULL CHECK(reason IN('action','break-action','range','speed','not-maintained','vessel-ended')),
 attack_modifier_before smallint,
 attack_modifier_after smallint NOT NULL CHECK(attack_modifier_after BETWEEN 0 AND 4),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(pursuit_id,engagement_id,campaign_id)
  REFERENCES senc_pursuit(pursuit_id,engagement_id,campaign_id),
 UNIQUE(pursuit_id,round_number,transition_kind)
);
CREATE FUNCTION senc_reject_pursuit_transition_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'Pursuit transition receipts are immutable'; END $$;
CREATE TRIGGER senc_pursuit_transition_immutable BEFORE UPDATE OR DELETE ON senc_pursuit_transition_receipt
FOR EACH ROW EXECUTE FUNCTION senc_reject_pursuit_transition_mutation();
