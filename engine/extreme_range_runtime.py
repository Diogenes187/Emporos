"""Referee authorization for source-governed Extreme Range fire."""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class ExtremeRangeAuthorization:
    command_public_id: str
    authorization_public_id: str
    encounter_public_id: str
    round_number: int
    attacker_actor_public_id: str
    target_actor_public_id: str
    weapon_rule_code: str
    attack_profile_code: str
    rest_reference: str
    energy_weapon: bool
    vehicle_public_id: str | None
    replayed: bool


def _load_authorization(connection, command_id, command_public_id, replayed):
    row = connection.execute(
        """SELECT auth.public_id,encounter.public_id,
                  auth.round_number,attacker.public_id,target.public_id,
                  weapon.rule_code,auth.attack_profile_code,
                  auth.rest_reference,auth.energy_weapon,
                  vehicle.public_id
             FROM cmd_personal_extreme_range_authorization_receipt receipt
             JOIN enc_personal_extreme_range_authorization auth
               ON auth.authorization_id=receipt.authorization_id
             JOIN enc_encounter encounter
               ON encounter.encounter_id=auth.encounter_id
             JOIN actor_actor attacker
               ON attacker.actor_id=auth.attacker_actor_id
             JOIN actor_actor target
               ON target.actor_id=auth.target_actor_id
             JOIN rule_rule weapon
               ON weapon.rule_id=auth.weapon_rule_id
             LEFT JOIN vehicle_vehicle vehicle
               ON vehicle.vehicle_id=auth.vehicle_id
            WHERE receipt.command_id=%s""",
        (command_id,),
    ).fetchone()
    return ExtremeRangeAuthorization(
        str(command_public_id), str(row[0]), str(row[1]), row[2],
        str(row[3]), str(row[4]), row[5], row[6], row[7], row[8],
        str(row[9]) if row[9] else None, replayed,
    )


def authorize_extreme_range_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    attacker_actor_public_id: str, target_actor_public_id: str,
    item_rule_code: str, attack_profile_code: str, rest_reference: str,
    line_of_sight: bool, vehicle_public_id: str | None = None,
) -> ExtremeRangeAuthorization:
    if not rest_reference.strip():
        raise ValueError("Extreme-range firing rest is required")
    if not line_of_sight:
        raise ValueError("Extreme-range fire requires line of sight")
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
                 FROM cmd_command
                WHERE initiator_reference=%s AND idempotency_key=%s
                FOR UPDATE""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("authorize_extreme_range", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_authorization(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,combat.current_round,
                      attacker.actor_id,target.actor_id,weapon.rule_id,
                      combatant.metres_moved_this_round,
                      skill.skill_level,
                      EXISTS (
                        SELECT 1 FROM inv_weapon_damage_type damage
                         WHERE damage.item_rule_id=weapon.rule_id
                           AND damage.damage_type_code='energy')
                 FROM enc_personal_combat combat
                 JOIN enc_encounter encounter
                   ON encounter.encounter_id=combat.encounter_id
                 JOIN camp_campaign campaign
                   ON campaign.campaign_id=encounter.campaign_id
                 JOIN actor_actor attacker ON attacker.public_id=%s
                 JOIN actor_actor target ON target.public_id=%s
                 JOIN enc_personal_combatant combatant
                   ON combatant.encounter_id=combat.encounter_id
                  AND combatant.actor_id=attacker.actor_id
                 JOIN rule_rule weapon ON weapon.rule_code=%s
                 JOIN inv_weapon_attack_mode mode
                   ON mode.item_rule_id=weapon.rule_id
                  AND mode.attack_profile_code=%s
                 JOIN combat_attack_profile profile
                   ON profile.attack_profile_code=mode.attack_profile_code
                 JOIN actor_skill skill
                   ON skill.actor_id=attacker.actor_id
                  AND skill.skill_rule_id=COALESCE(
                      mode.required_skill_rule_id,
                      profile.required_skill_rule_id)
                 JOIN rule_rule distant
                   ON distant.rule_code='combat.range.distant'
                 JOIN combat_attack_profile_difficulty difficulty
                   ON difficulty.attack_profile_code=mode.attack_profile_code
                  AND difficulty.range_band_rule_id=distant.rule_id
                  AND difficulty.permitted
                WHERE encounter.public_id=%s
                  AND encounter.encounter_status='active'
                  AND combat.combat_status='active'
                  AND campaign.owner_reference=%s
                FOR UPDATE OF combat,combatant""",
            (attacker_actor_public_id, target_actor_public_id, item_rule_code,
             attack_profile_code, encounter_public_id, initiator_reference),
        ).fetchone()
        if state is None:
            raise PermissionError(
                "Referee cannot authorize this active extreme-range shot")
        if state[2] == state[3]:
            raise ValueError("Combatant cannot attack itself")
        if state[5] != 0:
            raise ValueError("Extreme-range attacker must be stationary")
        if state[6] < 3:
            raise ValueError("Extreme-range fire requires weapon skill Level 3")
        vehicle = (None, None, None, None, None)
        if vehicle_public_id is not None:
            vehicle = connection.execute(
                """SELECT vehicle.vehicle_id,round.vehicle_combat_round_id,
                          engaged.venc_vehicle_id,
                          vehicle_state.movement_status,
                          vehicle_state.speed_kph
                     FROM vehicle_vehicle vehicle
                     JOIN vehicle_crew_assignment crew
                       ON crew.vehicle_id=vehicle.vehicle_id
                      AND crew.actor_id=%s AND crew.duty_status='active'
                     JOIN venc_vehicle engaged
                       ON engaged.vehicle_id=vehicle.vehicle_id
                     JOIN venc_engagement engagement
                       ON engagement.vehicle_engagement_id=
                          engaged.vehicle_engagement_id
                      AND engagement.encounter_id=%s
                      AND engagement.engagement_status='active'
                     JOIN venc_round round
                       ON round.vehicle_engagement_id=
                          engagement.vehicle_engagement_id
                      AND round.round_number=engagement.current_round
                      AND round.round_status IN ('open','resolving')
                     JOIN venc_vehicle_round_state vehicle_state
                       ON vehicle_state.vehicle_combat_round_id=
                          round.vehicle_combat_round_id
                      AND vehicle_state.venc_vehicle_id=
                          engaged.venc_vehicle_id
                    WHERE vehicle.public_id=%s
                      AND vehicle_state.movement_status='stationary'
                      AND vehicle_state.speed_kph=0""",
                (state[2], state[0], vehicle_public_id),
            ).fetchone()
            if vehicle is None:
                raise ValueError(
                    "Firing vehicle lacks a relational stationary state")
        command_id, command_public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('authorize_extreme_range',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        authorization_id = connection.execute(
            """INSERT INTO enc_personal_extreme_range_authorization
               (encounter_id,round_number,attacker_actor_id,target_actor_id,
                weapon_rule_id,attack_profile_code,rest_reference,line_of_sight,
                skill_level,attacker_metres_moved,energy_weapon,
                vehicle_id,vehicle_combat_round_id,venc_vehicle_id,
                vehicle_movement_status,vehicle_speed_kph)
               VALUES (%s,%s,%s,%s,%s,%s,%s,true,%s,%s,%s,%s,%s,%s,%s,%s)
               RETURNING authorization_id""",
            (state[0], state[1], state[2], state[3], state[4],
             attack_profile_code, rest_reference.strip(), state[6], state[5],
             state[7], *vehicle),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_personal_extreme_range_authorization_receipt
               VALUES (%s,%s)""",
            (command_id, authorization_id),
        )
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,),
        )
        return _load_authorization(
            connection, command_id, command_public_id, False)
