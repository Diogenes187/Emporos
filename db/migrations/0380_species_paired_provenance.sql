INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,anchor,display_citation,source_order
)
SELECT artifact.source_work_id,artifact.source_artifact_id,'heading',
       source.heading_path,source.anchor,
       CASE work.work_code
           WHEN 'cepheus-engine.ogn'
               THEN 'Cepheus Engine OGN, ' || source.title
           ELSE 'Cepheus Engine GitHub v9.1, ' || source.title
       END,
       source.source_order
FROM src_work work
JOIN src_artifact artifact ON artifact.source_work_id=work.source_work_id
CROSS JOIN (VALUES
    ('Character Creation > On Alien Species',
     'species-overview','On Alien Species',728),
    ('Character Creation > On Alien Species > Avians',
     'species-avians','Avians',736),
    ('Character Creation > On Alien Species > Espers',
     'species-espers','Espers',744),
    ('Character Creation > On Alien Species > Insectans',
     'species-insectans','Insectans',752),
    ('Character Creation > On Alien Species > Merfolk',
     'species-merfolk','Merfolk',764),
    ('Character Creation > On Alien Species > Reptilians',
     'species-reptilians','Reptilians',772),
    ('Character Creation > On Alien Species > Alien Species Trait Descriptions',
     'species-trait-descriptions','Alien Species Trait Descriptions',778)
) source(heading_path,anchor,title,source_order)
WHERE (
        work.work_code='cepheus-engine.ogn'
        AND artifact.source_uri=
          'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-character-creation/'
    )
   OR (
        work.work_code='cepheus-engine.github-v9.1'
        AND artifact.source_uri='src/book1/character-creation.md'
    );

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code
           WHEN 'cepheus-engine.ogn' THEN 'direct'
           ELSE 'corroborating'
       END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule
CROSS JOIN src_work work
JOIN src_locator locator ON locator.source_work_id=work.source_work_id
WHERE work.work_code IN (
          'cepheus-engine.ogn','cepheus-engine.github-v9.1'
      )
  AND rule.rule_code IN (
          'equipment.weapon.species-natural-weapon',
          'species.human','species.avian','species.esper',
          'species.insectan','species.merfolk','species.reptilian'
      )
  AND locator.anchor=CASE rule.rule_code
      WHEN 'species.human' THEN 'species-overview'
      WHEN 'species.avian' THEN 'species-avians'
      WHEN 'species.esper' THEN 'species-espers'
      WHEN 'species.insectan' THEN 'species-insectans'
      WHEN 'species.merfolk' THEN 'species-merfolk'
      WHEN 'species.reptilian' THEN 'species-reptilians'
      ELSE 'species-trait-descriptions'
  END;

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,locator.source_locator_id,
       CASE work.work_code
           WHEN 'cepheus-engine.ogn' THEN 'direct'
           ELSE 'corroborating'
       END,
       work.work_code='cepheus-engine.ogn'
FROM rule_rule rule
CROSS JOIN src_work work
JOIN src_locator locator ON locator.source_work_id=work.source_work_id
WHERE work.work_code IN (
          'cepheus-engine.ogn','cepheus-engine.github-v9.1'
      )
  AND rule.rule_code LIKE 'species-trait.%'
  AND locator.anchor='species-trait-descriptions';
