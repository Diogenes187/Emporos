import os
import unittest

import psycopg

from engine.careers import (
    apply_career_basic_training_command, attempt_career_entry_command,
    apply_career_injury_command, apply_career_rank_zero_award_command,
    apply_career_aging_command, apply_career_term_training_command,
    attempt_career_survival_command, complete_career_term_command,
    declare_career_anagathics_command,
    decide_career_reenlistment_command,
    determine_career_aging_command, determine_career_injury_command,
    determine_anagathic_stopping_shock_command,
    determine_aging_crisis_cost_command,
    determine_career_reenlistment_command,
    determine_injury_crisis_cost_command, resolve_failed_career_entry_command,
    finish_character_creation_command,
    initialize_career_muster_command, roll_career_benefit_command,
    resolve_career_weapon_benefit_command,
    resolve_aging_crisis_command,
    resolve_career_medical_care_command,
    resolve_career_rank_attempt_command, resolve_injury_crisis_command,
    resolve_survival_mishap_command,
)


class FixedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, minimum, maximum):
        return next(self.values)


@unittest.skipUnless(
    os.environ.get("BASE_CEPHEUS_DATABASE_URL"),
    "requires the project PostgreSQL database",
)
class CareerCatalogueIntegrationTests(unittest.TestCase):
    def _actor(self, connection):
        campaign_id = connection.execute(
            """INSERT INTO camp_campaign (name,owner_reference)
               VALUES ('Career Entry','player') RETURNING campaign_id"""
        ).fetchone()[0]
        actor_id, actor_public = connection.execute(
            """INSERT INTO actor_actor
               (campaign_id,name,controller_reference)
               VALUES (%s,'Career Traveller','player')
               RETURNING actor_id,public_id""",
            (campaign_id,),
        ).fetchone()
        connection.execute(
            """INSERT INTO actor_characteristic
               (actor_id,characteristic_rule_id,maximum_value,current_value)
               SELECT %s,rule_id,7,7 FROM rule_rule
               WHERE rule_code IN (
                 'characteristic.strength','characteristic.dexterity',
                 'characteristic.endurance','characteristic.intelligence',
                 'characteristic.education','characteristic.social-standing'
               )""",
            (actor_id,),
        )
        return actor_id, str(actor_public)

    def test_merchant_is_the_undivided_cepheus_engine_career(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            merchant = connection.execute(
                """SELECT qualification.rule_code,progression.qualification_target,
                          survival.rule_code,progression.survival_target,
                          commission.rule_code,progression.commission_target,
                          advancement.rule_code,progression.advancement_target,
                          progression.reenlistment_target
                   FROM rule_career career
                   JOIN rule_career_progression progression
                     ON progression.career_rule_id=career.career_rule_id
                   JOIN rule_rule qualification
                     ON qualification.rule_id=
                        progression.qualification_characteristic_rule_id
                   JOIN rule_rule survival
                     ON survival.rule_id=
                        progression.survival_characteristic_rule_id
                   JOIN rule_rule commission
                     ON commission.rule_id=
                        progression.commission_characteristic_rule_id
                   JOIN rule_rule advancement
                     ON advancement.rule_id=
                        progression.advancement_characteristic_rule_id
                   WHERE career.career_code='merchant'"""
            ).fetchone()
            self.assertEqual(
                merchant,
                (
                    "characteristic.intelligence", 4,
                    "characteristic.intelligence", 5,
                    "characteristic.intelligence", 5,
                    "characteristic.education", 8, 4,
                ),
            )
            assignments = connection.execute(
                """SELECT count(*) FROM rule_career_assignment assignment
                   JOIN rule_career career
                     ON career.career_rule_id=assignment.career_rule_id
                   WHERE career.career_code='merchant'"""
            ).fetchone()[0]
            self.assertEqual(assignments, 0)
            broker = connection.execute(
                """SELECT entry.roll_value,skill_rule.rule_code
                   FROM rule_career_training_entry entry
                   JOIN rule_career career
                     ON career.career_rule_id=entry.career_rule_id
                   JOIN rule_rule skill_rule
                     ON skill_rule.rule_id=entry.skill_rule_id
                   WHERE career.career_code='merchant'
                     AND entry.training_table_code='service'
                     AND entry.roll_value=5"""
            ).fetchone()
            self.assertEqual(broker, (5, "skill.broker"))

    def test_qualified_entry_is_idempotent_and_starts_merchant(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                result = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="career-merchant",
                    actor_public_id=actor_public, career_code="merchant",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(result.qualified)
                self.assertEqual(result.resulting_career_code, "merchant")
                self.assertEqual(result.qualification_dice, (6, 6))
                replay = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="career-merchant",
                    actor_public_id=actor_public, career_code="merchant",
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.qualification_dice, (6, 6))

    def test_failed_entry_supports_one_draft_then_drifter(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                failed = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="career-fail-merchant",
                    actor_public_id=actor_public, career_code="merchant",
                    random_source=FixedRandom((1, 1)),
                )
                self.assertFalse(failed.qualified)
                self.assertEqual(failed.attempt_status, "awaiting_fallback")
                drafted = resolve_failed_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="career-draft",
                    attempt_command_public_id=failed.command_public_id,
                    fallback_kind="draft",
                    random_source=FixedRandom((6,)),
                )
                self.assertEqual(
                    (drafted.resulting_career_code, drafted.draft_uses),
                    ("surface-defense", 1),
                )
                connection.execute(
                    """UPDATE actor_career_stint SET stint_status='left'
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="drafted-zero-benefit-muster",
                    actor_public_id=actor_public,
                )
                second = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="career-fail-noble",
                    actor_public_id=actor_public, career_code="noble",
                    random_source=FixedRandom((1, 1)),
                )
                self.assertEqual(
                    (second.previous_careers,
                     second.qualification_modifier),
                    (1, -2),
                )
                with self.assertRaisesRegex(ValueError, "already used"):
                    resolve_failed_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="career-second-draft",
                        attempt_command_public_id=second.command_public_id,
                        fallback_kind="draft",
                    )
                drifter = resolve_failed_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="career-drifter",
                    attempt_command_public_id=second.command_public_id,
                    fallback_kind="drifter",
                )
                self.assertEqual(drifter.resulting_career_code, "drifter")

    def test_first_career_basic_training_grants_all_service_skills(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="training-entry",
                    actor_public_id=actor_public, career_code="merchant",
                    random_source=FixedRandom((6, 6)),
                )
                with self.assertRaisesRegex(ValueError, "requires a specialization"):
                    apply_career_basic_training_command(
                        connection, initiator_reference="player",
                        idempotency_key="training-missing-cascade",
                        actor_public_id=actor_public,
                    )
                choices = {
                    "skill.gun-combat": "skill.slug-pistol",
                    "skill.melee-combat": "skill.slashing-weapons",
                    "skill.vehicle": "skill.wheeled-vehicle",
                }
                result = apply_career_basic_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="training-complete",
                    actor_public_id=actor_public,
                    cascade_specializations=choices,
                )
                self.assertTrue(result.first_career)
                self.assertEqual(len(result.grants), 6)
                self.assertIn(
                    "skill.broker",
                    {grant.granted_skill_rule_code for grant in result.grants},
                )
                replay = apply_career_basic_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="training-complete",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.grants, result.grants)

    def test_later_career_basic_training_grants_one_chosen_service_skill(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                first = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="first-entry",
                    actor_public_id=actor_public, career_code="merchant",
                    random_source=FixedRandom((6, 6)),
                )
                connection.execute(
                    """UPDATE actor_career_stint
                       SET stint_status='left',basic_training_completed=true
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="manual-zero-benefit-muster",
                    actor_public_id=actor_public,
                )
                self.assertTrue(first.qualified)
                attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="second-entry",
                    actor_public_id=actor_public, career_code="agent",
                    random_source=FixedRandom((6, 6)),
                )
                with self.assertRaisesRegex(ValueError, "requires a Service"):
                    apply_career_basic_training_command(
                        connection, initiator_reference="player",
                        idempotency_key="later-no-choice",
                        actor_public_id=actor_public,
                    )
                result = apply_career_basic_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="later-training",
                    actor_public_id=actor_public, selected_roll_value=1,
                )
                self.assertFalse(result.first_career)
                self.assertEqual(len(result.grants), 1)
                self.assertEqual(
                    result.grants[0].granted_skill_rule_code, "skill.admin")

    def test_rank_zero_award_uses_imported_fixed_level_and_replays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="rank-entry",
                    actor_public_id=actor_public, career_code="merchant",
                    random_source=FixedRandom((6, 6)),
                )
                apply_career_basic_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="rank-training",
                    actor_public_id=actor_public,
                    cascade_specializations={
                        "skill.gun-combat": "skill.slug-pistol",
                        "skill.melee-combat": "skill.slashing-weapons",
                        "skill.vehicle": "skill.wheeled-vehicle",
                    },
                )
                result = apply_career_rank_zero_award_command(
                    connection, initiator_reference="player",
                    idempotency_key="rank-zero",
                    actor_public_id=actor_public,
                )
                self.assertEqual(
                    (
                        result.rank_title,
                        result.source_grant_text,
                        result.granted_skill_rule_code,
                        result.resulting_skill_level,
                    ),
                    ("Crewman", "Steward-1", "skill.steward", 1),
                )
                replay = apply_career_rank_zero_award_command(
                    connection, initiator_reference="player",
                    idempotency_key="rank-zero",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.resulting_skill_level, 1)

    def _merchant_ready_for_survival(self, connection, actor_public):
        attempt_career_entry_command(
            connection, initiator_reference="player",
            idempotency_key=f"entry-{actor_public}",
            actor_public_id=actor_public, career_code="merchant",
            random_source=FixedRandom((6, 6)),
        )
        apply_career_basic_training_command(
            connection, initiator_reference="player",
            idempotency_key=f"training-{actor_public}",
            actor_public_id=actor_public,
            cascade_specializations={
                "skill.gun-combat": "skill.slug-pistol",
                "skill.melee-combat": "skill.slashing-weapons",
                "skill.vehicle": "skill.wheeled-vehicle",
            },
        )
        apply_career_rank_zero_award_command(
            connection, initiator_reference="player",
            idempotency_key=f"rank-zero-{actor_public}",
            actor_public_id=actor_public,
        )

    def _complete_first_merchant_term(
        self, connection, actor_public, suffix,
    ):
        self._merchant_ready_for_survival(connection, actor_public)
        attempt_career_survival_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-survival",
            actor_public_id=actor_public,
            random_source=FixedRandom((6, 6)),
        )
        resolve_career_rank_attempt_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-decline-commission",
            actor_public_id=actor_public,
            attempt_kind="commission", decision="decline",
        )
        apply_career_term_training_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-term-training",
            actor_public_id=actor_public,
            training_table_code="service",
            random_source=FixedRandom((1,)),
        )
        return complete_career_term_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-complete",
            actor_public_id=actor_public,
        )

    def _depart_completed_merchant(
        self, connection, actor_public, suffix,
    ):
        self._complete_first_merchant_term(
            connection, actor_public, suffix)
        determine_career_reenlistment_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-reenlistment",
            actor_public_id=actor_public,
            random_source=FixedRandom((3, 3)),
        )
        decide_career_reenlistment_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-leave",
            actor_public_id=actor_public, decision="leave",
        )

    def _create_merchant_aging_crisis(
        self, connection, actor_id, actor_public, suffix,
    ):
        self._merchant_ready_for_survival(connection, actor_public)
        attempt_career_survival_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-survival",
            actor_public_id=actor_public,
            random_source=FixedRandom((6, 6)),
        )
        resolve_career_rank_attempt_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-decline-commission",
            actor_public_id=actor_public,
            attempt_kind="commission", decision="decline",
        )
        apply_career_term_training_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-training",
            actor_public_id=actor_public,
            training_table_code="service",
            random_source=FixedRandom((1,)),
        )
        connection.execute(
            """UPDATE actor_lifepath_state
               SET total_terms=3,age_years=30 WHERE actor_id=%s""",
            (actor_id,),
        )
        connection.execute(
            """UPDATE actor_characteristic state
               SET maximum_value=1,current_value=1
               FROM rule_rule rule
               WHERE state.actor_id=%s
                 AND rule.rule_id=state.characteristic_rule_id
                 AND rule.rule_code IN (
                     'characteristic.strength',
                     'characteristic.dexterity',
                     'characteristic.endurance'
                 )""",
            (actor_id,),
        )
        complete_career_term_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-complete",
            actor_public_id=actor_public,
        )
        determine_career_aging_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-aging",
            actor_public_id=actor_public,
            random_source=FixedRandom((1, 1)),
        )
        result = apply_career_aging_command(
            connection, initiator_reference="player",
            idempotency_key=f"{suffix}-apply-aging",
            actor_public_id=actor_public,
            physical_characteristic_codes=(
                "characteristic.strength",
                "characteristic.dexterity",
                "characteristic.endurance",
            ),
        )
        self.assertTrue(result.crisis_started)

    def test_anagathics_add_cost_and_require_second_survival_check(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                declaration = declare_career_anagathics_command(
                    connection, initiator_reference="player",
                    idempotency_key="anagathic-declaration",
                    actor_public_id=actor_public, uses_anagathics=True,
                    random_source=FixedRandom((3,)),
                )
                self.assertEqual(declaration.cost_credits, 7500)
                result = attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="anagathic-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6, 1, 1)),
                )
                self.assertEqual(result.survival_dice, (6, 6))
                self.assertEqual(result.second_survival_dice, (1, 1))
                self.assertFalse(result.second_survival_passed)
                self.assertFalse(result.survived)
                finance = connection.execute(
                    """SELECT debt_credits,anagathic_debt_credits
                       FROM actor_financial_state WHERE actor_id=%s""",
                    (actor_id,),
                ).fetchone()
                self.assertEqual(finance, (7500, 7500))

    def test_anagathic_course_terms_are_positive_aging_modifier(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                declare_career_anagathics_command(
                    connection, initiator_reference="player",
                    idempotency_key="aging-anagathic-declaration",
                    actor_public_id=actor_public, uses_anagathics=True,
                    random_source=FixedRandom((1,)),
                )
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="aging-anagathic-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6, 6, 6)),
                )
                connection.execute(
                    """UPDATE actor_career_term SET term_status='completed'
                       WHERE career_stint_id=(
                         SELECT career_stint_id FROM actor_career_stint
                         WHERE actor_id=%s AND stint_status='active'
                       )""",
                    (actor_id,),
                )
                connection.execute(
                    """INSERT INTO actor_lifepath_state
                       (actor_id,age_years,total_terms,lifepath_status)
                       VALUES (%s,34,4,'active')
                       ON CONFLICT (actor_id) DO UPDATE
                       SET age_years=34,total_terms=4""",
                    (actor_id,),
                )
                aging = determine_career_aging_command(
                    connection, initiator_reference="player",
                    idempotency_key="aging-anagathic-roll",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertEqual(aging.anagathic_modifier, 1)
                self.assertEqual(aging.table_result, -1)

    def test_stopping_anagathics_immediately_uses_aging_table(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                declare_career_anagathics_command(
                    connection, initiator_reference="player",
                    idempotency_key="shock-start",
                    actor_public_id=actor_public, uses_anagathics=True,
                    random_source=FixedRandom((1,)),
                )
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="shock-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6, 6, 6)),
                )
                connection.execute(
                    """UPDATE actor_career_stint SET terms_completed=1
                       WHERE actor_id=%s AND stint_status='active'""",
                    (actor_id,),
                )
                connection.execute(
                    """UPDATE actor_lifepath_state SET total_terms=4,age_years=34
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                stopped = declare_career_anagathics_command(
                    connection, initiator_reference="player",
                    idempotency_key="shock-stop",
                    actor_public_id=actor_public, uses_anagathics=False,
                )
                self.assertEqual(stopped.declaration_status, "shock_required")
                shock = determine_anagathic_stopping_shock_command(
                    connection, initiator_reference="player",
                    idempotency_key="shock-aging",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertEqual(shock.anagathic_modifier, 0)
                self.assertEqual(shock.table_result, -2)
                applied = apply_career_aging_command(
                    connection, initiator_reference="player",
                    idempotency_key="shock-allocation",
                    actor_public_id=actor_public,
                    physical_characteristic_codes=(
                        "characteristic.strength",
                        "characteristic.dexterity",
                        "characteristic.endurance",
                    ),
                )
                self.assertEqual(applied.aging_status, "applied")
                status = connection.execute(
                    """SELECT declaration_status
                       FROM actor_career_anagathic_term
                       WHERE actor_id=%s ORDER BY career_anagathic_term_id DESC
                       LIMIT 1""",
                    (actor_id,),
                ).fetchone()[0]
                self.assertEqual(status, "resolved")

    def test_survival_uses_career_characteristic_and_replays_dice(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                result = attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((3, 4)),
                )
                self.assertEqual(
                    (
                        result.characteristic_rule_code,
                        result.characteristic_value,
                        result.characteristic_modifier,
                        result.target_number,
                    ),
                    ("characteristic.intelligence", 7, 0, 5),
                )
                self.assertTrue(result.survived)
                self.assertEqual(result.term_status, "survival_passed")
                replay = attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-survival",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.survival_dice, (3, 4))

    def test_natural_two_fails_survival_and_stops_term_progression(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                connection.execute(
                    """UPDATE actor_characteristic state
                       SET maximum_value=18,current_value=18
                       FROM rule_rule rule
                       WHERE state.actor_id=%s
                         AND rule.rule_id=state.characteristic_rule_id
                         AND rule.rule_code='characteristic.intelligence'""",
                    (actor_id,),
                )
                result = attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-natural-two",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertTrue(result.natural_two)
                self.assertGreaterEqual(
                    result.check_total, result.target_number)
                self.assertFalse(result.survived)
                self.assertEqual(result.term_status, "survival_failed")
                with self.assertRaisesRegex(
                    ValueError, "already reached the survival gate"
                ):
                    attempt_career_survival_command(
                        connection, initiator_reference="player",
                        idempotency_key="merchant-second-survival",
                        actor_public_id=actor_public,
                    )

    def test_legal_battle_mishap_adds_debt_and_reopens_career_choice(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="mishap-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                result = resolve_survival_mishap_command(
                    connection, initiator_reference="player",
                    idempotency_key="legal-mishap",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((3,)),
                )
                self.assertEqual(
                    (
                        result.outcome_code, result.elapsed_years,
                        result.debt_added, result.resulting_age,
                        result.injury_required,
                    ),
                    ("legal_battle", 2, 10000, 20, False),
                )
                replay = resolve_survival_mishap_command(
                    connection, initiator_reference="player",
                    idempotency_key="legal-mishap",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="legal-zero-benefit-muster",
                    actor_public_id=actor_public,
                )
                next_career = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="post-mishap-agent",
                    actor_public_id=actor_public, career_code="agent",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(next_career.qualified)

    def test_injury_mishap_blocks_next_career_until_injury_resolution(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="injury-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                result = resolve_survival_mishap_command(
                    connection, initiator_reference="player",
                    idempotency_key="injury-mishap",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1,)),
                )
                self.assertTrue(result.injury_required)
                injury = determine_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="fixed-severe-injury",
                    actor_public_id=actor_public,
                    result_two_choice="fixed_two",
                )
                self.assertEqual(injury.injury_dice, ())
                self.assertEqual(injury.injury_roll_value, 2)
                self.assertEqual(
                    injury.consequence_status, "awaiting_application")
                with self.assertRaisesRegex(
                    ValueError, "injury still requires resolution"
                ):
                    attempt_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="blocked-agent",
                        actor_public_id=actor_public, career_code="agent",
                        random_source=FixedRandom((6, 6)),
                    )
                applied = apply_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="apply-severe-injury",
                    actor_public_id=actor_public,
                    primary_characteristic_code="characteristic.endurance",
                    random_source=FixedRandom((4,)),
                )
                self.assertEqual(applied.injury_reduction_dice, (4,))
                self.assertEqual(
                    (
                        applied.reductions[0].prior_value,
                        applied.reductions[0].resulting_value,
                        applied.crisis_started,
                    ),
                    (7, 3, False),
                )
                resolve_career_medical_care_command(
                    connection, initiator_reference="player",
                    idempotency_key="decline-severe-medical-care",
                    actor_public_id=actor_public, decision="decline",
                )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="injury-zero-benefit-muster",
                    actor_public_id=actor_public,
                )
                next_career = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="unblocked-agent",
                    actor_public_id=actor_public, career_code="agent",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(next_career.qualified)

    def test_medical_discharge_light_injury_immediately_clears_gate(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                resolve_survival_mishap_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-mishap",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6,)),
                )
                injury = determine_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="light-injury",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6,)),
                )
                self.assertEqual(injury.injury_dice, (6,))
                self.assertEqual(injury.outcome_code, "lightly_injured")
                self.assertEqual(injury.consequence_status, "resolved")
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="light-injury-zero-benefit-muster",
                    actor_public_id=actor_public,
                )
                next_career = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="after-light-injury",
                    actor_public_id=actor_public, career_code="agent",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(next_career.qualified)

    def test_injury_crisis_cost_is_recorded_then_player_pays(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="crisis-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                resolve_survival_mishap_command(
                    connection, initiator_reference="player",
                    idempotency_key="crisis-mishap",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1,)),
                )
                determine_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="crisis-injury",
                    actor_public_id=actor_public,
                    result_two_choice="fixed_two",
                )
                connection.execute(
                    """UPDATE actor_characteristic state
                       SET maximum_value=1,current_value=1
                       FROM rule_rule rule
                       WHERE state.actor_id=%s
                         AND rule.rule_id=state.characteristic_rule_id
                         AND rule.rule_code='characteristic.endurance'""",
                    (actor_id,),
                )
                applied = apply_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="cause-crisis",
                    actor_public_id=actor_public,
                    primary_characteristic_code="characteristic.endurance",
                    random_source=FixedRandom((1,)),
                )
                self.assertTrue(applied.crisis_started)
                priced = determine_injury_crisis_cost_command(
                    connection, initiator_reference="player",
                    idempotency_key="price-crisis",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((2,)),
                )
                self.assertEqual(priced.medical_cost_credits, 20000)
                self.assertFalse(priced.affordable)
                replay = determine_injury_crisis_cost_command(
                    connection, initiator_reference="player",
                    idempotency_key="price-crisis",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                with self.assertRaisesRegex(ValueError, "cannot afford"):
                    resolve_injury_crisis_command(
                        connection, initiator_reference="player",
                        idempotency_key="premature-payment",
                        actor_public_id=actor_public,
                        resolution_kind="pay",
                    )
                connection.execute(
                    """INSERT INTO actor_financial_state
                       (actor_id,cash_credits) VALUES (%s,30000)
                       ON CONFLICT (actor_id) DO UPDATE
                       SET cash_credits=EXCLUDED.cash_credits""",
                    (actor_id,),
                )
                paid = resolve_injury_crisis_command(
                    connection, initiator_reference="player",
                    idempotency_key="pay-crisis",
                    actor_public_id=actor_public,
                    resolution_kind="pay",
                )
                self.assertEqual((paid.cash_before, paid.cash_after), (30000, 10000))
                self.assertEqual(
                    paid.restored_characteristic_codes,
                    ("characteristic.endurance",),
                )
                self.assertEqual(paid.lifepath_status, "active")

    def test_commission_then_advancement_each_adds_one_training_roll(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="rank-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                commission = resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-commission",
                    actor_public_id=actor_public,
                    attempt_kind="commission", decision="attempt",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertEqual(
                    (
                        commission.succeeded, commission.prior_rank,
                        commission.resulting_rank, commission.rank_title,
                        commission.bonus_training_rolls,
                    ),
                    (True, 0, 1, "Deck Cadet", 1),
                )
                advancement = resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-advancement",
                    actor_public_id=actor_public,
                    attempt_kind="advancement", decision="attempt",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertEqual(
                    (
                        advancement.succeeded, advancement.prior_rank,
                        advancement.resulting_rank, advancement.rank_title,
                        advancement.bonus_training_rolls,
                    ),
                    (True, 1, 2, "Fourth Officer", 2),
                )
                replay = resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-advancement",
                    actor_public_id=actor_public,
                    attempt_kind="advancement", decision="attempt",
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.dice, (6, 6))

    def test_declined_commission_consumes_no_randomness(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="decline-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                result = resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="decline-commission",
                    actor_public_id=actor_public,
                    attempt_kind="commission", decision="decline",
                )
                self.assertEqual(result.dice, ())
                self.assertIsNone(result.succeeded)
                self.assertEqual(result.resulting_rank, 0)

    def test_first_term_draftee_cannot_attempt_commission(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                connection.execute(
                    """UPDATE actor_career_stint SET entry_method='draft'
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="draft-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                with self.assertRaisesRegex(ValueError, "draftee"):
                    resolve_career_rank_attempt_command(
                        connection, initiator_reference="player",
                        idempotency_key="illegal-draft-commission",
                        actor_public_id=actor_public,
                        attempt_kind="commission", decision="attempt",
                        random_source=FixedRandom((6, 6)),
                    )
                training = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="draft-first-term-training",
                    actor_public_id=actor_public,
                    training_table_code="personal_development",
                    cascade_specializations={
                        "skill.melee-combat": "skill.slashing-weapons",
                    },
                    random_source=FixedRandom((1,)),
                )
                self.assertEqual(training.training_roll_order, 1)

    def test_repeated_cascade_training_advances_same_specialty_each_time(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="repeat-rifle-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="repeat-rifle-commission",
                    actor_public_id=actor_public,
                    attempt_kind="commission", decision="decline",
                )
                connection.execute(
                    """UPDATE actor_career_term term
                       SET bonus_training_rolls=3
                       FROM actor_career_stint stint
                       WHERE stint.career_stint_id=term.career_stint_id
                         AND stint.actor_id=%s
                         AND term.term_status='survival_passed'""",
                    (actor_id,),
                )
                transitions = []
                for number in range(1, 5):
                    result = apply_career_term_training_command(
                        connection, initiator_reference="player",
                        idempotency_key=f"repeat-rifle-training-{number}",
                        actor_public_id=actor_public,
                        training_table_code="service",
                        cascade_specialization="skill.slug-rifle",
                        random_source=FixedRandom((3,)),
                    )
                    transitions.append(
                        (result.prior_value, result.resulting_value))
                self.assertEqual(
                    transitions,
                    [(None, 1), (1, 2), (2, 3), (3, 4)],
                )
                stored = connection.execute(
                    """SELECT state.skill_level
                       FROM actor_skill state
                       JOIN rule_rule rule ON rule.rule_id=state.skill_rule_id
                       WHERE state.actor_id=%s
                         AND rule.rule_code='skill.slug-rifle'""",
                    (actor_id,),
                ).fetchone()[0]
                receipts = connection.execute(
                    """SELECT COUNT(*)
                       FROM cmd_career_term_training_receipt receipt
                       JOIN actor_career_term term
                         ON term.career_term_id=receipt.career_term_id
                       JOIN actor_career_stint stint
                         ON stint.career_stint_id=term.career_stint_id
                       WHERE stint.actor_id=%s
                         AND receipt.granted_skill_rule_id=(
                             SELECT rule_id FROM rule_rule
                             WHERE rule_code='skill.slug-rifle'
                         )""",
                    (actor_id,),
                ).fetchone()[0]
                self.assertEqual((stored, receipts), (4, 4))

    def test_term_training_accepts_keyed_cascade_specializations(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="keyed-training-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="keyed-training-commission",
                    actor_public_id=actor_public,
                    attempt_kind="commission", decision="decline",
                )
                result = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="keyed-training-roll",
                    actor_public_id=actor_public,
                    training_table_code="service",
                    cascade_specializations={
                        "skill.gun-combat": "skill.slug-pistol",
                        "skill.melee-combat": "skill.slashing-weapons",
                        "skill.vehicle": "skill.wheeled-vehicle",
                    },
                    random_source=FixedRandom((4,)),
                )
                self.assertEqual(
                    result.granted_rule_code, "skill.slashing-weapons"
                )

    def test_term_training_uses_player_table_and_rank_bonus_rolls(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="training-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="training-commission",
                    actor_public_id=actor_public,
                    attempt_kind="commission", decision="attempt",
                    random_source=FixedRandom((6, 6)),
                )
                resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="training-advancement",
                    actor_public_id=actor_public,
                    attempt_kind="advancement", decision="attempt",
                    random_source=FixedRandom((6, 6)),
                )
                with self.assertRaisesRegex(
                    ValueError, "Advanced Education requires"
                ):
                    apply_career_term_training_command(
                        connection, initiator_reference="player",
                        idempotency_key="blocked-advanced-education",
                        actor_public_id=actor_public,
                        training_table_code="advanced_education",
                        random_source=FixedRandom((1,)),
                    )
                result = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-training-one",
                    actor_public_id=actor_public,
                    training_table_code="service",
                    random_source=FixedRandom((5,)),
                )
                self.assertEqual(
                    (
                        result.training_roll_order,
                        result.allowed_training_rolls,
                        result.training_die,
                        result.granted_rule_code,
                        result.prior_value,
                        result.resulting_value,
                    ),
                    (1, 3, 5, "skill.broker", 0, 1),
                )
                replay = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-training-one",
                    actor_public_id=actor_public,
                    training_table_code="service",
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.training_die, 5)
                characteristic = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-training-two",
                    actor_public_id=actor_public,
                    training_table_code="personal_development",
                    random_source=FixedRandom((1,)),
                )
                self.assertEqual(
                    (
                        characteristic.granted_rule_code,
                        characteristic.prior_value,
                        characteristic.resulting_value,
                    ),
                    ("characteristic.strength", 7, 8),
                )
                with self.assertRaisesRegex(ValueError, "requires a specialization"):
                    apply_career_term_training_command(
                        connection, initiator_reference="player",
                        idempotency_key="missing-training-specialization",
                        actor_public_id=actor_public,
                        training_table_code="service",
                        random_source=FixedRandom((3,)),
                    )
                cascade = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="merchant-training-three",
                    actor_public_id=actor_public,
                    training_table_code="service",
                    cascade_specialization="skill.slug-rifle",
                    random_source=FixedRandom((3,)),
                )
                self.assertEqual(
                    (
                        cascade.training_roll_order,
                        cascade.granted_rule_code,
                        cascade.resulting_value,
                    ),
                    (3, "skill.slug-rifle", 1),
                )

    def test_training_waits_for_optional_rank_decisions(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="pending-rank-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                with self.assertRaisesRegex(ValueError, "Commission decision"):
                    apply_career_term_training_command(
                        connection, initiator_reference="player",
                        idempotency_key="premature-training",
                        actor_public_id=actor_public,
                        training_table_code="service",
                        random_source=FixedRandom((1,)),
                    )

    def test_no_hierarchy_career_receives_two_training_rolls(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="drifter-entry",
                    actor_public_id=actor_public, career_code="drifter",
                )
                apply_career_basic_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="drifter-training",
                    actor_public_id=actor_public,
                    cascade_specializations={
                        "skill.gun-combat": "skill.slug-pistol",
                        "skill.melee-combat": "skill.slashing-weapons",
                        "skill.vehicle": "skill.wheeled-vehicle",
                    },
                )
                apply_career_rank_zero_award_command(
                    connection, initiator_reference="player",
                    idempotency_key="drifter-rank-zero",
                    actor_public_id=actor_public,
                )
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="drifter-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                first = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="drifter-roll-one",
                    actor_public_id=actor_public,
                    training_table_code="service",
                    random_source=FixedRandom((1,)),
                )
                second = apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="drifter-roll-two",
                    actor_public_id=actor_public,
                    training_table_code="service",
                    random_source=FixedRandom((2,)),
                )
                self.assertEqual(first.allowed_training_rolls, 2)
                self.assertEqual(second.training_roll_order, 2)
                with self.assertRaisesRegex(ValueError, "complete"):
                    apply_career_term_training_command(
                        connection, initiator_reference="player",
                        idempotency_key="drifter-roll-three",
                        actor_public_id=actor_public,
                        training_table_code="service",
                        random_source=FixedRandom((3,)),
                    )

    def test_fourth_completed_term_requires_player_allocated_aging(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._merchant_ready_for_survival(connection, actor_public)
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="aging-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                resolve_career_rank_attempt_command(
                    connection, initiator_reference="player",
                    idempotency_key="aging-decline-commission",
                    actor_public_id=actor_public,
                    attempt_kind="commission", decision="decline",
                )
                apply_career_term_training_command(
                    connection, initiator_reference="player",
                    idempotency_key="aging-training",
                    actor_public_id=actor_public,
                    training_table_code="service",
                    random_source=FixedRandom((5,)),
                )
                connection.execute(
                    """UPDATE actor_lifepath_state
                       SET total_terms=3,age_years=30 WHERE actor_id=%s""",
                    (actor_id,),
                )
                completed = complete_career_term_command(
                    connection, initiator_reference="player",
                    idempotency_key="complete-fourth-term",
                    actor_public_id=actor_public,
                )
                self.assertEqual(
                    (completed.resulting_age, completed.resulting_total_terms),
                    (34, 4),
                )
                aging = determine_career_aging_command(
                    connection, initiator_reference="player",
                    idempotency_key="determine-fourth-aging",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertEqual(aging.table_result, -2)
                self.assertEqual(aging.effect_code, "minus_two")
                applied = apply_career_aging_command(
                    connection, initiator_reference="player",
                    idempotency_key="apply-fourth-aging",
                    actor_public_id=actor_public,
                    physical_characteristic_codes=(
                        "characteristic.strength",
                        "characteristic.dexterity",
                        "characteristic.endurance",
                    ),
                )
                self.assertFalse(applied.crisis_started)
                self.assertEqual(
                    {row.resulting_value for row in applied.reductions}, {6})

    def test_successful_reenlistment_preserves_player_choice_and_gates_next_term(
        self,
    ):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._complete_first_merchant_term(
                    connection, actor_public, "optional-reenlistment")
                with self.assertRaisesRegex(
                    ValueError, "continuation through reenlistment"
                ):
                    attempt_career_survival_command(
                        connection, initiator_reference="player",
                        idempotency_key="blocked-second-term",
                        actor_public_id=actor_public,
                        random_source=FixedRandom((6, 6)),
                    )
                result = determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="offer-reenlistment",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((3, 3)),
                )
                self.assertEqual(result.outcome, "choice_available")
                self.assertIsNone(result.continuation)
                decision = decide_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="choose-reenlistment",
                    actor_public_id=actor_public, decision="continue",
                )
                self.assertEqual(
                    (decision.continuation, decision.stint_status),
                    (True, "active"),
                )
                second_term = attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="allowed-second-term",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                self.assertEqual(second_term.term_number, 2)
                replay = determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="offer-reenlistment",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.dice, (3, 3))

    def test_failed_reenlistment_forces_departure(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._complete_first_merchant_term(
                    connection, actor_public, "failed-reenlistment")
                result = determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="fail-reenlistment",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                self.assertEqual(result.outcome, "forced_leave_failed")
                self.assertFalse(result.continuation)
                with self.assertRaisesRegex(
                    ValueError, "no optional reenlistment choice"
                ):
                    decide_career_reenlistment_command(
                        connection, initiator_reference="player",
                        idempotency_key="illegal-failure-choice",
                        actor_public_id=actor_public, decision="continue",
                    )

    def test_seven_terms_force_retirement_except_on_natural_twelve(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._complete_first_merchant_term(
                    connection, actor_public, "retirement")
                connection.execute(
                    """UPDATE actor_lifepath_state
                       SET total_terms=7,age_years=46 WHERE actor_id=%s""",
                    (actor_id,),
                )
                determine_career_aging_command(
                    connection, initiator_reference="player",
                    idempotency_key="retirement-aging",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6, 6)),
                )
                retired = determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="mandatory-retirement",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((3, 3)),
                )
                self.assertEqual(retired.outcome, "mandatory_retirement")
                self.assertTrue(retired.retirement_required)
                with self.assertRaisesRegex(
                    ValueError, "mandatory retirement"
                ):
                    attempt_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="post-retirement-entry",
                        actor_public_id=actor_public, career_code="drifter",
                    )

                second_id, second_public = self._actor(connection)
                self._complete_first_merchant_term(
                    connection, second_public, "natural-twelve")
                connection.execute(
                    """UPDATE actor_lifepath_state
                       SET total_terms=7,age_years=46 WHERE actor_id=%s""",
                    (second_id,),
                )
                determine_career_aging_command(
                    connection, initiator_reference="player",
                    idempotency_key="natural-twelve-aging",
                    actor_public_id=second_public,
                    random_source=FixedRandom((6, 6)),
                )
                forced = determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="natural-twelve-reenlistment",
                    actor_public_id=second_public,
                    random_source=FixedRandom((6, 6)),
                )
                self.assertEqual(
                    forced.outcome, "forced_continue_natural_12")
                self.assertTrue(forced.continuation)
                self.assertFalse(forced.retirement_required)

    def test_muster_entitlement_cash_modifier_and_pension_are_source_derived(
        self,
    ):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "cash-muster")
                connection.execute(
                    """UPDATE actor_career_stint SET terms_completed=5
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                gambling_id = connection.execute(
                    """SELECT rule_id FROM rule_rule
                       WHERE rule_code='skill.gambling'"""
                ).fetchone()[0]
                connection.execute(
                    """INSERT INTO actor_skill
                       (actor_id,skill_rule_id,skill_level)
                       VALUES (%s,%s,0) ON CONFLICT DO NOTHING""",
                    (actor_id, gambling_id),
                )
                muster = initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="initialize-cash-muster",
                    actor_public_id=actor_public,
                )
                self.assertEqual(
                    (
                        muster.eligible_term_benefits,
                        muster.rank_bonus_benefits,
                        muster.total_benefit_rolls,
                        muster.annual_pension_credits,
                    ),
                    (1, 0, 1, 10000),
                )
                cash = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="cash-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                    random_source=FixedRandom((6,)),
                )
                self.assertEqual(
                    (
                        cash.roll_modifier, cash.table_result,
                        cash.cash_awarded, cash.muster_status,
                    ),
                    (1, 7, 100000, "completed"),
                )
                replay = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="cash-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                )
                self.assertTrue(replay.replayed)
                self.assertEqual(replay.dice, (6,))

    def test_ship_shares_use_a_separately_recorded_source_roll(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "shares-muster")
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="initialize-shares-muster",
                    actor_public_id=actor_public,
                )
                result = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="ship-share-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="material",
                    random_source=FixedRandom((5, 4)),
                )
                shares = connection.execute(
                    """SELECT shares FROM actor_ship_share_state
                       WHERE actor_id=%s""",
                    (actor_id,),
                ).fetchone()[0]
                secondary = connection.execute(
                    """SELECT draw.result
                       FROM cmd_random_draw draw
                       JOIN cmd_command command
                         ON command.command_id=draw.command_id
                       WHERE command.public_id=%s
                         AND draw.draw_group='career_benefit_ship_shares'""",
                    (result.command_public_id,),
                ).fetchone()[0]
                self.assertEqual(
                    (result.outcome_kind, result.ship_shares_awarded,
                     shares, secondary),
                    ("ship_shares", 4, 4, 4),
                )

    def test_cash_cap_and_rank_material_modifier_are_enforced(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "benefit-boundaries")
                connection.execute(
                    """UPDATE actor_career_stint SET rank_number=5
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="initialize-benefit-boundaries",
                    actor_public_id=actor_public,
                )
                material = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="rank-material-modifier",
                    actor_public_id=actor_public,
                    benefit_table_code="material",
                    random_source=FixedRandom((6,)),
                )
                self.assertEqual(
                    (
                        material.roll_modifier, material.table_result,
                        material.outcome_kind,
                    ),
                    (1, 7, "membership"),
                )
                connection.execute(
                    """UPDATE actor_career_muster
                       SET eligible_term_benefits=4,
                           total_benefit_rolls=6
                       WHERE career_muster_id=(
                           SELECT muster.career_muster_id
                           FROM actor_career_muster muster
                           JOIN actor_career_stint stint
                             ON stint.career_stint_id=muster.career_stint_id
                           WHERE stint.actor_id=%s
                       )""",
                    (actor_id,),
                )
                for index in range(3):
                    roll_career_benefit_command(
                        connection, initiator_reference="player",
                        idempotency_key=f"cash-cap-{index}",
                        actor_public_id=actor_public,
                        benefit_table_code="cash",
                        random_source=FixedRandom((1,)),
                    )
                with self.assertRaisesRegex(
                    ValueError, "No more than three Cash"
                ):
                    roll_career_benefit_command(
                        connection, initiator_reference="player",
                        idempotency_key="cash-cap-four",
                        actor_public_id=actor_public,
                        benefit_table_code="cash",
                        random_source=FixedRandom((1,)),
                    )

    def test_retirement_boosts_cash_and_completes_after_final_benefit(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "retired-muster")
                connection.execute(
                    """UPDATE actor_lifepath_state
                       SET retirement_required=true WHERE actor_id=%s""",
                    (actor_id,),
                )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="initialize-retired-muster",
                    actor_public_id=actor_public,
                )
                result = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="retired-cash-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                    random_source=FixedRandom((6,)),
                )
                status = connection.execute(
                    """SELECT lifepath_status FROM actor_lifepath_state
                       WHERE actor_id=%s""",
                    (actor_id,),
                ).fetchone()[0]
                self.assertEqual(
                    (
                        result.roll_modifier, result.table_result,
                        result.cash_awarded, status,
                    ),
                    (1, 7, 100000, "completed"),
                )

    def test_weapon_benefits_pause_for_player_item_or_skill_choice(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "weapon-muster")
                connection.execute(
                    """UPDATE actor_career_stint SET rank_number=4
                       WHERE actor_id=%s""",
                    (actor_id,),
                )
                muster = initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="initialize-weapon-muster",
                    actor_public_id=actor_public,
                )
                self.assertEqual(muster.total_benefit_rolls, 2)
                first = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="first-weapon-roll",
                    actor_public_id=actor_public,
                    benefit_table_code="material",
                    random_source=FixedRandom((3,)),
                )
                self.assertEqual(
                    (first.outcome_kind, first.award_status),
                    ("weapon", "awaiting_weapon_choice"),
                )
                item = resolve_career_weapon_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="choose-dagger-item",
                    actor_public_id=actor_public,
                    weapon_rule_code="equipment.weapon.dagger",
                    resolution_kind="item",
                )
                self.assertEqual(
                    (item.resulting_value, item.muster_status), (1, "rolling"))
                roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="second-weapon-roll",
                    actor_public_id=actor_public,
                    benefit_table_code="material",
                    random_source=FixedRandom((3,)),
                )
                skill = resolve_career_weapon_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="choose-dagger-skill",
                    actor_public_id=actor_public,
                    weapon_rule_code="equipment.weapon.dagger",
                    resolution_kind="skill",
                    skill_rule_code="skill.piercing-weapons",
                )
                self.assertEqual(
                    (
                        skill.resolution_kind, skill.skill_rule_code,
                        skill.resulting_value, skill.muster_status,
                    ),
                    ("skill", "skill.piercing-weapons", 1, "completed"),
                )

    def test_every_imported_material_benefit_has_normalized_engine_meaning(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            rows = connection.execute(
                """SELECT DISTINCT source_outcome_text,outcome_kind
                   FROM rule_career_benefit
                   WHERE benefit_table_code='material'
                   ORDER BY source_outcome_text"""
            ).fetchall()
            self.assertEqual(len(rows), 13)
            self.assertNotIn(None, {row[1] for row in rows})

    def test_next_career_waits_for_completed_departure_benefits(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "transition-gate")
                with self.assertRaisesRegex(
                    ValueError, "departed career still requires"
                ):
                    attempt_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="premature-next-career",
                        actor_public_id=actor_public, career_code="agent",
                        random_source=FixedRandom((6, 6)),
                    )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="transition-muster",
                    actor_public_id=actor_public,
                )
                with self.assertRaisesRegex(
                    ValueError, "departed career still requires"
                ):
                    attempt_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="still-premature-next-career",
                        actor_public_id=actor_public, career_code="agent",
                        random_source=FixedRandom((6, 6)),
                    )
                roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="transition-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                    random_source=FixedRandom((1,)),
                )
                next_career = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="permitted-next-career",
                    actor_public_id=actor_public, career_code="agent",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertTrue(next_career.qualified)

    def test_player_explicitly_finishes_after_all_departure_choices(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                self._depart_completed_merchant(
                    connection, actor_public, "finish-gate")
                with self.assertRaisesRegex(
                    ValueError, "benefits must be completed"
                ):
                    finish_character_creation_command(
                        connection, initiator_reference="player",
                        idempotency_key="premature-finish",
                        actor_public_id=actor_public,
                    )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="finish-muster",
                    actor_public_id=actor_public,
                )
                roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="finish-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                    random_source=FixedRandom((1,)),
                )
                finished = finish_character_creation_command(
                    connection, initiator_reference="player",
                    idempotency_key="finish-character",
                    actor_public_id=actor_public,
                )
                self.assertEqual(
                    (
                        finished.age_years, finished.total_terms,
                        finished.career_stints,
                        finished.benefit_rolls_completed,
                        finished.lifepath_status,
                    ),
                    (22, 1, 1, 1, "completed"),
                )
                replay = finish_character_creation_command(
                    connection, initiator_reference="player",
                    idempotency_key="finish-character",
                    actor_public_id=actor_public,
                )
                self.assertTrue(replay.replayed)
                with self.assertRaisesRegex(ValueError, "not active"):
                    attempt_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="career-after-finish",
                        actor_public_id=actor_public, career_code="agent",
                    )

    def test_player_may_finish_without_prior_experience(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                _, actor_public = self._actor(connection)
                result = finish_character_creation_command(
                    connection, initiator_reference="player",
                    idempotency_key="finish-young-character",
                    actor_public_id=actor_public,
                )
                self.assertEqual(
                    (
                        result.age_years, result.total_terms,
                        result.career_stints, result.lifepath_status,
                    ),
                    (18, 0, 0, "completed"),
                )

    def test_paid_aging_crisis_restores_one_and_bars_qualifications(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._create_merchant_aging_crisis(
                    connection, actor_id, actor_public, "paid-aging-crisis")
                with self.assertRaisesRegex(ValueError, "aging must be resolved"):
                    determine_career_reenlistment_command(
                        connection, initiator_reference="player",
                        idempotency_key="blocked-by-aging-crisis",
                        actor_public_id=actor_public,
                        random_source=FixedRandom((6, 6)),
                    )
                connection.execute(
                    """INSERT INTO actor_financial_state
                       (actor_id,cash_credits) VALUES (%s,30000)
                       ON CONFLICT (actor_id) DO UPDATE
                       SET cash_credits=EXCLUDED.cash_credits""",
                    (actor_id,),
                )
                priced = determine_aging_crisis_cost_command(
                    connection, initiator_reference="player",
                    idempotency_key="price-aging-crisis",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((2,)),
                )
                self.assertEqual(
                    (
                        priced.cost_die, priced.medical_cost_credits,
                        priced.affordable,
                    ),
                    (2, 20000, True),
                )
                paid = resolve_aging_crisis_command(
                    connection, initiator_reference="player",
                    idempotency_key="pay-aging-crisis",
                    actor_public_id=actor_public, resolution_kind="pay",
                )
                self.assertEqual(
                    (
                        paid.cash_before, paid.cash_after,
                        paid.lifepath_status, paid.qualification_barred,
                    ),
                    (30000, 10000, "active", True),
                )
                self.assertEqual(
                    set(paid.restored_characteristic_codes),
                    {
                        "characteristic.strength",
                        "characteristic.dexterity",
                        "characteristic.endurance",
                    },
                )
                reenlistment = determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="post-crisis-reenlistment",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((3, 3)),
                )
                self.assertEqual(reenlistment.outcome, "choice_available")
                decide_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="leave-after-aging-crisis",
                    actor_public_id=actor_public, decision="leave",
                )
                initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="post-crisis-muster",
                    actor_public_id=actor_public,
                )
                roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="post-crisis-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                    random_source=FixedRandom((1,)),
                )
                failed = attempt_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="barred-agent-entry",
                    actor_public_id=actor_public, career_code="agent",
                    random_source=FixedRandom((6, 6)),
                )
                self.assertFalse(failed.qualified)
                self.assertEqual(failed.qualification_dice, ())
                with self.assertRaisesRegex(
                    ValueError, "only become a Drifter"
                ):
                    resolve_failed_career_entry_command(
                        connection, initiator_reference="player",
                        idempotency_key="barred-draft",
                        attempt_command_public_id=failed.command_public_id,
                        fallback_kind="draft",
                    )
                drifter = resolve_failed_career_entry_command(
                    connection, initiator_reference="player",
                    idempotency_key="barred-drifter",
                    attempt_command_public_id=failed.command_public_id,
                    fallback_kind="drifter",
                )
                self.assertEqual(drifter.resulting_career_code, "drifter")

    def test_unpaid_aging_crisis_accepts_death_without_spending_cash(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._create_merchant_aging_crisis(
                    connection, actor_id, actor_public, "fatal-aging-crisis")
                connection.execute(
                    """INSERT INTO actor_financial_state
                       (actor_id,cash_credits) VALUES (%s,5000)
                       ON CONFLICT (actor_id) DO UPDATE
                       SET cash_credits=EXCLUDED.cash_credits""",
                    (actor_id,),
                )
                determine_aging_crisis_cost_command(
                    connection, initiator_reference="player",
                    idempotency_key="price-fatal-aging-crisis",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((6,)),
                )
                with self.assertRaisesRegex(ValueError, "cannot afford"):
                    resolve_aging_crisis_command(
                        connection, initiator_reference="player",
                        idempotency_key="unaffordable-aging-care",
                        actor_public_id=actor_public, resolution_kind="pay",
                    )
                death = resolve_aging_crisis_command(
                    connection, initiator_reference="player",
                    idempotency_key="accept-aging-death",
                    actor_public_id=actor_public,
                    resolution_kind="accept_death",
                )
                self.assertEqual(
                    (
                        death.cash_before, death.cash_after,
                        death.lifepath_status, death.qualification_barred,
                        death.restored_characteristic_codes,
                    ),
                    (5000, 5000, "deceased", False, ()),
                )
                replay = resolve_aging_crisis_command(
                    connection, initiator_reference="player",
                    idempotency_key="accept-aging-death",
                    actor_public_id=actor_public,
                    resolution_kind="accept_death",
                )
                self.assertTrue(replay.replayed)

    def test_medical_care_uses_employer_coverage_and_cash_pays_debt_first(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            with connection.transaction(force_rollback=True):
                actor_id, actor_public = self._actor(connection)
                self._complete_first_merchant_term(
                    connection, actor_public, "medical-care")
                determine_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-care-reenlistment",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((3, 3)),
                )
                decide_career_reenlistment_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-care-continue",
                    actor_public_id=actor_public, decision="continue",
                )
                attempt_career_survival_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-care-failed-survival",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1, 1)),
                )
                resolve_survival_mishap_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-care-injury-mishap",
                    actor_public_id=actor_public,
                    random_source=FixedRandom((1,)),
                )
                determine_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-care-severe-injury",
                    actor_public_id=actor_public,
                    result_two_choice="fixed_two",
                )
                apply_career_injury_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-care-apply-injury",
                    actor_public_id=actor_public,
                    primary_characteristic_code="characteristic.endurance",
                    random_source=FixedRandom((4,)),
                )
                with self.assertRaisesRegex(
                    ValueError, "medical-care decision"
                ):
                    initialize_career_muster_command(
                        connection, initiator_reference="player",
                        idempotency_key="premature-medical-muster",
                        actor_public_id=actor_public,
                    )
                care = resolve_career_medical_care_command(
                    connection, initiator_reference="player",
                    idempotency_key="purchase-medical-care",
                    actor_public_id=actor_public, decision="purchase",
                    restoration_points={
                        "characteristic.endurance": 2,
                    },
                    random_source=FixedRandom((4, 4)),
                )
                self.assertEqual(
                    (
                        care.rank_number, care.employer_dice,
                        care.employer_roll_total,
                        care.employer_coverage_percent,
                        care.gross_cost_credits,
                        care.employer_paid_credits,
                        care.character_cost_credits,
                        care.medical_debt_after,
                        care.restorations[0].resulting_value,
                    ),
                    (0, (4, 4), 8, 75, 10000, 7500, 2500, 2500, 5),
                )
                muster = initialize_career_muster_command(
                    connection, initiator_reference="player",
                    idempotency_key="post-medical-muster",
                    actor_public_id=actor_public,
                )
                self.assertEqual(muster.total_benefit_rolls, 1)
                benefit = roll_career_benefit_command(
                    connection, initiator_reference="player",
                    idempotency_key="medical-debt-cash-benefit",
                    actor_public_id=actor_public,
                    benefit_table_code="cash",
                    random_source=FixedRandom((3,)),
                )
                finance = connection.execute(
                    """SELECT cash_credits,debt_credits,medical_debt_credits
                       FROM actor_financial_state WHERE actor_id=%s""",
                    (actor_id,),
                ).fetchone()
                self.assertEqual(
                    (
                        benefit.cash_awarded,
                        benefit.medical_debt_paid,
                        benefit.cash_retained,
                        finance,
                    ),
                    (10000, 2500, 7500, (7500, 0, 0)),
                )
                replay = resolve_career_medical_care_command(
                    connection, initiator_reference="player",
                    idempotency_key="purchase-medical-care",
                    actor_public_id=actor_public, decision="purchase",
                    restoration_points={
                        "characteristic.endurance": 2,
                    },
                )
                self.assertTrue(replay.replayed)

    def test_medical_coverage_table_classifies_every_imported_career(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as connection:
            count = connection.execute(
                "SELECT count(*) FROM rule_career_medical_coverage"
            ).fetchone()[0]
            self.assertEqual(count, 24)
