INSERT INTO src_locator (
    source_work_id,source_artifact_id,locator_type,
    heading_path,display_citation
)
SELECT artifact.source_work_id,artifact.source_artifact_id,
       'heading',source.heading_path,source.display_citation
FROM src_artifact artifact
CROSS JOIN (
    VALUES
        ('Vehicle Design > Special Rules for Vehicles > Alien Vehicles',
         'Cepheus Engine OGN VDS, Alien Vehicles'),
        ('Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope',
         'Cepheus Engine OGN VDS, Airship/Balloon Lift Envelope'),
        ('Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft',
         'Cepheus Engine OGN VDS, Atmospheres and Aircraft'),
        ('Vehicle Design > Special Rules for Vehicles > Missile and Torpedo Attacks',
         'Cepheus Engine OGN VDS, Missile and Torpedo Attacks'),
        ('Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles',
         'Cepheus Engine OGN VDS, Non-Powered Vehicles'),
        ('Vehicle Design > Special Rules for Vehicles > Off-Road Movement for Ground Vehicles',
         'Cepheus Engine OGN VDS, Off-Road Movement')
) source(heading_path,display_citation)
WHERE artifact.source_uri=
    'https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-introduction-2/';

INSERT INTO src_record_provenance (
    rule_id,content_package_id,source_locator_id,
    provenance_class,is_primary_citation
)
SELECT rule.rule_id,rule.content_package_id,
       CASE
           WHEN rule.rule_code='vehicle.special.alien-design'
               THEN alien_locator.source_locator_id
           WHEN rule.rule_code='vehicle.special.lift-envelope'
               THEN lift_locator.source_locator_id
           WHEN rule.rule_code LIKE
                'vehicle.special.aircraft-environment%'
               THEN aircraft_locator.source_locator_id
           WHEN rule.rule_code=
                'vehicle.special.missile-torpedo-attack'
               THEN missile_locator.source_locator_id
           WHEN rule.rule_code IN (
                'vehicle.special.animal-powered',
                'vehicle.special.wind-powered'
           )
               THEN power_locator.source_locator_id
           ELSE off_road_locator.source_locator_id
       END,
       'corroborating',false
FROM rule_rule rule
JOIN src_work work
  ON work.work_code='cepheus-engine.ogn'
LEFT JOIN src_locator alien_locator
  ON alien_locator.source_work_id=work.source_work_id
 AND alien_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Alien Vehicles'
LEFT JOIN src_locator lift_locator
  ON lift_locator.source_work_id=work.source_work_id
 AND lift_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Airship/Balloon Lift Envelope'
LEFT JOIN src_locator aircraft_locator
  ON aircraft_locator.source_work_id=work.source_work_id
 AND aircraft_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft'
LEFT JOIN src_locator missile_locator
  ON missile_locator.source_work_id=work.source_work_id
 AND missile_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Missile and Torpedo Attacks'
LEFT JOIN src_locator power_locator
  ON power_locator.source_work_id=work.source_work_id
 AND power_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Non-Powered Vehicles'
LEFT JOIN src_locator off_road_locator
  ON off_road_locator.source_work_id=work.source_work_id
 AND off_road_locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Off-Road Movement for Ground Vehicles'
WHERE rule.rule_code LIKE 'vehicle.special.%';

INSERT INTO src_issue_locator (
    source_issue_id,source_locator_id,evidence_role
)
SELECT issue.source_issue_id,locator.source_locator_id,'corroborating'
FROM src_issue issue
JOIN src_locator locator
  ON locator.heading_path=
     'Vehicle Design > Special Rules for Vehicles > Atmospheres and Aircraft'
JOIN src_work work
  ON work.source_work_id=locator.source_work_id
 AND work.work_code='cepheus-engine.ogn'
WHERE issue.issue_code=
      'vehicle.aircraft.environment-tolerance-wording';

INSERT INTO src_issue_comparison_check (
    source_issue_id,comparison_work_id,source_locator_id,
    check_status,evidence_summary
)
SELECT issue.source_issue_id,work.source_work_id,
       locator.source_locator_id,'no_independent_calculation',
       'The predecessor retains the same VDS text but has no aircraft environment-tolerance calculator or adjudication capable of resolving the boundary wording.'
FROM src_issue issue
JOIN src_work work
  ON work.work_code='cepheus-game.legacy-local'
JOIN src_locator locator
  ON locator.source_work_id=work.source_work_id
 AND locator.heading_path='engine/skills.py'
WHERE issue.issue_code=
      'vehicle.aircraft.environment-tolerance-wording';
