"""Source-governed environmental exposure and species resilience."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class SpeciesEnvironmentalExposureResult:
    command_public_id: str
    exposure_public_id: str
    actor_public_id: str
    environment_kind: str
    elapsed_minutes_before: int
    elapsed_minutes_added: int
    elapsed_minutes_after: int
    newly_processed_intervals: int
    protective_equipment_active: bool
    initiative_modifier: int | None
    damage_dice: tuple[int, ...]
    raw_damage: int
    damage_prevented: bool
    damage_instance_public_id: str | None
    exposure_status: str
    replayed: bool


def _load_environmental_exposure_result(
    connection, command_id, command_public_id, replayed,
):
    row = connection.execute(
        """SELECT exposure.public_id,actor.public_id,receipt.environment_kind,
                  receipt.elapsed_minutes_before,
                  receipt.elapsed_minutes_added,
                  receipt.elapsed_minutes_after,
                  receipt.newly_processed_intervals,
                  receipt.protective_equipment_active,
                  receipt.initiative_modifier,receipt.raw_damage,
                  receipt.damage_prevented,damage.public_id,
                  exposure.exposure_status
           FROM cmd_species_environmental_exposure_receipt receipt
           JOIN actor_species_environmental_exposure exposure
             ON exposure.exposure_id=receipt.exposure_id
           JOIN actor_actor actor ON actor.actor_id=receipt.actor_id
           LEFT JOIN health_damage_instance damage
             ON damage.damage_instance_id=receipt.damage_instance_id
           WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    dice = connection.execute(
        """SELECT result FROM cmd_random_draw
           WHERE command_id=%s AND draw_group='environment_damage'
           ORDER BY draw_order""",
        (command_id,),
    ).fetchall()
    return SpeciesEnvironmentalExposureResult(
        str(command_public_id), str(row[0]), str(row[1]), row[2], row[3],
        row[4], row[5], row[6], row[7], row[8],
        tuple(value[0] for value in dice), row[9], row[10],
        str(row[11]) if row[11] else None, row[12], replayed,
    )


