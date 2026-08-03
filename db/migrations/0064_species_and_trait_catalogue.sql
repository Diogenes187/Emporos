ALTER TABLE rule_rule DROP CONSTRAINT rule_rule_rule_category_check;
ALTER TABLE rule_rule ADD CONSTRAINT rule_rule_rule_category_check CHECK (
    rule_category IN (
        'characteristic', 'skill', 'skill_specialty', 'task', 'difficulty',
        'random_table', 'career', 'equipment', 'combat', 'travel', 'trade',
        'ship', 'vehicle', 'world', 'encounter', 'psionics', 'species',
        'species_trait', 'other'
    )
);

CREATE TABLE rule_species (
    species_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    species_code text NOT NULL UNIQUE CHECK (
        species_code ~ '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'
    ),
    display_order smallint NOT NULL UNIQUE CHECK (display_order > 0),
    maturity_age_years smallint CHECK (maturity_age_years > 0),
    aging_start_age_years smallint CHECK (
        aging_start_age_years IS NULL
        OR aging_start_age_years >= maturity_age_years
    ),
    replaces_social_standing boolean NOT NULL DEFAULT false,
    social_characteristic_name text,
    source_mechanics_text text NOT NULL CHECK (
        btrim(source_mechanics_text) <> ''
    ),
    CHECK (
        replaces_social_standing
        = (social_characteristic_name IS NOT NULL)
    )
);

CREATE TABLE rule_species_characteristic_generation (
    species_rule_id bigint NOT NULL REFERENCES rule_species(species_rule_id),
    characteristic_rule_id bigint NOT NULL REFERENCES
        rule_characteristic(rule_id),
    dice_count smallint NOT NULL CHECK (dice_count > 0),
    die_sides smallint NOT NULL CHECK (die_sides > 1),
    roll_modifier smallint NOT NULL DEFAULT 0,
    racial_maximum_modifier smallint NOT NULL DEFAULT 0,
    source_trait_kind text NOT NULL CHECK (
        source_trait_kind IN ('standard','notable','weak')
    ),
    PRIMARY KEY (species_rule_id,characteristic_rule_id)
);

CREATE TABLE rule_species_physical_generation (
    species_rule_id bigint PRIMARY KEY REFERENCES rule_species(species_rule_id),
    height_base_cm smallint NOT NULL CHECK (height_base_cm >= 0),
    height_dice_count smallint NOT NULL CHECK (height_dice_count > 0),
    height_die_sides smallint NOT NULL CHECK (height_die_sides > 1),
    height_multiplier_cm smallint NOT NULL CHECK (height_multiplier_cm > 0),
    mass_base_kg smallint NOT NULL CHECK (mass_base_kg >= 0),
    mass_dice_count smallint NOT NULL CHECK (mass_dice_count > 0),
    mass_die_sides smallint NOT NULL CHECK (mass_die_sides > 1),
    mass_multiplier_kg smallint NOT NULL CHECK (mass_multiplier_kg > 0)
);

CREATE TABLE rule_species_trait (
    species_trait_rule_id bigint PRIMARY KEY REFERENCES rule_rule(rule_id),
    trait_code text NOT NULL UNIQUE CHECK (
        trait_code ~ '^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$'
    ),
    source_effect_text text NOT NULL CHECK (btrim(source_effect_text) <> ''),
    opposite_trait_code text REFERENCES rule_species_trait(trait_code)
);

CREATE TABLE rule_species_trait_assignment (
    species_rule_id bigint NOT NULL REFERENCES rule_species(species_rule_id),
    species_trait_rule_id bigint NOT NULL REFERENCES
        rule_species_trait(species_trait_rule_id),
    assignment_order smallint NOT NULL CHECK (assignment_order > 0),
    movement_metres numeric(6,2),
    natural_weapon_form text,
    source_qualifier text,
    PRIMARY KEY (species_rule_id,species_trait_rule_id),
    UNIQUE (species_rule_id,assignment_order),
    CHECK (movement_metres IS NULL OR movement_metres > 0),
    CHECK (
        natural_weapon_form IS NULL OR btrim(natural_weapon_form) <> ''
    )
);

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT package.content_package_id,'species.' || value.code,value.name,
       'species','approved',value.description
FROM sys_content_package package
CROSS JOIN (VALUES
    ('human','Human','The standard species with no special species abilities.'),
    ('avian','Avian','Small winged sophonts descended from flying hunters.'),
    ('esper','Esper','Human or near-human sophonts with commonplace psionics.'),
    ('insectan','Insectan','Community-oriented insectoid sophonts.'),
    ('merfolk','Merfolk','Waterworld-adapted descendants of human stock.'),
    ('reptilian','Reptilian','Territorial saurian sophonts descended from chasers.')
) AS value(code,name,description)
WHERE package.package_code='cepheus-engine';

