import os
import unittest

import psycopg
from psycopg.errors import CheckViolation, UniqueViolation


DSN = os.environ.get("BASE_CEPHEUS_DATABASE_URL")


@unittest.skipUnless(DSN, "BASE_CEPHEUS_DATABASE_URL is required")
class PersonalArmorCapabilityTests(unittest.TestCase):
    def connect(self):
        return psycopg.connect(DSN)

    def test_degradation_layering_and_battle_dress_are_typed(self):
        with self.connect() as connection:
            degradation = connection.execute(
                """SELECT rule.rule_code,damage_type,
                          armor_rating_loss_per_hit,minimum_armor_rating
                   FROM rule_armor_degradation degradation
                   JOIN rule_rule rule
                     ON rule.rule_id=degradation.armor_rule_id"""
            ).fetchall()
            layering = connection.execute(
                """SELECT rule.rule_code,maximum_total_layers,
                          layer_position_choice
                   FROM rule_armor_layer_exception exception
                   JOIN rule_rule rule
                     ON rule.rule_id=exception.armor_rule_id"""
            ).fetchall()
            modifiers = connection.execute(
                """SELECT characteristic.rule_code,modifier,
                          modifies_damage_tracking
                   FROM rule_armor_characteristic_modifier modifier
                   JOIN rule_rule characteristic
                     ON characteristic.rule_id=
                        modifier.characteristic_rule_id
                   ORDER BY characteristic.rule_code"""
            ).fetchall()
            computer = connection.execute(
                """SELECT computer_model,skill.rule_code,expert_program_level
                   FROM rule_armor_computer_system computer
                   JOIN rule_rule skill
                     ON skill.rule_id=computer.expert_skill_rule_id"""
            ).fetchone()
        self.assertEqual(degradation, [
            ("equipment.armor.ablat", "laser", 1, 0)])
        self.assertEqual(layering, [
            ("equipment.armor.reflec", 2, True)])
        self.assertEqual(modifiers, [
            ("characteristic.dexterity", 4, False),
            ("characteristic.strength", 4, False),
        ])
        self.assertEqual(computer, (2, "skill.tactics", 2))

    def test_life_support_and_effective_protections_are_exact(self):
        with self.connect() as connection:
            life_support = connection.execute(
                """SELECT rule.rule_code,duration_seconds
                   FROM rule_armor_life_support support
                   JOIN rule_rule rule
                     ON rule.rule_id=support.armor_rule_id
                   ORDER BY rule.rule_code"""
            ).fetchall()
            radiation = connection.execute(
                """SELECT rule.rule_code,radiation_reduction_rads,
                          source.rule_code
                   FROM rule_armor_effective_environmental_protection p
                   JOIN rule_rule rule ON rule.rule_id=p.armor_rule_id
                   JOIN rule_rule source
                     ON source.rule_id=p.source_armor_rule_id
                   WHERE hazard_code='radiation'
                   ORDER BY rule.rule_code"""
            ).fetchall()
        self.assertEqual(life_support, [
            ("equipment.armor.battle-dress", 21600),
            ("equipment.armor.combat-armor", 21600),
            ("equipment.armor.hostile-environment-vacc-suit", 21600),
            ("equipment.armor.vacc-suit", 21600),
        ])
        self.assertEqual(radiation, [
            ("equipment.armor.battle-dress", 180,
             "equipment.armor.hostile-environment-vacc-suit"),
            ("equipment.armor.hostile-environment-vacc-suit", 180,
             "equipment.armor.hostile-environment-vacc-suit"),
            ("equipment.armor.vacc-suit", 40, "equipment.armor.vacc-suit"),
        ])

    def test_mechanics_have_paired_provenance(self):
        with self.connect() as connection:
            result = connection.execute(
                """SELECT count(*),count(*) FILTER (
                              WHERE is_primary_citation),
                          count(DISTINCT (
                              armor_rule_id,mechanic_code))
                   FROM src_armor_mechanic_provenance"""
            ).fetchone()
        self.assertEqual(result, (24, 12, 12))

    def test_invalid_radiation_and_second_primary_are_rejected(self):
        with self.connect() as connection:
            vacc = connection.execute(
                """SELECT rule_id FROM rule_rule
                   WHERE rule_code='equipment.armor.vacc-suit'"""
            ).fetchone()[0]
            with self.assertRaises(CheckViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE rule_armor_environmental_protection
                           SET radiation_reduction_rads=NULL
                           WHERE armor_rule_id=%s
                             AND hazard_code='radiation'""", (vacc,))
            provenance = connection.execute(
                """SELECT armor_rule_id,mechanic_code,source_locator_id,
                          import_candidate_id
                   FROM src_armor_mechanic_provenance
                   WHERE is_primary_citation LIMIT 1"""
            ).fetchone()
            with self.assertRaises(UniqueViolation):
                with connection.transaction():
                    connection.execute(
                        """UPDATE src_armor_mechanic_provenance
                           SET is_primary_citation=true
                           WHERE armor_rule_id=%s AND mechanic_code=%s
                             AND (source_locator_id,import_candidate_id)
                                 <>(%s,%s)""",
                        provenance)


if __name__ == "__main__":
    unittest.main()
