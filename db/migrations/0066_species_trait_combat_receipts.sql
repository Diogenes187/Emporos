ALTER TABLE cmd_attack_receipt
    ADD COLUMN natural_armor_rating integer NOT NULL DEFAULT 0 CHECK (
        natural_armor_rating >= 0
    ),
    ADD CONSTRAINT cmd_attack_natural_armor_subset_check CHECK (
        natural_armor_rating <= armor_rating
    );
