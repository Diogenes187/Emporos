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
            'Personal Combat > Vehicles in Personal Combat',
            'Cepheus Engine OGN, Vehicles in Personal Combat'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Closed and Open Vehicles',
            'Cepheus Engine OGN, Closed and Open Vehicles'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicle-Mounted Weapons',
            'Cepheus Engine OGN, Vehicle-Mounted Weapons'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Collisions',
            'Cepheus Engine OGN, Collisions'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions',
            'Cepheus Engine OGN, Vehicular Actions'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Evasive Action',
            'Cepheus Engine OGN, Evasive Action'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Maneuvering',
            'Cepheus Engine OGN, Maneuvering'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Ram',
            'Cepheus Engine OGN, Ram'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Stunt',
            'Cepheus Engine OGN, Stunt'
        ),
        (
            'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Weave',
            'Cepheus Engine OGN, Weave'
        )
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-personal-combat/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code='vehicle.combat.procedure'
               THEN procedure_locator.source_locator_id
           WHEN rule.rule_code=
                'vehicle.combat.occupant-protection'
               THEN protection_locator.source_locator_id
           WHEN rule.rule_code='vehicle.combat.weapon-arcs'
               THEN arc_locator.source_locator_id
           WHEN rule.rule_code='vehicle.combat.collision'
               THEN collision_locator.source_locator_id
           ELSE action_locator.source_locator_id
       END,
       'corroborating',false
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.ogn'
LEFT JOIN src_locator procedure_locator
  ON procedure_locator.source_work_id=work.source_work_id
 AND procedure_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat'
LEFT JOIN src_locator protection_locator
  ON protection_locator.source_work_id=work.source_work_id
 AND protection_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Closed and Open Vehicles'
LEFT JOIN src_locator arc_locator
  ON arc_locator.source_work_id=work.source_work_id
 AND arc_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Vehicle-Mounted Weapons'
LEFT JOIN src_locator collision_locator
  ON collision_locator.source_work_id=work.source_work_id
 AND collision_locator.heading_path=
     'Personal Combat > Vehicles in Personal Combat > Collisions'
LEFT JOIN src_locator action_locator
  ON action_locator.source_work_id=work.source_work_id
 AND action_locator.heading_path=
     CASE rule.rule_code
         WHEN 'vehicle.combat.action.evasive'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Evasive Action'
         WHEN 'vehicle.combat.action.maneuver'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Maneuvering'
         WHEN 'vehicle.combat.action.ram'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Ram'
         WHEN 'vehicle.combat.action.stunt'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Stunt'
         WHEN 'vehicle.combat.action.weave'
             THEN 'Personal Combat > Vehicles in Personal Combat > Vehicular Actions > Weave'
     END
WHERE rule.rule_code LIKE 'vehicle.combat.%';
