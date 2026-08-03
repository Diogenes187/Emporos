INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicle Damage',
            'Cepheus Engine OGN, Vehicle Damage'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicle Damage > Vehicle Hit Location',
            'Cepheus Engine OGN, Vehicle Hit Location'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs',
            'Cepheus Engine OGN, Vehicle Repairs'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage',
            'Cepheus Engine OGN, Vehicle System Damage Repair'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs > Hull Damage',
            'Cepheus Engine OGN, Vehicle Hull Damage Repair'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Repairs > Structure Damage',
            'Cepheus Engine OGN, Vehicle Structure Damage Repair'
        )
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-personal-combat/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.ogn'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path=
     CASE rule.rule_code
         WHEN 'vehicle.damage.procedure'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicle Damage'
         WHEN 'vehicle.damage.hit-location'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicle Damage > Vehicle Hit Location'
         WHEN 'vehicle.repair.system'
             THEN 'Personal Combat > Vehicles in Personal Combat > Repairs > System Damage'
         WHEN 'vehicle.repair.hull'
             THEN 'Personal Combat > Vehicles in Personal Combat > Repairs > Hull Damage'
         WHEN 'vehicle.repair.structure'
             THEN 'Personal Combat > Vehicles in Personal Combat > Repairs > Structure Damage'
     END
WHERE rule.rule_code LIKE 'vehicle.damage.%'
   OR rule.rule_code LIKE 'vehicle.repair.%';
