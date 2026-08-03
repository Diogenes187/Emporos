UPDATE rule_ship_bridge_band
SET minimum_hull_tons=300
WHERE bridge_band_code='300-to-1000';

UPDATE rule_ship_bridge_band
SET minimum_hull_tons=1100
WHERE bridge_band_code='1100-to-2000';
