INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Vehicle Armaments',
         'Cepheus Engine OGN VDS, Vehicle Armaments'),
        ('Vehicle Design > Vehicle Armaments > Gun Ports',
         'Cepheus Engine OGN VDS, Vehicle Gun Ports'),
        ('Vehicle Design > Vehicle Armaments > Weapon Mounts',
         'Cepheus Engine OGN VDS, Vehicle Weapon Mounts'),
        ('Vehicle Design > Vehicle Armaments > Vehicle Turrets',
         'Cepheus Engine OGN VDS, Vehicle Turrets'),
        ('Vehicle Design > Vehicle Armaments > Vehicle Armament Options',
         'Cepheus Engine OGN VDS, Vehicle Armament Options')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-introduction-2/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       locator.source_locator_id,'corroborating',false
FROM rule_rule rule
JOIN src_locator locator
  ON locator.heading_path=
     CASE
         WHEN rule.rule_code='vehicle.armament.gun-port'
           OR rule.rule_code LIKE 'vehicle.gun-port-weapon.%'
             THEN 'Vehicle Design > Vehicle Armaments > Gun Ports'
         WHEN rule.rule_code LIKE 'vehicle.weapon-mount.%'
           OR rule.rule_code LIKE 'vehicle.weapon-mount-option.%'
             THEN 'Vehicle Design > Vehicle Armaments > Weapon Mounts'
         WHEN rule.rule_code LIKE 'vehicle.turret.%'
           OR rule.rule_code LIKE 'vehicle.turret-option.%'
             THEN 'Vehicle Design > Vehicle Armaments > Vehicle Turrets'
         ELSE
             'Vehicle Design > Vehicle Armaments > Vehicle Armament Options'
     END
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE rule.rule_code='vehicle.armament.gun-port'
   OR rule.rule_code LIKE 'vehicle.gun-port-weapon.%'
   OR rule.rule_code LIKE 'vehicle.weapon-mount.%'
   OR rule.rule_code LIKE 'vehicle.weapon-mount-option.%'
   OR rule.rule_code LIKE 'vehicle.turret.%'
   OR rule.rule_code LIKE 'vehicle.turret-option.%'
   OR rule.rule_code LIKE 'vehicle.armament-option.%';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicle Armament Options'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code=
      'vehicle.armament.heavy-weapon-rof-rounding';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor defines vehicle-related skills but has no vehicle weapon-mount, turret, or rate-of-fire calculator capable of resolving this VDS question.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='engine/skills.py'
WHERE issue.issue_code=
      'vehicle.armament.heavy-weapon-rof-rounding';
