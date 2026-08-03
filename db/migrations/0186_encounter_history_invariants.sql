CREATE OR REPLACE FUNCTION enc_objective_history_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP='DELETE' OR OLD.objective_status<>'active' THEN
        RAISE EXCEPTION 'Encounter objectives are immutable history'
            USING ERRCODE='23514';
    END IF;
    IF (
        to_jsonb(NEW)-'objective_status'-'resolved_at'
    ) IS DISTINCT FROM (
        to_jsonb(OLD)-'objective_status'-'resolved_at'
    ) OR NEW.objective_status='active'
       OR NEW.resolved_at IS NULL THEN
        RAISE EXCEPTION
            'Encounter objective may only receive a final result'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_objective_history_immutable
BEFORE UPDATE OR DELETE ON enc_objective
FOR EACH ROW EXECUTE FUNCTION enc_objective_history_guard();

CREATE OR REPLACE FUNCTION enc_intention_history_guard()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP='DELETE' OR OLD.ended_at IS NOT NULL THEN
        RAISE EXCEPTION
            'Encounter participant intentions are immutable history'
            USING ERRCODE='23514';
    END IF;
    IF (to_jsonb(NEW)-'ended_at')
       IS DISTINCT FROM (to_jsonb(OLD)-'ended_at')
       OR NEW.ended_at IS NULL THEN
        RAISE EXCEPTION
            'Encounter intention may only be ended'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_intention_history_immutable
BEFORE UPDATE OR DELETE ON enc_participant_intention
FOR EACH ROW EXECUTE FUNCTION enc_intention_history_guard();

CREATE OR REPLACE FUNCTION enc_require_active_aggregate()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM 1
    FROM enc_encounter encounter
    WHERE encounter.encounter_id=NEW.encounter_id
      AND encounter.campaign_id=NEW.campaign_id
      AND encounter.encounter_status='active';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Encounter aggregate is not active'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER enc_objective_requires_active_encounter
BEFORE INSERT ON enc_objective
FOR EACH ROW EXECUTE FUNCTION enc_require_active_aggregate();

CREATE TRIGGER enc_intention_requires_active_encounter
BEFORE INSERT ON enc_participant_intention
FOR EACH ROW EXECUTE FUNCTION enc_require_active_aggregate();

CREATE TRIGGER enc_resolution_requires_active_encounter
BEFORE INSERT ON enc_resolution
FOR EACH ROW EXECUTE FUNCTION enc_require_active_aggregate();
