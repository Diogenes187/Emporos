import os
import unittest
import uuid

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class WorldGenerationCompletionTests(unittest.TestCase):
    def _location_type(self, connection, package, code):
        rule = connection.execute(
            """INSERT INTO rule_rule(content_package_id,rule_code,name,rule_category,rule_status)
               VALUES(%s,%s,%s,'world','approved') RETURNING rule_id""",
            (package, f"location.test-{code}-{uuid.uuid4().hex}", code),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO rule_location_type VALUES(%s,%s,true,true)",
            (rule, f"test-{code}-{uuid.uuid4().hex}"),
        )
        return rule

    def _context(self, connection):
        campaign = connection.execute(
            "INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id",
            (f"Generated World {uuid.uuid4().hex}",),
        ).fetchone()[0]
        package = connection.execute(
            "SELECT content_package_id FROM sys_content_package WHERE package_code='cepheus-engine'"
        ).fetchone()[0]
        kinds = {name: self._location_type(connection, package, name) for name in ("sector", "subsector", "system", "world")}
        locations = {
            name: connection.execute(
                "INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,%s) RETURNING location_id",
                (campaign, kinds[name], name),
            ).fetchone()[0]
            for name in kinds
        }
        connection.execute("INSERT INTO loc_sector VALUES(%s,%s,0,0)", (locations["sector"], campaign))
        connection.execute(
            "INSERT INTO loc_subsector VALUES(%s,%s,%s,2,3)",
            (locations["subsector"], campaign, locations["sector"]),
        )
        connection.execute(
            """INSERT INTO loc_star_system(location_id,campaign_id,sector_location_id,subsector_location_id,hex_column,hex_row)
               VALUES(%s,%s,%s,%s,9,21)""",
            (locations["system"], campaign, locations["sector"], locations["subsector"]),
        )
        connection.execute(
            "INSERT INTO loc_celestial_body(location_id,campaign_id,system_location_id,body_kind,orbit_order) VALUES(%s,%s,%s,'planet',1)",
            (locations["world"], campaign, locations["system"]),
        )
        return campaign, locations

    def test_world_rolls_system_details_and_trade_codes_are_audited(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, locations = self._context(connection)
                connection.execute(
                    """INSERT INTO loc_hex_generation_receipt(campaign_id,subsector_location_id,hex_column,hex_row,
                               density_code,presence_roll,density_modifier,adjusted_total,system_present,system_location_id)
                       VALUES(%s,%s,1,1,'standard',4,0,4,true,%s)""",
                    (campaign, locations["subsector"], locations["system"]),
                )
                profile = connection.execute(
                    """INSERT INTO loc_world_profile(location_id,campaign_id,revision_number,starport_code,size_code,
                               atmosphere_code,hydrographics_code,population_code,government_code,law_level_code,technology_level)
                       VALUES(%s,%s,1,'D',7,7,7,5,5,5,6) RETURNING world_profile_id""",
                    (locations["world"], campaign),
                ).fetchone()[0]
                generation = connection.execute(
                    """INSERT INTO loc_world_generation_receipt(campaign_id,world_profile_id,size_roll,atmosphere_roll,
                               hydrographics_roll,hydrographics_modifier,population_roll,population_modifier,starport_roll,
                               government_roll,law_level_roll,technology_roll,technology_modifier,technology_minimum)
                       VALUES(%s,%s,9,7,7,0,7,0,8,7,7,4,2,5) RETURNING world_generation_receipt_id""",
                    (campaign, profile),
                ).fetchone()[0]
                codes = connection.execute(
                    "SELECT trade_code_rule_id FROM loc_trade_code WHERE trade_code IN('Ag','Ni')"
                ).fetchall()
                for (trade_code_rule_id,) in codes:
                    connection.execute(
                        "INSERT INTO loc_world_trade_code(world_profile_id,trade_code_rule_id) VALUES(%s,%s)",
                        (profile, trade_code_rule_id),
                    )
                connection.execute(
                    "INSERT INTO loc_world_generation_final_receipt(world_generation_receipt_id,world_profile_id,assigned_trade_code_count) VALUES(%s,%s,2)",
                    (generation, profile),
                )
                detail = connection.execute(
                    """INSERT INTO loc_world_system_detail_receipt(campaign_id,world_profile_id,system_location_id,
                               population_multiplier_roll,population_multiplier,exact_population,belt_presence_roll,
                               belt_count_roll,planetoid_belt_count,gas_presence_roll,gas_count_roll,gas_giant_count,
                               naval_base_roll,naval_base_present,scout_base_roll,scout_base_present,pirate_base_roll,
                               pirate_base_present,base_code,amber_zone_candidate)
                       VALUES(%s,%s,%s,8,6,600000,3,NULL,0,5,6,4,NULL,false,7,true,11,false,'S',false)
                       RETURNING world_system_detail_receipt_id""",
                    (campaign, profile, locations["system"]),
                ).fetchone()[0]
                initial_zone = connection.execute(
                    """INSERT INTO loc_world_travel_zone_event(campaign_id,world_profile_id,zone_version,zone_code,
                               classification_basis,amber_candidate_snapshot)
                       VALUES(%s,%s,1,'clear','generated-candidate',false) RETURNING world_travel_zone_event_id""",
                    (campaign, profile),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO loc_world_generation_completion_receipt(world_generation_receipt_id,world_profile_id,
                               world_system_detail_receipt_id,initial_travel_zone_event_id)
                       VALUES(%s,%s,%s,%s)""",
                    (generation, profile, detail, initial_zone),
                )
                connection.execute(
                    """INSERT INTO loc_world_travel_zone_event(campaign_id,world_profile_id,zone_version,zone_code,
                               classification_basis,amber_candidate_snapshot)
                       VALUES(%s,%s,2,'red','referee-assigned',false)""",
                    (campaign, profile),
                )
                summary = connection.execute(
                    "SELECT exact_population,gas_giant_count,base_code,current_travel_zone,travel_zone_version FROM loc_generated_world_summary WHERE world_profile_id=%s",
                    (profile,),
                ).fetchone()
                self.assertEqual(summary, (600000, 4, "S", "red", 2))
                with self.assertRaisesRegex(psycopg.Error, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE loc_world_system_detail_receipt SET gas_giant_count=3 WHERE world_system_detail_receipt_id=%s",
                            (detail,),
                        )
                with self.assertRaisesRegex(psycopg.Error, "immutable"):
                    with connection.transaction():
                        connection.execute(
                            "UPDATE loc_world_profile SET technology_level=7 WHERE world_profile_id=%s",
                            (profile,),
                        )

    def test_absent_hex_cannot_hide_an_existing_system(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, locations = self._context(connection)
                with self.assertRaisesRegex(psycopg.Error, "conflicts with an existing system"):
                    connection.execute(
                        """INSERT INTO loc_hex_generation_receipt(campaign_id,subsector_location_id,hex_column,hex_row,
                                   density_code,presence_roll,density_modifier,adjusted_total,system_present,system_location_id)
                           VALUES(%s,%s,1,1,'standard',3,0,3,false,NULL)""",
                        (campaign, locations["subsector"]),
                    )

    def test_unpopulated_size_zero_world_forces_zero_profile_and_one_belt(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                campaign, locations = self._context(connection)
                profile = connection.execute(
                    """INSERT INTO loc_world_profile(location_id,campaign_id,revision_number,starport_code,size_code,
                               atmosphere_code,hydrographics_code,population_code,government_code,law_level_code,technology_level)
                       VALUES(%s,%s,1,'D',0,0,0,0,0,0,0) RETURNING world_profile_id""",
                    (locations["world"], campaign),
                ).fetchone()[0]
                generation = connection.execute(
                    """INSERT INTO loc_world_generation_receipt(campaign_id,world_profile_id,size_roll,atmosphere_roll,
                               hydrographics_roll,hydrographics_modifier,population_roll,population_modifier,starport_roll,
                               government_roll,law_level_roll,technology_roll,technology_modifier,technology_minimum)
                       VALUES(%s,%s,2,12,12,-4,2,-3,12,12,12,6,5,7) RETURNING world_generation_receipt_id""",
                    (campaign, profile),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO loc_world_trade_code(world_profile_id,trade_code_rule_id)
                       SELECT %s,trade_code_rule_id FROM loc_trade_code
                       WHERE loc_world_profile_qualifies_for_trade_code(%s,trade_code_rule_id)""",
                    (profile, profile),
                )
                code_count = connection.execute(
                    "SELECT count(*) FROM loc_world_trade_code WHERE world_profile_id=%s", (profile,)
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO loc_world_generation_final_receipt(world_generation_receipt_id,world_profile_id,assigned_trade_code_count) VALUES(%s,%s,%s)",
                    (generation, profile, code_count),
                )
                detail = connection.execute(
                    """INSERT INTO loc_world_system_detail_receipt(campaign_id,world_profile_id,system_location_id,
                               population_multiplier_roll,population_multiplier,exact_population,belt_presence_roll,
                               belt_count_roll,planetoid_belt_count,gas_presence_roll,gas_count_roll,gas_giant_count,
                               naval_base_roll,naval_base_present,scout_base_roll,scout_base_present,pirate_base_roll,
                               pirate_base_present,base_code,amber_zone_candidate)
                       VALUES(%s,%s,%s,12,0,0,2,NULL,1,2,NULL,0,NULL,false,6,false,12,true,'P',true)
                       RETURNING world_system_detail_receipt_id""",
                    (campaign, profile, locations["system"]),
                ).fetchone()[0]
                zone = connection.execute(
                    """INSERT INTO loc_world_travel_zone_event(campaign_id,world_profile_id,zone_version,zone_code,
                               classification_basis,amber_candidate_snapshot)
                       VALUES(%s,%s,1,'amber','generated-candidate',true) RETURNING world_travel_zone_event_id""",
                    (campaign, profile),
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO loc_world_generation_completion_receipt(world_generation_receipt_id,world_profile_id,
                               world_system_detail_receipt_id,initial_travel_zone_event_id) VALUES(%s,%s,%s,%s)""",
                    (generation, profile, detail, zone),
                )
                self.assertEqual(code_count, 4)
