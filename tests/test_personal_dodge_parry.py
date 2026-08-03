import os
import unittest
import psycopg
from psycopg.errors import RaiseException
from engine.combat_runtime import (
    begin_personal_turn_command,complete_personal_turn_command,
    declare_personal_attack_command,declare_personal_reaction_command)
from engine.commands import resolve_personal_attack_command
from tests import test_combat_runtime as combat_tests

DSN=os.environ.get("BASE_CEPHEUS_DATABASE_URL")

@unittest.skipUnless(DSN,"requires the project PostgreSQL database")
class PersonalDodgeParryTests(unittest.TestCase):
    def test_options_have_paired_provenance(self):
        with psycopg.connect(DSN) as c:
            rows=c.execute("""SELECT option.reaction_kind,count(provenance.rule_id)
              FROM rule_personal_reaction_option option
              JOIN src_record_provenance provenance USING(rule_id)
              GROUP BY option.rule_id ORDER BY option.reaction_kind""").fetchall()
        self.assertEqual(rows,[("dodge",2),("parry",2)])

    def test_parry_uses_held_ready_weapon_skill_snapshot(self):
        with psycopg.connect(DSN) as c:
          with c.transaction(force_rollback=True):
            encounter,actors=(combat_tests.PersonalCombatRuntimeIntegrationTests()
                              ._initialized_combat(c))
            actor_id,campaign_id=c.execute("SELECT actor_id,campaign_id FROM actor_actor WHERE public_id=%s",(actors[0],)).fetchone()
            c.execute("""INSERT INTO actor_skill(actor_id,skill_rule_id,skill_level)
              SELECT %s,rule_id,2 FROM rule_rule WHERE rule_code='skill.piercing-weapons'""",(actor_id,))
            c.execute("""INSERT INTO actor_weapon_state(actor_id,weapon_rule_id,ready)
              SELECT %s,rule_id,true FROM rule_rule WHERE rule_code='equipment.weapon.dagger'""",(actor_id,))
            container=c.execute("INSERT INTO inv_container(campaign_id,name) VALUES (%s,'Parry hand') RETURNING container_id",(campaign_id,)).fetchone()[0]
            c.execute("INSERT INTO inv_actor_container VALUES (%s,%s,%s)",(container,campaign_id,actor_id))
            weapon_id,weapon_public=c.execute("""INSERT INTO inv_item_instance(campaign_id,item_rule_id,instance_name)
              SELECT %s,rule_id,'Readied dagger' FROM rule_rule WHERE rule_code='equipment.weapon.dagger'
              RETURNING item_instance_id,public_id""",(campaign_id,)).fetchone()
            c.execute("INSERT INTO inv_container_item VALUES (%s,%s,%s,DEFAULT,NULL)",(weapon_id,campaign_id,container))
            begin_personal_turn_command(c,initiator_reference="player",idempotency_key="parry-player-begin",encounter_public_id=encounter,actor_public_id=actors[0])
            complete_personal_turn_command(c,initiator_reference="player",idempotency_key="parry-player-finish",encounter_public_id=encounter,actor_public_id=actors[0])
            begin_personal_turn_command(c,initiator_reference="referee",idempotency_key="parry-attacker-begin",encounter_public_id=encounter,actor_public_id=actors[2])
            attack=declare_personal_attack_command(c,initiator_reference="referee",idempotency_key="parry-attack",encounter_public_id=encounter,attacker_actor_public_id=actors[2],target_actor_public_id=actors[0],item_rule_code="equipment.weapon.dagger",attack_profile_code="close-quarters",range_rule_code="combat.range.personal")
            declare_personal_reaction_command(c,initiator_reference="player",idempotency_key="parry-reaction",encounter_public_id=encounter,actor_public_id=actors[0],attack_trigger_reference=attack.personal_attack_public_id,reaction_kind="parry",parrying_weapon_rule_code="equipment.weapon.dagger",parrying_weapon_item_instance_public_id=str(weapon_public))
            snapshot=c.execute("""SELECT skill.rule_code,receipt.parry_skill_modifier FROM cmd_personal_reaction_receipt receipt JOIN rule_rule skill ON skill.rule_id=receipt.parry_skill_rule_id WHERE receipt.reaction_kind='parry'""").fetchone()
            self.assertEqual(snapshot,("skill.piercing-weapons",2))
            result=resolve_personal_attack_command(c,initiator_reference="referee",idempotency_key="parry-resolve",item_rule_code="equipment.weapon.dagger",attack_profile_code="close-quarters",range_rule_code="combat.range.personal",armor_rule_code="equipment.armor.jack",target_actor_public_id=actors[0],personal_attack_public_id=attack.personal_attack_public_id,random_source=combat_tests.FixedRandom((4,4,4)))
            self.assertIn(-2,result.receipt.circumstance_modifiers)
            command_id=c.execute("SELECT command_id FROM cmd_command WHERE idempotency_key='parry-reaction'").fetchone()[0]
            with self.assertRaises(RaiseException):
              with c.transaction(): c.execute("UPDATE cmd_personal_reaction_receipt SET parry_skill_modifier=0 WHERE command_id=%s",(command_id,))

if __name__=="__main__": unittest.main()
