"""Build a complete Base Cepheus database from an empty PostgreSQL database.

Schema migrations and reviewed catalogue importers have historical dependency
boundaries. This command makes those boundaries explicit and reproducible.
It refuses to operate on a database that already contains public relations.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[1]

BOOTSTRAP_PHASES: tuple[tuple[int | None, tuple[str, ...]], ...] = (
    (
        8,
        (
            "import_foundation_rules.py",
            "import_task_resolution.py",
            "import_task_context.py",
        ),
    ),
    (15, ("import_combat_slice.py",)),
    (16, ("import_encounter_rules.py",)),
    (19, ("import_animal_reactions.py",)),
    (21, ("import_starship_encounters.py",)),
    (36, ("import_personal_combat_procedure.py",)),
    (38, ("import_ranged_weapons.py",)),
    (41, ("import_psionics.py",)),
    (44, ("import_careers.py",)),
    (187, ("import_personal_burst_fire.py",)),
    (188, ("import_personal_suppression_fire.py",)),
    (189, ("import_personal_panic_fire.py",)),
    (190, ("import_personal_shotgun_spread.py",)),
    (191, ("import_personal_comms_tactics.py",)),
    (192, ("import_personal_battlefield_conditions.py",)),
    (193, ("import_personal_blind_fire.py",)),
    (197, ("import_personal_explosions.py",)),
    (198, ("import_personal_extreme_range.py",)),
    (201, ("import_personal_zero_gravity.py",)),
    (203, ("import_personal_firing_into_combat.py",)),
    (206, ("import_personal_grappling.py",)),
    (209, ("import_personal_thrown_weapons.py",)),
    (211, ("import_personal_fatigue_unconsciousness.py",)),
    (214, ("import_personal_injury_natural_healing.py",)),
    (218, ("import_personal_medical_treatment.py",)),
    (221, ("import_personal_mental_healing.py",)),
    (223, ("import_ground_force_starship_scale.py",)),
    (227, ("import_personal_armor_catalogue.py",)),
    (228, ("import_personal_armor_capabilities.py",)),
    (233, ("import_personal_communicators.py",)),
    (234, ("import_personal_computer_hardware.py",)),
    (235, ("import_personal_computer_options.py",)),
    (236, ()),
    (237, ("import_personal_computer_software.py",)),
    (238, ()),
    (239, ("import_personal_software_mechanics.py",)),
    (240, ("import_personal_drugs.py",)),
    (241, ("import_personal_combat_drugs.py",)),
    (242, ("import_personal_support_drugs.py",)),
    (243, ("import_personal_explosives.py",)),
    (244, ("import_personal_devices.py",)),
    (245, ("import_personal_device_capabilities.py",)),
    (246, ("import_personal_robot_drone_framework.py",)),
    (247, ("import_personal_robot_drone_chassis.py",)),
    (248, ("import_personal_robot_drone_loadouts.py",)),
    (249, ("import_personal_robot_drone_options.py",)),
    (250, ()),
    (251, ("import_personal_sensory_aids.py",)),
    (252, ("import_personal_sensory_aid_capabilities.py",)),
    (253, ("import_personal_shelters.py",)),
    (254, ("import_personal_survival_equipment.py",)),
    (255, ("import_personal_survival_equipment_capabilities.py",)),
    (256, ("import_personal_tools.py",)),
    (257, ("import_book1_vehicle_catalogue.py",)),
    (258, ("import_book1_vehicle_capabilities.py",)),
    (259, ("import_book1_vehicle_options.py",)),
    (261, ("import_book1_melee_weapons.py",)),
    (262, ("import_book1_melee_weapon_capabilities.py",)),
    (263, ("import_book1_ranged_reconciliation.py",)),
    (264, ("import_book1_ranged_weapon_capabilities.py",)),
    (265, ("import_book1_ranged_weapon_options.py",)),
    (266, ("import_book1_grenades.py",)),
    (267, ("import_book1_heavy_weapons.py",)),
    (268, ("import_book1_heavy_weapon_capabilities.py",)),
    (269, ("import_psionic_training.py",)),
    (270, ("import_psionic_awareness_mechanics.py",)),
    (271, ()),
    (272, ()),
    (273, ("import_psionic_clairvoyance_mechanics.py",)),
    (274, ("import_psionic_telekinesis_mechanics.py",)),
    (275, ()),
    (276, ()),
    (277, ("import_psionic_life_detection.py",)),
    (278, ("import_psionic_telempathy.py",)),
    (279, ("import_psionic_read_surface_thoughts.py",)),
    (280, ("import_psionic_send_thoughts.py",)),
    (281, ("import_psionic_probe.py",)),
    (282, ("import_psionic_assault_mechanics.py",)),
    (283, ()),
    (284, ()),
    (285, ()),
    (286, ()),
    (287, ("import_psionic_shield.py",)),
    (288, ("import_psionic_teleportation_mechanics.py",)),
    (289, ()),
    (290, ()),
    (291, ("import_personal_coup_de_grace.py",)),
    (292, ()),
    (293, ("import_personal_extended_actions.py",)),
    (294, ()),
    (295, ("import_personal_free_actions.py",)),
    (296, ()),
    (297, ("import_personal_starting_range.py",)),
    (298, ()),
    (299, ()),
    (300, ("import_personal_weapon_readying.py",)),
    (301, ()),
    (302, ()),
    (303, ()),
    (304, ("import_personal_stance_change.py",)),
    (305, ("import_personal_miscellaneous_actions.py",)),
    (306, ()),
    (307, ("import_personal_dodge_parry.py",)),
    (308, ("import_personal_conflict_avoidance.py",)),
    (309, ("import_gameplay_skill_training.py",)),
    (310, ()),
    (311, ()),
    (312, ()),
    (313, ()),
    (314, ()),
    (315, ("import_bribery_rules.py",)),
    (316, ()),
    (317, ()),
    (318, ("import_gambling_house_rules.py",)),
    (319, ()),
    (320, ()),
    (321, ("import_gambling_competitive_rules.py",)),
    (322, ()),
    (323, ()),
    (324, ()),
    (325, ("import_leadership_coordination.py",)),
    (326, ()),
    (327, ()),
    (328, ()),
    (329, ("import_jack_of_all_trades.py",)),
    (330, ()),
    (331, ()),
    (332, ()),
    (333, ("import_liaison_negotiation.py",)),
    (334, ()),
    (335, ()),
    (336, ("import_computer_basic_operations.py",)),
    (337, ()),
    (338, ()),
    (339, ("import_trade_work.py",)),
    (340, ()),
    (341, ()),
    (342, ("import_linguistics.py",)),
    (343, ()),
    (344, ()),
    (345, ()),
    (346, ()),
    (347, ("import_navigation.py",)),
    (348, ()),
    (349, ()),
    (350, ("import_recon.py",)),
    (351, ()),
    (352, ()),
    (353, ("import_streetwise.py",)),
    (354, ()),
    (355, ()),
    (356, ("import_regulatory_skills.py",)),
    (357, ()),
    (358, ()),
    (359, ("import_steward.py",)),
    (360, ()),
    (361, ()),
    (362, ("import_survival_skill.py",)),
    (363, ()),
    (364, ()),
    (365, ("import_transport_operations.py",)),
    (366, ()),
    (367, ()),
    (368, ("import_device_operations.py",)),
    (369, ()),
    (370, ()),
    (371, ("import_animal_skill_operations.py",)),
    (372, ()),
    (373, ()),
    (374, ("import_broker_carousing.py",)),
    (375, ()),
    (376, ()),
    (377, ("import_spacecraft_journey_execution.py",)),
    (378, ()),
    (379, ()),
    (380, ()),
    (381, ()),
    (382, ()),
    (383, ()),
    (384, ()),
    (None, ()),
)


def public_relations(connection: psycopg.Connection) -> list[str]:
    """Return relations that prove an Emporos schema already exists.

    Managed databases can place service-owned objects in ``public``. Those
    objects must not make a fresh, dedicated Emporos database look populated.
    """
    return [
        row[0]
        for row in connection.execute(
            """SELECT c.relname
               FROM pg_class c
               JOIN pg_namespace n ON n.oid=c.relnamespace
               WHERE n.nspname='public'
                 AND c.relkind IN ('r','p','v','m','S','f')
                 AND c.relname IN (
                     'sys_schema_migration',
                     'sys_content_package',
                     'rule_rule'
                 )
               ORDER BY c.relname"""
        )
    ]


def run_project_tool(
    filename: str,
    env: dict[str, str],
    *arguments: str,
) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / filename), *arguments],
        cwd=ROOT,
        env=env,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted bootstrap from its recorded migration phase",
    )
    parser.add_argument(
        "--start-at",
        type=int,
        help="On recovery, skip importer phases below this migration target",
    )
    parser.add_argument(
        "--build",
        default=os.environ.get("BASE_CEPHEUS_BUILD", "development"),
        help="Application build identity recorded with applied migrations",
    )
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")

    with psycopg.connect(dsn) as connection:
        relations = public_relations(connection)
    if relations and not args.resume:
        sample = ", ".join(relations[:5])
        parser.error(
            "bootstrap requires an empty Emporos schema; found relations: "
            f"{sample}"
        )

    env = dict(os.environ)
    env["BASE_CEPHEUS_DATABASE_URL"] = dsn
    env["BASE_CEPHEUS_BUILD"] = args.build

    for target, importers in BOOTSTRAP_PHASES:
        if (
            args.start_at is not None
            and target is not None
            and target < args.start_at
        ):
            continue
        migration_arguments = (
            ("--target", str(target)) if target is not None else ()
        )
        run_project_tool("migrate.py", env, *migration_arguments)
        for importer in importers:
            run_project_tool(importer, env)

    run_project_tool("verify_database.py", env)
    run_project_tool("complete_database_bootstrap.py", env)
    print("bootstrapped and verified an empty Base Cepheus database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
