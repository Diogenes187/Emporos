import os
import unittest
import uuid

import psycopg


@unittest.skipUnless(os.environ.get("BASE_CEPHEUS_DATABASE_URL"), "requires PostgreSQL")
class WildernessGenerationTests(unittest.TestCase):
    def _campaign(self, connection):
        return connection.execute("INSERT INTO camp_campaign(name) VALUES(%s) RETURNING campaign_id", (f"Wild {uuid.uuid4().hex}",)).fetchone()[0]

    def _animal(self, connection, campaign, code, animal_type, subtype, terrain="hills"):
        subtype_id = connection.execute("SELECT rule_id FROM rule_animal_subtype WHERE subtype_code=%s", (subtype,)).fetchone()[0]
        return connection.execute(
            """INSERT INTO camp_animal_definition(campaign_id,definition_code,terrain_code,animal_type,subtype_rule_id,movement_code,
                   weight_kg,strength,dexterity,endurance,intelligence,instinct,pack,number_appearing_dice,number_appearing_sides,armor_rating,speed_meters)
               VALUES(%s,%s,%s,%s,%s,'W',100,10,10,10,1,7,7,2,6,1,12) RETURNING animal_definition_id""",
            (campaign, code, terrain, animal_type, subtype_id),
        ).fetchone()[0]

    def test_generated_chaser_is_reproducible_and_immutable(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                campaign = self._campaign(c)
                subtype = c.execute("SELECT rule_id FROM rule_animal_subtype WHERE subtype_code='chaser'").fetchone()[0]
                animal = c.execute(
                    """INSERT INTO camp_animal_definition(campaign_id,definition_code,name,terrain_code,animal_type,subtype_rule_id,movement_code,
                           weight_kg,strength,dexterity,endurance,intelligence,instinct,pack,number_appearing_dice,number_appearing_sides,armor_rating,speed_meters)
                       VALUES(%s,'ridge-chaser','Ridge Chaser','hills','carnivore',%s,'W',100,10,12,9,1,10,7,2,6,1,12)
                       RETURNING animal_definition_id""", (campaign, subtype)).fetchone()[0]
                with c.cursor() as cursor:
                    cursor.executemany("INSERT INTO camp_animal_definition_skill VALUES(%s,%s,%s,%s)", [
                        (animal, "athletics", 0, "baseline"), (animal, "recon", 0, "baseline"),
                        (animal, "survival", 0, "baseline"), (animal, "natural-weapons", 3, "rolled")])
                c.execute("INSERT INTO camp_animal_definition_skill_source VALUES(%s,'athletics','subtype')", (animal,))
                c.execute("INSERT INTO camp_animal_definition_weapon VALUES(%s,'claws',2,1)", (animal,))
                receipt = c.execute(
                    """INSERT INTO cmd_animal_generation_receipt(animal_definition_id,campaign_id,movement_roll,subtype_roll,subtype_adjusted_total,
                           size_roll,size_adjusted_total,strength_roll_total,dexterity_roll_total,endurance_roll_total,instinct_roll,pack_roll,
                           skill_pool_roll,allocated_skill_ranks,weapon_roll,weapon_adjusted_total,armor_roll,armor_adjusted_total,speed_roll,speed_multiplier)
                       VALUES(%s,%s,1,7,7,7,7,10,8,9,8,5,3,3,2,10,7,5,4,2) RETURNING animal_generation_receipt_id""",
                    (animal, campaign)).fetchone()[0]
                self.assertGreater(receipt, 0)
                summary = c.execute("SELECT subtype_code,skills,weapons FROM camp_generated_animal_summary WHERE animal_definition_id=%s", (animal,)).fetchone()
                self.assertEqual(summary[0], "chaser")
                self.assertIn("natural-weapons-3", summary[1])
                self.assertEqual(summary[2], "claws (2D6)")
                with self.assertRaisesRegex(psycopg.Error, "immutable"):
                    with c.transaction(): c.execute("UPDATE camp_animal_definition SET speed_meters=18 WHERE animal_definition_id=%s", (animal,))

    def test_finalized_table_and_occurrence_are_audited(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            with c.transaction(force_rollback=True):
                campaign = self._campaign(c)
                animals = {
                    "scavenger": self._animal(c,campaign,"scav","scavenger","reducer"),
                    "herbivore": self._animal(c,campaign,"herb","herbivore","grazer"),
                    "omnivore": self._animal(c,campaign,"omni","omnivore","hunter"),
                    "carnivore": self._animal(c,campaign,"carn","carnivore","chaser"),
                }
                table = c.execute("INSERT INTO camp_wilderness_encounter_table(campaign_id,table_code,terrain_code,template_code,title) VALUES(%s,'hills','hills','1d6','Hills') RETURNING wilderness_encounter_table_id", (campaign,)).fetchone()[0]
                kinds = ["scavenger","herbivore","herbivore","herbivore","omnivore","carnivore"]
                for roll, kind in enumerate(kinds, 1):
                    c.execute("INSERT INTO camp_wilderness_encounter_entry VALUES(%s,%s,'animal',%s,NULL)", (table, roll, animals[kind]))
                c.execute("INSERT INTO cmd_wilderness_table_finalization_receipt(wilderness_encounter_table_id,campaign_id,entry_count) VALUES(%s,%s,6)", (table,campaign))
                c.execute("""INSERT INTO enc_wilderness_occurrence_receipt(campaign_id,wilderness_encounter_table_id,check_date,check_phase,
                           occurrence_roll,encounter_occurred,table_roll_total,result_kind,animal_definition_id)
                           VALUES(%s,%s,CURRENT_DATE,'travelling',5,true,6,'animal',%s)""", (campaign,table,animals["carnivore"]))
                self.assertEqual(c.execute("SELECT finalized,entry_count FROM camp_wilderness_encounter_table_summary WHERE wilderness_encounter_table_id=%s", (table,)).fetchone(), (True,6))
                with self.assertRaisesRegex(psycopg.Error, r"5\+"):
                    with c.transaction(): c.execute("INSERT INTO enc_wilderness_occurrence_receipt(campaign_id,wilderness_encounter_table_id,check_date,check_phase,occurrence_roll,encounter_occurred) VALUES(%s,%s,CURRENT_DATE,'halted',4,true)", (campaign,table))

    def test_catalogue_matches_published_dimensions(self):
        with psycopg.connect(os.environ["BASE_CEPHEUS_DATABASE_URL"]) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM rule_animal_terrain").fetchone()[0], 16)
            self.assertEqual(c.execute("SELECT count(*) FROM rule_animal_terrain_movement").fetchone()[0], 96)
            self.assertEqual(c.execute("SELECT count(*) FROM rule_animal_subtype_band").fetchone()[0], 52)
            self.assertEqual(c.execute("SELECT count(*) FROM rule_animal_size_band").fetchone()[0], 20)
            self.assertEqual(c.execute("SELECT count(*) FROM rule_animal_subtype_skill").fetchone()[0], 7)
            rows = c.execute("""SELECT r.rule_code,count(DISTINCT w.work_code) FROM src_record_provenance p JOIN rule_rule r USING(rule_id)
                                JOIN src_locator l USING(source_locator_id) JOIN src_work w USING(source_work_id)
                                WHERE r.rule_code IN('encounter.wilderness-animal-generation','encounter.wilderness-table-generation','encounter.wilderness-occurrence')
                                GROUP BY r.rule_code ORDER BY r.rule_code""").fetchall()
            self.assertEqual(rows, [('encounter.wilderness-animal-generation',2),('encounter.wilderness-occurrence',2),('encounter.wilderness-table-generation',2)])
