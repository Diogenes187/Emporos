ALTER TABLE enc_participant
    ADD COLUMN campaign_id bigint;

UPDATE enc_participant participant
SET campaign_id=encounter.campaign_id
FROM enc_encounter encounter
WHERE encounter.encounter_id=participant.encounter_id;

ALTER TABLE enc_participant
    ALTER COLUMN campaign_id SET NOT NULL,
    DROP CONSTRAINT enc_participant_actor_id_fkey,
    ADD CONSTRAINT enc_participant_encounter_campaign_fk
        FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    ADD CONSTRAINT enc_participant_actor_campaign_fk
        FOREIGN KEY (actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    ADD CONSTRAINT enc_participant_identity_campaign_unique
        UNIQUE (encounter_id,actor_id,campaign_id);

CREATE TABLE enc_side (
    encounter_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    side_code text NOT NULL CHECK (btrim(side_code)<>''),
    side_name text NOT NULL CHECK (btrim(side_name)<>''),
    display_order smallint NOT NULL CHECK (display_order>0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (encounter_id,side_code),
    FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    UNIQUE (encounter_id,side_code,campaign_id),
    UNIQUE (encounter_id,display_order)
);

INSERT INTO enc_side (
    encounter_id,campaign_id,side_code,side_name,display_order
)
SELECT participant.encounter_id,participant.campaign_id,
       participant.side_code,participant.side_code,
       row_number() OVER (
           PARTITION BY participant.encounter_id
           ORDER BY participant.side_code
       )
FROM enc_participant participant
GROUP BY participant.encounter_id,participant.campaign_id,
         participant.side_code;

ALTER TABLE enc_participant
    ADD CONSTRAINT enc_participant_registered_side_fk
    FOREIGN KEY (encounter_id,side_code,campaign_id)
    REFERENCES enc_side(encounter_id,side_code,campaign_id);

CREATE TABLE enc_objective (
    encounter_objective_id bigint GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,
    encounter_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    objective_order smallint NOT NULL CHECK (objective_order>0),
    owner_kind text NOT NULL CHECK (
        owner_kind IN ('side','participant')
    ),
    owner_side_code text,
    owner_actor_id bigint,
    objective_kind text NOT NULL CHECK (
        objective_kind IN (
            'defeat','capture','escape','protect','acquire',
            'negotiate','survive','observe','delay','other'
        )
    ),
    target_kind text NOT NULL CHECK (
        target_kind IN (
            'none','actor','side','location','item','reference'
        )
    ),
    target_actor_id bigint,
    target_side_code text,
    target_location_id bigint,
    target_item_instance_id bigint,
    target_reference text CHECK (
        target_reference IS NULL OR btrim(target_reference)<>''
    ),
    objective_status text NOT NULL DEFAULT 'active' CHECK (
        objective_status IN (
            'active','achieved','failed','abandoned'
        )
    ),
    declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    resolved_at timestamptz,
    FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    FOREIGN KEY (encounter_id,owner_side_code,campaign_id)
        REFERENCES enc_side(encounter_id,side_code,campaign_id),
    FOREIGN KEY (encounter_id,owner_actor_id,campaign_id)
        REFERENCES enc_participant(
            encounter_id,actor_id,campaign_id
        ),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (encounter_id,target_side_code,campaign_id)
        REFERENCES enc_side(encounter_id,side_code,campaign_id),
    FOREIGN KEY (target_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    FOREIGN KEY (target_item_instance_id,campaign_id)
        REFERENCES inv_item_instance(item_instance_id,campaign_id),
    UNIQUE (encounter_id,objective_order),
    UNIQUE (encounter_objective_id,encounter_id,campaign_id),
    CHECK (
        (
            owner_kind='side'
            AND owner_side_code IS NOT NULL
            AND owner_actor_id IS NULL
        )
        OR (
            owner_kind='participant'
            AND owner_side_code IS NULL
            AND owner_actor_id IS NOT NULL
        )
    ),
    CHECK (
        num_nonnulls(
            target_actor_id,target_side_code,target_location_id,
            target_item_instance_id,target_reference
        )=CASE WHEN target_kind='none' THEN 0 ELSE 1 END
    ),
    CHECK (
        (target_kind='none')
        OR (target_kind='actor' AND target_actor_id IS NOT NULL)
        OR (target_kind='side' AND target_side_code IS NOT NULL)
        OR (target_kind='location' AND target_location_id IS NOT NULL)
        OR (target_kind='item' AND target_item_instance_id IS NOT NULL)
        OR (target_kind='reference' AND target_reference IS NOT NULL)
    ),
    CHECK (
        (objective_status='active' AND resolved_at IS NULL)
        OR (objective_status<>'active' AND resolved_at IS NOT NULL)
    )
);

CREATE TABLE enc_participant_intention (
    participant_intention_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    encounter_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    actor_id bigint NOT NULL,
    intention_order smallint NOT NULL CHECK (intention_order>0),
    intention_kind text NOT NULL CHECK (
        intention_kind IN (
            'attack','defend','withdraw','flee','surrender',
            'negotiate','assist','observe','hold','other'
        )
    ),
    target_kind text NOT NULL CHECK (
        target_kind IN ('none','actor','side','reference')
    ),
    target_actor_id bigint,
    target_side_code text,
    target_reference text CHECK (
        target_reference IS NULL OR btrim(target_reference)<>''
    ),
    effective_round integer CHECK (effective_round>0),
    declared_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    ended_at timestamptz,
    FOREIGN KEY (encounter_id,actor_id,campaign_id)
        REFERENCES enc_participant(
            encounter_id,actor_id,campaign_id
        ),
    FOREIGN KEY (target_actor_id,campaign_id)
        REFERENCES actor_actor(actor_id,campaign_id),
    FOREIGN KEY (encounter_id,target_side_code,campaign_id)
        REFERENCES enc_side(encounter_id,side_code,campaign_id),
    UNIQUE (encounter_id,actor_id,intention_order),
    CHECK (
        num_nonnulls(
            target_actor_id,target_side_code,target_reference
        )=CASE WHEN target_kind='none' THEN 0 ELSE 1 END
    ),
    CHECK (
        (target_kind='none')
        OR (target_kind='actor' AND target_actor_id IS NOT NULL)
        OR (target_kind='side' AND target_side_code IS NOT NULL)
        OR (target_kind='reference' AND target_reference IS NOT NULL)
    ),
    CHECK (ended_at IS NULL OR ended_at>=declared_at)
);

CREATE UNIQUE INDEX enc_one_current_participant_intention
    ON enc_participant_intention(encounter_id,actor_id)
    WHERE ended_at IS NULL;

CREATE TABLE enc_resolution (
    encounter_resolution_id bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    encounter_id bigint NOT NULL UNIQUE,
    campaign_id bigint NOT NULL,
    outcome_kind text NOT NULL CHECK (
        outcome_kind IN (
            'decisive','withdrawal','escape','surrender',
            'negotiated','avoided','inconclusive','other'
        )
    ),
    winning_side_code text,
    resolution_summary text,
    source_command_id bigint REFERENCES cmd_command(command_id),
    finalized boolean NOT NULL DEFAULT false,
    resolved_at timestamptz,
    FOREIGN KEY (encounter_id,campaign_id)
        REFERENCES enc_encounter(encounter_id,campaign_id),
    FOREIGN KEY (encounter_id,winning_side_code,campaign_id)
        REFERENCES enc_side(encounter_id,side_code,campaign_id),
    UNIQUE (encounter_resolution_id,encounter_id,campaign_id),
    CHECK (
        resolution_summary IS NULL
        OR btrim(resolution_summary)<>''
    ),
    CHECK (
        outcome_kind<>'decisive'
        OR winning_side_code IS NOT NULL
    ),
    CHECK (
        (finalized AND resolved_at IS NOT NULL)
        OR (NOT finalized AND resolved_at IS NULL)
    )
);

CREATE TABLE enc_objective_result (
    encounter_resolution_id bigint NOT NULL,
    encounter_id bigint NOT NULL,
    campaign_id bigint NOT NULL,
    encounter_objective_id bigint NOT NULL,
    result_status text NOT NULL CHECK (
        result_status IN ('achieved','failed','abandoned')
    ),
    PRIMARY KEY (
        encounter_resolution_id,encounter_objective_id
    ),
    FOREIGN KEY (
        encounter_resolution_id,encounter_id,campaign_id
    ) REFERENCES enc_resolution(
        encounter_resolution_id,encounter_id,campaign_id
    ),
    FOREIGN KEY (
        encounter_objective_id,encounter_id,campaign_id
    ) REFERENCES enc_objective(
        encounter_objective_id,encounter_id,campaign_id
    )
);

CREATE OR REPLACE FUNCTION enc_validate_resolution_finalization()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    objective_mismatch boolean;
BEGIN
    IF TG_OP='DELETE' OR OLD.finalized
       OR NOT NEW.finalized OR NEW.resolved_at IS NULL THEN
        RAISE EXCEPTION 'Finalized encounter resolutions are immutable'
            USING ERRCODE='23514';
    END IF;
    IF (to_jsonb(NEW)-'finalized'-'resolved_at')
       IS DISTINCT FROM
       (to_jsonb(OLD)-'finalized'-'resolved_at') THEN
        RAISE EXCEPTION
            'Encounter resolution body cannot change at finalization'
            USING ERRCODE='23514';
    END IF;
    PERFORM 1
    FROM enc_encounter encounter
    WHERE encounter.encounter_id=OLD.encounter_id
      AND encounter.campaign_id=OLD.campaign_id
      AND encounter.encounter_status='active'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Encounter is not active'
            USING ERRCODE='23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM enc_personal_attack attack
        WHERE attack.encounter_id=OLD.encounter_id
          AND attack.attack_status='awaiting_reactions'
    ) THEN
        RAISE EXCEPTION
            'Encounter has unresolved personal attacks'
            USING ERRCODE='23514';
    END IF;
    IF EXISTS (
        SELECT 1 FROM venc_engagement engagement
        WHERE engagement.encounter_id=OLD.encounter_id
          AND engagement.engagement_status IN ('forming','active')
    ) OR EXISTS (
        SELECT 1 FROM senc_engagement engagement
        WHERE engagement.encounter_id=OLD.encounter_id
          AND engagement.engagement_status IN ('forming','active')
    ) THEN
        RAISE EXCEPTION
            'Specialized engagement must resolve first'
            USING ERRCODE='23514';
    END IF;

    SELECT EXISTS (
        (
            SELECT encounter_objective_id
            FROM enc_objective
            WHERE encounter_id=OLD.encounter_id
              AND campaign_id=OLD.campaign_id
              AND objective_status='active'
            EXCEPT
            SELECT encounter_objective_id
            FROM enc_objective_result
            WHERE encounter_resolution_id=
                  OLD.encounter_resolution_id
        )
        UNION ALL
        (
            SELECT encounter_objective_id
            FROM enc_objective_result
            WHERE encounter_resolution_id=
                  OLD.encounter_resolution_id
            EXCEPT
            SELECT encounter_objective_id
            FROM enc_objective
            WHERE encounter_id=OLD.encounter_id
              AND campaign_id=OLD.campaign_id
              AND objective_status='active'
        )
    ) INTO objective_mismatch;
    IF objective_mismatch THEN
        RAISE EXCEPTION
            'Encounter objective results do not reconcile'
            USING ERRCODE='23514';
    END IF;

    UPDATE enc_objective objective
    SET objective_status=result.result_status,
        resolved_at=NEW.resolved_at
    FROM enc_objective_result result
    WHERE result.encounter_resolution_id=
          OLD.encounter_resolution_id
      AND result.encounter_objective_id=
          objective.encounter_objective_id;
    UPDATE enc_participant_intention
    SET ended_at=NEW.resolved_at
    WHERE encounter_id=OLD.encounter_id
      AND campaign_id=OLD.campaign_id
      AND ended_at IS NULL;
    UPDATE enc_personal_combat
    SET combat_status='completed',
        completed_at=NEW.resolved_at
    WHERE encounter_id=OLD.encounter_id
      AND combat_status='active';
    UPDATE enc_encounter
    SET encounter_status='resolved',
        resolved_at=NEW.resolved_at
    WHERE encounter_id=OLD.encounter_id
      AND campaign_id=OLD.campaign_id;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_resolution_finalization_valid
BEFORE UPDATE OR DELETE ON enc_resolution
FOR EACH ROW EXECUTE FUNCTION
    enc_validate_resolution_finalization();

CREATE OR REPLACE FUNCTION enc_resolution_line_open()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    resolution_id bigint;
    is_finalized boolean;
BEGIN
    resolution_id:=CASE
        WHEN TG_OP='DELETE' THEN OLD.encounter_resolution_id
        ELSE NEW.encounter_resolution_id
    END;
    SELECT finalized INTO is_finalized
    FROM enc_resolution
    WHERE encounter_resolution_id=resolution_id;
    IF is_finalized THEN
        RAISE EXCEPTION
            'Finalized encounter objective results are immutable'
            USING ERRCODE='23514';
    END IF;
    RETURN CASE WHEN TG_OP='DELETE' THEN OLD ELSE NEW END;
END;
$$;

CREATE TRIGGER enc_objective_result_open
BEFORE INSERT OR UPDATE OR DELETE ON enc_objective_result
FOR EACH ROW EXECUTE FUNCTION enc_resolution_line_open();

CREATE VIEW enc_current_summary AS
SELECT encounter.encounter_id,encounter.campaign_id,
       encounter.encounter_status,encounter.current_mode,
       count(DISTINCT side.side_code) AS side_count,
       count(DISTINCT participant.actor_id) AS participant_count,
       count(DISTINCT objective.encounter_objective_id)
           FILTER (WHERE objective.objective_status='active')
           AS active_objective_count,
       count(DISTINCT intention.participant_intention_id)
           FILTER (WHERE intention.ended_at IS NULL)
           AS current_intention_count,
       resolution.outcome_kind,
       resolution.winning_side_code,
       coalesce(resolution.finalized,false) AS outcome_finalized
FROM enc_encounter encounter
LEFT JOIN enc_side side
  ON side.encounter_id=encounter.encounter_id
LEFT JOIN enc_participant participant
  ON participant.encounter_id=encounter.encounter_id
LEFT JOIN enc_objective objective
  ON objective.encounter_id=encounter.encounter_id
LEFT JOIN enc_participant_intention intention
  ON intention.encounter_id=encounter.encounter_id
LEFT JOIN enc_resolution resolution
  ON resolution.encounter_id=encounter.encounter_id
GROUP BY encounter.encounter_id,encounter.campaign_id,
         encounter.encounter_status,encounter.current_mode,
         resolution.outcome_kind,resolution.winning_side_code,
         resolution.finalized;
