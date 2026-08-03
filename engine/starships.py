"""Noncombat starship encounter occurrence, category, and contact range."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class StarshipEncounterResult:
    command_public_id: str
    encounter_public_id: str | None
    occurred: bool
    occurrence_dice: tuple[int, ...]
    category_dice: tuple[int, ...]
    category_code: str | None
    referee_choice_required: bool
    type_was_chosen: bool
    comms_dice: tuple[int, ...]
    comms_total: int | None
    comms_succeeded: bool | None
    initial_range: str | None
    subtype_dice: tuple[int, ...]
    subtype_result_code: str | None
    subtype_result_name: str | None
    subtype_result_kind: str | None
    replayed: bool


def _draws(connection, command_id, group):
    return tuple(row[0] for row in connection.execute(
        """SELECT result FROM cmd_random_draw WHERE command_id=%s
           AND draw_group=%s ORDER BY draw_order""",
        (command_id, group),
    ).fetchall())


def _load_result(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT e.public_id,r.encounter_occurred,r.category_rule_id,
                  category.category_code,r.referee_choice,r.type_was_chosen,
                  contact.comms_check_total,contact.comms_succeeded,
                  contact.final_range,resolution.final_result_code,
                  subtype.result_name,subtype.result_kind
           FROM cmd_starship_encounter_receipt r
           LEFT JOIN enc_encounter e ON e.encounter_id=r.encounter_id
           LEFT JOIN rule_starship_encounter_category category
             ON category.rule_id=r.category_rule_id
           LEFT JOIN enc_starship_contact contact
             ON contact.encounter_id=r.encounter_id
           LEFT JOIN cmd_starship_subtype_resolution_receipt resolution
             ON resolution.command_id=r.command_id
           LEFT JOIN rule_starship_encounter_result subtype
             ON subtype.result_code=resolution.final_result_code
           WHERE r.command_id=%s""", (command_id,)
    ).fetchone()
    return StarshipEncounterResult(
        str(public_id), str(row[0]) if row[0] else None, row[1],
        _draws(connection, command_id, "occurrence"),
        _draws(connection, command_id, "encounter_type"), row[3], row[4],
        row[5], _draws(connection, command_id, "task"), row[6], row[7],
        row[8], tuple(value for (value,) in connection.execute(
            """SELECT roll_result FROM cmd_starship_subtype_draw
               WHERE command_id=%s ORDER BY draw_sequence""", (command_id,))),
        row[9], row[10], row[11], replayed)