def advance_species_environmental_exposure_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, actor_public_id: str, environment_kind: str,
    elapsed_minutes: int, protective_equipment_active: bool = False,
    exposure_public_id: str | None = None, end_exposure: bool = False,
    random_source=None,
) -> SpeciesEnvironmentalExposureResult:
    """Start or advance one continuous source-defined species exposure."""
    if environment_kind not in {"extreme_cold", "hot_weather"}:
        raise ValueError("Unknown species environmental exposure")
    if elapsed_minutes <= 0:
        raise ValueError("Elapsed exposure time must be positive")
    if environment_kind == "hot_weather" and protective_equipment_active:
        raise ValueError(
            "Protective equipment is not part of the Heat Endurance rule")
    rng = random_source or secrets.SystemRandom()

    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != (
                "advance_species_environmental_exposure", "completed",
            ):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_environmental_exposure_result(
                connection, existing[0], existing[1], True)

        actor = connection.execute(
            """SELECT actor_id FROM actor_actor
               WHERE public_id=%s AND controller_reference=%s
               FOR UPDATE""",
            (actor_public_id, initiator_reference),
        ).fetchone()
        if actor is None:
            raise ValueError("Actor is absent or not controlled by this player")

        trait_code = (
            "cold-blooded"
            if environment_kind == "extreme_cold"
            else "heat-endurance"
        )
        trait = connection.execute(
            """SELECT trait.species_trait_rule_id
               FROM actor_current_species current_species
               JOIN rule_species_trait_assignment assignment
                 ON assignment.species_rule_id=current_species.species_rule_id
               JOIN rule_species_trait trait
                 ON trait.species_trait_rule_id=
                    assignment.species_trait_rule_id
               WHERE current_species.actor_id=%s AND trait.trait_code=%s""",
            (actor[0], trait_code),
        ).fetchone()
        if trait is None:
            raise ValueError(
                f"Actor's species does not have the {trait_code} trait")

        if environment_kind == "extreme_cold":
            rule = connection.execute(
                """SELECT interval_minutes,damage_dice_count,
                          damage_die_sides,initiative_modifier
                   FROM rule_species_cold_blooded_exposure
                   WHERE species_trait_rule_id=%s""",
                (trait[0],),
            ).fetchone()
            interval_minutes, dice_count, die_sides, source_initiative = rule
            initiative_modifier = (
                0 if protective_equipment_active else source_initiative)
        else:
            interval_minutes = connection.execute(
                """SELECT damage_interval_minutes
                   FROM rule_species_heat_endurance
                   WHERE species_trait_rule_id=%s""",
                (trait[0],),
            ).fetchone()[0]
            dice_count = 0
            die_sides = 0
            initiative_modifier = None

        exposure = None
        if exposure_public_id is not None:
            exposure = connection.execute(
                """SELECT exposure_id,public_id,elapsed_minutes,
                          processed_intervals,protective_equipment_active
                   FROM actor_species_environmental_exposure
                   WHERE public_id=%s AND actor_id=%s
                     AND environment_kind=%s AND exposure_status='active'
                   FOR UPDATE""",
                (exposure_public_id, actor[0], environment_kind),
            ).fetchone()
            if exposure is None:
                raise ValueError("Active environmental exposure does not exist")
            if exposure[4] != protective_equipment_active:
                raise ValueError(
                    "Protection cannot change within one continuous exposure")
        else:
            if connection.execute(
                """SELECT 1 FROM actor_species_environmental_exposure
                   WHERE actor_id=%s AND environment_kind=%s
                     AND exposure_status='active'""",
                (actor[0], environment_kind),
            ).fetchone():
                raise ValueError(
                    "Actor already has an active exposure of this kind")
            exposure = connection.execute(
                """INSERT INTO actor_species_environmental_exposure
                   (actor_id,environment_kind,protective_equipment_active)
                   VALUES (%s,%s,%s)
                   RETURNING exposure_id,public_id,elapsed_minutes,
                             processed_intervals,
                             protective_equipment_active""",
                (actor[0], environment_kind, protective_equipment_active),
            ).fetchone()

        elapsed_before = exposure[2]
        intervals_before = exposure[3]
        elapsed_after = elapsed_before + elapsed_minutes
        intervals_after = elapsed_after // interval_minutes
        newly_processed = intervals_after - intervals_before
        damage_prevented = (
            newly_processed > 0
            and (
                environment_kind == "hot_weather"
                or protective_equipment_active
            )
        )
        damage_dice = ()
        if (
            environment_kind == "extreme_cold"
            and not protective_equipment_active
            and newly_processed > 0
        ):
            damage_dice = tuple(
                rng.randint(1, die_sides)
                for _ in range(newly_processed * dice_count)
            )
        raw_damage = sum(damage_dice)

        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('advance_species_environmental_exposure',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        for order, result in enumerate(damage_dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'environment_damage',%s,%s,%s)""",
                (command_id, order, die_sides, result),
            )

        damage_instance_id = None
        if raw_damage:
            damage_instance_id = connection.execute(
                """INSERT INTO health_damage_instance
                   (environmental_command_id,target_actor_id,
                    penetrating_damage)
                   VALUES (%s,%s,%s) RETURNING damage_instance_id""",
                (command_id, actor[0], raw_damage),
            ).fetchone()[0]

        connection.execute(
            """UPDATE actor_species_environmental_exposure
               SET elapsed_minutes=%s,processed_intervals=%s,
                   exposure_status=%s,
                   ended_at=CASE WHEN %s THEN clock_timestamp() END
               WHERE exposure_id=%s""",
            (elapsed_after, intervals_after,
             "ended" if end_exposure else "active",
             end_exposure, exposure[0]),
        )
        connection.execute(
            """INSERT INTO cmd_species_environmental_exposure_receipt
               (command_id,exposure_id,actor_id,environment_kind,
                elapsed_minutes_before,elapsed_minutes_added,
                elapsed_minutes_after,processed_intervals_before,
                processed_intervals_after,newly_processed_intervals,
                protective_equipment_active,initiative_modifier,
                damage_prevented,raw_damage,damage_instance_id)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, exposure[0], actor[0], environment_kind,
             elapsed_before, elapsed_minutes, elapsed_after,
             intervals_before, intervals_after, newly_processed,
             protective_equipment_active, initiative_modifier,
             damage_prevented, raw_damage, damage_instance_id),
        )
        event_type = (
            "species_environmental_damage_created"
            if raw_damage
            else "species_environmental_damage_prevented"
            if damage_prevented
            else "species_environmental_exposure_advanced"
        )
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES (%s,1,%s)""",
            (command_id, event_type),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
               completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_environmental_exposure_result(
            connection, command_id, command_public_id, False)
