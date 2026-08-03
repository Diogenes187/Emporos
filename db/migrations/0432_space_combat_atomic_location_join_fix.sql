DO $$
DECLARE definition text; revised text;
BEGIN
    SELECT pg_get_functiondef(
        'senc_apply_next_damage_location_hit(bigint,smallint)'::regprocedure
    ) INTO definition;
    revised:=replace(
        replace(
            definition,
            'JOIN ship_ship ship USING (ship_id)',
            'JOIN ship_ship ship ON ship.ship_id=vessel.ship_id'
        ),
        'JOIN ship_class class USING (ship_class_rule_id)',
        'JOIN ship_class class ON class.ship_class_rule_id=ship.ship_class_rule_id'
    );
    IF revised=definition THEN
        RAISE EXCEPTION 'Atomic location hit function join text was not found';
    END IF;
    EXECUTE revised;
END $$;