def check_starship_encounter_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, campaign_public_id: str, region_context: str,
    comms_skill_modifier: int = 0, comms_characteristic_modifier: int = 0,
    comms_circumstance_modifiers: tuple[int, ...] = (),
    target_transponder_active: bool = False, target_stealth_modifier: int = 0,
    chosen_category_code: str | None = None, random_source=None,
) -> StarshipEncounterResult:
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
               AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("check_starship_encounter", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_result(
                connection, existing[0], existing[1], replayed=True)
        campaign = connection.execute(
            """SELECT campaign_id,owner_reference FROM camp_campaign
               WHERE public_id=%s FOR UPDATE""", (campaign_public_id,)
        ).fetchone()
        if campaign is None:
            raise ValueError("Campaign does not exist")
        if campaign[1] != initiator_reference:
            raise PermissionError("Initiator does not own this campaign")
        if region_context not in ("deep_space", "near_planet"):
            raise ValueError("Unknown starship encounter region context")
        system = connection.execute(
            """SELECT occurrence_dice_count,occurrence_die_sides,
                      occurrence_target,type_dice_count,type_die_sides,
                      deep_space_initial_range,near_planet_initial_range,
                      failed_comms_moves_one_category_closer,
                      active_transponder_detection_modifier
               FROM rule_starship_encounter_system""").fetchone()
        core = connection.execute(
            "SELECT dice_count,die_sides,target_number FROM rule_check_system"
        ).fetchone()
        occurrence = tuple(
            rng.randint(1, system[1]) for _ in range(system[0]))
        occurred = sum(occurrence) >= system[2]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('check_starship_encounter',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, value in enumerate(occurrence, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'occurrence',%s,%s,%s)""",
                (command_id, order, system[1], value))
        encounter_id = category_id = None
        encounter_public = None
        category_roll = None
        referee_choice = False
        type_was_chosen = False
        transponder_modifier = stealth_modifier = None
        if occurred:
            if chosen_category_code:
                type_was_chosen = True
                category = connection.execute(
                    """SELECT rule_id FROM rule_starship_encounter_category
                       WHERE category_code=%s""", (chosen_category_code,)
                ).fetchone()
                if category is None:
                    raise ValueError("Chosen starship category does not exist")
                category_id = category[0]
            else:
                category_dice = tuple(
                    rng.randint(1, system[4]) for _ in range(system[3]))
                category_roll = sum(category_dice)
                for order, value in enumerate(category_dice, 1):
                    connection.execute(
                        """INSERT INTO cmd_random_draw
                           (command_id,draw_group,draw_order,die_sides,result)
                           VALUES (%s,'encounter_type',%s,%s,%s)""",
                        (command_id, order, system[4], value))
                category_id, referee_choice = connection.execute(
                    """SELECT category_rule_id,referee_choice
                       FROM rule_starship_encounter_roll
                       WHERE roll_total=%s""", (category_roll,)
                ).fetchone()
            encounter_type = connection.execute(
                """SELECT rule_id FROM rule_encounter_type
                   WHERE encounter_type_code='starship'""").fetchone()[0]
            encounter_id, encounter_public = connection.execute(
                """INSERT INTO enc_encounter
                   (campaign_id,encounter_type_rule_id,current_mode)
                   VALUES (%s,%s,'starship') RETURNING encounter_id,public_id""",
                (campaign[0], encounter_type),
            ).fetchone()
            comms_dice = tuple(
                rng.randint(1, core[1]) for _ in range(core[0]))
            for order, value in enumerate(comms_dice, 1):
                connection.execute(
                    """INSERT INTO cmd_random_draw
                       (command_id,draw_group,draw_order,die_sides,result)
                       VALUES (%s,'task',%s,%s,%s)""",
                    (command_id, order, core[1], value))
            transponder_modifier = (
                system[8] if target_transponder_active else 0)
            stealth_modifier = target_stealth_modifier
            comms_total = (
                sum(comms_dice) + comms_skill_modifier
                + comms_characteristic_modifier
                + sum(comms_circumstance_modifiers)
                + transponder_modifier + stealth_modifier)
            comms_succeeded = comms_total >= core[2]
            base_range = system[5] if region_context == "deep_space" else system[6]
            closer = {"very_long": "long", "medium": "short"}
            final_range = (
                base_range if comms_succeeded or not system[7]
                else closer[base_range])
            connection.execute(
                """INSERT INTO enc_starship_contact
                   (encounter_id,category_rule_id,region_context,base_range,
                    comms_check_total,comms_target_number,comms_succeeded,
                    final_range,contact_status)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (encounter_id, category_id, region_context, base_range,
                 comms_total, core[2], comms_succeeded, final_range,
                 "requires_referee_category" if referee_choice
                 else "established"))
        connection.execute(
            """INSERT INTO cmd_starship_encounter_receipt
               (command_id,campaign_id,encounter_id,encounter_occurred,
                occurrence_total,category_roll_total,category_rule_id,
                type_was_chosen,referee_choice,region_context,
                comms_skill_modifier,comms_characteristic_modifier,
                comms_circumstance_total,transponder_modifier,stealth_modifier)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, campaign[0], encounter_id, occurred, sum(occurrence),
             category_roll, category_id, type_was_chosen, referee_choice,
             region_context, comms_skill_modifier if occurred else None,
             comms_characteristic_modifier if occurred else None,
             sum(comms_circumstance_modifiers) if occurred else None,
             transponder_modifier, stealth_modifier))
        if occurred and category_id is not None:
            subtable_code = connection.execute(
                "SELECT category_code FROM rule_starship_encounter_category WHERE rule_id=%s",
                (category_id,),
            ).fetchone()[0]
            subtype_sequence = 0
            while subtable_code is not None:
                subtype_sequence += 1
                subtype_roll = rng.randint(1, 6)
                subtype_result, next_subtable = connection.execute(
                    """SELECT roll.result_code,result.next_subtable_code
                       FROM rule_starship_encounter_subtype_roll roll
                       JOIN rule_starship_encounter_result result USING(result_code)
                       WHERE roll.subtable_code=%s AND roll.roll_total=%s""",
                    (subtable_code, subtype_roll),
                ).fetchone()
                connection.execute(
                    """INSERT INTO cmd_starship_subtype_draw
                       (command_id,draw_sequence,subtable_code,die_sides,roll_result,result_code)
                       VALUES(%s,%s,%s,6,%s,%s)""",
                    (command_id, subtype_sequence, subtable_code, subtype_roll, subtype_result),
                )
                subtable_code = next_subtable
            connection.execute(
                """INSERT INTO cmd_starship_subtype_resolution_receipt
                   (command_id,encounter_id,category_rule_id,draw_count,final_result_code,source_command_id)
                   VALUES(%s,%s,%s,%s,%s,%s)""",
                (command_id, encounter_id, category_id, subtype_sequence, subtype_result, command_id),
            )
        if occurred:
            for order, value in enumerate(comms_circumstance_modifiers, 1):
                connection.execute(
                    "INSERT INTO cmd_starship_comms_modifier VALUES (%s,%s,%s)",
                    (command_id, order, value))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, "starship_contact_created" if occurred
             else "starship_encounter_checked"))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_result(connection, command_id, public_id, replayed=False)
