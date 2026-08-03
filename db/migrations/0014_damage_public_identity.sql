ALTER TABLE health_damage_instance
    ADD COLUMN public_id uuid NOT NULL DEFAULT gen_random_uuid() UNIQUE;
