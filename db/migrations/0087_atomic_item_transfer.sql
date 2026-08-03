ALTER TABLE inv_item_transfer
    ADD COLUMN from_location_id bigint,
    ADD COLUMN to_location_id bigint,
    ADD CONSTRAINT inv_item_transfer_from_location_scope_fkey
        FOREIGN KEY (from_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    ADD CONSTRAINT inv_item_transfer_to_location_scope_fkey
        FOREIGN KEY (to_location_id,campaign_id)
        REFERENCES loc_location(location_id,campaign_id),
    DROP CONSTRAINT inv_item_transfer_check,
    ADD CONSTRAINT inv_item_transfer_changes_state_check CHECK (
        from_container_id IS DISTINCT FROM to_container_id
        OR from_location_id IS DISTINCT FROM to_location_id
        OR from_actor_id IS DISTINCT FROM to_actor_id
        OR from_faction_id IS DISTINCT FROM to_faction_id
    ),
    ADD CONSTRAINT inv_item_transfer_from_custody_check CHECK (
        (from_container_id IS NOT NULL)::integer
        +(from_location_id IS NOT NULL)::integer <= 1
    ),
    ADD CONSTRAINT inv_item_transfer_to_custody_check CHECK (
        (to_container_id IS NOT NULL)::integer
        +(to_location_id IS NOT NULL)::integer <= 1
    );

CREATE OR REPLACE FUNCTION inv_transfer_item_atomic(
    target_campaign_id bigint,
    target_item_instance_id bigint,
    target_container_id bigint,
    target_location_id bigint,
    target_actor_id bigint,
    target_faction_id bigint,
    source_command_id bigint DEFAULT NULL,
    transfer_description text DEFAULT NULL
)
RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
    prior_container_id bigint;
    prior_location_id bigint;
    prior_actor_id bigint;
    prior_faction_id bigint;
    new_transfer_id bigint;
    custody_changed boolean;
    ownership_changed boolean;
    resolved_kind text;
BEGIN
    IF (
        (target_container_id IS NOT NULL)::integer
        +(target_location_id IS NOT NULL)::integer > 1
    ) THEN
        RAISE EXCEPTION
            'Item may have only one target custody position'
            USING ERRCODE='23514';
    END IF;
    IF (
        (target_actor_id IS NOT NULL)::integer
        +(target_faction_id IS NOT NULL)::integer > 1
    ) THEN
        RAISE EXCEPTION 'Item may have only one target legal owner'
            USING ERRCODE='23514';
    END IF;

    PERFORM 1
    FROM inv_item_instance
    WHERE item_instance_id=target_item_instance_id
      AND campaign_id=target_campaign_id
      AND item_status='active'
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active item does not exist in target campaign'
            USING ERRCODE='23514';
    END IF;

    SELECT container_id INTO prior_container_id
    FROM inv_container_item
    WHERE item_instance_id=target_item_instance_id;
    SELECT location_id INTO prior_location_id
    FROM loc_item_position
    WHERE item_instance_id=target_item_instance_id;
    SELECT actor_id,faction_id
    INTO prior_actor_id,prior_faction_id
    FROM inv_item_owner
    WHERE item_instance_id=target_item_instance_id;

    custody_changed :=
        prior_container_id IS DISTINCT FROM target_container_id
        OR prior_location_id IS DISTINCT FROM target_location_id;
    ownership_changed :=
        prior_actor_id IS DISTINCT FROM target_actor_id
        OR prior_faction_id IS DISTINCT FROM target_faction_id;
    IF NOT custody_changed AND NOT ownership_changed THEN
        RAISE EXCEPTION 'Item transfer does not change authoritative state'
            USING ERRCODE='23514';
    END IF;

    resolved_kind := CASE
        WHEN custody_changed AND ownership_changed
            THEN 'custody_and_ownership'
        WHEN ownership_changed THEN 'ownership'
        ELSE 'custody'
    END;

    INSERT INTO inv_transfer (
        campaign_id,transfer_kind,command_id,description
    )
    VALUES (
        target_campaign_id,resolved_kind,source_command_id,
        transfer_description
    )
    RETURNING transfer_id INTO new_transfer_id;

    INSERT INTO inv_item_transfer (
        transfer_id,campaign_id,item_instance_id,
        from_container_id,to_container_id,
        from_location_id,to_location_id,
        from_actor_id,to_actor_id,
        from_faction_id,to_faction_id
    )
    VALUES (
        new_transfer_id,target_campaign_id,target_item_instance_id,
        prior_container_id,target_container_id,
        prior_location_id,target_location_id,
        prior_actor_id,target_actor_id,
        prior_faction_id,target_faction_id
    );

    IF custody_changed THEN
        DELETE FROM inv_container_item
        WHERE item_instance_id=target_item_instance_id;
        DELETE FROM loc_item_position
        WHERE item_instance_id=target_item_instance_id;

        IF target_container_id IS NOT NULL THEN
            INSERT INTO inv_container_item (
                item_instance_id,campaign_id,container_id,
                source_transfer_id
            )
            VALUES (
                target_item_instance_id,target_campaign_id,
                target_container_id,new_transfer_id
            );
        ELSIF target_location_id IS NOT NULL THEN
            INSERT INTO loc_item_position (
                item_instance_id,campaign_id,location_id,
                source_transfer_id
            )
            VALUES (
                target_item_instance_id,target_campaign_id,
                target_location_id,new_transfer_id
            );
        END IF;
    END IF;

    IF ownership_changed THEN
        DELETE FROM inv_item_owner
        WHERE item_instance_id=target_item_instance_id;
        IF target_actor_id IS NOT NULL
           OR target_faction_id IS NOT NULL THEN
            INSERT INTO inv_item_owner (
                item_instance_id,campaign_id,actor_id,faction_id,
                source_transfer_id
            )
            VALUES (
                target_item_instance_id,target_campaign_id,
                target_actor_id,target_faction_id,new_transfer_id
            );
        END IF;
    END IF;

    UPDATE inv_transfer
    SET transfer_status='completed',
        completed_at=clock_timestamp()
    WHERE transfer_id=new_transfer_id;
    RETURN new_transfer_id;
END;
$$;
