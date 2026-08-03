ALTER TABLE cmd_random_draw DROP CONSTRAINT cmd_random_draw_draw_group_check;
ALTER TABLE cmd_random_draw ADD CONSTRAINT cmd_random_draw_draw_group_check CHECK (
    draw_group IN (
        'attack','damage','task','occurrence','encounter_type','initiative',
        'psionic_activation','psionic_timing','career_qualification',
        'career_draft','career_survival','career_mishap','career_injury',
        'career_injury_reduction','career_injury_crisis_cost',
        'career_commission','career_advancement','career_training',
        'career_aging','career_reenlistment','career_benefit',
        'career_benefit_ship_shares','career_aging_crisis_cost',
        'career_medical_employer','career_anagathic_cost',
        'career_anagathic_survival','environment_damage',
        'blind_target','explosion_damage','explosion_dodge',
        'combat_scatter','combat_nearest_tie',
        'grapple_challenger','grapple_opponent','grapple_throw_damage',
        'thrown_scatter_direction','telekinetic_attack',
        'telekinetic_damage','psionic_assault_defense',
        'psionic_assault_damage'
    )
);
