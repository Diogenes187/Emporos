INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle-Mounted Weapon Ranges > Attack Difficulties by Weapon Type',
         'Cepheus Engine OGN VDS, Vehicle-Mounted Weapon Ranges'),
        ('Vehicle Design > Vehicle Armaments > Vehicular Weapons',
         'Cepheus Engine OGN VDS, Vehicular Weapons'),
        ('Vehicle Design > Vehicle Armaments > Vehicular Weapons > Special Weapon Rules',
         'Cepheus Engine OGN VDS, Special Weapon Rules'),
        ('Vehicle Design > Vehicle Armaments > Vehicular Weapon Ammunition',
         'Cepheus Engine OGN VDS, Vehicular Weapon Ammunition'),
        ('Vehicle Design > Vehicle Armaments > Ordinance Bays',
         'Cepheus Engine OGN VDS, Ordinance Bays'),
        ('Vehicle Design > Vehicle Armaments > Missiles',
         'Cepheus Engine OGN VDS, Vehicular Missiles'),
        ('Vehicle Design > Vehicle Armaments > Anti-Missile Systems',
         'Cepheus Engine OGN VDS, Anti-Missile Systems')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-introduction-2/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code LIKE 'vehicle.weapon-special.%'
               THEN special_locator.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.weapon.%'
               THEN weapon_locator.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.ordnance%'
               THEN ordnance_locator.source_locator_id
           WHEN rule.rule_code LIKE 'vehicle.missile.%'
               THEN missile_locator.source_locator_id
           ELSE defense_locator.source_locator_id
       END,
       'corroborating',false
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.ogn'
LEFT JOIN src_locator weapon_locator
  ON weapon_locator.source_work_id=work.source_work_id
 AND weapon_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons'
LEFT JOIN src_locator special_locator
  ON special_locator.source_work_id=work.source_work_id
 AND special_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Vehicular Weapons > Special Weapon Rules'
LEFT JOIN src_locator ordnance_locator
  ON ordnance_locator.source_work_id=work.source_work_id
 AND ordnance_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Ordinance Bays'
LEFT JOIN src_locator missile_locator
  ON missile_locator.source_work_id=work.source_work_id
 AND missile_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Missiles'
LEFT JOIN src_locator defense_locator
  ON defense_locator.source_work_id=work.source_work_id
 AND defense_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Anti-Missile Systems'
WHERE rule.rule_code LIKE 'vehicle.weapon.%'
   OR rule.rule_code LIKE 'vehicle.weapon-special.%'
   OR rule.rule_code LIKE 'vehicle.ordnance%'
   OR rule.rule_code LIKE 'vehicle.missile.%'
   OR rule.rule_code='vehicle.anti-missile.general'
   OR rule.rule_code LIKE 'vehicle.anti-missile-system.%';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,
       CASE
           WHEN issue.issue_code LIKE 'vehicle.ordnance.%'
               THEN ordnance_locator.source_locator_id
           WHEN issue.issue_code LIKE 'vehicle.missile.%'
               THEN missile_locator.source_locator_id
           ELSE defense_locator.source_locator_id
       END,
       'corroborating'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-engine.ogn'
LEFT JOIN src_locator ordnance_locator
  ON ordnance_locator.source_work_id=work.source_work_id
 AND ordnance_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Ordinance Bays'
LEFT JOIN src_locator missile_locator
  ON missile_locator.source_work_id=work.source_work_id
 AND missile_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Missiles'
LEFT JOIN src_locator defense_locator
  ON defense_locator.source_work_id=work.source_work_id
 AND defense_locator.heading_path=
     'Vehicle Design > Vehicle Armaments > Anti-Missile Systems'
WHERE issue.issue_code IN (
    'vehicle.ordnance.heavy-nuclear-torpedo-row',
    'vehicle.missile.nas-radiation-hit',
    'vehicle.anti-missile.decoy-guidance-label'
);

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor retains the same VDS source text and common-vehicle summaries but has no independent vehicle armament, missile, ordnance, or anti-missile calculator capable of resolving this question.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='engine/skills.py'
WHERE issue.issue_code IN (
    'vehicle.ordnance.heavy-nuclear-torpedo-row',
    'vehicle.missile.nas-radiation-hit',
    'vehicle.anti-missile.decoy-guidance-label'
);
