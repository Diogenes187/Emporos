"""Verify the live Base Cepheus PostgreSQL foundation."""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.errors import ExclusionViolation


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engine.orchestration import available_tools
from tools.generate_source_coverage_report import build_report
MIGRATIONS = ROOT / "db" / "migrations"
VERSION = re.compile(r"^(?P<version>\d{4})_")
LONG_TEXT_LIMIT = 80
NARRATIVE_TEXT_MARKERS = (
    "description", "summary", "rationale", "notes", "message",
    "citation", "evidence", "question", "statement", "reason",
    "explanation", "text", "uri", "path", "value", "basis",
    "obligations", "scope",
)


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expected_checksums() -> dict[int, str]:
    checksums: dict[int, str] = {}
    for path in sorted(MIGRATIONS.glob("*.sql")):
        match = VERSION.match(path.name)
        if match is None:
            raise AssertionError(f"Invalid migration filename: {path.name}")
        checksums[int(match.group("version"))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return checksums


def mechanical_long_text_columns(
    connection: psycopg.Connection,
) -> list[tuple[str, str, int, int]]:
    findings: list[tuple[str, str, int, int]] = []
    columns = connection.execute(
        """SELECT field.table_name,field.column_name
           FROM information_schema.columns field
           JOIN information_schema.tables relation
             ON relation.table_schema=field.table_schema
            AND relation.table_name=field.table_name
           WHERE field.table_schema='public'
             AND relation.table_type='BASE TABLE'
             AND field.data_type IN (
                 'text','character varying','character'
             )
           ORDER BY field.table_name,field.ordinal_position"""
    ).fetchall()
    for table_name, column_name in columns:
        if any(
            marker in column_name.lower()
            for marker in NARRATIVE_TEXT_MARKERS
        ):
            continue
        count, maximum = connection.execute(
            sql.SQL(
                """SELECT count(*) FILTER (
                              WHERE length({column})>{limit}
                                AND {column} ~ '[[:space:]]'
                          ),
                          coalesce(max(length({column})),0)
                   FROM {table}"""
            ).format(
                column=sql.Identifier(column_name),
                table=sql.Identifier(table_name),
                limit=sql.Literal(LONG_TEXT_LIMIT),
            )
        ).fetchone()
        if count:
            findings.append(
                (table_name, column_name, count, maximum)
            )
    return findings


def main() -> int:
    orchestration_tools = available_tools()
    expect(len(orchestration_tools) == 30, "AI gameplay tool count changed.")
    expect(
        len({tool.name for tool in orchestration_tools}) == 30,
        "AI gameplay tool names are not unique.",
    )
    forbidden = {
        "c", "connection", "initiator_reference", "referee_reference",
        "random_source",
    }
    expect(
        all(
            forbidden.isdisjoint(
                tool.required_arguments + tool.optional_arguments
            )
            for tool in orchestration_tools
        ),
        "AI gameplay tools expose host-controlled arguments.",
    )
    dsn = os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        print("BASE_CEPHEUS_DATABASE_URL is required.", file=sys.stderr)
        return 2

    with psycopg.connect(dsn) as connection:
        long_text_findings = mechanical_long_text_columns(connection)
        expect(
            long_text_findings == [],
            "Long prose appears in mechanical text columns: "
            f"{long_text_findings}",
        )
        recorded = dict(
            connection.execute(
                "SELECT version, checksum_sha256 FROM sys_schema_migration"
            ).fetchall()
        )
        expect(recorded == expected_checksums(), "Migration checksums do not match.")

        package = connection.execute(
            """
            SELECT package_code, package_version, lifecycle_status
            FROM sys_content_package
            WHERE package_code = 'cepheus-engine'
            """
        ).fetchone()
        expect(
            package == ("cepheus-engine", "9.1-draft", "draft"),
            "Cepheus Engine draft package is missing or altered.",
        )

        paired = connection.execute(
            """
            SELECT left_work.work_code, right_work.work_code, relation_type
            FROM src_work_relation relation
            JOIN src_work left_work
              ON left_work.source_work_id = relation.left_work_id
            JOIN src_work right_work
              ON right_work.source_work_id = relation.right_work_id
            WHERE relation.relation_type = 'paired_publication'
            """
        ).fetchall()
        expect(
            paired
            == [
                (
                    "cepheus-engine.github-v9.1",
                    "cepheus-engine.ogn",
                    "paired_publication",
                )
            ],
            "Paired GitHub/OGN governing-source decision is missing.",
        )

        json_columns = connection.execute(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND data_type IN ('json', 'jsonb')
            ORDER BY table_name, column_name
            """
        ).fetchall()
        expect(
            json_columns == [("src_import_candidate", "staging_value")],
            f"Unexpected JSON authority columns: {json_columns}",
        )

        catalogue_counts = dict(
            connection.execute(
                """
                SELECT 'rules', count(*) FROM rule_rule
                UNION ALL
                SELECT 'characteristics', count(*) FROM rule_characteristic
                UNION ALL
                SELECT 'modifier_bands', count(*)
                  FROM rule_characteristic_modifier_band
                UNION ALL
                SELECT 'skills', count(*) FROM rule_skill
                UNION ALL
                SELECT 'cascade_skills', count(*)
                  FROM rule_skill WHERE cascade_skill
                UNION ALL
                SELECT 'specialty_links', count(*)
                  FROM rule_skill_specialty
                UNION ALL
                SELECT 'check_systems', count(*) FROM rule_check_system
                UNION ALL
                SELECT 'difficulties', count(*) FROM rule_difficulty
                UNION ALL
                SELECT 'effect_bands', count(*) FROM rule_effect_band
                UNION ALL
                SELECT 'time_frames', count(*) FROM rule_time_frame
                UNION ALL
                SELECT 'task_adjustments', count(*) FROM rule_task_adjustment
                UNION ALL
                SELECT 'law_mappings', count(*) FROM rule_law_level_difficulty
                UNION ALL
                SELECT 'general_task_context_runtime_columns',count(*)
                  FROM information_schema.columns
                 WHERE table_schema='public' AND table_name='cmd_actor_task_receipt'
                   AND column_name IN ('law_level','base_time_frame_rule_id',
                     'time_frame_steps','resolved_time_frame_rule_id',
                     'task_time_roll','task_time_quantity','task_time_unit',
                     'pace_modifier','simultaneous_action_count',
                     'simultaneous_action_modifier')
                UNION ALL
                SELECT 'characteristic_only_task_skill_nullable',count(*)
                  FROM information_schema.columns
                 WHERE table_schema='public' AND table_name='cmd_actor_task_receipt'
                   AND column_name='skill_rule_id' AND is_nullable='YES'
                UNION ALL
                SELECT 'bribery_offense_rules',count(*) FROM rule_bribery_offense
                UNION ALL
                SELECT 'bribery_offense_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code LIKE 'skill.bribery.offense.%'
                UNION ALL
                SELECT 'bribery_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_bribery_case','cmd_bribery_attempt_receipt','cmd_bribery_consequence_receipt')
                UNION ALL
                SELECT 'gambling_house_rules',count(*) FROM rule_gambling_house_odds
                UNION ALL
                SELECT 'gambling_house_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code LIKE 'skill.gambling.house.%'
                UNION ALL
                SELECT 'gambling_house_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_house_gambling_receipt'
                UNION ALL
                SELECT 'competitive_gambling_rules',count(*) FROM rule_competitive_gambling
                UNION ALL
                SELECT 'competitive_gambling_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.gambling.competitive'
                UNION ALL
                SELECT 'competitive_gambling_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_competitive_gambling_game','cmd_competitive_gambling_receipt','cmd_competitive_gambling_participant')
                UNION ALL
                SELECT 'leadership_coordination_rules',count(*) FROM rule_leadership_coordination
                UNION ALL
                SELECT 'leadership_coordination_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.leadership.coordinating-effort'
                UNION ALL
                SELECT 'leadership_coordination_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_leadership_coordination','cmd_leadership_coordination_receipt','camp_leadership_coordination_allocation','cmd_leadership_coordination_allocation_receipt')
                UNION ALL
                SELECT 'leadership_task_columns',count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='cmd_actor_task_receipt' AND column_name IN ('leadership_allocation_id','leadership_modifier')
                UNION ALL
                SELECT 'jack_of_all_trades_rules',count(*) FROM rule_jack_of_all_trades
                UNION ALL
                SELECT 'jack_of_all_trades_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.jack-of-all-trades.mechanics'
                UNION ALL
                SELECT 'jack_of_all_trades_task_columns',count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='cmd_actor_task_receipt' AND column_name IN ('base_skill_modifier','jack_of_all_trades_level','jack_of_all_trades_reduction')
                UNION ALL
                SELECT 'liaison_negotiation_rules',count(*) FROM rule_liaison_negotiation
                UNION ALL
                SELECT 'liaison_negotiation_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.liaison.negotiation'
                UNION ALL
                SELECT 'liaison_negotiation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_liaison_negotiation','cmd_liaison_negotiation_receipt','cmd_liaison_negotiation_participant')
                UNION ALL
                SELECT 'computer_basic_use_rules',count(*) FROM rule_computer_basic_use
                UNION ALL
                SELECT 'computer_basic_operations',count(*) FROM rule_computer_basic_operation
                UNION ALL
                SELECT 'computer_basic_use_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.computer.basic-operations'
                UNION ALL
                SELECT 'computer_basic_operation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_computer_basic_operation_receipt'
                UNION ALL
                SELECT 'trade_work_policies',count(*) FROM rule_trade_work_policy
                UNION ALL
                SELECT 'trade_work_skills',count(*) FROM rule_trade_work_skill
                UNION ALL
                SELECT 'trade_work_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.trade-work.weekly-pay'
                UNION ALL
                SELECT 'trade_work_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_trade_work_week','cmd_trade_work_start_receipt','cmd_trade_work_complete_receipt')
                UNION ALL
                SELECT 'linguistics_rules',count(*) FROM rule_linguistics_mechanic
                UNION ALL
                SELECT 'linguistics_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.linguistics.mechanics'
                UNION ALL
                SELECT 'linguistics_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_language','actor_language_proficiency','cmd_actor_language_receipt','cmd_linguistics_decipher_receipt')
                UNION ALL
                SELECT 'navigation_rules',count(*) FROM rule_navigation_mechanic
                UNION ALL
                SELECT 'navigation_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.navigation.mechanics'
                UNION ALL
                SELECT 'navigation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('journey_navigation_solution','cmd_navigation_receipt')
                UNION ALL
                SELECT 'recon_rules',count(*) FROM rule_recon_operation
                UNION ALL
                SELECT 'recon_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.recon.mechanics'
                UNION ALL
                SELECT 'recon_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_recon_receipt'
                UNION ALL
                SELECT 'streetwise_rules',count(*) FROM rule_streetwise_operation
                UNION ALL
                SELECT 'streetwise_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.streetwise.mechanics'
                UNION ALL
                SELECT 'streetwise_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_streetwise_receipt'
                UNION ALL
                SELECT 'regulatory_rules',count(*) FROM rule_regulatory_operation
                UNION ALL
                SELECT 'regulatory_skill_links',count(*) FROM rule_regulatory_operation_skill
                UNION ALL
                SELECT 'regulatory_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.admin-advocate.mechanics'
                UNION ALL
                SELECT 'regulatory_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_regulatory_task_receipt'
                UNION ALL
                SELECT 'steward_services',count(*) FROM rule_steward_service
                UNION ALL
                SELECT 'steward_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.steward.mechanics'
                UNION ALL
                SELECT 'steward_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_steward_service_receipt'
                UNION ALL
                SELECT 'survival_operations',count(*) FROM rule_survival_operation
                UNION ALL
                SELECT 'survival_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.survival.mechanics'
                UNION ALL
                SELECT 'survival_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_survival_task_receipt'
                UNION ALL
                SELECT 'transport_capabilities',count(*) FROM rule_transport_skill_capability
                UNION ALL
                SELECT 'transport_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.transport.operations'
                UNION ALL
                SELECT 'transport_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_transport_operation_receipt'
                UNION ALL
                SELECT 'device_operations',count(*) FROM rule_device_operation
                UNION ALL
                SELECT 'device_operation_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.device.operations'
                UNION ALL
                SELECT 'device_operation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_device_operation_receipt'
                UNION ALL
                SELECT 'animal_skill_operations',count(*) FROM rule_animal_skill_operation
                UNION ALL
                SELECT 'animal_skill_operation_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.animal.operations'
                UNION ALL
                SELECT 'animal_skill_operation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_animal_skill_operation_receipt'
                UNION ALL
                SELECT 'broker_operations',count(*) FROM rule_broker_operation
                UNION ALL
                SELECT 'broker_operation_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.broker.operations'
                UNION ALL
                SELECT 'carousing_influence_rules',count(*) FROM rule_carousing_influence_mechanic
                UNION ALL
                SELECT 'carousing_influence_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.carousing.influence'
                UNION ALL
                SELECT 'broker_carousing_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('cmd_broker_operation_receipt','cmd_carousing_influence_receipt')
                UNION ALL
                SELECT 'spacecraft_journey_execution_rules',count(*) FROM rule_spacecraft_journey_execution
                UNION ALL
                SELECT 'spacecraft_journey_execution_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='travel.spacecraft.journey-execution'
                UNION ALL
                SELECT 'spacecraft_journey_execution_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('journey_leg_execution','cmd_spacecraft_leg_start_receipt','cmd_spacecraft_leg_complete_receipt')
                UNION ALL
                SELECT 'range_bands', count(*) FROM combat_range_band
                UNION ALL
                SELECT 'attack_profiles', count(*) FROM combat_attack_profile
                UNION ALL
                SELECT 'items', count(*) FROM inv_item_definition
                UNION ALL
                SELECT 'ammunition_variants', count(*)
                  FROM inv_ammunition_definition
                UNION ALL
                SELECT 'psionic_talents', count(*) FROM psi_talent
                UNION ALL
                SELECT 'psionic_powers', count(*) FROM psi_power
                UNION ALL
                SELECT 'psionic_range_bands', count(*) FROM psi_range_band
                UNION ALL
                SELECT 'careers', count(*) FROM rule_career
                UNION ALL
                SELECT 'career_assignments', count(*)
                  FROM rule_career_assignment
                UNION ALL
                SELECT 'career_systems', count(*) FROM rule_career_system
                UNION ALL
                SELECT 'career_draft_rows', count(*)
                  FROM rule_career_draft_roll
                UNION ALL
                SELECT 'species', count(*) FROM rule_species
                UNION ALL
                SELECT 'species_traits', count(*) FROM rule_species_trait
                UNION ALL
                SELECT 'species_trait_assignments', count(*)
                  FROM rule_species_trait_assignment
                UNION ALL
                SELECT 'species_characteristic_overrides', count(*)
                  FROM rule_species_characteristic_generation
                UNION ALL
                SELECT 'species_physical_formulas', count(*)
                  FROM rule_species_physical_generation
                UNION ALL
                SELECT 'species_skill_grants', count(*)
                  FROM rule_species_trait_skill_grant
                UNION ALL
                SELECT 'encounter_types', count(*) FROM rule_encounter_type
                UNION ALL
                SELECT 'attitudes', count(*) FROM rule_attitude
                UNION ALL
                SELECT 'animal_subtypes', count(*) FROM rule_animal_subtype
                UNION ALL
                SELECT 'animal_reactions', count(*)
                  FROM rule_animal_reaction_condition
                UNION ALL
                SELECT 'starship_categories', count(*)
                  FROM rule_starship_encounter_category
                UNION ALL
                SELECT 'world_sizes', count(*) FROM rule_world_size
                UNION ALL
                SELECT 'world_atmospheres', count(*)
                  FROM rule_world_atmosphere
                UNION ALL
                SELECT 'world_trade_codes', count(*) FROM loc_trade_code
                UNION ALL
                SELECT 'trade_goods', count(*) FROM rule_trade_good
                UNION ALL
                SELECT 'trade_good_modifiers', count(*)
                  FROM rule_trade_good_modifier
                UNION ALL
                SELECT 'ship_crew_positions', count(*)
                  FROM ship_crew_position_definition
                UNION ALL
                SELECT 'ship_operating_costs', count(*)
                  FROM rule_ship_operating_cost
                UNION ALL
                SELECT 'ship_hull_designs', count(*)
                  FROM rule_ship_hull_design
                UNION ALL
                SELECT 'ship_configurations', count(*)
                  FROM rule_ship_configuration
                UNION ALL
                SELECT 'ship_armor_designs', count(*)
                  FROM rule_ship_armor_design
                UNION ALL
                SELECT 'ship_armor_options', count(*)
                  FROM rule_ship_armor_option
                UNION ALL
                SELECT 'ship_bridge_bands', count(*)
                  FROM rule_ship_bridge_band
                UNION ALL
                SELECT 'ship_computers', count(*)
                  FROM rule_ship_computer
                UNION ALL
                SELECT 'ship_computer_options', count(*)
                  FROM rule_ship_computer_option
                UNION ALL
                SELECT 'ship_software', count(*)
                  FROM rule_ship_software
                UNION ALL
                SELECT 'ship_electronics', count(*)
                  FROM rule_ship_electronics_suite
                UNION ALL
                SELECT 'ship_drive_designs', count(*)
                  FROM rule_ship_drive_design
                UNION ALL
                SELECT 'ship_drive_performance', count(*)
                  FROM rule_ship_drive_performance
                UNION ALL
                SELECT 'ship_power_fuel_rows', count(*)
                  FROM rule_ship_power_plant_fuel
                UNION ALL
                SELECT 'ship_component_definitions', count(*)
                  FROM ship_component_definition
                UNION ALL
                SELECT 'ship_hangar_options', count(*)
                  FROM rule_ship_hangar_option
                UNION ALL
                SELECT 'ship_weapon_mounts', count(*)
                  FROM rule_ship_weapon_mount
                UNION ALL
                SELECT 'ship_weapon_definitions', count(*)
                  FROM ship_weapon_definition
                UNION ALL
                SELECT 'ship_missiles', count(*)
                  FROM rule_ship_missile
                UNION ALL
                SELECT 'ship_screens', count(*)
                  FROM rule_ship_screen
                UNION ALL
                SELECT 'ship_sand_ammunition', count(*)
                  FROM rule_ship_sand_ammunition
                UNION ALL
                SELECT 'standard_ship_classes', count(*)
                  FROM ship_class
                UNION ALL
                SELECT 'ship_class_drives', count(*)
                  FROM ship_class_drive
                UNION ALL
                SELECT 'ship_class_weapon_mount_groups', count(*)
                  FROM ship_class_weapon_mount
                UNION ALL
                SELECT 'ship_class_mount_weapon_slots', count(*)
                  FROM ship_class_mount_weapon
                UNION ALL
                SELECT 'ship_class_source_assertions', count(*)
                  FROM ship_class_source_assertion
                UNION ALL
                SELECT 'ship_published_drive_conflicts', count(*)
                  FROM ship_class_drive
                 WHERE validation_status='published_conflict'
                UNION ALL
                SELECT 'ship_class_components', count(*)
                  FROM ship_class_component
                UNION ALL
                SELECT 'ship_class_hangars', count(*)
                  FROM ship_class_hangar_option
                UNION ALL
                SELECT 'ship_class_carried_craft_rows', count(*)
                  FROM ship_class_carried_craft
                UNION ALL
                SELECT 'ship_class_carried_craft_count',
                       coalesce(sum(craft_count),0)
                  FROM ship_class_carried_craft
                UNION ALL
                SELECT 'ship_class_carried_items', count(*)
                  FROM ship_class_carried_item
                UNION ALL
                SELECT 'ship_armament_declarations', count(*)
                  FROM ship_class_armament_declaration
                UNION ALL
                SELECT 'ship_structurally_complete', count(*)
                  FROM ship_class_catalogue_completeness
                 WHERE is_structurally_complete
                UNION ALL
                SELECT 'ship_unresolved_source_assertions',
                       coalesce(sum(unresolved_source_assertions),0)
                  FROM ship_class_catalogue_completeness
                UNION ALL
                SELECT 'ship_construction_receipts', count(*)
                  FROM ship_class_construction_receipt
                UNION ALL
                SELECT 'ship_finalized_construction_receipts', count(*)
                  FROM ship_class_construction_receipt
                 WHERE finalized
                UNION ALL
                SELECT 'ship_construction_lines', count(*)
                  FROM ship_class_construction_line
                UNION ALL
                SELECT 'ship_reconciled_construction_receipts', count(*)
                  FROM ship_class_construction_total
                 WHERE reconciliation_status='reconciled'
                UNION ALL
                SELECT 'ship_source_gap_construction_receipts', count(*)
                  FROM ship_class_construction_total
                 WHERE reconciliation_status='source_gap'
                UNION ALL
                SELECT 'ship_tonnage_variance_receipts', count(*)
                  FROM ship_class_construction_total
                 WHERE reconciliation_status='tonnage_variance'
                UNION ALL
                SELECT 'ship_cost_variance_receipts', count(*)
                  FROM ship_class_construction_total
                 WHERE reconciliation_status='cost_variance'
                UNION ALL
                SELECT 'ship_current_construction_receipts', count(*)
                  FROM ship_class_construction_total
                UNION ALL
                SELECT 'ship_construction_variances', count(*)
                  FROM ship_class_construction_variance
                UNION ALL
                SELECT 'ship_armor_proration_conflicts', count(*)
                  FROM ship_class_construction_variance
                 WHERE explanation_code='capped-armor-proration'
                UNION ALL
                SELECT 'ship_effective_cost_adjudications',count(*)
                  FROM ship_class_effective_cost_adjudication
                UNION ALL
                SELECT 'open_source_issues', count(*)
                  FROM src_open_issue_report
                UNION ALL
                SELECT 'high_priority_source_issues', count(*)
                  FROM src_open_issue_report
                 WHERE review_priority='high'
                UNION ALL
                SELECT 'construction_variance_issues', count(*)
                  FROM src_issue_construction_variance
                UNION ALL
                SELECT 'ship_assertion_issues', count(*)
                  FROM src_issue_ship_assertion
                UNION ALL
                SELECT 'legacy_issue_comparisons', count(*)
                  FROM src_issue_comparison_check
                 WHERE check_status='no_independent_calculation'
                UNION ALL
                SELECT 'vehicle_component_definitions', count(*)
                  FROM vehicle_component_definition
                UNION ALL
                SELECT 'vehicle_electronics_ranges', count(*)
                  FROM rule_vehicle_electronics_range
                UNION ALL
                SELECT 'vehicle_control_systems', count(*)
                  FROM rule_vehicle_control_system
                UNION ALL
                SELECT 'vehicle_drone_controllers', count(*)
                  FROM rule_vehicle_drone_controller
                UNION ALL
                SELECT 'vehicle_robot_brains', count(*)
                  FROM rule_vehicle_robot_brain
                UNION ALL
                SELECT 'vehicle_autopilot_introductions', count(*)
                  FROM rule_vehicle_autopilot_introduction
                UNION ALL
                SELECT 'vehicle_communication_systems', count(*)
                  FROM rule_vehicle_communication_system
                UNION ALL
                SELECT 'vehicle_communicator_types', count(*)
                  FROM rule_vehicle_communicator_type
                UNION ALL
                SELECT 'vehicle_sensor_packages', count(*)
                  FROM rule_vehicle_sensor_package
                UNION ALL
                SELECT 'vehicle_sensor_capabilities', count(*)
                  FROM rule_vehicle_sensor_capability
                UNION ALL
                SELECT 'vehicle_sensor_capability_links', count(*)
                  FROM rule_vehicle_sensor_package_capability
                UNION ALL
                SELECT 'vehicle_computers', count(*)
                  FROM rule_vehicle_computer
                UNION ALL
                SELECT 'vehicle_computer_options', count(*)
                  FROM rule_vehicle_computer_option
                UNION ALL
                SELECT 'vehicle_accommodations', count(*)
                  FROM rule_vehicle_accommodation
                UNION ALL
                SELECT 'vehicle_life_support_systems', count(*)
                  FROM rule_vehicle_life_support
                UNION ALL
                SELECT 'vehicle_life_support_inclusions', count(*)
                  FROM rule_vehicle_life_support_inclusion
                UNION ALL
                SELECT 'vehicle_sailing_crew_formulas', count(*)
                  FROM rule_vehicle_sailing_crew_formula
                UNION ALL
                SELECT 'vehicle_component_formulas', count(*)
                  FROM rule_vehicle_component_formula
                UNION ALL
                SELECT 'vehicle_cargo_trailer_rules', count(*)
                  FROM rule_vehicle_cargo_trailer_rule
                UNION ALL
                SELECT 'vehicle_cargo_trailer_models', count(*)
                  FROM rule_vehicle_cargo_trailer_model
                UNION ALL
                SELECT 'vehicle_cranes', count(*)
                  FROM rule_vehicle_crane
                UNION ALL
                SELECT 'vehicle_galleys', count(*)
                  FROM rule_vehicle_galley
                UNION ALL
                SELECT 'vehicle_mobility_components', count(*)
                  FROM rule_vehicle_mobility_component
                UNION ALL
                SELECT 'vehicle_manipulator_arms', count(*)
                  FROM rule_vehicle_manipulator_arm
                UNION ALL
                SELECT 'vehicle_manipulator_limits', count(*)
                  FROM rule_vehicle_manipulator_limit
                UNION ALL
                SELECT 'vehicle_cargo_arms', count(*)
                  FROM rule_vehicle_cargo_arm
                UNION ALL
                SELECT 'vehicle_liquid_cannons', count(*)
                  FROM rule_vehicle_liquid_cannon
                UNION ALL
                SELECT 'vehicle_operating_theaters', count(*)
                  FROM rule_vehicle_operating_theater
                UNION ALL
                SELECT 'vehicle_refueling_rates', count(*)
                  FROM rule_vehicle_refueling_rate
                UNION ALL
                SELECT 'vehicle_sampler_bonuses', count(*)
                  FROM rule_vehicle_sampler_bonus
                UNION ALL
                SELECT 'vehicle_emergency_low_berths', count(*)
                  FROM rule_vehicle_emergency_low_berth
                UNION ALL
                SELECT 'vehicle_fire_extinguisher_regulations', count(*)
                  FROM rule_vehicle_fire_extinguisher_regulation
                UNION ALL
                SELECT 'vehicle_holding_tank_contents', count(*)
                  FROM rule_vehicle_holding_tank_content
                UNION ALL
                SELECT 'vehicle_research_lab_bonuses', count(*)
                  FROM rule_vehicle_research_lab_bonus
                UNION ALL
                SELECT 'vehicle_research_lab_disciplines', count(*)
                  FROM rule_vehicle_research_lab_discipline
                UNION ALL
                SELECT 'vehicle_liquid_cannon_purposes', count(*)
                  FROM rule_vehicle_liquid_cannon_purpose
                UNION ALL
                SELECT 'vehicle_configurations', count(*)
                  FROM rule_vehicle_configuration
                UNION ALL
                SELECT 'vehicle_configuration_cover_rows', count(*)
                  FROM rule_vehicle_configuration_cover
                UNION ALL
                SELECT 'vehicle_design_categories', count(*)
                  FROM rule_vehicle_design_category
                UNION ALL
                SELECT 'vehicle_propulsion_category_rows', count(*)
                  FROM rule_vehicle_propulsion_category
                UNION ALL
                SELECT 'vehicle_configuration_options', count(*)
                  FROM rule_vehicle_configuration_option
                UNION ALL
                SELECT 'vehicle_configuration_option_categories', count(*)
                  FROM rule_vehicle_configuration_option_category
                UNION ALL
                SELECT 'vehicle_configuration_price_combinations', count(*)
                  FROM rule_vehicle_configuration_price_combination
                UNION ALL
                SELECT 'vehicle_environmental_hazards', count(*)
                  FROM rule_vehicle_environmental_hazard
                UNION ALL
                SELECT 'vehicle_environmental_protections', count(*)
                  FROM rule_vehicle_environmental_protection
                UNION ALL
                SELECT 'vehicle_environmental_protection_hazards', count(*)
                  FROM rule_vehicle_environmental_protection_hazard
                UNION ALL
                SELECT 'vehicle_configuration_option_inclusions', count(*)
                  FROM rule_vehicle_configuration_option_inclusion
                UNION ALL
                SELECT 'vehicle_submersible_depth_rows', count(*)
                  FROM rule_vehicle_submersible_depth
                UNION ALL
                SELECT 'vehicle_submersible_world_adjustments', count(*)
                  FROM rule_vehicle_submersible_world_adjustment
                UNION ALL
                SELECT 'vehicle_submersible_depth_upgrades', count(*)
                  FROM rule_vehicle_submersible_depth_upgrade
                UNION ALL
                SELECT 'vehicle_drive_options', count(*)
                  FROM rule_vehicle_drive_option
                UNION ALL
                SELECT 'vehicle_drive_option_categories', count(*)
                  FROM rule_vehicle_drive_option_category
                UNION ALL
                SELECT 'vehicle_drive_adjustment_options', count(*)
                  FROM rule_vehicle_drive_adjustment_option
                UNION ALL
                SELECT 'vehicle_secondary_drive_options', count(*)
                  FROM rule_vehicle_secondary_drive_option
                UNION ALL
                SELECT 'vehicle_extra_contact_elements', count(*)
                  FROM rule_vehicle_extra_contact_element
                UNION ALL
                SELECT 'vehicle_jump_jet_options', count(*)
                  FROM rule_vehicle_jump_jet_option
                UNION ALL
                SELECT 'vehicle_off_road_options', count(*)
                  FROM rule_vehicle_off_road_option
                UNION ALL
                SELECT 'vehicle_tilt_rotor_jet_options', count(*)
                  FROM rule_vehicle_tilt_rotor_jet_option
                UNION ALL
                SELECT 'vehicle_weapon_point_formulas', count(*)
                  FROM rule_vehicle_weapon_point_formula
                UNION ALL
                SELECT 'vehicle_gun_ports', count(*)
                  FROM rule_vehicle_gun_port
                UNION ALL
                SELECT 'vehicle_gun_port_weapons', count(*)
                  FROM rule_vehicle_gun_port_weapon
                UNION ALL
                SELECT 'vehicle_weapon_mounts', count(*)
                  FROM rule_vehicle_weapon_mount
                UNION ALL
                SELECT 'vehicle_gun_shields', count(*)
                  FROM rule_vehicle_gun_shield
                UNION ALL
                SELECT 'vehicle_gun_shield_mounts', count(*)
                  FROM rule_vehicle_gun_shield_mount
                UNION ALL
                SELECT 'vehicle_turrets', count(*)
                  FROM rule_vehicle_turret
                UNION ALL
                SELECT 'vehicle_coaxial_mount_formulas', count(*)
                  FROM rule_vehicle_coaxial_mount
                UNION ALL
                SELECT 'vehicle_pop_up_turrets', count(*)
                  FROM rule_vehicle_pop_up_turret
                UNION ALL
                SELECT 'vehicle_armament_options', count(*)
                  FROM rule_vehicle_armament_option
                UNION ALL
                SELECT 'vehicle_armament_option_families', count(*)
                  FROM rule_vehicle_armament_option_weapon_family
                UNION ALL
                SELECT 'vehicle_armament_option_scopes', count(*)
                  FROM rule_vehicle_armament_option_scope
                UNION ALL
                SELECT 'vehicle_armament_option_incompatibilities', count(*)
                  FROM rule_vehicle_armament_option_incompatibility
                UNION ALL
                SELECT 'vehicle_weapon_target_ranges', count(*)
                  FROM rule_vehicle_weapon_target_range
                UNION ALL
                SELECT 'vehicle_weapon_range_profiles', count(*)
                  FROM rule_vehicle_weapon_range_profile
                UNION ALL
                SELECT 'vehicle_weapon_range_difficulties', count(*)
                  FROM rule_vehicle_weapon_range_difficulty
                UNION ALL
                SELECT 'vehicle_weapon_families', count(*)
                  FROM rule_vehicle_weapon_family
                UNION ALL
                SELECT 'vehicle_weapon_definitions', count(*)
                  FROM rule_vehicle_weapon_definition
                UNION ALL
                SELECT 'vehicle_weapon_special_rules', count(*)
                  FROM rule_vehicle_weapon_special_rule
                UNION ALL
                SELECT 'vehicle_weapon_family_special_rules', count(*)
                  FROM rule_vehicle_weapon_family_special_rule
                UNION ALL
                SELECT 'vehicle_weapon_ammunition_rows', count(*)
                  FROM rule_vehicle_weapon_ammunition
                UNION ALL
                SELECT 'vehicle_ordnance_bays', count(*)
                  FROM rule_vehicle_ordnance_bay
                UNION ALL
                SELECT 'vehicle_ordnance_bay_formulas', count(*)
                  FROM rule_vehicle_ordnance_bay_weapon_point_formula
                UNION ALL
                SELECT 'vehicle_ordnance_definitions', count(*)
                  FROM rule_vehicle_ordnance_definition
                UNION ALL
                SELECT 'vehicle_missile_guidance_types', count(*)
                  FROM rule_vehicle_missile_guidance
                UNION ALL
                SELECT 'vehicle_missiles', count(*)
                  FROM rule_vehicle_missile
                UNION ALL
                SELECT 'vehicle_anti_missile_resolutions', count(*)
                  FROM rule_vehicle_anti_missile_resolution
                UNION ALL
                SELECT 'vehicle_anti_missile_systems', count(*)
                  FROM rule_vehicle_anti_missile_system
                UNION ALL
                SELECT 'vehicle_anti_missile_guidance_claims', count(*)
                  FROM rule_vehicle_anti_missile_guidance_claim
                UNION ALL
                SELECT 'vehicle_alien_design_assumptions', count(*)
                  FROM rule_vehicle_alien_design_assumption
                UNION ALL
                SELECT 'vehicle_lift_envelope_rules', count(*)
                  FROM rule_vehicle_lift_envelope
                UNION ALL
                SELECT 'vehicle_lift_media', count(*)
                  FROM rule_vehicle_lift_medium
                UNION ALL
                SELECT 'vehicle_lift_atmosphere_rows', count(*)
                  FROM rule_vehicle_lift_envelope_atmosphere
                UNION ALL
                SELECT 'vehicle_aircraft_environment_rules', count(*)
                  FROM rule_vehicle_aircraft_environment
                UNION ALL
                SELECT 'vehicle_missile_impact_times', count(*)
                  FROM rule_vehicle_missile_impact_time
                UNION ALL
                SELECT 'vehicle_missile_launch_skills', count(*)
                  FROM rule_vehicle_missile_launch_skill
                UNION ALL
                SELECT 'vehicle_missile_launch_effects', count(*)
                  FROM rule_vehicle_missile_launch_effect
                UNION ALL
                SELECT 'vehicle_animal_power_rules', count(*)
                  FROM rule_vehicle_animal_power
                UNION ALL
                SELECT 'vehicle_animal_gaits', count(*)
                  FROM rule_vehicle_animal_gait
                UNION ALL
                SELECT 'vehicle_draft_animal_profiles', count(*)
                  FROM rule_vehicle_draft_animal_profile
                UNION ALL
                SELECT 'vehicle_wind_sailing_speeds', count(*)
                  FROM rule_vehicle_wind_sailing_speed
                UNION ALL
                SELECT 'vehicle_off_road_movement_rules', count(*)
                  FROM rule_vehicle_off_road_movement
                UNION ALL
                SELECT 'vehicle_ship_scale_hulls', count(*)
                  FROM vehicle_class_ship_scale_hull
                UNION ALL
                SELECT 'vehicle_ship_scale_power_plants', count(*)
                  FROM vehicle_class_ship_scale_power_plant
                UNION ALL
                SELECT 'vehicle_ship_scale_propulsions', count(*)
                  FROM vehicle_class_ship_scale_propulsion
                UNION ALL
                SELECT 'vehicle_class_components', count(*)
                  FROM vehicle_class_component
                UNION ALL
                SELECT 'vehicle_class_configuration_options', count(*)
                  FROM vehicle_class_configuration_option
                UNION ALL
                SELECT 'vehicle_class_drive_options', count(*)
                  FROM vehicle_class_drive_option
                UNION ALL
                SELECT 'vehicle_class_autopilots', count(*)
                  FROM vehicle_class_autopilot
                UNION ALL
                SELECT 'vehicle_class_computer_options', count(*)
                  FROM vehicle_class_computer_option
                UNION ALL
                SELECT 'vehicle_class_fuel_tanks', count(*)
                  FROM vehicle_class_fuel_tank
                UNION ALL
                SELECT 'vehicle_class_alternative_communications',
                       count(*)
                  FROM vehicle_class_alternative_communication
                UNION ALL
                SELECT 'vehicle_construction_receipts', count(*)
                  FROM vehicle_class_construction_receipt
                UNION ALL
                SELECT 'vehicle_construction_lines', count(*)
                  FROM vehicle_class_construction_line
                UNION ALL
                SELECT 'vehicle_construction_variances', count(*)
                  FROM vehicle_class_construction_variance
                UNION ALL
                SELECT 'vehicle_personal_combat_rules', count(*)
                  FROM rule_vehicle_personal_combat
                UNION ALL
                SELECT 'vehicle_occupant_protection_rules', count(*)
                  FROM rule_vehicle_occupant_protection
                UNION ALL
                SELECT 'vehicle_weapon_arc_rules', count(*)
                  FROM rule_vehicle_weapon_arc
                UNION ALL
                SELECT 'vehicle_collision_rules', count(*)
                  FROM rule_vehicle_collision
                UNION ALL
                SELECT 'vehicle_combat_actions', count(*)
                  FROM rule_vehicle_combat_action
                UNION ALL
                SELECT 'vehicle_combat_rule_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'vehicle.combat.%'
                UNION ALL
                SELECT 'vehicle_damage_rules', count(*)
                  FROM rule_vehicle_damage_procedure
                UNION ALL
                SELECT 'vehicle_damage_bands', count(*)
                  FROM rule_vehicle_damage_band
                UNION ALL
                SELECT 'vehicle_damage_band_packets', count(*)
                  FROM rule_vehicle_damage_band_packet
                UNION ALL
                SELECT 'vehicle_excess_damage_packets', count(*)
                  FROM rule_vehicle_excess_damage_packet
                UNION ALL
                SELECT 'vehicle_hit_locations', count(*)
                  FROM rule_vehicle_hit_location
                UNION ALL
                SELECT 'vehicle_hit_location_rolls', count(*)
                  FROM rule_vehicle_hit_location_roll
                UNION ALL
                SELECT 'vehicle_hit_location_options', count(*)
                  FROM rule_vehicle_hit_location_roll_option
                UNION ALL
                SELECT 'vehicle_system_hit_stages', count(*)
                  FROM rule_vehicle_system_hit_stage
                UNION ALL
                SELECT 'vehicle_location_overflows', count(*)
                  FROM rule_vehicle_location_overflow
                UNION ALL
                SELECT 'vehicle_explosion_zones', count(*)
                  FROM rule_vehicle_explosion_zone
                UNION ALL
                SELECT 'vehicle_repair_categories', count(*)
                  FROM rule_vehicle_repair_category
                UNION ALL
                SELECT 'vehicle_system_repair_states', count(*)
                  FROM rule_vehicle_system_repair_state
                UNION ALL
                SELECT 'vehicle_damage_repair_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'vehicle.damage.%'
                    OR rule.rule_code LIKE 'vehicle.repair.%'
                UNION ALL
                SELECT 'vehicle_encounter_tables', count(*)
                 FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name LIKE 'venc_%'
                   AND table_type='BASE TABLE'
                UNION ALL
                SELECT 'vehicle_attack_receipt_tables', count(*)
                 FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name LIKE 'venc_attack%'
                   AND table_type='BASE TABLE'
                UNION ALL
                SELECT 'vehicle_damage_application_tables', count(*)
                 FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                       'vehicle_system_state',
                       'venc_damage_application',
                       'venc_damage_location_hit'
                   )
                   AND table_type='BASE TABLE'
                UNION ALL
                SELECT 'vehicle_repair_history_tables', count(*)
                 FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                       'vehicle_repair_receipt',
                       'vehicle_repair_modifier',
                       'vehicle_repair_random_die',
                       'vehicle_repair_spare_source'
                   )
                   AND table_type='BASE TABLE'
                UNION ALL
                SELECT 'vehicle_classes_relational_complete', count(*)
                  FROM vehicle_class_catalogue_completeness
                 WHERE is_relationally_complete
                UNION ALL
                SELECT 'vehicle_classes_relational_incomplete', count(*)
                  FROM vehicle_class_catalogue_completeness
                 WHERE NOT is_relationally_complete
                UNION ALL
                SELECT 'encounter_aggregate_state_tables', count(*)
                 FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                       'enc_side','enc_objective',
                       'enc_participant_intention',
                       'enc_resolution','enc_objective_result'
                   )
                   AND table_type='BASE TABLE'
                UNION ALL
                SELECT 'personal_burst_sizes', count(*)
                  FROM rule_personal_burst_size
                UNION ALL
                SELECT 'personal_burst_options', count(*)
                  FROM rule_personal_burst_option
                UNION ALL
                SELECT 'weapon_burst_capabilities', count(*)
                  FROM inv_weapon_burst_capability
                UNION ALL
                SELECT 'personal_burst_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'combat.burst-%'
                UNION ALL
                SELECT 'personal_suppression_procedures', count(*)
                  FROM rule_personal_suppression_fire
                UNION ALL
                SELECT 'personal_suppression_immunities', count(*)
                  FROM rule_personal_suppression_immunity
                UNION ALL
                SELECT 'personal_suppression_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'combat.suppression-%'
                UNION ALL
                SELECT 'personal_panic_procedures', count(*)
                  FROM rule_personal_panic_fire
                UNION ALL
                SELECT 'personal_panic_weapons', count(*)
                  FROM inv_weapon_panic_fire_capability
                UNION ALL
                SELECT 'personal_panic_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.panic-fire'
                UNION ALL
                SELECT 'personal_shotgun_spread_rules', count(*)
                  FROM rule_personal_shotgun_spread
                UNION ALL
                SELECT 'personal_shotgun_spread_capabilities', count(*)
                  FROM inv_weapon_shotgun_spread_capability
                UNION ALL
                SELECT 'personal_shotgun_spread_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code IN (
                   'combat.shotgun-spread',
                   'equipment.ammunition.shotgun.flechette-shell'
                 )
                UNION ALL
                SELECT 'personal_communication_methods', count(*)
                  FROM rule_personal_communication_method
                UNION ALL
                SELECT 'personal_initiative_support_rules', count(*)
                  FROM rule_personal_initiative_support
                UNION ALL
                SELECT 'personal_comms_support_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'combat.communication.%'
                    OR rule.rule_code LIKE 'combat.initiative-support.%'
                UNION ALL
                SELECT 'personal_battlefield_conditions', count(*)
                  FROM rule_personal_battlefield_condition
                UNION ALL
                SELECT 'personal_battlefield_sensors', count(*)
                  FROM rule_personal_battlefield_sensor
                UNION ALL
                SELECT 'personal_conditions_sensor_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'combat.battlefield-condition.%'
                    OR rule.rule_code LIKE 'combat.battlefield-sensor.%'
                UNION ALL
                SELECT 'personal_blind_fire_rules', count(*)
                  FROM rule_personal_blind_fire
                UNION ALL
                SELECT 'personal_blind_fire_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.blind-fire'
                UNION ALL
                SELECT 'personal_explosion_rules', count(*)
                  FROM rule_personal_explosion
                UNION ALL
                SELECT 'personal_explosion_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.explosions'
                UNION ALL
                SELECT 'personal_extreme_range_rules', count(*)
                  FROM rule_personal_extreme_range
                UNION ALL
                SELECT 'personal_extreme_range_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.extreme-range-firing'
                UNION ALL
                SELECT 'personal_zero_gravity_rules', count(*)
                  FROM rule_personal_zero_gravity_combat
                UNION ALL
                SELECT 'personal_zero_gravity_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.zero-gravity'
                UNION ALL
                SELECT 'personal_firing_into_combat_rules', count(*)
                  FROM rule_personal_firing_into_combat
                UNION ALL
                SELECT 'personal_firing_into_combat_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.firing-into-combat'
                UNION ALL
                SELECT 'personal_grapple_rules', count(*)
                  FROM rule_personal_grapple
                UNION ALL
                SELECT 'personal_grapple_options', count(*)
                  FROM rule_personal_grapple_option
                UNION ALL
                SELECT 'personal_grapple_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.grappling'
                UNION ALL
                SELECT 'personal_thrown_weapon_rules', count(*)
                  FROM rule_personal_thrown_weapon
                UNION ALL
                SELECT 'personal_thrown_capabilities', count(*)
                  FROM inv_thrown_delivery_capability
                UNION ALL
                SELECT 'personal_thrown_weapon_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.thrown-weapons'
                UNION ALL
                SELECT 'personal_coup_de_grace_rules',count(*)
                  FROM rule_personal_coup_de_grace
                UNION ALL
                SELECT 'personal_coup_de_grace_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.coup-de-grace'
                UNION ALL
                SELECT 'personal_coup_de_grace_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_personal_coup_de_grace_receipt'
                UNION ALL
                SELECT 'personal_extended_action_rules',count(*)
                  FROM rule_personal_extended_action
                UNION ALL
                SELECT 'personal_extended_action_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.extended-actions'
                UNION ALL
                SELECT 'personal_extended_action_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                     'enc_personal_extended_action',
                     'cmd_personal_extended_action_receipt',
                     'cmd_personal_extended_action_interruption')
                UNION ALL
                SELECT 'personal_free_action_rules',count(*)
                  FROM rule_personal_free_action
                UNION ALL
                SELECT 'personal_free_action_examples',count(*)
                  FROM rule_personal_free_action_example
                UNION ALL
                SELECT 'personal_free_action_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.free-actions'
                UNION ALL
                SELECT 'personal_free_action_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_personal_free_action_receipt'
                UNION ALL
                SELECT 'personal_starting_range_contexts',count(*)
                  FROM rule_personal_starting_range_context
                UNION ALL
                SELECT 'personal_starting_range_options',count(*)
                  FROM rule_personal_starting_range_option
                UNION ALL
                SELECT 'personal_starting_range_light_caps',count(*)
                  FROM rule_personal_starting_range_light_cap
                UNION ALL
                SELECT 'personal_starting_range_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.starting-range'
                UNION ALL
                SELECT 'personal_starting_range_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='enc_personal_combat_starting_range'
                UNION ALL
                SELECT 'personal_weapon_ready_rules',count(*)
                  FROM rule_personal_weapon_readying
                UNION ALL
                SELECT 'personal_weapon_ready_profiles',count(*)
                  FROM inv_weapon_ready_profile
                UNION ALL
                SELECT 'personal_weapon_ready_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.weapon-readying'
                UNION ALL
                SELECT 'personal_weapon_ready_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_personal_weapon_ready_receipt'
                UNION ALL
                SELECT 'personal_weapon_assistance_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='enc_personal_attack_weapon_assistance'
                UNION ALL
                SELECT 'personal_stance_change_rules',count(*)
                  FROM rule_personal_stance_change
                UNION ALL
                SELECT 'personal_stance_change_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING(rule_id)
                 WHERE rule.rule_code='combat.stance-change'
                UNION ALL
                SELECT 'personal_miscellaneous_action_rules',count(*)
                  FROM rule_personal_miscellaneous_action
                UNION ALL
                SELECT 'personal_miscellaneous_action_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING(rule_id)
                 WHERE rule.rule_code LIKE 'combat.miscellaneous-action.%'
                UNION ALL
                SELECT 'personal_miscellaneous_action_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_personal_miscellaneous_action_receipt'
                UNION ALL
                SELECT 'personal_reaction_option_rules',count(*)
                  FROM rule_personal_reaction_option
                UNION ALL
                SELECT 'personal_reaction_option_provenance',count(*)
                  FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id)
                 WHERE rule.rule_code LIKE 'combat.reaction.%'
                UNION ALL
                SELECT 'personal_conflict_avoidance_rules',count(*) FROM rule_personal_conflict_avoidance
                UNION ALL
                SELECT 'personal_conflict_avoidance_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='combat.conflict-avoidance'
                UNION ALL
                SELECT 'personal_combat_resolution_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_personal_combat_resolution_receipt'
                UNION ALL
                SELECT 'gameplay_skill_training_rules',count(*) FROM rule_gameplay_skill_training
                UNION ALL
                SELECT 'gameplay_skill_training_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='skill.gameplay-training'
                UNION ALL
                SELECT 'gameplay_skill_training_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('camp_skill_training_project','cmd_skill_training_week_receipt')
                UNION ALL
                SELECT 'personal_fatigue_rules', count(*)
                  FROM rule_personal_fatigue
                UNION ALL
                SELECT 'personal_unconsciousness_rules', count(*)
                  FROM rule_personal_unconsciousness
                UNION ALL
                SELECT 'personal_condition_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code IN (
                    'combat.fatigue','combat.unconsciousness')
                UNION ALL
                SELECT 'personal_natural_healing_rules', count(*)
                  FROM rule_personal_natural_healing
                UNION ALL
                SELECT 'personal_natural_healing_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.natural-healing'
                UNION ALL
                SELECT 'personal_medical_treatment_rules', count(*)
                  FROM rule_personal_medical_treatment
                UNION ALL
                SELECT 'personal_medical_treatment_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='combat.medical-treatment'
                UNION ALL
                SELECT 'personal_mental_healing_rules', count(*)
                  FROM rule_personal_mental_healing
                UNION ALL
                SELECT 'personal_mental_healing_characteristics', count(*)
                  FROM rule_personal_mental_healing_characteristic
                UNION ALL
                SELECT 'personal_mental_healing_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code=
                       'combat.mental-characteristic-healing'
                UNION ALL
                SELECT 'ground_force_starship_rules', count(*)
                  FROM rule_ground_force_starship_attack
                UNION ALL
                SELECT 'ground_force_starship_contributions', count(*)
                  FROM rule_ground_force_starship_volley_contribution
                UNION ALL
                SELECT 'ground_force_starship_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code=
                       'combat.ground-force-starship-scale'
                UNION ALL
                SELECT 'ground_force_starship_runtime_tables', count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                     'gf_ground_weapon_battery',
                     'cmd_ground_starship_volley',
                     'cmd_ground_starship_volley_attack',
                     'cmd_ground_starship_volley_final_receipt',
                     'cmd_ground_starship_volley_damage_die')
                UNION ALL
                SELECT 'personal_armor_catalogue_rules', count(*)
                  FROM rule_personal_armor_catalogue
                UNION ALL
                SELECT 'personal_armor_profiles', count(*)
                  FROM inv_armor_definition
                 WHERE catalogue_display_order IS NOT NULL
                UNION ALL
                SELECT 'personal_armor_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN src_import_candidate candidate
                    USING (import_candidate_id)
                  JOIN rule_rule rule USING (rule_id)
                 WHERE candidate.candidate_type=
                       'personal_armor_catalogue'
                   AND (rule.rule_code='equipment.personal-armor-catalogue'
                    OR rule.rule_code LIKE 'equipment.armor.%')
                UNION ALL
                SELECT 'personal_armor_source_issues', count(*)
                  FROM src_issue
                 WHERE domain_code='equipment.armor'
                UNION ALL
                SELECT 'personal_armor_degradation_rules', count(*)
                  FROM rule_armor_degradation
                UNION ALL
                SELECT 'personal_armor_layer_exceptions', count(*)
                  FROM rule_armor_layer_exception
                UNION ALL
                SELECT 'personal_armor_characteristic_modifiers', count(*)
                  FROM rule_armor_characteristic_modifier
                UNION ALL
                SELECT 'personal_armor_life_support_rules', count(*)
                  FROM rule_armor_life_support
                UNION ALL
                SELECT 'personal_armor_direct_protections', count(*)
                  FROM rule_armor_environmental_protection
                UNION ALL
                SELECT 'personal_armor_effective_protections', count(*)
                  FROM rule_armor_effective_environmental_protection
                UNION ALL
                SELECT 'personal_armor_mechanic_provenance', count(*)
                  FROM src_armor_mechanic_provenance
                UNION ALL
                SELECT 'personal_armor_runtime_tables', count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                     'inv_armor_instance_state',
                     'inv_actor_armor_layer',
                     'cmd_personal_armor_equip_receipt',
                     'cmd_personal_armor_layer_receipt',
                     'cmd_personal_armor_usage_receipt')
                UNION ALL
                SELECT 'personal_communicator_usage_rules', count(*)
                  FROM rule_personal_communicator_usage
                UNION ALL
                SELECT 'personal_communicator_profiles', count(*)
                  FROM inv_communicator_definition
                UNION ALL
                SELECT 'personal_communicator_tl_profiles', count(*)
                  FROM inv_communicator_tech_profile
                UNION ALL
                SELECT 'personal_communicator_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-communicators'
                    OR rule.rule_code LIKE 'equipment.communicator.%'
                UNION ALL
                SELECT 'personal_computer_profiles', count(*)
                  FROM inv_personal_computer_definition
                UNION ALL
                SELECT 'personal_computer_form_factors', count(*)
                  FROM rule_personal_computer_form_factor
                UNION ALL
                SELECT 'personal_computer_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-computers'
                    OR rule.rule_code LIKE 'equipment.computer.%'
                UNION ALL
                SELECT 'personal_computer_source_issues', count(*)
                  FROM src_issue
                 WHERE domain_code='equipment.computer'
                UNION ALL
                SELECT 'personal_computer_options', count(*)
                  FROM inv_personal_computer_option_definition
                UNION ALL
                SELECT 'personal_computer_specialization_rules', count(*)
                  FROM rule_personal_computer_specialization
                UNION ALL
                SELECT 'personal_computer_option_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE
                       'equipment.computer-option.%'
                UNION ALL
                SELECT 'personal_software_families', count(*)
                  FROM rule_personal_software_family
                UNION ALL
                SELECT 'personal_software_profiles', count(*)
                  FROM rule_personal_software_profile
                UNION ALL
                SELECT 'personal_software_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code=
                       'equipment.personal-computer-software'
                    OR rule.rule_code LIKE 'software.personal.%'
                UNION ALL
                SELECT 'personal_software_security_mappings', count(*)
                  FROM rule_personal_security_difficulty
                UNION ALL
                SELECT 'personal_software_ai_capabilities', count(*)
                  FROM rule_personal_intelligent_interface_capability
                UNION ALL
                SELECT 'personal_software_expert_characteristics', count(*)
                  FROM rule_personal_expert_allowed_characteristic
                UNION ALL
                SELECT 'personal_software_mechanic_tables', count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                    'rule_personal_database_mechanic',
                    'rule_personal_interface_mechanic',
                    'rule_personal_security_difficulty',
                    'rule_personal_translator_mechanic',
                    'rule_personal_intrusion_mechanic',
                    'rule_personal_intelligent_interface_capability',
                    'rule_personal_expert_mechanic',
                    'rule_personal_expert_allowed_characteristic',
                    'rule_personal_agent_mechanic',
                    'rule_personal_intellect_mechanic')
                UNION ALL
                SELECT 'personal_drugs', count(*)
                  FROM inv_personal_drug_definition
                UNION ALL
                SELECT 'personal_drug_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-drugs'
                    OR rule.rule_code LIKE 'equipment.drug.%'
                UNION ALL
                SELECT 'anagathic_availability_rules', count(*)
                  FROM rule_anagathic_availability
                UNION ALL
                SELECT 'personal_combat_drug_effects', count(*)
                  FROM rule_personal_combat_drug_effect
                UNION ALL
                SELECT 'personal_antiradiation_rules', count(*)
                  FROM rule_personal_antiradiation_drug
                UNION ALL
                SELECT 'personal_stim_rules', count(*)
                  FROM rule_personal_stim_drug
                UNION ALL
                SELECT 'personal_support_drug_rules', count(*)
                  FROM (
                        SELECT drug_rule_id FROM rule_personal_fast_drug
                        UNION ALL
                        SELECT drug_rule_id FROM rule_personal_medicinal_drug
                        UNION ALL
                        SELECT drug_rule_id
                          FROM rule_personal_medicinal_slow_drug
                        UNION ALL
                        SELECT drug_rule_id FROM rule_personal_panacea
                        UNION ALL
                        SELECT drug_rule_id
                          FROM rule_personal_anagathic_dosing
                  ) support_drugs
                UNION ALL
                SELECT 'personal_explosives', count(*)
                  FROM inv_personal_explosive_definition
                UNION ALL
                SELECT 'personal_explosive_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-explosives'
                    OR rule.rule_code LIKE 'equipment.explosive.%'
                UNION ALL
                SELECT 'personal_explosive_use_rules', count(*)
                  FROM rule_personal_explosive_use
                UNION ALL
                SELECT 'personal_devices', count(*)
                  FROM inv_personal_device_definition
                UNION ALL
                SELECT 'personal_device_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-devices'
                    OR rule.rule_code LIKE 'equipment.device.%'
                UNION ALL
                SELECT 'personal_device_capabilities', count(*)
                  FROM rule_personal_device_capability
                UNION ALL
                SELECT 'personal_device_skill_links', count(*)
                  FROM rule_personal_device_capability_skill
                UNION ALL
                SELECT 'personal_hologram_upgrades', count(*)
                  FROM rule_personal_holographic_projector_upgrade
                UNION ALL
                SELECT 'personal_robot_drone_frameworks', count(*)
                  FROM rule_personal_robot_drone_framework
                UNION ALL
                SELECT 'personal_robot_drone_kinds', count(*)
                  FROM rule_personal_robot_drone_kind
                UNION ALL
                SELECT 'personal_robot_drone_chassis', count(*)
                  FROM inv_personal_robot_drone_chassis
                UNION ALL
                SELECT 'personal_robot_drone_chassis_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-robot-drone-chassis'
                    OR rule.rule_code='equipment.probe-drone'
                    OR rule.rule_code LIKE 'equipment.robot-drone.%'
                UNION ALL
                SELECT 'personal_robot_drone_systems', count(*)
                  FROM inv_personal_robot_drone_system
                UNION ALL
                SELECT 'personal_robot_drone_programs', count(*)
                  FROM inv_personal_robot_drone_program
                UNION ALL
                SELECT 'personal_robot_drone_weapons', count(*)
                  FROM inv_personal_robot_drone_weapon
                UNION ALL
                SELECT 'personal_robot_drone_mobility', count(*)
                  FROM rule_personal_robot_drone_mobility
                UNION ALL
                SELECT 'personal_combat_drone_operations', count(*)
                  FROM rule_personal_combat_drone_operation
                UNION ALL
                SELECT 'personal_robot_drone_options', count(*)
                  FROM rule_personal_robot_drone_option
                UNION ALL
                SELECT 'personal_robot_drone_option_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE
                       'equipment.robot-drone-option.%'
                UNION ALL
                SELECT 'personal_sensory_aids', count(*)
                  FROM inv_personal_sensory_aid_definition
                UNION ALL
                SELECT 'personal_sensory_aid_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-sensory-aids'
                    OR rule.rule_code LIKE 'equipment.sensory-aid.%'
                UNION ALL
                SELECT 'personal_sensory_aid_capabilities', count(*)
                  FROM rule_personal_sensory_aid_capability
                UNION ALL
                SELECT 'personal_sensory_aid_light_modes', count(*)
                  FROM rule_personal_sensory_aid_illumination_mode
                UNION ALL
                SELECT 'personal_binocular_upgrades', count(*)
                  FROM rule_personal_binocular_upgrade
                UNION ALL
                SELECT 'personal_shelters', count(*)
                  FROM inv_personal_shelter_definition
                UNION ALL
                SELECT 'personal_shelter_capabilities', count(*)
                  FROM rule_personal_shelter_capability
                UNION ALL
                SELECT 'personal_modular_shelter_geometry', count(*)
                  FROM rule_personal_modular_shelter_geometry
                UNION ALL
                SELECT 'personal_shelter_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-shelters'
                    OR rule.rule_code LIKE 'equipment.shelter.%'
                UNION ALL
                SELECT 'personal_survival_equipment', count(*)
                  FROM inv_personal_survival_equipment_definition
                UNION ALL
                SELECT 'personal_survival_equipment_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code=
                       'equipment.personal-survival-equipment'
                    OR rule.rule_code LIKE 'equipment.survival.%'
                UNION ALL
                SELECT 'personal_survival_capabilities', count(*)
                  FROM rule_personal_survival_equipment_capability
                UNION ALL
                SELECT 'personal_survival_atmosphere_links', count(*)
                  FROM rule_personal_survival_equipment_atmosphere
                UNION ALL
                SELECT 'personal_survival_skill_links', count(*)
                  FROM rule_personal_survival_equipment_skill
                UNION ALL
                SELECT 'personal_tools', count(*)
                  FROM inv_personal_tool_definition
                UNION ALL
                SELECT 'personal_tool_operations', count(*)
                  FROM rule_personal_tool_operation
                UNION ALL
                SELECT 'personal_tool_law_prices', count(*)
                  FROM rule_personal_tool_law_price
                UNION ALL
                SELECT 'personal_tool_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.personal-tools'
                    OR rule.rule_code LIKE 'equipment.tool.%'
                UNION ALL
                SELECT 'book1_vehicle_profiles', count(*)
                  FROM rule_book1_vehicle_profile
                UNION ALL
                SELECT 'book1_vehicle_occupancy', count(*)
                  FROM rule_book1_vehicle_occupancy
                UNION ALL
                SELECT 'book1_vehicle_weapon_summaries', count(*)
                  FROM rule_book1_vehicle_weapon_summary
                UNION ALL
                SELECT 'book1_vehicle_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code='equipment.book1-vehicles'
                    OR (rule.rule_code LIKE 'vehicle.book1.%'
                        AND rule.rule_code NOT LIKE
                            'vehicle.book1.option.%')
                UNION ALL
                SELECT 'book1_vehicle_capabilities', count(*)
                  FROM rule_book1_vehicle_capability
                UNION ALL
                SELECT 'book1_grav_belt_batteries', count(*)
                  FROM rule_book1_grav_belt_battery
                UNION ALL
                SELECT 'book1_afv_laser_rules', count(*)
                  FROM rule_book1_afv_laser_fire
                UNION ALL
                SELECT 'book1_vehicle_options', count(*)
                  FROM rule_book1_vehicle_option
                UNION ALL
                SELECT 'book1_vehicle_option_inclusions', count(*)
                  FROM rule_book1_vehicle_included_option
                UNION ALL
                SELECT 'book1_vehicle_option_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'vehicle.book1.option.%'
                UNION ALL
                SELECT 'book1_melee_attacks', count(*)
                  FROM rule_book1_melee_attack
                UNION ALL
                SELECT 'book1_melee_attack_modes', count(*)
                  FROM rule_book1_melee_attack_mode
                UNION ALL
                SELECT 'book1_melee_damage_types', count(*)
                  FROM inv_weapon_damage_type damage
                  JOIN rule_book1_melee_attack attack
                    ON attack.weapon_item_rule_id=damage.item_rule_id
                UNION ALL
                SELECT 'book1_melee_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN src_locator locator USING (source_locator_id)
                 WHERE locator.heading_path=
                   'Equipment > Weapons > Common Personal Melee Weapons'
                UNION ALL
                SELECT 'book1_melee_capabilities', count(*)
                  FROM rule_book1_melee_weapon_capability
                UNION ALL
                SELECT 'book1_melee_length_profiles', count(*)
                  FROM rule_book1_melee_weapon_capability
                 WHERE minimum_length_mm IS NOT NULL
                UNION ALL
                SELECT 'book1_melee_two_handed', count(*)
                  FROM rule_book1_melee_weapon_capability
                 WHERE requires_two_hands
                UNION ALL
                SELECT 'book1_melee_capability_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN src_locator locator USING (source_locator_id)
                 WHERE locator.heading_path=
                   'Equipment > Weapons > Melee Weapon Descriptions'
                UNION ALL
                SELECT 'book1_ranged_fire_profiles', count(*)
                  FROM rule_book1_ranged_weapon_fire_profile
                UNION ALL
                SELECT 'book1_ranged_ammunition_variants', count(*)
                  FROM rule_book1_ranged_ammunition_listing
                UNION ALL
                SELECT 'book1_ranged_ammunition_source_rows',
                       count(DISTINCT source_listing_code)
                  FROM rule_book1_ranged_ammunition_listing
                UNION ALL
                SELECT 'book1_ranged_capabilities', count(*)
                  FROM rule_book1_ranged_weapon_capability
                UNION ALL
                SELECT 'book1_crossbow_reload_profiles', count(*)
                  FROM rule_book1_crossbow_reload_profile
                UNION ALL
                SELECT 'book1_ranged_mode_switches', count(*)
                  FROM rule_book1_ranged_mode_switch
                UNION ALL
                SELECT 'book1_revolver_reload_choices', count(*)
                  FROM rule_book1_revolver_reload_choice
                UNION ALL
                SELECT 'book1_ammunition_compatibilities', count(*)
                  FROM rule_book1_ammunition_compatibility
                UNION ALL
                SELECT 'book1_ranged_weapon_options', count(*)
                  FROM rule_book1_ranged_weapon_option
                UNION ALL
                SELECT 'book1_ranged_weapon_option_effects', count(*)
                  FROM rule_book1_ranged_weapon_option_effect
                UNION ALL
                SELECT 'book1_ranged_weapon_option_upgrades', count(*)
                  FROM rule_book1_ranged_weapon_option_upgrade
                UNION ALL
                SELECT 'book1_ranged_weapon_option_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'equipment.weapon-option.%'
                UNION ALL
                SELECT 'book1_grenades', count(*) FROM rule_book1_grenade
                UNION ALL
                SELECT 'book1_grenade_delivery_modes', count(*)
                  FROM rule_book1_grenade_delivery_mode
                UNION ALL
                SELECT 'book1_frag_damage_bands', count(*)
                  FROM rule_book1_frag_grenade_damage_band
                UNION ALL
                SELECT 'book1_grenade_field_effects', count(*)
                  FROM rule_book1_grenade_field_effect
                UNION ALL
                SELECT 'book1_stun_grenade_effects', count(*)
                  FROM rule_book1_stun_grenade_effect
                UNION ALL
                SELECT 'book1_grenade_provenance', count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING (rule_id)
                 WHERE rule.rule_code LIKE 'equipment.grenade.%'
                UNION ALL
                SELECT 'book1_heavy_weapons',count(*) FROM rule_book1_heavy_weapon
                UNION ALL
                SELECT 'book1_heavy_fire_profiles',count(*)
                  FROM rule_book1_heavy_weapon_fire_profile
                UNION ALL
                SELECT 'book1_heavy_ammunition',count(*)
                  FROM rule_book1_heavy_ammunition
                UNION ALL
                SELECT 'book1_heavy_provenance',count(*)
                  FROM src_record_provenance provenance
                  JOIN rule_rule rule USING(rule_id)
                 WHERE rule.rule_code LIKE 'equipment.heavy-weapon.%'
                    OR rule.rule_code LIKE 'equipment.heavy-ammunition.%'
                UNION ALL
                SELECT 'book1_heavy_capabilities',count(*)
                  FROM rule_book1_heavy_weapon_capability
                UNION ALL
                SELECT 'book1_rocket_impacts',count(*)
                  FROM rule_book1_rocket_impact
                UNION ALL
                SELECT 'psionic_training_rules',count(*)
                  FROM rule_psionic_training
                UNION ALL
                SELECT 'psionic_awareness_suspension_rules',count(*)
                  FROM rule_psi_suspended_animation
                UNION ALL
                SELECT 'psionic_awareness_enhancement_rules',count(*)
                  FROM rule_psi_characteristic_enhancement
                UNION ALL
                SELECT 'psionic_awareness_regeneration_rules',count(*)
                  FROM rule_psi_regeneration
                UNION ALL
                SELECT 'psionic_awareness_regeneration_characteristics',
                       count(*)
                  FROM rule_psi_regeneration_characteristic
                UNION ALL
                SELECT 'psionic_awareness_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN (
                   'cmd_psi_awareness_effect_receipt',
                   'cmd_psi_suspended_animation_receipt',
                   'cmd_psi_suspended_animation_end_receipt',
                   'cmd_psi_characteristic_enhancement_receipt',
                   'cmd_psi_regeneration_receipt',
                   'cmd_psi_regeneration_allocation',
                   'camp_psi_regeneration_recovery_lock',
                   'cmd_psi_regeneration_release_receipt')
                UNION ALL
                SELECT 'psionic_awareness_runtime_views',count(*)
                  FROM information_schema.views
                 WHERE table_schema='public' AND table_name IN (
                   'camp_active_psi_suspended_animation',
                   'camp_current_psi_characteristic_enhancement')
                UNION ALL
                SELECT 'psionic_clairvoyance_power_rules',count(*)
                  FROM rule_psi_clairvoyance_power
                UNION ALL
                SELECT 'psionic_clairvoyance_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_clairvoyant_observation_receipt'
                UNION ALL
                SELECT 'psionic_telekinesis_system_rules',count(*)
                  FROM rule_psi_telekinesis_system
                UNION ALL
                SELECT 'psionic_telekinesis_mass_profiles',count(*)
                  FROM rule_psi_telekinesis_mass_profile
                UNION ALL
                SELECT 'psionic_telekinesis_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name=
                     'cmd_psi_telekinetic_manipulation_receipt'
                UNION ALL
                SELECT 'psionic_telekinetic_throw_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_telekinetic_throw_receipt'
                UNION ALL
                SELECT 'psionic_life_detection_rules',count(*)
                  FROM rule_psi_life_detection
                UNION ALL
                SELECT 'psionic_life_detection_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                     'cmd_psi_life_detection_receipt',
                     'cmd_psi_life_detection_mind'
                   )
                UNION ALL
                SELECT 'psionic_telempathy_rules',count(*)
                  FROM rule_psi_telempathy
                UNION ALL
                SELECT 'psionic_telempathy_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_telempathy_receipt'
                UNION ALL
                SELECT 'psionic_surface_thought_rules',count(*)
                  FROM rule_psi_read_surface_thoughts
                UNION ALL
                SELECT 'psionic_surface_thought_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_surface_thought_receipt'
                UNION ALL
                SELECT 'psionic_send_thought_rules',count(*)
                  FROM rule_psi_send_thoughts
                UNION ALL
                SELECT 'psionic_sent_thought_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_sent_thought_receipt'
                UNION ALL
                SELECT 'psionic_probe_rules',count(*)
                  FROM rule_psi_probe
                UNION ALL
                SELECT 'psionic_probe_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                     'cmd_psi_probe_receipt',
                     'cmd_psi_probe_question'
                   )
                UNION ALL
                SELECT 'psionic_assault_rules',count(*)
                  FROM rule_psi_assault
                UNION ALL
                SELECT 'psionic_assault_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_assault_receipt'
                UNION ALL
                SELECT 'psionic_shield_rules',count(*)
                  FROM rule_psi_shield
                UNION ALL
                SELECT 'psionic_shield_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name IN (
                     'actor_telepathic_shield_state',
                     'cmd_telepathic_shield_receipt'
                   )
                UNION ALL
                SELECT 'psionic_teleportation_system_rules',count(*)
                  FROM rule_psi_teleportation_system
                UNION ALL
                SELECT 'psionic_teleportation_power_rules',count(*)
                  FROM rule_psi_teleportation_power
                UNION ALL
                SELECT 'psionic_teleportation_disorientation_rules',count(*)
                  FROM rule_psi_teleportation_disorientation
                UNION ALL
                SELECT 'psionic_teleportation_runtime_tables',count(*)
                  FROM information_schema.tables
                 WHERE table_schema='public'
                   AND table_name='cmd_psi_teleportation_receipt'
                UNION ALL
                SELECT 'personal_drug_source_issues', count(*)
                  FROM src_issue WHERE domain_code='equipment.drug'
                UNION ALL
                SELECT 'vehicle_class_armament_missiles', count(*)
                  FROM vehicle_class_armament_missile
                UNION ALL
                SELECT 'vehicle_class_armament_ordnance', count(*)
                  FROM vehicle_class_armament_ordnance
                UNION ALL
                SELECT 'vehicle_class_ammunition_loads', count(*)
                  FROM vehicle_class_weapon_ammunition_load
                UNION ALL
                SELECT 'vehicle_class_missile_loads', count(*)
                  FROM vehicle_class_missile_load
                UNION ALL
                SELECT 'vehicle_class_ordnance_loads', count(*)
                  FROM vehicle_class_ordnance_load
                UNION ALL
                SELECT 'vehicle_class_weapon_point_summaries', count(*)
                  FROM vehicle_class_weapon_point_summary
                UNION ALL
                SELECT 'vehicle_class_armament_mounts', count(*)
                  FROM vehicle_class_armament_mount
                UNION ALL
                SELECT 'vehicle_class_armament_weapons', count(*)
                  FROM vehicle_class_armament_weapon
                UNION ALL
                SELECT 'vehicle_class_armament_gun_shields', count(*)
                  FROM vehicle_class_armament_gun_shield
                UNION ALL
                SELECT 'vehicle_chassis', count(*)
                  FROM rule_vehicle_chassis
                UNION ALL
                SELECT 'vehicle_armor', count(*)
                  FROM rule_vehicle_armor
                UNION ALL
                SELECT 'vehicle_power_plants', count(*)
                  FROM rule_vehicle_power_plant_type
                UNION ALL
                SELECT 'vehicle_propulsion_types', count(*)
                  FROM rule_vehicle_propulsion_type
                UNION ALL
                SELECT 'vehicle_drives', count(*)
                  FROM rule_vehicle_drive
                UNION ALL
                SELECT 'vehicle_drive_performance', count(*)
                  FROM rule_vehicle_drive_performance
                UNION ALL
                SELECT 'vehicle_propulsion_speeds', count(*)
                  FROM rule_vehicle_propulsion_speed
                UNION ALL
                SELECT 'vehicle_drive_fuel_requirements', count(*)
                  FROM rule_vehicle_drive_fuel_requirement
                UNION ALL
                SELECT 'vehicle_power_plant_fuels', count(*)
                  FROM rule_vehicle_power_plant_fuel
                UNION ALL
                SELECT 'standard_vehicle_classes', count(*)
                  FROM vehicle_class
                UNION ALL
                SELECT 'space_range_bands', count(*)
                  FROM rule_space_range_band
                UNION ALL
                SELECT 'space_combat_actions', count(*)
                  FROM rule_space_combat_action
                UNION ALL
                SELECT 'space_combat_turn_order_procedures', count(*)
                  FROM rule_space_combat_procedure
                 WHERE higher_thrust_breaks_initiative_ties
                   AND remaining_initiative_ties_simultaneous
                   AND vessel_crew_acts_together
                   AND initiative_is_dynamic
                   AND NOT initiative_rerolled_each_round
                UNION ALL
                SELECT 'space_combat_initiative_rules', count(*)
                  FROM rule_space_combat_initiative
                 WHERE dice_count=2 AND die_sides=6
                   AND awareness_fixed_total=12
                   AND awareness_uses_pilot_dexterity
                   AND compare_highest_hostile_thrust
                   AND higher_thrust_modifier=1
                   AND vessel_tactics_scope AND fleet_tactics_scope
                   AND NOT tactics_scopes_stack
                UNION ALL
                SELECT 'space_combat_range_check_rules', count(*)
                  FROM rule_space_combat_range_check
                 WHERE maximum_band_change=1
                   AND winner_may_increase AND winner_may_decrease
                   AND winner_may_maintain
                   AND opposed_tie_uses_characteristic
                   AND full_tie_requires_reroll
                UNION ALL
                SELECT 'space_combat_increase_initiative_rules', count(*)
                  FROM rule_space_combat_increase_initiative
                 WHERE applies_following_round_only
                   AND consumes_significant_action_on_failure
                   AND minimum_initiative_modifier=0
                   AND uses_positive_effect
                UNION ALL
                SELECT 'space_combat_pursuit_rules', count(*)
                  FROM rule_space_combat_pursuit
                 WHERE establishment_range_codes=ARRAY['close','short']
                   AND equal_speed_required
                   AND maintenance_requires_significant_action
                   AND NOT maintenance_requires_check
                   AND first_turn_attack_modifier=0
                   AND attack_modifier_per_later_turn=1
                   AND maximum_attack_modifier=4
                   AND automatic_break_minimum_range_order=(
                     SELECT display_order FROM rule_space_range_band
                      WHERE range_band_code='medium')
                   AND automatic_break_speed_advantage=7
                   AND immediate_automatic_break
                   AND reestablishment_required_after_break
                UNION ALL
                SELECT 'space_combat_evasive_maneuver_rules', count(*)
                  FROM rule_space_combat_evasive_maneuvers
                 WHERE success_attack_penalty=-1
                   AND exceptional_effect_threshold=6
                   AND exceptional_attack_penalty=-2
                   AND applies_to_attacks_targeting_vessel
                   AND applies_current_round_only
                   AND failure_consumes_action
                UNION ALL
                SELECT 'space_combat_line_up_shot_rules', count(*)
                  FROM rule_space_combat_line_up_shot
                 WHERE success_attack_bonus=1
                   AND exceptional_effect_threshold=6
                   AND exceptional_attack_bonus=2
                   AND applies_to_all_vessel_attacks
                   AND applies_current_round_only
                   AND failure_consumes_action
                UNION ALL
                SELECT 'space_combat_docking_rules', count(*)
                  FROM rule_space_combat_docking
                 WHERE resisted_docking_modifier=-2
                   AND required_start_range_code='adjacent'
                   AND success_range_code='docked'
                   AND opposed_tie_uses_characteristic
                   AND full_tie_requires_reroll
                   AND success_allows_boarding
                UNION ALL
                SELECT 'space_combat_ram_rules', count(*)
                  FROM rule_space_combat_ram
                 WHERE required_range_code='close'
                   AND rammer_must_be_faster
                   AND damage_dice_per_speed_difference=1
                   AND damage_die_sides=6
                   AND opposed_tie_uses_characteristic
                   AND full_tie_requires_reroll
                   AND shared_damage_roll
                   AND damage_applies_to_both_vessels
                   AND armor_applies_independently
                UNION ALL
                SELECT 'space_combat_pilot_movement_rules', count(*)
                  FROM rule_space_combat_pilot_movement
                 WHERE adjust_speed_action_code='adjust-speed'
                   AND maintain_course_action_code='maintain-course'
                   AND speed_change_limited_by_thrust
                   AND minimum_speed=0
                   AND NOT adjust_requires_check
                   AND NOT maintain_requires_check
                   AND maintain_preserves_speed
                   AND both_are_minor_actions
                UNION ALL
                SELECT 'space_combat_avoid_collision_rules', count(*)
                  FROM rule_space_combat_avoid_collision
                 WHERE applicable_range_codes=ARRAY['close','short']
                   AND check_required_each_turn
                   AND damage_dice_per_speed_point=1
                   AND damage_die_sides=6
                   AND significant_speed_difference_modifier=-2
                   AND armor_applies
                UNION ALL
                SELECT 'space_combat_reaction_system_rules', count(*)
                  FROM rule_space_combat_reaction_system
                 WHERE targeted_beam_allows_reaction
                   AND incoming_missile_allows_reaction
                   AND attempted_boarding_allows_reaction
                   AND initiative_determines_limit
                UNION ALL
                SELECT 'space_combat_dodge_rules', count(*)
                  FROM rule_space_combat_dodge
                 WHERE success_attack_modifier=-2
                   AND failure_attack_modifier=0
                   AND reaction_consumed_on_failure
                UNION ALL
                SELECT 'space_combat_fire_sand_rules', count(*)
                  FROM rule_space_combat_fire_sand
                 WHERE canisters_per_reaction=1
                   AND beam_reduction_dice_per_beam=1
                   AND beam_reduction_die_sides=6
                   AND resolve_each_beam_separately
                   AND boarding_damage_dice=8
                   AND boarding_damage_die_sides=6
                   AND ammunition_consumed_on_failure
                UNION ALL
                SELECT 'space_combat_point_defense_rules', count(*)
                  FROM rule_space_combat_point_defense
                 WHERE required_weapon_kind='laser'
                   AND missiles_destroyed_per_success=1
                   AND cumulative_modifier_per_check=-1
                   AND continue_until_failure
                   AND may_change_missile_target
                   AND boarding_parties_allowed
                UNION ALL
                SELECT 'space_combat_trigger_screen_rules', count(*)
                  FROM rule_space_combat_trigger_screens
                 WHERE minimum_skill_level=0
                   AND damage_reduction_dice=2
                   AND damage_reduction_die_sides=6
                   AND add_operator_skill
                   AND nuclear_removes_automatic_radiation
                   AND commander_or_gunner_may_operate
                UNION ALL
                SELECT 'space_combat_coordinate_crew_rules', count(*)
                  FROM rule_space_combat_coordinate_crew
                 WHERE minimum_pool_points=1
                   AND points_per_effect=1
                   AND modifier_per_point=1
                   AND individual_crew_allocations
                   AND current_round_only
                UNION ALL
                SELECT 'space_combat_sensor_targeting_rules', count(*)
                  FROM rule_space_combat_sensor_targeting
                 WHERE success_attack_bonus=1
                   AND exceptional_effect_threshold=6
                   AND exceptional_attack_bonus=2
                   AND applies_to_all_gunners AND applies_current_round_only AND target_specific
                   AND missile_launch_check_benefits AND NOT missile_impact_roll_benefits AND NOT smart_missiles_benefit
                UNION ALL
                SELECT 'space_combat_crew_roles', count(*) FROM rule_space_combat_crew_role
                UNION ALL
                SELECT 'space_combat_attack_range_rows', count(*) FROM rule_space_combat_attack_range
                UNION ALL
                SELECT 'space_combat_attack_weapon_profiles', count(*) FROM rule_space_combat_weapon_profile
                UNION ALL
                SELECT 'space_combat_mount_attack_runtime_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_mount_attack_declaration','senc_mount_weapon_attack_check')
                UNION ALL
                SELECT 'space_combat_damage_bands', count(*) FROM rule_space_combat_damage_band
                UNION ALL
                SELECT 'space_combat_hit_locations', count(*) FROM rule_space_combat_hit_location
                UNION ALL
                SELECT 'space_combat_location_effects', count(*) FROM rule_space_combat_location_effect
                UNION ALL
                SELECT 'space_combat_damage_grouping_rules', count(*) FROM rule_space_combat_damage_grouping
                 WHERE weapon_damage_rolled_separately AND armor_applied_per_weapon AND fire_sand_applied_per_beam
                  AND screen_applied_once_per_mount_attack AND post_armor_damage_combined_before_screen
                UNION ALL
                SELECT 'space_combat_staged_damage_tables', count(*) FROM information_schema.tables WHERE table_schema='public'
                 AND table_name IN('senc_weapon_damage_attempt','senc_weapon_damage_die','senc_weapon_damage_final_receipt','senc_mount_damage_final_receipt')
                UNION ALL
                SELECT 'space_combat_defense_damage_link_tables', count(*) FROM information_schema.tables WHERE table_schema='public'
                 AND table_name IN('senc_fire_sand_weapon_reduction','senc_screen_mount_reduction')
                UNION ALL
                SELECT 'space_combat_location_roll_tables', count(*) FROM information_schema.tables WHERE table_schema='public'
                 AND table_name IN('senc_damage_location_group_roll','senc_damage_location_roll_set_receipt')
                UNION ALL
                SELECT 'ship_combat_armor_state_columns', count(*) FROM information_schema.columns
                 WHERE table_schema='public' AND table_name='ship_ship' AND column_name='armor_current'
                UNION ALL
                SELECT 'space_combat_system_damage_state_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name='senc_ship_system_damage_state'
                UNION ALL
                SELECT 'space_combat_atomic_location_hit_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name='senc_damage_location_hit_receipt'
                UNION ALL
                SELECT 'space_combat_crew_damage_bands', count(*) FROM rule_space_combat_crew_damage_band
                UNION ALL
                SELECT 'space_combat_crew_damage_roll_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_crew_damage_attempt','senc_crew_damage_outcome_die','senc_crew_damage_outcome_receipt')
                UNION ALL
                SELECT 'space_combat_crew_target_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_crew_damage_population','senc_crew_damage_population_receipt','senc_crew_damage_target','senc_crew_damage_target_receipt','senc_crew_damage_consequence_die','senc_crew_damage_consequence_receipt')
                UNION ALL
                SELECT 'space_combat_crew_application_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('actor_radiation_state','health_radiation_exposure','senc_crew_damage_application_receipt')
                UNION ALL
                SELECT 'space_combat_damage_completion_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name='senc_mount_damage_application_receipt'
                UNION ALL
                SELECT 'space_combat_storage_damage_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('ship_cargo_lot','senc_ship_fuel_leak_state','senc_storage_damage_attempt','senc_storage_damage_die','senc_storage_damage_final_receipt','senc_storage_damage_allocation_receipt')
                UNION ALL
                SELECT 'space_combat_storage_adjudications', count(*) FROM rule_interpretation
                 WHERE decision_register_entry='CE-SC-009'
                UNION ALL
                SELECT 'space_combat_system_enforcement_columns', count(*) FROM information_schema.columns
                 WHERE table_schema='public' AND (table_name,column_name) IN(('senc_sensor_targeting_receipt','sensor_damage_modifier'),('senc_mount_weapon_attack_check','system_damage_modifier'))
                UNION ALL
                SELECT 'space_combat_mdrive_damage_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name='senc_mdrive_thrust_damage_receipt'
                UNION ALL
                SELECT 'space_combat_mdrive_adjudications', count(*) FROM rule_interpretation
                 WHERE decision_register_entry='CE-SC-010'
                UNION ALL
                SELECT 'space_combat_repair_effect_bands', count(*) FROM rule_space_combat_repair_effect_band
                UNION ALL
                SELECT 'space_combat_battlefield_repair_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_system_battlefield_repair_receipt','senc_system_temporary_repair_state','senc_system_repair_expiration_receipt')
                UNION ALL
                SELECT 'space_combat_auto_repair_rules', count(*) FROM rule_space_combat_auto_repair
                UNION ALL
                SELECT 'space_combat_auto_repair_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_repair_drone_round_allocation','senc_auto_repair_attempt','senc_auto_repair_temporary_state','senc_auto_repair_expiration_receipt')
                UNION ALL
                SELECT 'space_combat_auto_repair_adjudications', count(*) FROM rule_interpretation WHERE decision_register_entry='CE-SC-011'
                UNION ALL
                SELECT 'space_combat_weapon_reload_rules', count(*) FROM rule_space_combat_weapon_reload
                UNION ALL
                SELECT 'space_combat_weapon_reload_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_weapon_readiness_state','senc_weapon_ammunition_consumption_receipt','senc_weapon_reload_receipt')
                UNION ALL
                SELECT 'space_combat_missile_range_rows', count(*) FROM rule_space_combat_missile_range
                UNION ALL
                SELECT 'space_combat_missile_effect_bands', count(*) FROM rule_space_combat_missile_launch_effect
                UNION ALL
                SELECT 'space_combat_missile_runtime_tables', count(*) FROM information_schema.tables
                 WHERE table_schema='public' AND table_name IN('senc_missile_launch_receipt','senc_missile_arrival_receipt','senc_missile_arrival_close_receipt','senc_missile_impact_attempt','senc_missile_impact_roll','senc_missile_impact_final_receipt','senc_missile_damage_attempt','senc_missile_damage_die','senc_missile_damage_final_receipt','senc_missile_damage_location_group_roll','senc_missile_damage_location_hit_receipt','senc_nuclear_missile_radiation_hit_receipt','senc_missile_crew_hit_receipt','senc_missile_crew_population','senc_missile_crew_population_receipt','senc_missile_crew_target','senc_missile_crew_target_receipt','senc_missile_crew_consequence_die','senc_missile_crew_consequence_receipt','senc_missile_crew_application_receipt')
                UNION ALL
                SELECT 'space_combat_boarding_planetary_rules', count(*) FROM rule_rule WHERE rule_code IN('combat.space.abstract-boarding','combat.space.planetary-maneuvers')
                UNION ALL
                SELECT 'space_combat_boarding_planetary_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_boarding_operation','senc_boarding_round_receipt','senc_boarding_internal_damage_die','senc_boarding_internal_damage_receipt','senc_boarding_reaction_denial','senc_boarding_damage_location_group_roll','senc_boarding_damage_location_hit_receipt','senc_vessel_planetary_state','senc_planetary_maneuver_receipt')
                UNION ALL
                SELECT 'space_combat_special_weapon_profiles', count(*) FROM rule_space_combat_special_weapon
                UNION ALL
                SELECT 'space_combat_personal_scale_profiles', count(*) FROM rule_space_combat_personal_scale_damage
                UNION ALL
                SELECT 'space_combat_special_scaling_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('senc_special_weapon_radiation_hit_receipt','senc_offensive_sand_damage_receipt','senc_personal_scale_attack_receipt','senc_personal_scale_damage_die','senc_personal_scale_damage_receipt')
                UNION ALL
                SELECT 'environment_acid_rules', count(*) FROM rule_environment_acid
                UNION ALL
                SELECT 'environment_acid_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('actor_environmental_immunity','env_acid_exposure','env_acid_damage_attempt','env_acid_damage_die','env_acid_damage_receipt','env_acid_fume_exposure','env_acid_fume_check_receipt')
                UNION ALL
                SELECT 'environment_carrying_load_bands', count(*) FROM rule_carrying_load_band
                UNION ALL
                SELECT 'environment_carrying_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('actor_encumbrance_state','actor_encumbrance_receipt')
                UNION ALL
                SELECT 'environment_carrying_resolved_issues', count(*) FROM src_issue WHERE issue_code='environment.carrying.maximum-load-example' AND issue_status='resolved'
                UNION ALL
                SELECT 'environment_disease_profiles', count(*) FROM rule_disease_profile
                UNION ALL
                SELECT 'environment_disease_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_disease_case','env_disease_check_receipt')
                UNION ALL
                SELECT 'environment_temperature_bands', count(*) FROM rule_extreme_temperature_band
                UNION ALL
                SELECT 'environment_fire_rules', count(*) FROM rule_catching_fire
                UNION ALL
                SELECT 'environment_temperature_fire_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_temperature_exposure','env_temperature_damage_receipt','env_fire_episode','env_fire_resolution_receipt')
                UNION ALL
                SELECT 'environment_falling_rules', count(*) FROM rule_falling_gravity
                UNION ALL
                SELECT 'environment_falling_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_fall_attempt','env_fall_damage_die','env_fall_damage_receipt')
                UNION ALL
                SELECT 'environment_poison_profiles', count(*) FROM rule_poison_profile
                UNION ALL
                SELECT 'environment_poison_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_poison_attempt','actor_poison_unconscious_state','env_poison_resolution_receipt')
                UNION ALL
                SELECT 'environment_radiation_source_profiles', count(*) FROM rule_radiation_source_profile
                UNION ALL
                SELECT 'environment_radiation_effect_bands', count(*) FROM rule_radiation_effect_band
                UNION ALL
                SELECT 'environment_radiation_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('actor_radiation_state','env_radiation_exposure_attempt','env_radiation_exposure_die','env_radiation_exposure_receipt','env_antiradiation_dose_receipt','env_antiradiation_overdose_die','actor_antiradiation_prophylaxis','health_radiation_recovery_entitlement','env_radiation_sickness_case','env_radiation_sickness_check_receipt')
                UNION ALL
                SELECT 'environment_radiation_resolved_issues', count(*) FROM src_issue WHERE issue_code='environment.radiation.below-mild-wording' AND issue_status='resolved'
                UNION ALL
                SELECT 'environment_deprivation_profiles', count(*) FROM rule_deprivation_profile
                UNION ALL
                SELECT 'environment_deprivation_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_deprivation_episode','env_deprivation_check_receipt','env_deprivation_relief_receipt','health_deprivation_recovery_lock')
                UNION ALL
                SELECT 'environment_suffocation_profiles', count(*) FROM rule_suffocation_profile
                UNION ALL
                SELECT 'environment_suffocation_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_suffocation_episode','env_suffocation_tick_receipt','env_suffocation_relief_receipt')
                UNION ALL
                SELECT 'environment_vacuum_rules', count(*) FROM rule_vacuum_exposure
                UNION ALL
                SELECT 'environment_vacuum_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_vacuum_episode','env_vacuum_check_receipt','env_vacuum_pressure_restoration_receipt')
                UNION ALL
                SELECT 'environment_weather_rules', count(*) FROM rule_weather_effect
                UNION ALL
                SELECT 'environment_weather_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('env_weather_observation','env_weather_task_modifier_receipt')
                UNION ALL
                SELECT 'ship_security_access_profiles', count(*) FROM rule_ship_access_security
                UNION ALL
                SELECT 'ship_security_cybersecurity_tasks', count(*) FROM rule_ship_cybersecurity_task
                UNION ALL
                SELECT 'ship_security_measures', count(*) FROM rule_ship_security_measure
                UNION ALL
                SELECT 'ship_security_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('ship_security_access_point','ship_security_override_receipt')
                UNION ALL
                SELECT 'ship_security_ratings', count(*) FROM rule_ship_security_rating
                UNION ALL
                SELECT 'ship_cybersecurity_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('ship_security_computer_state','ship_security_cyber_attempt')
                UNION ALL
                SELECT 'ship_security_compartment_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('ship_security_compartment','ship_security_measure_receipt','ship_security_vent_strength_receipt','ship_security_vent_suffocation_link')
                UNION ALL
                SELECT 'ship_security_tranq_runtime_tables', count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('ship_security_tranq_episode','ship_security_tranq_exposure','ship_security_tranq_check_receipt','ship_security_tranq_unconscious_state','ship_security_tranq_clear_receipt')
                UNION ALL SELECT 'law_encounter_situations',count(*) FROM rule_law_encounter_situation
                UNION ALL SELECT 'sentencing_crimes',count(*) FROM rule_sentencing_crime
                UNION ALL SELECT 'sentencing_bands',count(*) FROM rule_sentencing_band
                UNION ALL SELECT 'sentencing_consequences',count(*) FROM rule_sentencing_consequence
                UNION ALL SELECT 'starship_revenue_systems',count(*) FROM rule_ship_revenue_system
                UNION ALL SELECT 'starship_charter_rates',count(*) FROM rule_ship_charter_rate
                UNION ALL SELECT 'starship_revenue_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='travel.starship-revenue'
                UNION ALL SELECT 'starship_revenue_availability_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('journey_revenue_availability_cycle','journey_revenue_availability_draw','journey_revenue_availability_receipt')
                UNION ALL SELECT 'starship_revenue_freight_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('ship_cargo_reservation','journey_freight_contract','journey_freight_delivery_receipt','journey_freight_cancellation_receipt','journey_passage_availability_receipt')
                UNION ALL SELECT 'starship_revenue_postal_charter_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('journey_postal_contract','journey_postal_delivery_receipt','journey_postal_cancellation_receipt','journey_starship_charter_quote_receipt','journey_starship_charter_contract','journey_starship_charter_completion_receipt')
                UNION ALL SELECT 'task_assistance_effects',count(*) FROM rule_task_assistance_effect
                UNION ALL SELECT 'task_assistance_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='task.aiding-another'
                UNION ALL SELECT 'task_assistance_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_task_assistance_receipt'
                UNION ALL SELECT 'passage_operations',count(*) FROM rule_passage_operation
                UNION ALL SELECT 'passage_low_revival_rules',count(*) FROM rule_low_passage_revival
                UNION ALL SELECT 'passage_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='travel.ship-passage-operations'
                UNION ALL SELECT 'passage_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('journey_passage_accommodation_assignment','journey_passage_accommodation_release_receipt','journey_passage_manifest_receipt','journey_low_passage_revival_receipt','actor_low_passage_death_state')
                UNION ALL SELECT 'passage_runtime_views',count(*) FROM information_schema.views WHERE table_schema='public' AND table_name='journey_active_passage_accommodation'
                UNION ALL SELECT 'supplier_stock_generation_rules',count(*) FROM rule_supplier_stock_generation
                UNION ALL SELECT 'supplier_stock_generation_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='trade.supplier-stock-generation'
                UNION ALL SELECT 'supplier_stock_generation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('mkt_supplier_stock_generation','mkt_supplier_stock_selection_draw','mkt_supplier_stock_quantity_draw','mkt_supplier_stock_result','mkt_supplier_stock_final_receipt')
                UNION ALL SELECT 'rejected_quote_cooldown_rules',count(*) FROM rule_rejected_quote_cooldown
                UNION ALL SELECT 'rejected_quote_cooldown_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='trade.rejected-quote-cooldown'
                UNION ALL SELECT 'rejected_quote_cooldown_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='mkt_quote_rejection_receipt'
                UNION ALL SELECT 'local_broker_settlement_rules',count(*) FROM rule_local_broker_settlement
                UNION ALL SELECT 'local_broker_settlement_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='trade.local-broker-settlement'
                UNION ALL SELECT 'local_broker_settlement_adjudications',count(*) FROM rule_interpretation interpretation JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code='trade.local-broker-settlement' AND interpretation.decision_register_entry='CE-TRADE-001'
                UNION ALL SELECT 'local_broker_settlement_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('mkt_local_broker_engagement','mkt_local_broker_negotiation_receipt')
                UNION ALL SELECT 'world_generation_rules',count(*) FROM rule_rule WHERE rule_code IN('world.subsector-star-mapping','world.uwp-generation','world.system-details-generation','world.travel-zone-classification')
                UNION ALL SELECT 'world_generation_provenance',count(*) FROM src_record_provenance provenance JOIN rule_rule rule USING(rule_id) WHERE rule.rule_code IN('world.subsector-star-mapping','world.uwp-generation','world.system-details-generation','world.travel-zone-classification')
                UNION ALL SELECT 'world_generation_rule_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('rule_world_hex_density','rule_world_generation_component','rule_world_generation_modifier','rule_world_generation_modifier_condition','rule_world_starport_band','rule_world_starport_technology_modifier','rule_world_technology_minimum','rule_world_technology_minimum_condition','rule_world_system_detail_procedure','rule_world_base_eligibility','rule_world_amber_candidate_condition')
                UNION ALL SELECT 'world_generation_density_rows',count(*) FROM rule_world_hex_density
                UNION ALL SELECT 'world_generation_component_rows',count(*) FROM rule_world_generation_component
                UNION ALL SELECT 'world_generation_modifier_rows',count(*) FROM rule_world_generation_modifier
                UNION ALL SELECT 'world_generation_modifier_condition_rows',count(*) FROM rule_world_generation_modifier_condition
                UNION ALL SELECT 'world_generation_starport_band_rows',count(*) FROM rule_world_starport_band
                UNION ALL SELECT 'world_generation_starport_tech_rows',count(*) FROM rule_world_starport_technology_modifier
                UNION ALL SELECT 'world_generation_tech_minimum_rows',count(*) FROM rule_world_technology_minimum
                UNION ALL SELECT 'world_generation_tech_condition_rows',count(*) FROM rule_world_technology_minimum_condition
                UNION ALL SELECT 'world_generation_system_procedure_rows',count(*) FROM rule_world_system_detail_procedure
                UNION ALL SELECT 'world_generation_base_rows',count(*) FROM rule_world_base_eligibility
                UNION ALL SELECT 'world_generation_amber_rows',count(*) FROM rule_world_amber_candidate_condition
                UNION ALL SELECT 'world_generation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('loc_hex_generation_receipt','loc_world_generation_receipt','loc_world_generation_final_receipt','loc_world_system_detail_receipt','loc_world_travel_zone_event','loc_world_generation_completion_receipt')
                UNION ALL SELECT 'world_generation_runtime_views',count(*) FROM information_schema.views WHERE table_schema='public' AND table_name IN('loc_world_current_travel_zone','loc_generated_world_summary')
                UNION ALL SELECT 'wilderness_generation_rules',count(*) FROM rule_rule WHERE rule_code IN('encounter.wilderness-animal-generation','encounter.wilderness-table-generation','encounter.wilderness-occurrence')
                UNION ALL SELECT 'wilderness_generation_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code IN('encounter.wilderness-animal-generation','encounter.wilderness-table-generation','encounter.wilderness-occurrence')
                UNION ALL SELECT 'wilderness_generation_rule_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('rule_animal_terrain','rule_animal_terrain_movement','rule_animal_subtype_band','rule_animal_subtype_generation','rule_animal_subtype_skill','rule_animal_size_band','rule_animal_number_appearing','rule_animal_damage_band','rule_animal_weapon_band','rule_animal_weapon','rule_animal_armor_band','rule_wilderness_encounter_template')
                UNION ALL SELECT 'wilderness_terrain_rows',count(*) FROM rule_animal_terrain
                UNION ALL SELECT 'wilderness_movement_rows',count(*) FROM rule_animal_terrain_movement
                UNION ALL SELECT 'wilderness_subtype_band_rows',count(*) FROM rule_animal_subtype_band
                UNION ALL SELECT 'wilderness_subtype_skill_rows',count(*) FROM rule_animal_subtype_skill
                UNION ALL SELECT 'wilderness_size_band_rows',count(*) FROM rule_animal_size_band
                UNION ALL SELECT 'wilderness_generation_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('camp_animal_definition','camp_animal_definition_skill','camp_animal_definition_skill_source','camp_animal_definition_weapon','cmd_animal_generation_receipt','camp_wilderness_encounter_table','camp_wilderness_encounter_entry','cmd_wilderness_table_finalization_receipt','enc_wilderness_occurrence_receipt')
                UNION ALL SELECT 'wilderness_generation_runtime_views',count(*) FROM information_schema.views WHERE table_schema='public' AND table_name IN('camp_generated_animal_summary','camp_wilderness_encounter_table_summary')
                UNION ALL SELECT 'starship_subtype_rules',count(*) FROM rule_rule WHERE rule_code='encounter.starship-subtype-resolution'
                UNION ALL SELECT 'starship_subtype_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='encounter.starship-subtype-resolution'
                UNION ALL SELECT 'starship_subtype_rule_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('rule_starship_encounter_subtable','rule_starship_encounter_result','rule_starship_encounter_subtype_roll','rule_starship_encounter_effect')
                UNION ALL SELECT 'starship_subtype_subtables',count(*) FROM rule_starship_encounter_subtable
                UNION ALL SELECT 'starship_subtype_results',count(*) FROM rule_starship_encounter_result
                UNION ALL SELECT 'starship_subtype_rolls',count(*) FROM rule_starship_encounter_subtype_roll
                UNION ALL SELECT 'starship_subtype_paired_rolls',count(*) FROM(SELECT p.subtable_code,p.roll_total FROM src_starship_encounter_subtype_roll_provenance p JOIN src_locator l USING(source_locator_id) JOIN src_work w USING(source_work_id) GROUP BY p.subtable_code,p.roll_total HAVING count(DISTINCT w.work_code)=2) paired
                UNION ALL SELECT 'starship_subtype_effects',count(*) FROM rule_starship_encounter_effect
                UNION ALL SELECT 'starship_subtype_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('cmd_starship_subtype_draw','cmd_starship_subtype_resolution_receipt')
                UNION ALL SELECT 'starship_subtype_runtime_views',count(*) FROM information_schema.views WHERE table_schema='public' AND table_name='enc_starship_contact_resolution'
                UNION ALL SELECT 'starship_combat_handoff_rules',count(*) FROM rule_rule WHERE rule_code='encounter.starship-combat-handoff'
                UNION ALL SELECT 'starship_combat_handoff_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='encounter.starship-combat-handoff'
                UNION ALL SELECT 'starship_combat_handoff_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_starship_combat_handoff_receipt'
                UNION ALL SELECT 'social_content_rules',count(*) FROM rule_rule WHERE rule_code IN('encounter.patron-role-table','encounter.rumor-content-table')
                UNION ALL SELECT 'social_content_rule_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code IN('encounter.patron-role-table','encounter.rumor-content-table')
                UNION ALL SELECT 'social_content_catalogue_rows',(SELECT count(*) FROM rule_patron_role_roll)+(SELECT count(*) FROM rule_rumor_content_roll)
                UNION ALL SELECT 'social_content_paired_rows',(SELECT count(*) FROM src_patron_role_roll_provenance)+(SELECT count(*) FROM src_rumor_content_roll_provenance)
                UNION ALL SELECT 'social_content_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='cmd_social_content_selection_receipt'
                UNION ALL SELECT 'social_content_runtime_views',count(*) FROM information_schema.views WHERE table_schema='public' AND table_name='enc_social_content_selection'
                UNION ALL SELECT 'reusable_patron_format_rules',count(*) FROM rule_rule WHERE rule_code='encounter.reusable-patron-format'
                UNION ALL SELECT 'reusable_patron_format_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='encounter.reusable-patron-format'
                UNION ALL SELECT 'reusable_patron_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('camp_patron_brief','camp_patron_brief_revision','camp_patron_requirement','camp_patron_truth_variant','camp_patron_npc_objective','cmd_patron_brief_receipt')
                UNION ALL SELECT 'structured_scene_rules',count(*) FROM rule_rule WHERE rule_code='referee.structured-scene-preparation'
                UNION ALL SELECT 'structured_scene_provenance',count(*) FROM src_record_provenance p JOIN rule_rule r USING(rule_id) WHERE r.rule_code='referee.structured-scene-preparation'
                UNION ALL SELECT 'structured_scene_templates',count(*) FROM rule_scene_template
                UNION ALL SELECT 'structured_scene_slots',count(*) FROM rule_scene_template_slot
                UNION ALL SELECT 'structured_scene_runtime_tables',count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN('camp_scene_snapshot','camp_scene_fact','cmd_scene_snapshot_receipt')
                UNION ALL
                SELECT 'modified_price_bands', count(*)
                  FROM rule_modified_price_band
                UNION ALL
                SELECT 'starport_traffic_rows', count(*)
                  FROM rule_starport_traffic_expression
                """
            ).fetchall()
        )
        expect(
            catalogue_counts
            == {
                "rules": 1087,
                "characteristics": 7,
                "modifier_bands": 12,
                "skills": 74,
                "cascade_skills": 8,
                "specialty_links": 36,
                "check_systems": 1,
                "difficulties": 7,
                "effect_bands": 4,
                "time_frames": 9,
                "task_adjustments": 3,
                "law_mappings": 5,
                "general_task_context_runtime_columns": 10,
                "characteristic_only_task_skill_nullable": 1,
                "bribery_offense_rules": 4,
                "bribery_offense_provenance": 8,
                "bribery_runtime_tables": 3,
                "gambling_house_rules": 6,
                "gambling_house_provenance": 12,
                "gambling_house_runtime_tables": 1,
                "competitive_gambling_rules": 1,
                "competitive_gambling_provenance": 2,
                "competitive_gambling_runtime_tables": 3,
                "leadership_coordination_rules": 1,
                "leadership_coordination_provenance": 2,
                "leadership_coordination_runtime_tables": 4,
                "leadership_task_columns": 2,
                "space_combat_coordinate_crew_rules": 1,
                "space_combat_sensor_targeting_rules": 1,
                "space_combat_crew_roles": 8,
                "space_combat_attack_range_rows": 42,
                "space_combat_attack_weapon_profiles": 9,
                "space_combat_mount_attack_runtime_tables": 2,
                "space_combat_damage_bands": 12,
                "space_combat_hit_locations": 11,
                "space_combat_location_effects": 52,
                "space_combat_damage_grouping_rules": 1,
                "space_combat_staged_damage_tables": 4,
                "space_combat_defense_damage_link_tables": 2,
                "space_combat_location_roll_tables": 2,
                "ship_combat_armor_state_columns": 1,
                "space_combat_system_damage_state_tables": 1,
                "space_combat_atomic_location_hit_tables": 1,
                "space_combat_crew_damage_bands": 10,
                "space_combat_crew_damage_roll_tables": 3,
                "space_combat_crew_target_tables": 6,
                "space_combat_crew_application_tables": 3,
                "space_combat_damage_completion_tables": 1,
                "space_combat_storage_damage_tables": 6,
                "space_combat_storage_adjudications": 1,
                "space_combat_system_enforcement_columns": 2,
                "space_combat_mdrive_damage_tables": 1,
                "space_combat_mdrive_adjudications": 1,
                "space_combat_repair_effect_bands": 3,
                "space_combat_battlefield_repair_tables": 3,
                "space_combat_auto_repair_rules": 1,
                "space_combat_auto_repair_tables": 4,
                "space_combat_auto_repair_adjudications": 1,
                "space_combat_weapon_reload_rules": 1,
                "space_combat_weapon_reload_tables": 3,
                "space_combat_missile_range_rows": 7,
                "space_combat_missile_effect_bands": 5,
                "space_combat_missile_runtime_tables": 20,
                "space_combat_boarding_planetary_rules": 2,
                "space_combat_boarding_planetary_tables": 9,
                "space_combat_special_weapon_profiles": 5,
                "space_combat_personal_scale_profiles": 10,
                "space_combat_special_scaling_tables": 5,
                "environment_acid_rules": 1,
                "environment_acid_runtime_tables": 7,
                "environment_carrying_load_bands": 4,
                "environment_carrying_runtime_tables": 2,
                "environment_carrying_resolved_issues": 1,
                "environment_disease_profiles": 4,
                "environment_disease_runtime_tables": 2,
                "environment_temperature_bands": 11,
                "environment_fire_rules": 1,
                "environment_temperature_fire_runtime_tables": 4,
                "environment_falling_rules": 1,
                "environment_falling_runtime_tables": 3,
                "environment_poison_profiles": 3,
                "environment_poison_runtime_tables": 3,
                "environment_radiation_source_profiles": 8,
                "environment_radiation_effect_bands": 5,
                "environment_radiation_runtime_tables": 10,
                "environment_radiation_resolved_issues": 1,
                "environment_deprivation_profiles": 2,
                "environment_deprivation_runtime_tables": 4,
                "environment_suffocation_profiles": 2,
                "environment_suffocation_runtime_tables": 3,
                "environment_vacuum_rules": 1,
                "environment_vacuum_runtime_tables": 3,
                "environment_weather_rules": 1,
                "environment_weather_runtime_tables": 2,
                "ship_security_access_profiles": 4,
                "ship_security_cybersecurity_tasks": 4,
                "ship_security_measures": 4,
                "ship_security_runtime_tables": 2,
                "ship_security_ratings": 4,
                "ship_cybersecurity_runtime_tables": 2,
                "ship_security_compartment_runtime_tables": 4,
                "ship_security_tranq_runtime_tables": 5,
                "law_encounter_situations": 8,
                "sentencing_crimes": 6,
                "sentencing_bands": 9,
                "sentencing_consequences": 15,
                "starship_revenue_systems": 1,
                "starship_charter_rates": 2,
                "starship_revenue_provenance": 10,
                "starship_revenue_availability_tables": 3,
                "starship_revenue_freight_tables": 5,
                "starship_revenue_postal_charter_tables": 6,
                "task_assistance_effects": 4,
                "task_assistance_provenance": 2,
                "task_assistance_runtime_tables": 1,
                "passage_operations": 5,
                "passage_low_revival_rules": 1,
                "passage_provenance": 12,
                "passage_runtime_tables": 5,
                "passage_runtime_views": 1,
                "supplier_stock_generation_rules": 1,
                "supplier_stock_generation_provenance": 3,
                "supplier_stock_generation_runtime_tables": 5,
                "rejected_quote_cooldown_rules": 1,
                "rejected_quote_cooldown_provenance": 4,
                "rejected_quote_cooldown_runtime_tables": 1,
                "local_broker_settlement_rules": 1,
                "local_broker_settlement_provenance": 2,
                "local_broker_settlement_adjudications": 1,
                "local_broker_settlement_runtime_tables": 2,
                "world_generation_rules": 4,
                "world_generation_provenance": 30,
                "world_generation_rule_tables": 11,
                "world_generation_density_rows": 4,
                "world_generation_component_rows": 8,
                "world_generation_modifier_rows": 23,
                "world_generation_modifier_condition_rows": 24,
                "world_generation_starport_band_rows": 6,
                "world_generation_starport_tech_rows": 6,
                "world_generation_tech_minimum_rows": 4,
                "world_generation_tech_condition_rows": 11,
                "world_generation_system_procedure_rows": 1,
                "world_generation_base_rows": 11,
                "world_generation_amber_rows": 6,
                "world_generation_runtime_tables": 6,
                "world_generation_runtime_views": 2,
                "wilderness_generation_rules": 3,
                "wilderness_generation_provenance": 8,
                "wilderness_generation_rule_tables": 12,
                "wilderness_terrain_rows": 16,
                "wilderness_movement_rows": 96,
                "wilderness_subtype_band_rows": 52,
                "wilderness_subtype_skill_rows": 7,
                "wilderness_size_band_rows": 20,
                "wilderness_generation_runtime_tables": 9,
                "wilderness_generation_runtime_views": 2,
                "starship_subtype_rules": 1,
                "starship_subtype_provenance": 2,
                "starship_subtype_rule_tables": 4,
                "starship_subtype_subtables": 11,
                "starship_subtype_results": 60,
                "starship_subtype_rolls": 66,
                "starship_subtype_paired_rolls": 66,
                "starship_subtype_effects": 4,
                "starship_subtype_runtime_tables": 2,
                "starship_subtype_runtime_views": 1,
                "starship_combat_handoff_rules": 1,
                "starship_combat_handoff_provenance": 2,
                "starship_combat_handoff_runtime_tables": 1,
                "social_content_rules": 2,
                "social_content_rule_provenance": 4,
                "social_content_catalogue_rows": 72,
                "social_content_paired_rows": 144,
                "social_content_runtime_tables": 1,
                "social_content_runtime_views": 1,
                "reusable_patron_format_rules": 1,
                "reusable_patron_format_provenance": 2,
                "reusable_patron_runtime_tables": 6,
                "structured_scene_rules": 1,
                "structured_scene_provenance": 2,
                "structured_scene_templates": 8,
                "structured_scene_slots": 32,
                "structured_scene_runtime_tables": 3,
                "jack_of_all_trades_rules": 1,
                "jack_of_all_trades_provenance": 2,
                "jack_of_all_trades_task_columns": 3,
                "liaison_negotiation_rules": 1,
                "liaison_negotiation_provenance": 2,
                "liaison_negotiation_runtime_tables": 3,
                "computer_basic_use_rules": 1,
                "computer_basic_operations": 4,
                "computer_basic_use_provenance": 2,
                "computer_basic_operation_runtime_tables": 1,
                "trade_work_policies": 1,
                "trade_work_skills": 4,
                "trade_work_provenance": 4,
                "trade_work_runtime_tables": 3,
                "linguistics_rules": 1,
                "linguistics_provenance": 2,
                "linguistics_runtime_tables": 4,
                "navigation_rules": 1,
                "navigation_provenance": 2,
                "navigation_runtime_tables": 2,
                "recon_rules": 6,
                "recon_provenance": 2,
                "recon_runtime_tables": 1,
                "streetwise_rules": 5,
                "streetwise_provenance": 2,
                "streetwise_runtime_tables": 1,
                "regulatory_rules": 6,
                "regulatory_skill_links": 7,
                "regulatory_provenance": 4,
                "regulatory_runtime_tables": 1,
                "steward_services": 6,
                "steward_provenance": 2,
                "steward_runtime_tables": 1,
                "survival_operations": 10,
                "survival_provenance": 2,
                "survival_runtime_tables": 1,
                "transport_capabilities": 11,
                "transport_provenance": 22,
                "transport_runtime_tables": 1,
                "device_operations": 10,
                "device_operation_provenance": 6,
                "device_operation_runtime_tables": 1,
                "animal_skill_operations": 13,
                "animal_skill_operation_provenance": 6,
                "animal_skill_operation_runtime_tables": 1,
                "broker_operations": 4,
                "broker_operation_provenance": 4,
                "carousing_influence_rules": 1,
                "carousing_influence_provenance": 4,
                "broker_carousing_runtime_tables": 2,
                "spacecraft_journey_execution_rules": 1,
                "spacecraft_journey_execution_provenance": 2,
                "spacecraft_journey_execution_runtime_tables": 3,
                "range_bands": 7,
                "attack_profiles": 9,
                "items": 217,
                "ammunition_variants": 20,
                "psionic_talents": 5,
                "psionic_powers": 26,
                "psionic_range_bands": 10,
                "careers": 24,
                "career_assignments": 0,
                "career_systems": 1,
                "career_draft_rows": 6,
                "species": 6,
                "species_traits": 33,
                "species_trait_assignments": 23,
                "species_characteristic_overrides": 7,
                "species_physical_formulas": 3,
                "species_skill_grants": 3,
                "encounter_types": 8,
                "attitudes": 5,
                "animal_subtypes": 15,
                "animal_reactions": 30,
                "starship_categories": 10,
                "world_sizes": 11,
                "world_atmospheres": 16,
                "world_trade_codes": 18,
                "trade_goods": 42,
                "trade_good_modifiers": 140,
                "ship_crew_positions": 9,
                "ship_operating_costs": 17,
                "ship_hull_designs": 36,
                "ship_configurations": 3,
                "ship_armor_designs": 3,
                "ship_armor_options": 3,
                "ship_bridge_bands": 4,
                "ship_computers": 7,
                "ship_computer_options": 2,
                "ship_software": 5,
                "ship_electronics": 5,
                "ship_drive_designs": 45,
                "ship_drive_performance": 449,
                "ship_power_fuel_rows": 48,
                "ship_component_definitions": 23,
                "ship_hangar_options": 12,
                "ship_weapon_mounts": 6,
                "ship_weapon_definitions": 9,
                "ship_missiles": 3,
                "ship_screens": 2,
                "ship_sand_ammunition": 1,
                "standard_ship_classes": 24,
                "ship_class_drives": 64,
                "ship_class_weapon_mount_groups": 25,
                "ship_class_mount_weapon_slots": 63,
                "ship_class_source_assertions": 9,
                "ship_published_drive_conflicts": 0,
                "ship_class_components": 122,
                "ship_class_hangars": 23,
                "ship_class_carried_craft_rows": 14,
                "ship_class_carried_craft_count": 60,
                "ship_class_carried_items": 2,
                "ship_armament_declarations": 24,
                "ship_structurally_complete": 24,
                "ship_unresolved_source_assertions": 0,
                "ship_construction_receipts": 39,
                "ship_finalized_construction_receipts": 39,
                "ship_construction_lines": 738,
                "ship_reconciled_construction_receipts": 5,
                "ship_source_gap_construction_receipts": 1,
                "ship_tonnage_variance_receipts": 0,
                "ship_cost_variance_receipts": 18,
                "ship_current_construction_receipts": 24,
                "ship_construction_variances": 34,
                "ship_armor_proration_conflicts": 4,
                "ship_effective_cost_adjudications": 18,
                "open_source_issues": 0,
                "high_priority_source_issues": 0,
                "construction_variance_issues": 31,
                "ship_assertion_issues": 4,
                "legacy_issue_comparisons": 65,
                "vehicle_component_definitions": 77,
                "vehicle_electronics_ranges": 6,
                "vehicle_control_systems": 5,
                "vehicle_drone_controllers": 5,
                "vehicle_robot_brains": 3,
                "vehicle_autopilot_introductions": 3,
                "vehicle_communication_systems": 4,
                "vehicle_communicator_types": 3,
                "vehicle_sensor_packages": 5,
                "vehicle_sensor_capabilities": 5,
                "vehicle_sensor_capability_links": 16,
                "vehicle_computers": 6,
                "vehicle_computer_options": 1,
                "vehicle_accommodations": 12,
                "vehicle_life_support_systems": 2,
                "vehicle_life_support_inclusions": 2,
                "vehicle_sailing_crew_formulas": 1,
                "vehicle_component_formulas": 9,
                "vehicle_cargo_trailer_rules": 1,
                "vehicle_cargo_trailer_models": 6,
                "vehicle_cranes": 3,
                "vehicle_galleys": 2,
                "vehicle_mobility_components": 2,
                "vehicle_manipulator_arms": 1,
                "vehicle_manipulator_limits": 4,
                "vehicle_cargo_arms": 1,
                "vehicle_liquid_cannons": 1,
                "vehicle_operating_theaters": 1,
                "vehicle_refueling_rates": 2,
                "vehicle_sampler_bonuses": 4,
                "vehicle_emergency_low_berths": 1,
                "vehicle_fire_extinguisher_regulations": 1,
                "vehicle_holding_tank_contents": 2,
                "vehicle_research_lab_bonuses": 3,
                "vehicle_research_lab_disciplines": 6,
                "vehicle_liquid_cannon_purposes": 3,
                "vehicle_configurations": 2,
                "vehicle_configuration_cover_rows": 4,
                "vehicle_design_categories": 11,
                "vehicle_propulsion_category_rows": 34,
                "vehicle_configuration_options": 11,
                "vehicle_configuration_option_categories": 10,
                "vehicle_configuration_price_combinations": 2,
                "vehicle_environmental_hazards": 8,
                "vehicle_environmental_protections": 4,
                "vehicle_environmental_protection_hazards": 23,
                "vehicle_configuration_option_inclusions": 2,
                "vehicle_submersible_depth_rows": 6,
                "vehicle_submersible_world_adjustments": 1,
                "vehicle_submersible_depth_upgrades": 1,
                "vehicle_drive_options": 10,
                "vehicle_drive_option_categories": 6,
                "vehicle_drive_adjustment_options": 4,
                "vehicle_secondary_drive_options": 1,
                "vehicle_extra_contact_elements": 2,
                "vehicle_jump_jet_options": 1,
                "vehicle_off_road_options": 1,
                "vehicle_tilt_rotor_jet_options": 1,
                "vehicle_weapon_point_formulas": 1,
                "vehicle_gun_ports": 1,
                "vehicle_gun_port_weapons": 24,
                "vehicle_weapon_mounts": 5,
                "vehicle_gun_shields": 1,
                "vehicle_gun_shield_mounts": 4,
                "vehicle_turrets": 2,
                "vehicle_coaxial_mount_formulas": 1,
                "vehicle_pop_up_turrets": 1,
                "vehicle_armament_options": 5,
                "vehicle_armament_option_families": 5,
                "vehicle_armament_option_scopes": 3,
                "vehicle_armament_option_incompatibilities": 1,
                "vehicle_weapon_target_ranges": 10,
                "vehicle_weapon_range_profiles": 13,
                "vehicle_weapon_range_difficulties": 73,
                "vehicle_weapon_families": 19,
                "vehicle_weapon_definitions": 76,
                "vehicle_weapon_special_rules": 3,
                "vehicle_weapon_family_special_rules": 5,
                "vehicle_weapon_ammunition_rows": 11,
                "vehicle_ordnance_bays": 2,
                "vehicle_ordnance_bay_formulas": 1,
                "vehicle_ordnance_definitions": 12,
                "vehicle_missile_guidance_types": 8,
                "vehicle_missiles": 10,
                "vehicle_anti_missile_resolutions": 1,
                "vehicle_anti_missile_systems": 9,
                "vehicle_anti_missile_guidance_claims": 7,
                "vehicle_alien_design_assumptions": 1,
                "vehicle_lift_envelope_rules": 1,
                "vehicle_lift_media": 3,
                "vehicle_lift_atmosphere_rows": 4,
                "vehicle_aircraft_environment_rules": 2,
                "vehicle_missile_impact_times": 9,
                "vehicle_missile_launch_skills": 2,
                "vehicle_missile_launch_effects": 5,
                "vehicle_animal_power_rules": 1,
                "vehicle_animal_gaits": 4,
                "vehicle_draft_animal_profiles": 5,
                "vehicle_wind_sailing_speeds": 3,
                "vehicle_off_road_movement_rules": 2,
                "vehicle_ship_scale_hulls": 4,
                "vehicle_ship_scale_power_plants": 4,
                "vehicle_ship_scale_propulsions": 4,
                "vehicle_class_components": 106,
                "vehicle_class_configuration_options": 11,
                "vehicle_class_drive_options": 3,
                "vehicle_class_autopilots": 10,
                "vehicle_class_computer_options": 3,
                "vehicle_class_fuel_tanks": 19,
                "vehicle_class_alternative_communications": 2,
                "vehicle_construction_receipts": 36,
                "vehicle_construction_lines": 537,
                "vehicle_construction_variances": 10,
                "vehicle_personal_combat_rules": 1,
                "vehicle_occupant_protection_rules": 3,
                "vehicle_weapon_arc_rules": 2,
                "vehicle_collision_rules": 1,
                "vehicle_combat_actions": 5,
                "vehicle_combat_rule_provenance": 18,
                "vehicle_damage_rules": 1,
                "vehicle_damage_bands": 12,
                "vehicle_damage_band_packets": 16,
                "vehicle_excess_damage_packets": 2,
                "vehicle_hit_locations": 12,
                "vehicle_hit_location_rolls": 33,
                "vehicle_hit_location_options": 35,
                "vehicle_system_hit_stages": 14,
                "vehicle_location_overflows": 10,
                "vehicle_explosion_zones": 2,
                "vehicle_repair_categories": 3,
                "vehicle_system_repair_states": 2,
                "vehicle_damage_repair_provenance": 10,
                "vehicle_encounter_tables": 16,
                "vehicle_attack_receipt_tables": 3,
                "vehicle_damage_application_tables": 3,
                "vehicle_repair_history_tables": 4,
                "vehicle_classes_relational_complete": 20,
                "vehicle_classes_relational_incomplete": 0,
                "encounter_aggregate_state_tables": 5,
                "personal_burst_sizes": 5,
                "personal_burst_options": 2,
                "weapon_burst_capabilities": 7,
                "personal_burst_provenance": 14,
                "personal_suppression_procedures": 1,
                "personal_suppression_immunities": 5,
                "personal_suppression_provenance": 12,
                "personal_panic_procedures": 1,
                "personal_panic_weapons": 12,
                "personal_panic_provenance": 2,
                "personal_shotgun_spread_rules": 1,
                "personal_shotgun_spread_capabilities": 1,
                "personal_shotgun_spread_provenance": 4,
                "personal_communication_methods": 6,
                "personal_initiative_support_rules": 2,
                "personal_comms_support_provenance": 16,
                "personal_battlefield_conditions": 6,
                "personal_battlefield_sensors": 8,
                "personal_conditions_sensor_provenance": 28,
                "personal_blind_fire_rules": 1,
                "personal_blind_fire_provenance": 2,
                "personal_explosion_rules": 1,
                "personal_explosion_provenance": 2,
                "personal_extreme_range_rules": 1,
                "personal_extreme_range_provenance": 2,
                "personal_zero_gravity_rules": 1,
                "personal_zero_gravity_provenance": 2,
                "personal_firing_into_combat_rules": 1,
                "personal_firing_into_combat_provenance": 2,
                "personal_grapple_rules": 1,
                "personal_grapple_options": 7,
                "personal_grapple_provenance": 2,
                "personal_thrown_weapon_rules": 1,
                "personal_thrown_capabilities": 1,
                "personal_thrown_weapon_provenance": 2,
                "personal_coup_de_grace_rules": 1,
                "personal_coup_de_grace_provenance": 2,
                "personal_coup_de_grace_runtime_tables": 1,
                "personal_extended_action_rules": 1,
                "personal_extended_action_provenance": 2,
                "personal_extended_action_runtime_tables": 3,
                "personal_free_action_rules": 1,
                "personal_free_action_examples": 3,
                "personal_free_action_provenance": 2,
                "personal_free_action_runtime_tables": 1,
                "personal_starting_range_contexts": 3,
                "personal_starting_range_options": 4,
                "personal_starting_range_light_caps": 3,
                "personal_starting_range_provenance": 2,
                "personal_starting_range_runtime_tables": 1,
                "personal_weapon_ready_rules": 1,
                "personal_weapon_ready_profiles": 0,
                "personal_weapon_ready_provenance": 2,
                "personal_weapon_ready_runtime_tables": 1,
                "personal_weapon_assistance_runtime_tables": 1,
                "personal_stance_change_rules": 1,
                "personal_stance_change_provenance": 2,
                "personal_miscellaneous_action_rules": 2,
                "personal_miscellaneous_action_provenance": 4,
                "personal_miscellaneous_action_runtime_tables": 1,
                "personal_reaction_option_rules": 2,
                "personal_reaction_option_provenance": 4,
                "personal_conflict_avoidance_rules": 1,
                "personal_conflict_avoidance_provenance": 2,
                "personal_combat_resolution_runtime_tables": 1,
                "gameplay_skill_training_rules": 1,
                "gameplay_skill_training_provenance": 2,
                "gameplay_skill_training_runtime_tables": 2,
                "personal_fatigue_rules": 1,
                "personal_unconsciousness_rules": 1,
                "personal_condition_provenance": 4,
                "personal_natural_healing_rules": 1,
                "personal_natural_healing_provenance": 2,
                "personal_medical_treatment_rules": 1,
                "personal_medical_treatment_provenance": 2,
                "personal_mental_healing_rules": 1,
                "personal_mental_healing_characteristics": 2,
                "personal_mental_healing_provenance": 2,
                "ground_force_starship_rules": 1,
                "ground_force_starship_contributions": 1,
                "ground_force_starship_provenance": 2,
                "ground_force_starship_runtime_tables": 5,
                "personal_armor_catalogue_rules": 1,
                "personal_armor_profiles": 9,
                "personal_armor_provenance": 20,
                "personal_armor_source_issues": 3,
                "personal_armor_degradation_rules": 1,
                "personal_armor_layer_exceptions": 1,
                "personal_armor_characteristic_modifiers": 2,
                "personal_armor_life_support_rules": 4,
                "personal_armor_direct_protections": 13,
                "personal_armor_effective_protections": 20,
                "personal_armor_mechanic_provenance": 24,
                "personal_armor_runtime_tables": 5,
                "personal_communicator_usage_rules": 1,
                "personal_communicator_profiles": 4,
                "personal_communicator_tl_profiles": 7,
                "personal_communicator_provenance": 10,
                "personal_computer_profiles": 17,
                "personal_computer_form_factors": 2,
                "personal_computer_provenance": 36,
                "personal_computer_source_issues": 1,
                "personal_computer_options": 2,
                "personal_computer_specialization_rules": 1,
                "personal_computer_option_provenance": 6,
                "personal_software_families": 9,
                "personal_software_profiles": 25,
                "personal_software_provenance": 20,
                "personal_software_security_mappings": 4,
                "personal_software_ai_capabilities": 3,
                "personal_software_expert_characteristics": 2,
                "personal_software_mechanic_tables": 10,
                "personal_drugs": 9,
                "personal_drug_provenance": 20,
                "anagathic_availability_rules": 1,
                "personal_combat_drug_effects": 2,
                "personal_antiradiation_rules": 1,
                "personal_stim_rules": 1,
                "personal_support_drug_rules": 5,
                "personal_explosives": 3,
                "personal_explosive_provenance": 8,
                "personal_explosive_use_rules": 1,
                "personal_devices": 12,
                "personal_device_provenance": 26,
                "personal_device_capabilities": 24,
                "personal_device_skill_links": 6,
                "personal_hologram_upgrades": 2,
                "personal_robot_drone_frameworks": 1,
                "personal_robot_drone_kinds": 2,
                "personal_robot_drone_chassis": 7,
                "personal_robot_drone_chassis_provenance": 18,
                "personal_robot_drone_systems": 17,
                "personal_robot_drone_programs": 13,
                "personal_robot_drone_weapons": 5,
                "personal_robot_drone_mobility": 1,
                "personal_combat_drone_operations": 1,
                "personal_robot_drone_options": 3,
                "personal_robot_drone_option_provenance": 6,
                "personal_sensory_aids": 8,
                "personal_sensory_aid_provenance": 18,
                "personal_sensory_aid_capabilities": 7,
                "personal_sensory_aid_light_modes": 8,
                "personal_binocular_upgrades": 2,
                "personal_shelters": 6,
                "personal_shelter_capabilities": 6,
                "personal_modular_shelter_geometry": 2,
                "personal_shelter_provenance": 14,
                "personal_survival_equipment": 12,
                "personal_survival_equipment_provenance": 26,
                "personal_survival_capabilities": 12,
                "personal_survival_atmosphere_links": 16,
                "personal_survival_skill_links": 2,
                "personal_tools": 8,
                "personal_tool_operations": 14,
                "personal_tool_law_prices": 1,
                "personal_tool_provenance": 18,
                "book1_vehicle_profiles": 16,
                "book1_vehicle_occupancy": 32,
                "book1_vehicle_weapon_summaries": 16,
                "book1_vehicle_provenance": 34,
                "book1_vehicle_capabilities": 16,
                "book1_grav_belt_batteries": 2,
                "book1_afv_laser_rules": 1,
                "book1_vehicle_options": 8,
                "book1_vehicle_option_inclusions": 4,
                "book1_vehicle_option_provenance": 16,
                "book1_melee_attacks": 12,
                "book1_melee_attack_modes": 14,
                "book1_melee_damage_types": 12,
                "book1_melee_provenance": 24,
                "book1_melee_capabilities": 11,
                "book1_melee_length_profiles": 10,
                "book1_melee_two_handed": 3,
                "book1_melee_capability_provenance": 22,
                "book1_ranged_fire_profiles": 18,
                "book1_ranged_ammunition_variants": 19,
                "book1_ranged_ammunition_source_rows": 18,
                "book1_ranged_capabilities": 18,
                "book1_crossbow_reload_profiles": 3,
                "book1_ranged_mode_switches": 1,
                "book1_revolver_reload_choices": 1,
                "book1_ammunition_compatibilities": 3,
                "book1_ranged_weapon_options": 10,
                "book1_ranged_weapon_option_effects": 10,
                "book1_ranged_weapon_option_upgrades": 2,
                "book1_ranged_weapon_option_provenance": 20,
                "book1_grenades": 4,
                "book1_grenade_delivery_modes": 8,
                "book1_frag_damage_bands": 3,
                "book1_grenade_field_effects": 2,
                "book1_stun_grenade_effects": 1,
                "book1_grenade_provenance": 8,
                "book1_heavy_weapons": 5,
                "book1_heavy_fire_profiles": 5,
                "book1_heavy_ammunition": 5,
                "book1_heavy_provenance": 20,
                "book1_heavy_capabilities": 5,
                "book1_rocket_impacts": 1,
                "psionic_training_rules": 1,
                "psionic_awareness_suspension_rules": 1,
                "psionic_awareness_enhancement_rules": 2,
                "psionic_awareness_regeneration_rules": 1,
                "psionic_awareness_regeneration_characteristics": 3,
                "psionic_awareness_runtime_tables": 8,
                "psionic_awareness_runtime_views": 2,
                "psionic_clairvoyance_power_rules": 4,
                "psionic_clairvoyance_runtime_tables": 1,
                "psionic_telekinesis_system_rules": 1,
                "psionic_telekinesis_mass_profiles": 6,
                "psionic_telekinesis_runtime_tables": 1,
                "psionic_telekinetic_throw_tables": 1,
                "psionic_life_detection_rules": 1,
                "psionic_life_detection_tables": 2,
                "psionic_telempathy_rules": 1,
                "psionic_telempathy_tables": 1,
                "psionic_surface_thought_rules": 1,
                "psionic_surface_thought_tables": 1,
                "psionic_send_thought_rules": 1,
                "psionic_sent_thought_tables": 1,
                "psionic_probe_rules": 2,
                "psionic_probe_tables": 2,
                "psionic_assault_rules": 1,
                "psionic_assault_runtime_tables": 1,
                "psionic_shield_rules": 1,
                "psionic_shield_runtime_tables": 2,
                "psionic_teleportation_system_rules": 1,
                "psionic_teleportation_power_rules": 4,
                "psionic_teleportation_disorientation_rules": 1,
                "psionic_teleportation_runtime_tables": 1,
                "personal_drug_source_issues": 2,
                "vehicle_class_armament_missiles": 1,
                "vehicle_class_armament_ordnance": 1,
                "vehicle_class_ammunition_loads": 3,
                "vehicle_class_missile_loads": 1,
                "vehicle_class_ordnance_loads": 1,
                "vehicle_class_weapon_point_summaries": 4,
                "vehicle_class_armament_mounts": 8,
                "vehicle_class_armament_weapons": 7,
                "vehicle_class_armament_gun_shields": 1,
                "vehicle_chassis": 24,
                "vehicle_armor": 7,
                "vehicle_power_plants": 10,
                "vehicle_propulsion_types": 16,
                "vehicle_drives": 24,
                "vehicle_drive_performance": 292,
                "vehicle_propulsion_speeds": 90,
                "vehicle_drive_fuel_requirements": 24,
                "vehicle_power_plant_fuels": 11,
                "standard_vehicle_classes": 20,
                "space_range_bands": 8,
                "space_combat_actions": 30,
                "space_combat_turn_order_procedures": 1,
                "space_combat_initiative_rules": 1,
                "space_combat_range_check_rules": 1,
                "space_combat_increase_initiative_rules": 1,
                "space_combat_pursuit_rules": 1,
                "space_combat_evasive_maneuver_rules": 1,
                "space_combat_line_up_shot_rules": 1,
                "space_combat_docking_rules": 1,
                "space_combat_ram_rules": 1,
                "space_combat_pilot_movement_rules": 1,
                "space_combat_avoid_collision_rules": 1,
                "space_combat_reaction_system_rules": 1,
                "space_combat_dodge_rules": 1,
                "space_combat_fire_sand_rules": 1,
                "space_combat_point_defense_rules": 1,
                "space_combat_trigger_screen_rules": 1,
                "modified_price_bands": 15,
                "starport_traffic_rows": 24,
            },
            f"Foundation catalogue counts changed: {catalogue_counts}",
        )
        core_check = connection.execute(
            """SELECT dice_count, die_sides, target_number,
                      natural_min_auto_failure, natural_max_auto_success
               FROM rule_check_system"""
        ).fetchone()
        expect(
            core_check == (2, 6, 8, False, False),
            f"Core check changed: {core_check}",
        )
        difficulties = connection.execute(
            """SELECT rule.name, difficulty.modifier, difficulty.is_default
               FROM rule_difficulty difficulty
               JOIN rule_rule rule ON rule.rule_id = difficulty.rule_id
               ORDER BY difficulty.display_order"""
        ).fetchall()
        expect(
            difficulties == [
                ("Simple", 6, False), ("Easy", 4, False),
                ("Routine", 2, False), ("Average", 0, True),
                ("Difficult", -2, False), ("Very Difficult", -4, False),
                ("Formidable", -6, False),
            ],
            f"Difficulty ladder changed: {difficulties}",
        )
        context = connection.execute(
            """SELECT
                 (SELECT exact_increment_seconds FROM rule_time_frame tf
                  JOIN rule_rule r ON r.rule_id=tf.rule_id
                  WHERE r.rule_code='time-frame.months'),
                 (SELECT count(*) FROM src_law_level_difficulty_provenance),
                 (SELECT count(*) FROM rule_law_level_difficulty
                  WHERE maximum_law_level IS NULL)"""
        ).fetchone()
        expect(
            context == (None, 10, 1),
            f"Task-context fidelity changed: {context}",
        )
        combat_slice = connection.execute(
            """SELECT
                 (SELECT count(*) FROM combat_attack_profile_difficulty),
                 (SELECT count(*) FROM src_attack_profile_difficulty_provenance),
                 (SELECT count(*) FROM inv_weapon_attack_mode),
                 (SELECT count(*) FROM src_weapon_attack_mode_provenance),
                 (SELECT general_armor_rating FROM inv_armor_definition a
                  JOIN rule_rule r ON r.rule_id=a.item_rule_id
                  WHERE r.rule_code='equipment.armor.jack'),
                 (SELECT damage_dice_count FROM inv_weapon_definition w
                  JOIN rule_rule r ON r.rule_id=w.item_rule_id
                  WHERE r.rule_code='equipment.weapon.dagger')"""
        ).fetchone()
        expect(
            combat_slice == (63, 112, 32, 40, 3, 1),
            f"Combat slice changed: {combat_slice}",
        )
        psionics_slice = connection.execute(
            """SELECT
                 (SELECT count(*) FROM psi_talent_range_cost),
                 (SELECT count(*) FROM src_psi_talent_range_cost_provenance),
                 (SELECT count(*) FROM psi_power_targeting),
                 (SELECT failed_activation_cost FROM psi_system),
                 (SELECT recovery_delay_hours FROM psi_system),
                 (SELECT recovery_points_per_hour FROM psi_system),
                 (SELECT combat_action_kind FROM psi_system),
                 (SELECT array_agg(power_code ORDER BY power_code)
                    FROM psi_power WHERE NOT mechanics_complete),
                 (SELECT maximum_metres FROM psi_range_band band
                    JOIN rule_rule rule
                      ON rule.rule_id=band.range_band_rule_id
                   WHERE rule.rule_code='psionics.range.very-distant'),
                 (SELECT minimum_metres FROM psi_range_band band
                    JOIN rule_rule rule
                      ON rule.rule_id=band.range_band_rule_id
                   WHERE rule.rule_code='psionics.range.regional')"""
        ).fetchone()
        expect(
            psionics_slice == (
                40, 80, 26, 1, 3, 1, "significant", None,
                500000, 50000,
            ),
            f"Psionics catalogue changed: {psionics_slice}",
        )
        career_slice = connection.execute(
            """SELECT
                 (SELECT count(*) FROM rule_career_progression),
                 (SELECT count(*) FROM rule_career_rank),
                 (SELECT count(*) FROM rule_career_training_entry),
                 (SELECT count(*) FROM rule_career_benefit),
                 (SELECT count(*) FROM src_career_progression_provenance),
                 (SELECT count(*) FROM src_career_rank_provenance),
                 (SELECT count(*) FROM src_career_training_entry_provenance),
                 (SELECT count(*) FROM src_career_benefit_provenance),
                 (SELECT count(*) FROM src_career_draft_roll_provenance),
                 (SELECT starting_age_years FROM rule_career_system),
                 (SELECT term_years FROM rule_career_system),
                 (SELECT retirement_terms FROM rule_career_system),
                 (SELECT previous_career_qualification_modifier
                    FROM rule_career_system),
                 (SELECT draft_uses_allowed FROM rule_career_system),
                 (SELECT count(*) FROM (
                    SELECT career_progression_id
                      FROM src_career_progression_provenance
                     WHERE provenance_class='fills_source_gap'
                    UNION ALL
                    SELECT career_rank_id FROM src_career_rank_provenance
                     WHERE provenance_class='fills_source_gap'
                    UNION ALL
                    SELECT career_training_entry_id
                      FROM src_career_training_entry_provenance
                     WHERE provenance_class='fills_source_gap'
                    UNION ALL
                    SELECT career_benefit_id FROM src_career_benefit_provenance
                     WHERE provenance_class='fills_source_gap'
                 ) source_gaps)"""
        ).fetchone()
        expect(
            career_slice == (
                24, 168, 576, 336, 30, 210, 720, 420,
                12, 18, 4, 7, -2, 1, 828,
            ),
            f"Career catalogue changed: {career_slice}",
        )
        unresolved_career_outcomes = connection.execute(
            """SELECT source_outcome_text,count(*)
               FROM rule_career_training_entry
               WHERE outcome_kind='text'
               GROUP BY source_outcome_text
               UNION ALL
               SELECT source_grant_text,count(*)
               FROM rule_career_rank
               WHERE source_grant_text IS NOT NULL
                 AND granted_skill_rule_id IS NULL
               GROUP BY source_grant_text
               ORDER BY 1"""
        ).fetchall()
        expect(
            unresolved_career_outcomes
            == [("Liaision-1", 1), ("Perception", 1), ("Prospecting", 2)],
            "Unexpected unresolved career outcomes: "
            f"{unresolved_career_outcomes}",
        )
        damage_rules = connection.execute(
            """SELECT add_attack_effect,armor_reduces_damage,
                      exceptional_effect_threshold,
                      exceptional_minimum_damage,
                      overflow_player_choice,subsequent_player_choice
               FROM rule_personal_damage_system"""
        ).fetchone()
        expect(
            damage_rules == (True, True, 6, 1, True, True),
            f"Personal damage rules changed: {damage_rules}",
        )
        outcomes = connection.execute(
            """SELECT outcome_code,trigger_metric,threshold_count
               FROM rule_health_outcome ORDER BY threshold_count,outcome_code"""
        ).fetchall()
        expect(
            len(outcomes) == 4
            and ("wounded", "physical_characteristics_damaged", 1) in outcomes
            and ("dead", "physical_characteristics_at_zero", 3) in outcomes,
            f"Health outcomes changed: {outcomes}",
        )
        attitudes = connection.execute(
            """SELECT attitude_code FROM rule_attitude ORDER BY source_order"""
        ).fetchall()
        expect(
            attitudes == [("hostile",), ("unfriendly",), ("indifferent",),
                          ("friendly",), ("helpful",)],
            f"Attitude order changed: {attitudes}",
        )
        influence = connection.execute(
            """SELECT d.modifier,i.success_shift,
                      i.exceptional_success_shift,i.failure_shift,
                      i.exceptional_failure_shift,
                      i.usual_attempts_per_scene,
                      i.can_force_player_character
               FROM rule_attitude_influence_system i
               JOIN rule_difficulty d ON d.rule_id=i.difficulty_rule_id"""
        ).fetchone()
        expect(
            influence == (-2, 1, 2, 0, -1, 1, False),
            f"Attitude influence changed: {influence}",
        )
        animal_specials = connection.execute(
            """SELECT s.subtype_code,c.outcome,c.condition_kind,c.threshold,
                      c.alternate_threshold
               FROM rule_animal_reaction_condition c
               JOIN rule_animal_subtype s ON s.rule_id=c.subtype_rule_id
               WHERE s.subtype_code IN ('chaser','pouncer','hunter')
               ORDER BY s.subtype_code,c.outcome"""
        ).fetchall()
        expect(
            ("chaser", "attack", "outnumbers_characters", None, None)
            in animal_specials
            and ("pouncer", "flee", "is_surprised", None, None)
            in animal_specials
            and ("hunter", "attack", "size_dependent_roll", 6, 10)
            in animal_specials,
            f"Animal special reactions changed: {animal_specials}",
        )
        animal_provenance = connection.execute(
            "SELECT count(*) FROM src_animal_reaction_condition_provenance"
        ).fetchone()[0]
        expect(
            animal_provenance == 60,
            f"Animal reaction provenance changed: {animal_provenance}",
        )
        starship_system = connection.execute(
            """SELECT occurrence_dice_count,occurrence_die_sides,
                      occurrence_target,type_dice_count,type_die_sides,
                      deep_space_initial_range,near_planet_initial_range,
                      failed_comms_moves_one_category_closer,
                      active_transponder_detection_modifier
               FROM rule_starship_encounter_system"""
        ).fetchone()
        expect(
            starship_system == (1, 6, 6, 2, 6, "very_long", "medium", True, 4),
            f"Starship encounter system changed: {starship_system}",
        )
        starship_rolls = connection.execute(
            """SELECT count(*),count(*) FILTER (WHERE referee_choice)
               FROM rule_starship_encounter_roll"""
        ).fetchone()
        expect(
            starship_rolls == (11, 1),
            f"Starship encounter rolls changed: {starship_rolls}",
        )
        starship_provenance = connection.execute(
            "SELECT count(*) FROM src_starship_encounter_roll_provenance"
        ).fetchone()[0]
        expect(
            starship_provenance == 22,
            f"Starship roll provenance changed: {starship_provenance}",
        )
        combat_procedure = connection.execute(
            """SELECT p.round_seconds,p.initiative_dice_count,
                      p.initiative_die_sides,p.aware_unopposed_base,
                      p.initiative_descending,p.exact_tie_simultaneous,
                      p.initiative_rerolled_each_round,
                      e.significant_actions,e.minor_actions_with_significant,
                      e.minor_actions_without_significant,
                      r.initiative_cost_per_reaction,
                      r.check_modifier_per_reaction,r.maximum_per_round,
                      r.maximum_per_attack,r.requires_awareness,
                      attack.consumes_significant_action,
                      attack.target_declared_before_reaction,
                      attack.reaction_before_attack_check,
                      attack.damage_after_successful_check,
                      hasten.initiative_modifier,hasten.check_modifier,
                      hasten.maximum_per_round,
                      hasten.lasts_current_round_only,
                      hasten.declared_at_round_start,
                      delay.may_act_later_in_round,
                      delay.may_interrupt_action,
                      delay.initiative_becomes_action_count,
                      delay.may_forfeit_for_first_next_round,
                      delay.next_round_initiative_above_current_first,
                      aim.minor_actions_per_step,aim.modifier_per_step,
                      aim.maximum_modifier,aim.requires_same_target,
                      aim.lost_on_other_action
               FROM rule_personal_combat_procedure p
               CROSS JOIN rule_personal_action_economy e
               CROSS JOIN rule_personal_reaction_system r
               CROSS JOIN rule_personal_attack_sequence attack
               CROSS JOIN rule_personal_hasten hasten
               CROSS JOIN rule_personal_delay delay
               CROSS JOIN rule_personal_aim aim"""
        ).fetchone()
        expect(
            combat_procedure
            == (6, 2, 6, 12, True, True, False, 1, 1, 3,
                -2, -1, None, 1, True, True, True, True, True,
                2, -1, 1, True, True, True, True, True, True, 1,
                1, 1, 6, True, True),
            f"Personal combat procedure changed: {combat_procedure}",
        )

        burst_fire = connection.execute(
            """SELECT size.rounds_consumed,size.attack_modifier,
                      size.extra_damage_dice,size.extra_damage_flat
               FROM rule_personal_burst_size size
               ORDER BY size.rounds_consumed"""
        ).fetchall()
        expect(
            burst_fire
            == [(3, 1, 0, 1), (4, 1, 1, 0), (10, 2, 2, 0),
                (20, 3, 3, 0), (100, 4, 4, 0)],
            f"Published burst-fire table changed: {burst_fire}",
        )
        suppression = connection.execute(
            """SELECT attack_modifier,ammunition_multiplier,check_modifier,
                      duration_rounds,initiative_penalty_uses_effect,
                      highest_effect_only,requires_intervening_action
               FROM rule_personal_suppression_fire"""
        ).fetchall()
        expect(
            suppression == [(-2, 2, -1, 1, True, True, True)],
            f"Published suppression-fire procedure changed: {suppression}",
        )
        immunities = connection.execute(
            """SELECT immunity_code FROM rule_personal_suppression_immunity
               ORDER BY immunity_code"""
        ).fetchall()
        expect(
            [row[0] for row in immunities] == [
                "full-battle-dress", "mechanical-android", "suicidal",
                "vehicle-enclosed", "zealot",
            ],
            f"Published suppression immunities changed: {immunities}",
        )
        panic = connection.execute(
            """SELECT panic.attack_modifier,panic.consumes_all_remaining,
                      panic.damage_only_burst_fire,panic.tier_selection_code,
                      interpretation.interpretation_type,
                      interpretation.decision_register_entry
               FROM rule_personal_panic_fire panic
               JOIN rule_interpretation interpretation
                 ON interpretation.rule_id=panic.rule_id"""
        ).fetchall()
        expect(
            panic == [(
                -2, True, True, "greatest-not-exceeding",
                "agreed_interpretation", "CE-COMBAT-001",
            )],
            f"Published Panic Fire adjudication changed: {panic}",
        )
        shotgun_spread = connection.execute(
            """SELECT spread.attack_modifier,spread.damage_dice,
                      spread.affects_personal_range_bystanders,
                      spread.shared_attack_roll,spread.shared_damage_roll,
                      spread.armor_resolved_individually,
                      interpretation.interpretation_type,
                      interpretation.decision_register_entry
               FROM rule_personal_shotgun_spread spread
               JOIN rule_interpretation interpretation
                 ON interpretation.rule_id=spread.rule_id"""
        ).fetchall()
        expect(
            shotgun_spread == [(
                1, 2, True, True, True, True,
                "agreed_interpretation", "CE-COMBAT-002",
            )],
            f"Published Shotgun Spread adjudication changed: {shotgun_spread}",
        )
        communication = connection.execute(
            """SELECT method_code,can_be_jammed,can_be_blocked,
                      requires_line_of_sight,penetrates_smoke_aerosols,
                      forbidden_while_moving
               FROM rule_personal_communication_method
               ORDER BY method_code"""
        ).fetchall()
        expect(
            communication == [
                ("direct", False, False, False, False, False),
                ("hardlink", False, False, False, False, False),
                ("laser", False, True, True, False, False),
                ("maser", False, True, True, True, False),
                ("meson", False, False, False, True, True),
                ("radio", True, True, False, False, False),
            ],
            f"Published communication methods changed: {communication}",
        )
        initiative_support = connection.execute(
            """SELECT support.support_code,support.affects_whole_unit,
                      support.consumes_significant_action,
                      interpretation.decision_register_entry
               FROM rule_personal_initiative_support support
               JOIN rule_interpretation interpretation
                 ON interpretation.rule_id=support.rule_id
               ORDER BY support.support_code"""
        ).fetchall()
        expect(
            initiative_support == [
                ("leadership", False, True, "CE-COMBAT-003"),
                ("tactics", True, False, "CE-COMBAT-003"),
            ],
            f"Published initiative support changed: {initiative_support}",
        )
        battlefield_conditions = connection.execute(
            """SELECT condition_code,ranged_attack_modifier,
                      doubled_for_laser_weapons,sensor_avoidable
               FROM rule_personal_battlefield_condition
               ORDER BY condition_code"""
        ).fetchall()
        expect(
            battlefield_conditions == [
                ("complete-darkness", -4, False, True),
                ("extreme-weather-interference", -1, False, False),
                ("extreme-weather-visibility", -1, False, True),
                ("low-light", -1, False, True),
                ("smoke", -1, True, True),
                ("thick-smoke", -2, True, True),
            ],
            f"Published battlefield conditions changed: {battlefield_conditions}",
        )
        targeting_sensors = connection.execute(
            """SELECT sensor_code,qualifies_for_weather_visibility
               FROM rule_personal_battlefield_sensor
               ORDER BY sensor_code"""
        ).fetchall()
        expect(
            targeting_sensors == [
                ("bioscanner", False), ("densitometer", True),
                ("electromagnetic-detector", False), ("infra-red", True),
                ("laser-assisted-targeting", True),
                ("light-intensification", True), ("motion-sensor", True),
                ("neural-activity-sensor", True),
            ],
            f"Published sensor qualification changed: {targeting_sensors}",
        )
        condition_interpretation = connection.execute(
            """SELECT interpretation.interpretation_type,
                      interpretation.decision_register_entry
               FROM rule_interpretation interpretation
               JOIN rule_rule rule USING (rule_id)
               WHERE rule.rule_code=
                 'combat.battlefield-condition.extreme-weather-visibility'"""
        ).fetchall()
        expect(
            condition_interpretation == [
                ("agreed_interpretation", "CE-COMBAT-004")],
            "Battlefield sensor qualification ruling changed: "
            f"{condition_interpretation}",
        )
        blind_fire = connection.execute(
            """SELECT blind.effective_skill_level,
                      blind.attack_dice_rolled,
                      blind.highest_attack_die_removed,
                      blind.random_target_after_success,
                      blind.permits_friendly_targets,
                      interpretation.decision_register_entry
               FROM rule_personal_blind_fire blind
               JOIN rule_interpretation interpretation
                 ON interpretation.rule_id=blind.rule_id"""
        ).fetchall()
        expect(
            blind_fire == [(0, 3, True, True, True, "CE-COMBAT-005")],
            f"Published Blind Firing adjudication changed: {blind_fire}",
        )
        explosions = connection.execute(
            """SELECT explosion.shared_damage_roll,
                      explosion.dodge_reduction_dice,
                      explosion.dive_divisor,explosion.dive_rounding,
                      explosion.reduction_before_armor,
                      explosion.dive_ends_prone,
                      explosion.dive_loses_significant_actions,
                      interpretation.decision_register_entry
                 FROM rule_personal_explosion explosion
                 JOIN rule_interpretation interpretation
                   ON interpretation.rule_id=explosion.rule_id"""
        ).fetchall()
        expect(
            explosions == [
                (True, 1, 2, "down", True, True, 1, "CE-COMBAT-006")],
            f"Published Explosions adjudication changed: {explosions}",
        )
        extreme_range = connection.execute(
            """SELECT range_rule.rule_code,
                      extreme.additional_attack_modifier,
                      extreme.minimum_skill_level,
                      extreme.requires_line_of_sight,
                      extreme.requires_stationary_firer,
                      extreme.requires_firing_rest,
                      extreme.vehicle_requires_stationary,
                      extreme.energy_damage_divisor,
                      extreme.energy_damage_rounding,
                      extreme.permits_kill_aim,
                      interpretation.decision_register_entry
                 FROM rule_personal_extreme_range extreme
                 JOIN rule_rule range_rule
                   ON range_rule.rule_id=extreme.base_range_rule_id
                 JOIN rule_interpretation interpretation
                   ON interpretation.rule_id=extreme.rule_id"""
        ).fetchall()
        expect(
            extreme_range == [(
                "combat.range.distant", -2, 3, True, True, True, True,
                2, "up", True, "CE-COMBAT-007")],
            f"Published Extreme Range adjudication changed: {extreme_range}",
        )
        zero_gravity = connection.execute(
            """SELECT skill.rule_code,zero.missing_zero_g_uses_untrained,
                      zero.skill_cap_uses_lower,zero.recoil_attack_modifier,
                      interpretation.decision_register_entry
               FROM rule_personal_zero_gravity_combat zero
               JOIN rule_rule skill ON skill.rule_id=zero.zero_g_skill_rule_id
               JOIN rule_interpretation interpretation
                 ON interpretation.rule_id=zero.rule_id"""
        ).fetchall()
        expect(
            zero_gravity == [
                ("skill.zero-g",True,True,-2,"CE-COMBAT-008")],
            f"Published Zero Gravity adjudication changed: {zero_gravity}",
        )

        under_sourced_rules = connection.execute(
            """
            SELECT rule.rule_code, count(DISTINCT locator.source_work_id)
            FROM rule_rule rule
            JOIN src_record_provenance provenance
              ON provenance.rule_id = rule.rule_id
            JOIN src_locator locator
              ON locator.source_locator_id = provenance.source_locator_id
            GROUP BY rule.rule_id, rule.rule_code
            HAVING count(DISTINCT locator.source_work_id) < 2
               AND count(*) FILTER (
                       WHERE provenance.provenance_class='fills_source_gap'
                   )=0
            """
        ).fetchall()
        expect(
            under_sourced_rules == [],
            f"Rules lack paired-source provenance: {under_sourced_rules}",
        )

        under_sourced_bands = connection.execute(
            """
            SELECT band.source_order, count(DISTINCT locator.source_work_id)
            FROM rule_characteristic_modifier_band band
            JOIN src_characteristic_modifier_band_provenance provenance
              ON provenance.characteristic_modifier_band_id =
                 band.characteristic_modifier_band_id
            JOIN src_locator locator
              ON locator.source_locator_id = provenance.source_locator_id
            GROUP BY band.characteristic_modifier_band_id, band.source_order
            HAVING count(DISTINCT locator.source_work_id) < 2
            """
        ).fetchall()
        expect(
            under_sourced_bands == [],
            f"Modifier bands lack paired-source provenance: {under_sourced_bands}",
        )

        specialty_source_counts = connection.execute(
            """
            SELECT parent.rule_code, specialty.rule_code,
                   count(DISTINCT locator.source_work_id)
            FROM rule_skill_specialty relation
            JOIN rule_rule parent
              ON parent.rule_id = relation.parent_skill_rule_id
            JOIN rule_rule specialty
              ON specialty.rule_id = relation.specialty_rule_id
            JOIN src_skill_specialty_provenance provenance
              ON provenance.parent_skill_rule_id = relation.parent_skill_rule_id
             AND provenance.specialty_rule_id = relation.specialty_rule_id
            JOIN src_locator locator
              ON locator.source_locator_id = provenance.source_locator_id
            GROUP BY parent.rule_code, specialty.rule_code
            ORDER BY parent.rule_code, specialty.rule_code
            """
        ).fetchall()
        gaps = [
            row
            for row in specialty_source_counts
            if row[2] < 2
        ]
        expect(
            gaps == [("skill.aircraft", "skill.airship", 1)],
            f"Unexpected specialty source gaps: {gaps}",
        )
        gap_classification = connection.execute(
            """
            SELECT provenance.provenance_class, work.work_code
            FROM src_skill_specialty_provenance provenance
            JOIN rule_rule parent
              ON parent.rule_id = provenance.parent_skill_rule_id
            JOIN rule_rule specialty
              ON specialty.rule_id = provenance.specialty_rule_id
            JOIN src_locator locator
              ON locator.source_locator_id = provenance.source_locator_id
            JOIN src_work work ON work.source_work_id = locator.source_work_id
            WHERE parent.rule_code = 'skill.aircraft'
              AND specialty.rule_code = 'skill.airship'
            """
        ).fetchall()
        expect(
            gap_classification
            == [("fills_source_gap", "cepheus-engine.github-v9.1")],
            f"Aircraft/Airship gap classification changed: {gap_classification}",
        )
        adjudication = connection.execute(
            """
            SELECT concordance.concordance_status,
                   concordance.comparison_method,
                   concordance.reviewed_by,
                   concordance.evidence_summary
            FROM src_concordance concordance
            JOIN src_locator left_locator
              ON left_locator.source_locator_id =
                 concordance.left_locator_id
            JOIN src_locator right_locator
              ON right_locator.source_locator_id =
                 concordance.right_locator_id
            WHERE left_locator.anchor = 'aircraft-specialty-airship'
              AND right_locator.anchor = 'aircraft'
            """
        ).fetchone()
        expect(
            adjudication is not None
            and adjudication[0:3]
            == ("left_only", "manual source adjudication", "Raymond")
            and "GitHub v9.1 correctly includes Airship" in adjudication[3],
            f"Aircraft/Airship adjudication missing or changed: {adjudication}",
        )

        coverage_report = ROOT / "CEPHEUS_SOURCE_COVERAGE.md"
        expect(coverage_report.exists(), "Source coverage report is missing.")
        expect(
            coverage_report.read_text(encoding="utf-8")
            == build_report(connection),
            "Source coverage report is stale; regenerate it from the database.",
        )

        package_id = connection.execute(
            """
            SELECT content_package_id
            FROM sys_content_package
            WHERE package_code = 'cepheus-engine'
              AND package_version = '9.1-draft'
            """
        ).fetchone()[0]

        overlap_rejected = False
        try:
            with connection.transaction():
                rule_id = connection.execute(
                    """
                    INSERT INTO rule_rule (
                        content_package_id, rule_code, name, rule_category
                    ) VALUES (%s, 'verify.strength', 'Verification Strength',
                              'characteristic')
                    RETURNING rule_id
                    """,
                    (package_id,),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO rule_characteristic (
                        rule_id, abbreviation, display_order
                    ) VALUES (%s, 'VStr', 1)
                    """,
                    (rule_id,),
                )
                connection.execute(
                    """
                    INSERT INTO rule_characteristic_modifier_band (
                        content_package_id, characteristic_rule_id,
                        minimum_score, maximum_score, modifier, source_order
                    ) VALUES
                        (%s, %s, 0, 2, -2, 0),
                        (%s, %s, 2, 5, -1, 1)
                    """,
                    (package_id, rule_id, package_id, rule_id),
                )
        except ExclusionViolation:
            overlap_rejected = True
            connection.rollback()
        expect(overlap_rejected, "Overlapping modifier bands were not rejected.")

    print(
        "verified migrations, paired sources, catalogue counts, provenance, "
        "JSON and prose boundaries, and modifier-band exclusion constraint"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
