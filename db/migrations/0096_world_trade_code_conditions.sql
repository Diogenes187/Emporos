CREATE TABLE rule_trade_code_constraint (
    trade_code_constraint_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    trade_code_rule_id bigint NOT NULL REFERENCES
        loc_trade_code(trade_code_rule_id),
    profile_component text NOT NULL CHECK (
        profile_component IN (
            'size','atmosphere','hydrographics','population',
            'government','law_level','technology_level'
        )
    ),
    minimum_value smallint,
    maximum_value smallint,
    source_locator_id bigint NOT NULL REFERENCES
        src_locator(source_locator_id),
    UNIQUE (trade_code_rule_id,profile_component),
    CHECK (
        minimum_value IS NULL OR maximum_value IS NULL
        OR minimum_value<=maximum_value
    )
);

CREATE TABLE rule_trade_code_constraint_value (
    trade_code_constraint_id bigint NOT NULL REFERENCES
        rule_trade_code_constraint(trade_code_constraint_id),
    allowed_value smallint NOT NULL,
    PRIMARY KEY (trade_code_constraint_id,allowed_value)
);

INSERT INTO rule_trade_code_constraint (
    trade_code_rule_id,profile_component,
    minimum_value,maximum_value,source_locator_id
)
SELECT trade.trade_code_rule_id,source.component,
       source.minimum_value,source.maximum_value,
       locator.source_locator_id
FROM loc_trade_code trade
JOIN (
    VALUES
        ('Ag','atmosphere',4,9),('Ag','hydrographics',4,8),
        ('Ag','population',5,7),
        ('As','size',0,0),('As','atmosphere',0,0),
        ('As','hydrographics',0,0),
        ('Ba','population',0,0),('Ba','government',0,0),
        ('Ba','law_level',0,0),
        ('De','atmosphere',2,NULL),('De','hydrographics',0,0),
        ('Fl','atmosphere',10,NULL),('Fl','hydrographics',1,NULL),
        ('Ga','atmosphere',NULL,NULL),('Ga','hydrographics',4,9),
        ('Ga','population',4,8),
        ('Hi','population',9,NULL),
        ('Ht','technology_level',12,NULL),
        ('Ic','atmosphere',0,1),('Ic','hydrographics',1,NULL),
        ('In','atmosphere',NULL,NULL),('In','population',9,NULL),
        ('Lo','population',1,3),('Lt','technology_level',NULL,5),
        ('Na','atmosphere',0,3),('Na','hydrographics',0,3),
        ('Na','population',6,NULL),('Ni','population',4,6),
        ('Po','atmosphere',2,5),('Po','hydrographics',0,3),
        ('Ri','atmosphere',NULL,NULL),('Ri','population',6,8),
        ('Wa','hydrographics',10,10),('Va','atmosphere',0,0)
) source(trade_code,component,minimum_value,maximum_value)
  ON trade.trade_code=source.trade_code
JOIN src_locator locator
  ON locator.heading_path='Worlds > Trade Codes'
JOIN src_work work ON work.source_work_id=locator.source_work_id
WHERE work.work_code='cepheus-engine.github-v9.1';

INSERT INTO rule_trade_code_constraint_value (
    trade_code_constraint_id,allowed_value
)
SELECT constraint_row.trade_code_constraint_id,source.allowed_value
FROM rule_trade_code_constraint constraint_row
JOIN loc_trade_code trade
  ON trade.trade_code_rule_id=constraint_row.trade_code_rule_id
JOIN (
    VALUES
        ('Ga','atmosphere',5),('Ga','atmosphere',6),
        ('Ga','atmosphere',8),
        ('In','atmosphere',0),('In','atmosphere',1),
        ('In','atmosphere',2),('In','atmosphere',4),
        ('In','atmosphere',7),('In','atmosphere',9),
        ('Ri','atmosphere',6),('Ri','atmosphere',8)
) source(trade_code,component,allowed_value)
  ON source.trade_code=trade.trade_code
 AND source.component=constraint_row.profile_component;

CREATE OR REPLACE FUNCTION loc_world_profile_qualifies_for_trade_code(
    target_world_profile_id bigint,
    target_trade_code_rule_id bigint
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT NOT EXISTS (
        SELECT 1
        FROM rule_trade_code_constraint constraint_row
        JOIN loc_world_profile profile
          ON profile.world_profile_id=target_world_profile_id
        WHERE constraint_row.trade_code_rule_id=
              target_trade_code_rule_id
          AND (
              (
                  constraint_row.minimum_value IS NOT NULL
                  AND CASE constraint_row.profile_component
                      WHEN 'size' THEN profile.size_code
                      WHEN 'atmosphere' THEN profile.atmosphere_code
                      WHEN 'hydrographics' THEN profile.hydrographics_code
                      WHEN 'population' THEN profile.population_code
                      WHEN 'government' THEN profile.government_code
                      WHEN 'law_level' THEN profile.law_level_code
                      WHEN 'technology_level'
                          THEN profile.technology_level
                  END < constraint_row.minimum_value
              )
              OR (
                  constraint_row.maximum_value IS NOT NULL
                  AND CASE constraint_row.profile_component
                      WHEN 'size' THEN profile.size_code
                      WHEN 'atmosphere' THEN profile.atmosphere_code
                      WHEN 'hydrographics' THEN profile.hydrographics_code
                      WHEN 'population' THEN profile.population_code
                      WHEN 'government' THEN profile.government_code
                      WHEN 'law_level' THEN profile.law_level_code
                      WHEN 'technology_level'
                          THEN profile.technology_level
                  END > constraint_row.maximum_value
              )
              OR (
                  EXISTS (
                      SELECT 1
                      FROM rule_trade_code_constraint_value allowed
                      WHERE allowed.trade_code_constraint_id=
                            constraint_row.trade_code_constraint_id
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM rule_trade_code_constraint_value allowed
                      WHERE allowed.trade_code_constraint_id=
                            constraint_row.trade_code_constraint_id
                        AND allowed.allowed_value=
                            CASE constraint_row.profile_component
                                WHEN 'size' THEN profile.size_code
                                WHEN 'atmosphere'
                                    THEN profile.atmosphere_code
                                WHEN 'hydrographics'
                                    THEN profile.hydrographics_code
                                WHEN 'population'
                                    THEN profile.population_code
                                WHEN 'government'
                                    THEN profile.government_code
                                WHEN 'law_level'
                                    THEN profile.law_level_code
                                WHEN 'technology_level'
                                    THEN profile.technology_level
                            END
                  )
              )
          )
    );
$$;

CREATE OR REPLACE FUNCTION loc_require_qualified_trade_code()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT loc_world_profile_qualifies_for_trade_code(
        NEW.world_profile_id,NEW.trade_code_rule_id
    ) THEN
        RAISE EXCEPTION 'World profile does not qualify for trade code'
            USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER loc_world_trade_code_qualification
BEFORE INSERT OR UPDATE ON loc_world_trade_code
FOR EACH ROW EXECUTE FUNCTION loc_require_qualified_trade_code();
