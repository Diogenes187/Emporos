UPDATE ship_component_definition
SET unit_tons=4,
    unit_cost_minor=500000,
    tonnage_basis='fixed',
    tonnage_factor=1,
    cost_basis='fixed',
    effect_code='tactics-dm-plus-1',
    calculation_status='published'
WHERE component_code='briefing-room';

