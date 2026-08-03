INSERT INTO src_artifact(source_work_id,artifact_kind,source_uri,source_revision,media_type,local_role)
SELECT source_work_id,'repository_file','src/book3/refereeing-the-game.md',source_revision,'text/markdown','verification' FROM src_work WHERE work_code='cepheus-engine.github-v9.1' ON CONFLICT DO NOTHING;
INSERT INTO src_artifact(source_work_id,artifact_kind,source_uri,media_type,local_role)
SELECT source_work_id,'web_page','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-refereeing-the-game/','text/html','governing' FROM src_work WHERE work_code='cepheus-engine.ogn' ON CONFLICT DO NOTHING;
INSERT INTO src_locator(source_work_id,source_artifact_id,locator_type,heading_path,display_citation)
SELECT a.source_work_id,a.source_artifact_id,'heading','Refereeing the Game > Improvisation > Improvisational Preparation',CASE w.work_code WHEN 'cepheus-engine.ogn' THEN 'Cepheus Engine SRD, Improvisational Preparation' ELSE 'Cepheus Engine v9.1, Improvisational Preparation' END
FROM src_artifact a JOIN src_work w USING(source_work_id) WHERE a.source_uri IN('src/book3/refereeing-the-game.md','https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/cepheus-engine-refereeing-the-game/') ON CONFLICT DO NOTHING;
INSERT INTO src_record_provenance(rule_id,content_package_id,source_locator_id,provenance_class,is_primary_citation)
SELECT r.rule_id,r.content_package_id,l.source_locator_id,'agreed_addition',w.work_code='cepheus-engine.ogn' FROM rule_rule r CROSS JOIN src_locator l JOIN src_work w USING(source_work_id)
WHERE r.rule_code='referee.structured-scene-preparation' AND l.heading_path='Refereeing the Game > Improvisation > Improvisational Preparation' AND w.work_code IN('cepheus-engine.ogn','cepheus-engine.github-v9.1') ON CONFLICT DO NOTHING;
