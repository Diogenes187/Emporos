ALTER TABLE ship_component_definition
    DROP CONSTRAINT ship_component_definition_calculation_status_check,
    ADD CONSTRAINT ship_component_definition_calculation_status_check CHECK (
        calculation_status IN (
            'published','formula','included','source_unspecified','adjudicated'
        )
    );

UPDATE ship_component_definition
SET unit_tons=4,unit_cost_minor=90000,tonnage_basis='fixed',
    tonnage_factor=1,cost_basis='fixed',calculation_status='adjudicated'
WHERE component_code='smelter';

UPDATE ship_class_component selected
SET allocated_tons=4
FROM ship_class class,ship_component_definition component
WHERE class.ship_class_rule_id=selected.ship_class_rule_id
  AND component.component_rule_id=selected.component_rule_id
  AND class.class_code='asteroid-miner'
  AND component.component_code='smelter';

UPDATE ship_class_drive selected
SET drive_code=CASE selected.drive_kind WHEN 'jump' THEN 'H' ELSE 'N' END,
    validation_status='validated'
FROM ship_class class
WHERE class.ship_class_rule_id=selected.ship_class_rule_id
  AND class.class_code='destroyer'
  AND selected.drive_kind IN ('jump','maneuver');

ALTER TABLE ship_class_carried_item
    DROP CONSTRAINT ship_class_carried_item_relationship_status_check,
    ADD CONSTRAINT ship_class_carried_item_relationship_status_check CHECK (
        relationship_status IN (
            'published','published_tl_conflict','published_cross_tl_payload'
        )
    );

CREATE OR REPLACE FUNCTION ship_validate_class_carried_item()
RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    capacity integer;
    class_tl smallint;
    item_tl smallint;
BEGIN
    SELECT hangar.installation_count*option.units_per_installation,
           class.minimum_tech_level,item.minimum_tech_level
    INTO capacity,class_tl,item_tl
    FROM ship_class_hangar_option hangar
    JOIN rule_ship_hangar_option option USING (hangar_option_code)
    JOIN ship_class class ON class.ship_class_rule_id=hangar.ship_class_rule_id
    JOIN inv_item_definition item ON item.rule_id=NEW.item_rule_id
    WHERE hangar.ship_class_rule_id=NEW.carrier_class_rule_id
      AND hangar.hangar_identifier=NEW.hangar_identifier;

    IF NEW.item_count>capacity
       OR (class_tl<item_tl AND NEW.relationship_status NOT IN (
               'published_tl_conflict','published_cross_tl_payload'))
       OR (class_tl>=item_tl AND NEW.relationship_status<>'published') THEN
        RAISE EXCEPTION
            'Carried item exceeds hangar capacity or conflicts with tech level'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

UPDATE ship_class_carried_item carried
SET relationship_status='published_cross_tl_payload'
FROM ship_class class,rule_rule item
WHERE class.ship_class_rule_id=carried.carrier_class_rule_id
  AND item.rule_id=carried.item_rule_id
  AND class.class_code='research-vessel'
  AND item.rule_code='equipment.probe-drone';

UPDATE ship_class_source_assertion assertion
SET canonical_value=source.canonical_value,
    assertion_status='reconciled',rationale=source.rationale
FROM ship_class class
JOIN (VALUES
    ('asteroid-miner','smelter-specification',
     '4 tons; Cr90,000; capacity unspecified',
     'Raymond agreed that the exact four-ton and Cr90,000 construction gaps define the named smelter; no processing capacity is invented.'),
    ('destroyer','jump-drive-performance','H / Jump-2',
     'Raymond agreed that drive D is a transcription error because the published 800-ton performance matrix requires drive H for Jump-2.'),
    ('destroyer','maneuver-drive-performance','N / 4-G',
     'Raymond agreed that drive M is a transcription error because the published 800-ton performance matrix requires drive N for 4-G.'),
    ('research-vessel','probe-drone-tech-level',
     'TL9 spacecraft design carrying TL11 procured payload',
     'Raymond agreed that carried probe drones are payload procurement and do not raise the underlying spacecraft design tech level.')
) source(class_code,field_code,canonical_value,rationale)
  ON source.class_code=class.class_code
WHERE assertion.ship_class_rule_id=class.ship_class_rule_id
  AND assertion.field_code=source.field_code;

INSERT INTO rule_interpretation (
    rule_id,interpretation_type,decision_register_entry,rationale
)
SELECT rule.rule_id,'agreed_interpretation',source.entry,source.rationale
FROM (VALUES
    ('ship.class.asteroid-miner','CE-SHIP-001',
     'The named smelter fills the exact four-ton and Cr90,000 published construction gaps; capacity remains unspecified.'),
    ('ship.class.destroyer','CE-SHIP-002',
     'For the 800-ton Destroyer, drive H supplies Jump-2 and drive N supplies 4-G under the published performance matrix.'),
    ('ship.class.research-vessel','CE-SHIP-003',
     'The vessel remains a TL9 spacecraft design; its explicitly carried TL11 probe drones require TL11 procurement as payload.')
) source(rule_code,entry,rationale)
JOIN rule_rule rule ON rule.rule_code=source.rule_code;

UPDATE src_issue issue
SET issue_status=source.issue_status,resolved_at=clock_timestamp(),
    resolution_summary=source.resolution_summary,
    engine_disposition='preserve_rule'
FROM (VALUES
    ('ship.asteroid-miner.construction.cost','resolved',
     'CE-SHIP-001 assigns the named smelter the exact missing Cr90,000 installed cost.'),
    ('ship.asteroid-miner.construction.tonnage','resolved',
     'CE-SHIP-001 assigns the named smelter the exact four unallocated hull tons.'),
    ('ship.asteroid-miner.source.smelter-specification','resolved',
     'CE-SHIP-001 defines four tons and Cr90,000 while retaining source-unspecified capacity.'),
    ('ship.destroyer.source.jump-drive-performance','resolved',
     'CE-SHIP-002 corrects the drive code to H for Jump-2 on an 800-ton hull.'),
    ('ship.destroyer.source.maneuver-drive-performance','resolved',
     'CE-SHIP-002 corrects the drive code to N for 4-G on an 800-ton hull.'),
    ('ship.research-vessel.source.probe-drone-tech-level',
     'accepted_as_published',
     'CE-SHIP-003 retains the TL9 spacecraft design and classifies its TL11 drones as separately procured carried payload.')
) source(issue_code,issue_status,resolution_summary)
WHERE issue.issue_code=source.issue_code;
