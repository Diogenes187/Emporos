"""Transactional CE-COMBAT-016 ground-force starship volleys."""
from dataclasses import dataclass
import secrets

import psycopg

from engine.scale_combat import resolve_ground_starship_damage


@dataclass(frozen=True)
class GroundStarshipVolleyResult:
    command_public_id: str
    volley_status: str
    successful_attack_count: int
    attacks: tuple[tuple[int, str, int, bool, int], ...]
    replayed: bool


@dataclass(frozen=True)
class GroundStarshipFinalResult:
    command_public_id: str
    volley_command_public_id: str
    combined_damage_dice: int
    personal_scale_damage: int
    converted_damage: int
    armor_rating: int
    hull_damage: int
    hull_before: int
    hull_after: int
    replayed: bool


def _load_volley(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT volley.volley_status,volley.successful_attack_count
           FROM cmd_ground_starship_volley volley
           WHERE volley.command_id=%s""", (command_id,)).fetchone()
    attacks = tuple(connection.execute(
        """SELECT attack.attack_order,battery.public_id,
                  attack.attack_total,attack.hit,attack.damage_dice_count
           FROM cmd_ground_starship_volley_attack attack
           JOIN gf_ground_weapon_battery battery USING (
             ground_weapon_battery_id)
           WHERE attack.command_id=%s ORDER BY attack.attack_order""",
        (command_id,)).fetchall())
    return GroundStarshipVolleyResult(
        str(public_id), row[0], row[1],
        tuple((a[0], str(a[1]), a[2], a[3], a[4]) for a in attacks),
        replayed,
    )


def _load_final(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT volley_command.public_id,receipt.combined_damage_dice,
                  receipt.personal_scale_damage,receipt.converted_damage,
                  receipt.armor_rating,receipt.hull_damage,
                  receipt.hull_before,receipt.hull_after
           FROM cmd_ground_starship_volley_final_receipt receipt
           JOIN cmd_command volley_command
             ON volley_command.command_id=receipt.volley_command_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    return GroundStarshipFinalResult(
        str(public_id), str(row[0]), *row[1:], replayed)


def resolve_ground_starship_volley_attacks_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, target_ship_public_id: str,
    target_range_code: str,
    batteries: tuple[tuple[str, int], ...], random_source=None,
) -> GroundStarshipVolleyResult:
    """Roll every weapon attack and consume its ammunition atomically."""
    if not batteries or any(quantity <= 0 for _, quantity in batteries):
        raise ValueError("Volley requires positive battery quantities")
    if len({public for public, _ in batteries}) != len(batteries):
        raise ValueError("Each battery may appear only once")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != (
                "resolve_ground_starship_volley_attacks", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_volley(
                connection, existing[0], existing[1], True)
        target = connection.execute(
            """SELECT ship.ship_id,ship.campaign_id,
                      clock.day_number,clock.second_of_day
               FROM ship_ship ship
               JOIN camp_clock clock ON clock.campaign_id=ship.campaign_id
               WHERE ship.public_id=%s
                 AND ship.lifecycle_status NOT IN ('destroyed','scrapped')
               FOR UPDATE OF ship,clock""",
            (target_ship_public_id,)).fetchone()
        if target is None:
            raise ValueError("Active target starship does not exist")
        loaded = []
        for public_id, quantity in batteries:
            battery = connection.execute(
                """SELECT battery.ground_weapon_battery_id,
                          battery.weapon_rule_id,
                          battery.operational_weapon_count,
                          battery.ammunition_remaining,
                          battery.operator_actor_id,
                          weapon.damage_dice_count,
                          difficulty.rule_id,difficulty.modifier,
                          COALESCE(skill.skill_level,
                                   skill_rule.untrained_modifier),
                          characteristic.current_value,
                          characteristic.characteristic_rule_id
                   FROM gf_ground_weapon_battery battery
                   JOIN rule_vehicle_weapon_definition weapon
                     ON weapon.weapon_rule_id=battery.weapon_rule_id
                   JOIN rule_vehicle_weapon_range_difficulty matrix
                     ON matrix.range_profile_code=weapon.range_profile_code
                    AND matrix.target_range_code=%s
                   JOIN rule_difficulty difficulty
                     ON difficulty.rule_id=matrix.difficulty_rule_id
                   JOIN rule_skill skill_rule
                     ON skill_rule.rule_id=battery.governing_skill_rule_id
                   JOIN actor_actor operator
                     ON operator.actor_id=battery.operator_actor_id
                    AND operator.controller_reference=%s
                   LEFT JOIN actor_skill skill
                     ON skill.actor_id=operator.actor_id
                    AND skill.skill_rule_id=battery.governing_skill_rule_id
                   JOIN rule_rule dexterity_rule
                     ON dexterity_rule.rule_code=
                        'characteristic.dexterity'
                   JOIN actor_characteristic characteristic
                     ON characteristic.actor_id=operator.actor_id
                    AND characteristic.characteristic_rule_id=
                        dexterity_rule.rule_id
                   WHERE battery.public_id=%s
                     AND battery.campaign_id=%s AND battery.active
                   FOR UPDATE OF battery,operator,characteristic""",
                (target_range_code, initiator_reference, public_id,
                 target[1])).fetchone()
            if battery is None:
                raise ValueError(
                    "Controlled active battery lacks a legal range profile")
            if quantity > battery[2]:
                raise ValueError("Volley exceeds operational weapon count")
            if battery[3] is not None and quantity > battery[3]:
                raise ValueError("Battery lacks ammunition for volley")
            dexterity_modifier = connection.execute(
                """SELECT modifier FROM rule_characteristic_modifier_band
                   WHERE (characteristic_rule_id IS NULL
                          OR characteristic_rule_id=%s)
                     AND score_range @> %s::integer
                   ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
                (battery[10], battery[9])).fetchone()[0]
            loaded.append((public_id, quantity, battery, dexterity_modifier))
        command_id, command_public = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('resolve_ground_starship_volley_attacks',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        attack_rows = []
        draw_order = 0
        attack_order = 0
        for _public, quantity, battery, dexterity_modifier in loaded:
            for unit_order in range(1, quantity+1):
                attack_order += 1
                dice = (rng.randint(1, 6), rng.randint(1, 6))
                for die in dice:
                    draw_order += 1
                    connection.execute(
                        """INSERT INTO cmd_random_draw
                           (command_id,draw_group,draw_order,die_sides,result)
                           VALUES (%s,'attack',%s,6,%s)""",
                        (command_id, draw_order, die))
                total = (
                    sum(dice)+battery[8]+dexterity_modifier+battery[7]+4)
                ammo_before = (
                    None if battery[3] is None
                    else battery[3]-unit_order+1)
                ammo_after = (
                    None if ammo_before is None else ammo_before-1)
                attack_rows.append((
                    attack_order, battery[0], unit_order, battery[1],
                    battery[6], *dice, battery[8], dexterity_modifier,
                    battery[7], total, total-8, total >= 8, battery[5],
                    ammo_before, ammo_after))
            connection.execute(
                """UPDATE gf_ground_weapon_battery
                   SET ammunition_remaining=CASE
                         WHEN ammunition_remaining IS NULL THEN NULL
                         ELSE ammunition_remaining-%s END,
                       concurrency_version=concurrency_version+1
                   WHERE ground_weapon_battery_id=%s""",
                (quantity, battery[0]))
        hits = sum(row[12] for row in attack_rows)
        status = "awaiting_primary" if hits else "missed"
        connection.execute(
            """INSERT INTO cmd_ground_starship_volley
               VALUES (%s,%s,%s,%s,%s,%s,4,%s,%s)""",
            (command_id, target[0], target[1], target[2], target[3],
             target_range_code, status, hits))
        for row in attack_rows:
            connection.execute(
                """INSERT INTO cmd_ground_starship_volley_attack
                   (command_id,campaign_id,attack_order,
                    ground_weapon_battery_id,weapon_unit_order,
                    weapon_rule_id,difficulty_rule_id,
                    attack_die_one,attack_die_two,skill_modifier,
                    characteristic_modifier,difficulty_modifier,
                    scale_modifier,attack_total,target_number,effect,hit,
                    damage_dice_count,ammunition_before,ammunition_after)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,4,
                           %s,8,%s,%s,%s,%s,%s)""",
                (command_id, target[1], *row[:10], *row[10:]))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_volley(
            connection, command_id, command_public, False)


def finalize_ground_starship_volley_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, volley_command_public_id: str,
    primary_attack_order: int, random_source=None,
) -> GroundStarshipFinalResult:
    """Select a successful primary hit and commit converted Hull damage."""
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != (
                "finalize_ground_starship_volley", "completed"
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_final(
                connection, existing[0], existing[1], True)
        volley = connection.execute(
            """SELECT volley.command_id,volley.target_ship_id,
                      volley.campaign_id,ship.hull_current,
                      ship.concurrency_version,ship.ship_class_rule_id
               FROM cmd_ground_starship_volley volley
               JOIN cmd_command command USING (command_id)
               JOIN ship_ship ship ON ship.ship_id=volley.target_ship_id
               WHERE command.public_id=%s
                 AND command.initiator_reference=%s
                 AND volley.volley_status='awaiting_primary'
               FOR UPDATE OF volley,ship""",
            (volley_command_public_id, initiator_reference)).fetchone()
        if volley is None:
            raise ValueError("Volley is not available for finalization")
        attacks = connection.execute(
            """SELECT attack_order,damage_dice_count,hit
               FROM cmd_ground_starship_volley_attack
               WHERE command_id=%s ORDER BY attack_order""",
            (volley[0],)).fetchall()
        primary = next(
            (row for row in attacks if row[0] == primary_attack_order), None)
        if primary is None or not primary[2]:
            raise ValueError("Primary weapon must be a successful attack")
        additional = tuple(
            row[1] for row in attacks
            if row[2] and row[0] != primary_attack_order)
        armor = connection.execute(
            """SELECT COALESCE(
                 (SELECT armor_value
                    FROM ship_class_published_armor
                   WHERE ship_class_rule_id=%s),
                 (SELECT characteristic_value::integer
                    FROM ship_class_characteristic
                   WHERE ship_class_rule_id=%s
                     AND characteristic_code='armor'),0)""",
            (volley[5], volley[5])).fetchone()[0]
        combined = primary[1] + sum(additional)//2
        rolls = tuple(rng.randint(1, 6) for _ in range(combined))
        resolved = resolve_ground_starship_damage(
            primary_damage_dice=primary[1],
            additional_successful_damage_dice=additional,
            damage_rolls=rolls, armor_rating=armor)
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('finalize_ground_starship_volley',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        for order, die in enumerate(rolls, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'damage',%s,6,%s)""",
                (command_id, order, die))
        hull_after = max(0, volley[3]-resolved.hull_damage)
        ship_damage_id = None
        if resolved.hull_damage:
            ship_damage_id = connection.execute(
                """INSERT INTO ship_damage
                   (ship_id,campaign_id,target_kind,damage_points,
                    description,source_command_id)
                   VALUES (%s,%s,'hull',%s,
                     'Ground-force simultaneous starship-scale volley',%s)
                   RETURNING ship_damage_id""",
                (volley[1], volley[2], resolved.hull_damage,
                 command_id)).fetchone()[0]
        connection.execute(
            """UPDATE ship_ship SET hull_current=%s,
                      concurrency_version=concurrency_version+1
               WHERE ship_id=%s""", (hull_after, volley[1]))
        connection.execute(
            """INSERT INTO cmd_ground_starship_volley_final_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                       %s,%s,%s)""",
            (command_id, volley[0], primary_attack_order,
             resolved.primary_damage_dice,
             resolved.additional_damage_dice,
             resolved.contributed_additional_dice,
             resolved.combined_damage_dice,
             resolved.personal_scale_damage,
             resolved.converted_damage, resolved.armor_rating,
             resolved.hull_damage, volley[3], hull_after,
             max(0, resolved.hull_damage-volley[3]),
             volley[4], volley[4]+1, ship_damage_id))
        for order, die in enumerate(rolls, 1):
            connection.execute(
                """INSERT INTO cmd_ground_starship_volley_damage_die
                   VALUES (%s,%s,%s)""", (command_id, order, die))
        connection.execute(
            """UPDATE cmd_ground_starship_volley
               SET volley_status='finalized' WHERE command_id=%s""",
            (volley[0],))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_final(connection, command_id, public_id, False)