INSERT INTO rule_species (
    species_rule_id,species_code,display_order,maturity_age_years,
    aging_start_age_years,replaces_social_standing,
    social_characteristic_name,source_mechanics_text
)
SELECT rule.rule_id,value.code,value.ord,value.maturity,value.aging,
       value.replaces_soc,value.social_name,value.mechanics
FROM rule_rule rule
JOIN (VALUES
    ('human',1,18,34,false,NULL::text,
     'Standard human characteristic generation and no special traits.'),
    ('avian',2,22,46,false,NULL::text,
     'Weak Strength and Endurance; Notable Dexterity; winged and small.'),
    ('esper',3,18,34,false,NULL::text,
     'Standard human rules plus the Psionic trait.'),
    ('insectan',4,18,34,true,'Caste',
     'Notable Dexterity; Caste replaces Social Standing.'),
    ('merfolk',5,18,34,false,NULL::text,
     'Amphibious, aquatic, naturally swimming, and water dependent.'),
    ('reptilian',6,22,42,false,NULL::text,
     'Notable Strength and Dexterity; Weak Endurance.')
) AS value(code,ord,maturity,aging,replaces_soc,social_name,mechanics)
  ON rule.rule_code='species.' || value.code;

INSERT INTO rule_species_characteristic_generation (
    species_rule_id,characteristic_rule_id,dice_count,die_sides,
    roll_modifier,racial_maximum_modifier,source_trait_kind
)
SELECT species.species_rule_id,characteristic.rule_id,
       value.dice_count,6,value.modifier,value.maximum_modifier,value.kind
FROM rule_species species
JOIN (VALUES
    ('avian','characteristic.strength',1,0,-2,'weak'),
    ('avian','characteristic.dexterity',3,0,2,'notable'),
    ('avian','characteristic.endurance',1,0,-2,'weak'),
    ('insectan','characteristic.dexterity',2,2,2,'notable'),
    ('reptilian','characteristic.strength',2,1,1,'notable'),
    ('reptilian','characteristic.dexterity',2,1,1,'notable'),
    ('reptilian','characteristic.endurance',2,-2,-2,'weak')
) AS value(species_code,characteristic_code,dice_count,modifier,
           maximum_modifier,kind)
  ON species.species_code=value.species_code
JOIN rule_rule characteristic
  ON characteristic.rule_code=value.characteristic_code;

INSERT INTO rule_species_physical_generation VALUES
    ((SELECT species_rule_id FROM rule_species WHERE species_code='avian'),
     105,2,6,2,20,2,6,2),
    ((SELECT species_rule_id FROM rule_species WHERE species_code='insectan'),
     160,2,6,5,60,2,6,5),
    ((SELECT species_rule_id FROM rule_species WHERE species_code='reptilian'),
     155,2,6,5,50,2,6,5);

INSERT INTO rule_rule (
    content_package_id,rule_code,name,rule_category,rule_status,description
)
SELECT package.content_package_id,'species-trait.' || value.code,value.name,
       'species_trait','approved',value.effect
FROM sys_content_package package
CROSS JOIN (VALUES
    ('amphibious','Amphibious','Breathes underwater; Dexterity is halved on land.'),
    ('anti-psionic','Anti-Psionic','Psionic Strength is zero; cannot train in or suffer mental psionics.'),
    ('aquatic','Aquatic','Adapted to underwater life and requires aid when unable to operate out of water.'),
    ('armored','Armored','Natural protection provides one point of armor.'),
    ('atmospheric-requirements','Atmospheric Requirements','Requires unusual breathing gases and artificial aid in most atmospheres.'),
    ('bad-first-impression','Bad First Impression','Other species begin Unfriendly until interaction overcomes the response.'),
    ('caste','Caste','Social DMs involving Social Standing or Charisma are halved.'),
    ('cold-blooded','Cold-Blooded','Extreme cold gives initiative DM-2 and causes 1D6 damage per ten minutes.'),
    ('engineered','Engineered','Lower-TL medical treatment suffers DM equal to the TL difference.'),
    ('fast-metabolism','Fast Metabolism','Double life support, initiative +2, and halve Endurance for fatigue.'),
    ('feral','Feral','Education is generated with 1D6.'),
    ('fast-speed','Fast Speed','Uses the species-defined fast movement speed.'),
    ('flyer','Flyer','Grants Athletics 0 and winged flight at the defined speed.'),
    ('great-leaper','Great Leaper','Athletics check jumps four squares plus Effect; grants Athletics 0.'),
    ('heat-endurance','Heat Endurance','Ignores hourly damage from hot weather and exposure.'),
    ('heavy-gravity-adaptation','Heavy Gravity Adaptation','Does not acclimatize to high-gravity environments.'),
    ('hive-mentality','Hive Mentality','Intelligence check resists risking safety for the family group.'),
    ('large','Large','Doubled life support; Huge members grant attackers DM+1.'),
    ('low-gravity-adaptation','Low Gravity Adaptation','Does not acclimatize to low-gravity environments.'),
    ('low-light-vision','Low-Light Vision','Sees twice human distance in poor illumination with color and detail.'),
    ('natural-pilot','Natural Pilot','Piloting and Navigation checks receive DM+2.'),
    ('natural-swimmer','Natural Swimmer','Swimming-related checks receive DM+2.'),
    ('natural-weapon','Natural Weapon','Personal natural weapon deals +1 damage and grants Natural Weapons 0.'),
    ('naturally-curious','Naturally Curious','Intelligence check resists acting on mysterious impulses.'),
    ('no-fine-manipulators','No Fine Manipulators','Cannot easily perform tasks requiring fingers or prehensile appendages.'),
    ('notable-characteristic','Notable Characteristic','Positive generation modifier also raises the racial maximum.'),
    ('psionic','Psionic','May determine Psionic Strength and talents at character-generation start.'),
    ('small','Small','Typically weak Strength and Endurance with high Dexterity.'),
    ('slow-metabolism','Slow Metabolism','Half life support and initiative DM-2.'),
    ('slow-speed','Slow Speed','Uses the species-defined slow movement speed.'),
    ('uplifted','Uplifted','Raised from non-sentience and commonly a patron client species.'),
    ('water-dependent','Water Dependent','Survives out of water one hour per two Endurance.'),
    ('weak-characteristic','Weak Characteristic','Negative generation modifier also lowers the racial maximum.')
) AS value(code,name,effect)
WHERE package.package_code='cepheus-engine';

