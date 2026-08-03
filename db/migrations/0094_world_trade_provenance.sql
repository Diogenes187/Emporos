INSERT INTO src_artifact (
    source_work_id,artifact_kind,source_uri,source_revision,
    byte_length,checksum_sha256,media_type,local_role
)
SELECT source_work_id,'repository_file',source.source_uri,
       '0839018902355215fb8148f0b4ce1b1f8e011080',
       source.byte_length,source.checksum,'text/markdown','governing'
FROM src_work
CROSS JOIN (
    VALUES
        ('src/book3/worlds.md',22834::bigint,
         'e4cad29d7b99eadd5e2d143fd1a32fe6b6c0647ac7ffc86f20bf54198e486570'),
        ('src/book2/off-world-travel.md',39738::bigint,
         '8bc365323a009873d64bde259ed372936fe0944c04a404fd64d571765d6d56bf'),
        ('src/book2/trade-and-commerce.md',9207::bigint,
         '6cb57e103486f95c79c7f32218f895bae289f9bc16726da4cfc821308fbaf959')
) source(source_uri,byte_length,checksum)
WHERE work_code='cepheus-engine.github-v9.1';

INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
JOIN (
    VALUES
        ('src/book3/worlds.md','Worlds > World Size',
         'Cepheus Engine v9.1, Worlds: World Size'),
        ('src/book3/worlds.md','Worlds > Atmosphere',
         'Cepheus Engine v9.1, Worlds: Atmosphere'),
        ('src/book3/worlds.md','Worlds > Hydrographics',
         'Cepheus Engine v9.1, Worlds: Hydrographics'),
        ('src/book3/worlds.md','Worlds > World Population',
         'Cepheus Engine v9.1, Worlds: World Population'),
        ('src/book3/worlds.md','Worlds > Primary Starport',
         'Cepheus Engine v9.1, Worlds: Primary Starport'),
        ('src/book3/worlds.md','Worlds > World Government',
         'Cepheus Engine v9.1, Worlds: World Government'),
        ('src/book3/worlds.md','Worlds > Law Level',
         'Cepheus Engine v9.1, Worlds: Law Level'),
        ('src/book3/worlds.md','Worlds > Trade Codes',
         'Cepheus Engine v9.1, Worlds: Trade Codes'),
        ('src/book2/off-world-travel.md',
         'Off-World Travel > Interstellar Travel',
         'Cepheus Engine v9.1, Off-World Travel: Interstellar Travel'),
        ('src/book2/off-world-travel.md',
         'Off-World Travel > Ship''s Passage',
         'Cepheus Engine v9.1, Off-World Travel: Ship''s Passage'),
        ('src/book2/off-world-travel.md',
         'Off-World Travel > Fuel',
         'Cepheus Engine v9.1, Off-World Travel: Fuel'),
        ('src/book2/off-world-travel.md',
         'Off-World Travel > Starship Revenue',
         'Cepheus Engine v9.1, Off-World Travel: Starship Revenue'),
        ('src/book2/trade-and-commerce.md',
         'Trade and Commerce > Determine Goods Available',
         'Cepheus Engine v9.1, Trade: Determine Goods Available'),
        ('src/book2/trade-and-commerce.md',
         'Trade and Commerce > Modified Price',
         'Cepheus Engine v9.1, Trade: Modified Price'),
        ('src/book2/trade-and-commerce.md',
         'Trade and Commerce > Local Brokers',
         'Cepheus Engine v9.1, Trade: Local Brokers')
) source(source_uri,heading_path,display_citation)
  ON source.source_uri=artifact.source_uri;

ALTER TABLE rule_world_size
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_world_size SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > World Size'
);
ALTER TABLE rule_world_size ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_world_atmosphere
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_world_atmosphere SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > Atmosphere'
);
ALTER TABLE rule_world_atmosphere
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_atmosphere_survival_requirement
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_atmosphere_survival_requirement SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > Atmosphere'
);
ALTER TABLE rule_atmosphere_survival_requirement
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_world_hydrographics
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_world_hydrographics SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > Hydrographics'
);
ALTER TABLE rule_world_hydrographics
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_world_population
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_world_population SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > World Population'
);
ALTER TABLE rule_world_population
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_starport_class
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_starport_class SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > Primary Starport'
);
ALTER TABLE rule_starport_class
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_world_government
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_world_government SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > World Government'
);
ALTER TABLE rule_world_government
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_world_law_level
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_world_law_level SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Worlds > Law Level'
);
ALTER TABLE rule_world_law_level
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_jump_travel_system
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_jump_travel_system SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Off-World Travel > Interstellar Travel'
);
ALTER TABLE rule_jump_travel_system
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_passage_class
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_passage_class SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Off-World Travel > Ship''s Passage'
);
ALTER TABLE rule_passage_class
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_fuel_type
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_fuel_type SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Off-World Travel > Fuel'
);
ALTER TABLE rule_fuel_type
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_starport_traffic_expression
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_starport_traffic_expression SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Off-World Travel > Starship Revenue'
);
ALTER TABLE rule_starport_traffic_expression
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_modified_price_band
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_modified_price_band SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Trade and Commerce > Modified Price'
);
ALTER TABLE rule_modified_price_band
    ALTER COLUMN source_locator_id SET NOT NULL;

ALTER TABLE rule_local_broker
    ADD COLUMN source_locator_id bigint REFERENCES
        src_locator(source_locator_id);
UPDATE rule_local_broker SET source_locator_id=(
    SELECT source_locator_id FROM src_locator
    WHERE heading_path='Trade and Commerce > Local Brokers'
);
ALTER TABLE rule_local_broker
    ALTER COLUMN source_locator_id SET NOT NULL;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       'direct',true
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=CASE
      WHEN rule.rule_code LIKE 'world.trade-code.%'
          THEN 'Worlds > Trade Codes'
      ELSE 'Trade and Commerce > Determine Goods Available'
  END
WHERE rule.rule_code LIKE 'world.trade-code.%'
   OR rule.rule_code LIKE 'trade.good.%';