INSERT INTO rule_species_trait (
    species_trait_rule_id,trait_code,source_effect_text
)
SELECT rule_id,replace(rule_code,'species-trait.',''),description
FROM rule_rule WHERE rule_code LIKE 'species-trait.%';

UPDATE rule_species_trait weak
SET opposite_trait_code='notable-characteristic'
WHERE weak.trait_code='weak-characteristic';
UPDATE rule_species_trait notable
SET opposite_trait_code='weak-characteristic'
WHERE notable.trait_code='notable-characteristic';
UPDATE rule_species_trait anti
SET opposite_trait_code='psionic'
WHERE anti.trait_code='anti-psionic';
UPDATE rule_species_trait psi
SET opposite_trait_code='anti-psionic'
WHERE psi.trait_code='psionic';
UPDATE rule_species_trait fast
SET opposite_trait_code='slow-metabolism'
WHERE fast.trait_code='fast-metabolism';
UPDATE rule_species_trait slow
SET opposite_trait_code='fast-metabolism'
WHERE slow.trait_code='slow-metabolism';
UPDATE rule_species_trait fast
SET opposite_trait_code='slow-speed'
WHERE fast.trait_code='fast-speed';
UPDATE rule_species_trait slow
SET opposite_trait_code='fast-speed'
WHERE slow.trait_code='slow-speed';

INSERT INTO rule_species_trait_assignment (
    species_rule_id,species_trait_rule_id,assignment_order,
    movement_metres,natural_weapon_form,source_qualifier
)
SELECT species.species_rule_id,trait.species_trait_rule_id,value.ord,
       value.speed,value.weapon,value.qualifier
FROM (VALUES
    ('avian','flyer',1,9.0,NULL::text,NULL::text),
    ('avian','low-gravity-adaptation',2,NULL,NULL,NULL),
    ('avian','natural-pilot',3,NULL,NULL,NULL),
    ('avian','slow-speed',4,4.5,NULL,NULL),
    ('avian','small',5,NULL,NULL,NULL),
    ('esper','psionic',1,NULL,NULL,NULL),
    ('insectan','armored',1,NULL,NULL,NULL),
    ('insectan','bad-first-impression',2,NULL,NULL,NULL),
    ('insectan','caste',3,NULL,NULL,NULL),
    ('insectan','cold-blooded',4,NULL,NULL,NULL),
    ('insectan','fast-speed',5,9.0,NULL,NULL),
    ('insectan','great-leaper',6,NULL,NULL,NULL),
    ('insectan','hive-mentality',7,NULL,NULL,NULL),
    ('merfolk','amphibious',1,NULL,NULL,NULL),
    ('merfolk','aquatic',2,NULL,NULL,NULL),
    ('merfolk','natural-swimmer',3,NULL,NULL,NULL),
    ('merfolk','water-dependent',4,NULL,NULL,NULL),
    ('reptilian','anti-psionic',1,NULL,NULL,NULL),
    ('reptilian','fast-speed',2,9.0,NULL,NULL),
    ('reptilian','heat-endurance',3,NULL,NULL,NULL),
    ('reptilian','low-light-vision',4,NULL,NULL,NULL),
    ('reptilian','natural-weapon',5,NULL,'teeth',NULL),
    ('reptilian','low-gravity-adaptation',6,NULL,NULL,NULL)
) AS value(species_code,trait_code,ord,speed,weapon,qualifier)
JOIN rule_species species ON species.species_code=value.species_code
JOIN rule_species_trait trait ON trait.trait_code=value.trait_code;
