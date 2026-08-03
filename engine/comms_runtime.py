"""Battlefield communication and initiative-support commands."""

from dataclasses import dataclass
import secrets

import psycopg


@dataclass(frozen=True)
class BattlefieldCommunicationResult:
    command_public_id: str
    encounter_public_id: str
    commander_actor_public_id: str
    member_actor_public_id: str
    method_code: str
    active: bool
    tactics_suspended: bool
    initiative: int
    replayed: bool


@dataclass(frozen=True)
class InitiativeSupportTarget:
    actor_public_id: str
    communicated: bool
    initiative_before: int
    initiative_after: int


@dataclass(frozen=True)
class InitiativeSupportResult:
    command_public_id: str
    encounter_public_id: str
    support_code: str
    commander_actor_public_id: str
    target_actor_public_id: str | None
    dice: tuple[int, ...]
    check_total: int
    effect: int
    applied_bonus: int
    targets: tuple[InitiativeSupportTarget, ...]
    replayed: bool


def _characteristic_modifier(connection, rule_id, value):
    return connection.execute(
        """SELECT modifier FROM rule_characteristic_modifier_band
           WHERE (characteristic_rule_id IS NULL
                  OR characteristic_rule_id=%s)
             AND score_range @> %s::integer
           ORDER BY characteristic_rule_id NULLS LAST LIMIT 1""",
        (rule_id, value),
    ).fetchone()[0]


def _load_communication(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT encounter.public_id,commander.public_id,member.public_id,
                  method.method_code,receipt.active_after,
                  receipt.tactics_suspended_after,receipt.initiative_after
           FROM cmd_personal_communication_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN actor_actor commander
             ON commander.actor_id=receipt.commander_actor_id
           JOIN actor_actor member ON member.actor_id=receipt.member_actor_id
           JOIN rule_personal_communication_method method
             ON method.rule_id=receipt.method_rule_id
           WHERE receipt.command_id=%s""", (command_id,)
    ).fetchone()
    return BattlefieldCommunicationResult(
        str(public_id), str(row[0]), str(row[1]), str(row[2]), row[3],
        row[4], row[5], row[6], replayed)


def set_battlefield_communication_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    commander_actor_public_id: str, member_actor_public_id: str,
    method_code: str, jammed: bool = False, blocked: bool = False,
    line_of_sight: bool = True, smoke_or_aerosols: bool = False,
    member_moving: bool = False,
) -> BattlefieldCommunicationResult:
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("set_battlefield_communication", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_communication(
                connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,encounter.campaign_id,
                      commander.actor_id,member.actor_id,
                      commander_participant.side_code,
                      combatant.initiative_current,combatant.tactics_bonus,
                      combatant.tactics_bonus_suspended,method.rule_id
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN camp_campaign campaign
                 ON campaign.campaign_id=encounter.campaign_id
               JOIN actor_actor commander ON commander.public_id=%s
               JOIN actor_actor member ON member.public_id=%s
               JOIN enc_participant commander_participant
                 ON commander_participant.encounter_id=combat.encounter_id
                AND commander_participant.actor_id=commander.actor_id
               JOIN enc_participant member_participant
                 ON member_participant.encounter_id=combat.encounter_id
                AND member_participant.actor_id=member.actor_id
                AND member_participant.side_code=commander_participant.side_code
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=member.actor_id
               JOIN rule_personal_communication_method method
                 ON method.method_code=%s
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND campaign.owner_reference=%s
               FOR UPDATE OF combat,combatant""",
            (commander_actor_public_id, member_actor_public_id, method_code,
             encounter_public_id, initiator_reference)).fetchone()
        if state is None:
            raise PermissionError(
                "Communication requires an owned active combat and same-side actors")
        if state[2] == state[3]:
            raise ValueError("A commander does not require a link to themself")
        connection.execute(
            """INSERT INTO enc_personal_unit_commander
               (encounter_id,campaign_id,side_code,commander_actor_id)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (encounter_id,side_code) DO UPDATE
                 SET commander_actor_id=EXCLUDED.commander_actor_id
               WHERE NOT enc_personal_unit_commander.tactics_resolved""",
            (state[0], state[1], state[4], state[2]))
        mapping = connection.execute(
            """SELECT commander_actor_id FROM enc_personal_unit_commander
               WHERE encounter_id=%s AND side_code=%s""",
            (state[0], state[4])).fetchone()
        if mapping[0] != state[2]:
            raise ValueError("The unit commander is fixed after Tactics resolves")
        before = connection.execute(
            """SELECT communication_active
               FROM enc_personal_communication_link
               WHERE encounter_id=%s AND commander_actor_id=%s
                 AND member_actor_id=%s""",
            (state[0], state[2], state[3])).fetchone()
        connection.execute(
            """INSERT INTO enc_personal_communication_link
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,false)
               ON CONFLICT (encounter_id,commander_actor_id,member_actor_id)
               DO UPDATE SET method_rule_id=EXCLUDED.method_rule_id,
                 jammed=EXCLUDED.jammed,blocked=EXCLUDED.blocked,
                 line_of_sight=EXCLUDED.line_of_sight,
                 smoke_or_aerosols=EXCLUDED.smoke_or_aerosols,
                 member_moving=EXCLUDED.member_moving""",
            (state[0], state[2], state[3], state[8], jammed, blocked,
             line_of_sight, smoke_or_aerosols, member_moving))
        active = connection.execute(
            """SELECT communication_active
               FROM enc_personal_communication_link
               WHERE encounter_id=%s AND commander_actor_id=%s
                 AND member_actor_id=%s""",
            (state[0], state[2], state[3])).fetchone()[0]
        suspended_after = state[7]
        initiative_after = state[5]
        if state[6] > 0 and active != (not state[7]):
            suspended_after = not active
            delta = state[6] if active else -state[6]
            initiative_after += delta
            connection.execute(
                """UPDATE enc_personal_combatant
                   SET initiative_base=initiative_base+%s,
                       initiative_current=initiative_current+%s,
                       tactics_bonus_suspended=%s
                   WHERE encounter_id=%s AND actor_id=%s""",
                (delta, delta, suspended_after, state[0], state[3]))
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('set_battlefield_communication',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        connection.execute(
            """INSERT INTO cmd_personal_communication_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[2], state[3], state[8],
             None if before is None else before[0], active, state[7],
             suspended_after, state[5], initiative_after))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES
               (%s,1,'battlefield_communication_changed')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_communication(connection, command_id, public_id, False)


def _load_support(connection, command_id, public_id, replayed):
    row = connection.execute(
        """SELECT encounter.public_id,support.support_code,
                  commander.public_id,target.public_id,receipt.check_total,
                  receipt.effect,receipt.applied_bonus
           FROM cmd_personal_initiative_support_receipt receipt
           JOIN enc_encounter encounter
             ON encounter.encounter_id=receipt.encounter_id
           JOIN rule_personal_initiative_support support
             ON support.rule_id=receipt.support_rule_id
           JOIN actor_actor commander
             ON commander.actor_id=receipt.commander_actor_id
           LEFT JOIN actor_actor target
             ON target.actor_id=receipt.target_actor_id
           WHERE receipt.command_id=%s""", (command_id,)).fetchone()
    dice = tuple(x[0] for x in connection.execute(
        """SELECT result FROM cmd_random_draw WHERE command_id=%s
           AND draw_group='task' ORDER BY draw_order""", (command_id,)))
    targets = tuple(InitiativeSupportTarget(
        str(x[0]), x[1], x[2], x[3]) for x in connection.execute(
            """SELECT actor.public_id,target.communicated,
                      target.initiative_before,target.initiative_after
               FROM cmd_personal_initiative_support_target target
               JOIN actor_actor actor ON actor.actor_id=target.actor_id
               WHERE target.command_id=%s ORDER BY actor.actor_id""",
            (command_id,)))
    return InitiativeSupportResult(
        str(public_id), str(row[0]), row[1], str(row[2]),
        None if row[3] is None else str(row[3]), dice, row[4], row[5],
        row[6], targets, replayed)


def apply_personal_initiative_support_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str,
    commander_actor_public_id: str, support_code: str,
    characteristic_rule_code: str, target_actor_public_id: str | None = None,
    random_source=None,
) -> InitiativeSupportResult:
    if support_code not in ("tactics", "leadership"):
        raise ValueError("Unsupported initiative support")
    if (support_code == "leadership") != (target_actor_public_id is not None):
        raise ValueError("Leadership alone requires one target")
    rng = random_source or secrets.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s
                 AND idempotency_key=%s FOR UPDATE""",
            (initiator_reference, idempotency_key)).fetchone()
        if existing:
            if existing[2:] != ("apply_personal_initiative_support", "completed"):
                raise RuntimeError("Idempotency key belongs to another command")
            return _load_support(connection, existing[0], existing[1], True)
        state = connection.execute(
            """SELECT combat.encounter_id,encounter.campaign_id,
                      combat.current_round,commander.actor_id,
                      participant.side_code,combatant.significant_actions_remaining,
                      characteristic.rule_id,characteristic_state.current_value,
                      COALESCE(skill.skill_level,-3),support.rule_id,
                      core.dice_count,core.die_sides,core.target_number,
                      support.consumes_significant_action
               FROM enc_personal_combat combat
               JOIN enc_encounter encounter
                 ON encounter.encounter_id=combat.encounter_id
               JOIN actor_actor commander ON commander.public_id=%s
               JOIN enc_participant participant
                 ON participant.encounter_id=combat.encounter_id
                AND participant.actor_id=commander.actor_id
               JOIN enc_personal_combatant combatant
                 ON combatant.encounter_id=combat.encounter_id
                AND combatant.actor_id=commander.actor_id
               JOIN rule_personal_initiative_support support
                 ON support.support_code=%s
               JOIN rule_rule characteristic
                 ON characteristic.rule_code=%s
               JOIN actor_characteristic characteristic_state
                 ON characteristic_state.actor_id=commander.actor_id
                AND characteristic_state.characteristic_rule_id=characteristic.rule_id
               LEFT JOIN actor_skill skill
                 ON skill.actor_id=commander.actor_id
                AND skill.skill_rule_id=support.skill_rule_id
               CROSS JOIN rule_check_system core
               WHERE encounter.public_id=%s
                 AND encounter.encounter_status='active'
                 AND combat.combat_status='active'
                 AND commander.controller_reference=%s
                 AND (support.support_code<>'leadership'
                      OR (combatant.turn_started_this_round
                          AND NOT combatant.acted_this_round))
               FOR UPDATE OF combat,combatant""",
            (commander_actor_public_id, support_code,
             characteristic_rule_code, encounter_public_id,
             initiator_reference)).fetchone()
        if state is None:
            raise ValueError("Initiative support is not legal now")
        if support_code == "tactics":
            if state[2] != 1 or connection.execute(
                """SELECT 1 FROM enc_personal_combatant
                   WHERE encounter_id=%s AND turn_started_this_round LIMIT 1""",
                (state[0],)).fetchone():
                raise ValueError("Tactics must resolve at the start of combat")
            connection.execute(
                """INSERT INTO enc_personal_unit_commander
                   (encounter_id,campaign_id,side_code,commander_actor_id)
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (encounter_id,side_code) DO NOTHING""",
                (state[0], state[1], state[4], state[3]))
            unit = connection.execute(
                """SELECT commander_actor_id,tactics_resolved
                   FROM enc_personal_unit_commander
                   WHERE encounter_id=%s AND side_code=%s FOR UPDATE""",
                (state[0], state[4])).fetchone()
            if unit != (state[3], False):
                raise ValueError("Tactics already resolved or commander differs")
        elif state[5] < 1:
            raise ValueError("No significant action remains")
        target_id = None
        if target_actor_public_id is not None:
            target = connection.execute(
                """SELECT actor.actor_id
                   FROM actor_actor actor
                   JOIN enc_participant participant
                     ON participant.actor_id=actor.actor_id
                    AND participant.encounter_id=%s
                    AND participant.side_code=%s
                   WHERE actor.public_id=%s""",
                (state[0], state[4], target_actor_public_id)).fetchone()
            if target is None:
                raise ValueError("Leadership target must be in the same unit")
            target_id = target[0]
        modifier = _characteristic_modifier(connection, state[6], state[7])
        dice = tuple(rng.randint(1, state[11]) for _ in range(state[10]))
        total = sum(dice) + state[8] + modifier
        effect = total - state[12]
        bonus = max(0, effect)
        if support_code == "tactics":
            members = connection.execute(
                """SELECT combatant.actor_id,combatant.initiative_current,
                          combatant.initiative_base,
                          (combatant.actor_id=%s OR COALESCE(link.communication_active,false))
                   FROM enc_personal_combatant combatant
                   JOIN enc_participant participant
                     ON participant.encounter_id=combatant.encounter_id
                    AND participant.actor_id=combatant.actor_id
                   LEFT JOIN enc_personal_communication_link link
                     ON link.encounter_id=combatant.encounter_id
                    AND link.commander_actor_id=%s
                    AND link.member_actor_id=combatant.actor_id
                   WHERE combatant.encounter_id=%s
                     AND participant.side_code=%s
                   FOR UPDATE OF combatant""",
                (state[3], state[3], state[0], state[4])).fetchall()
        else:
            communicated = connection.execute(
                """SELECT (%s=unit.commander_actor_id
                          OR COALESCE(link.communication_active,false))
                   FROM enc_personal_unit_commander unit
                   LEFT JOIN enc_personal_communication_link link
                     ON link.encounter_id=unit.encounter_id
                    AND link.commander_actor_id=unit.commander_actor_id
                    AND link.member_actor_id=%s
                   WHERE unit.encounter_id=%s AND unit.side_code=%s""",
                (target_id, target_id, state[0], state[4])).fetchone()
            if communicated is None:
                raise ValueError("The unit has no registered commander")
            current = connection.execute(
                """SELECT initiative_current,initiative_base
                   FROM enc_personal_combatant WHERE encounter_id=%s
                     AND actor_id=%s FOR UPDATE""",
                (state[0], target_id)).fetchone()
            members = [(target_id, current[0], current[1], communicated[0])]
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command
               (command_type,initiator_reference,idempotency_key)
               VALUES ('apply_personal_initiative_support',%s,%s)
               RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key)).fetchone()
        for order, die in enumerate(dice, 1):
            connection.execute(
                """INSERT INTO cmd_random_draw
                   (command_id,draw_group,draw_order,die_sides,result)
                   VALUES (%s,'task',%s,%s,%s)""",
                (command_id, order, state[11], die))
        affected = sum(1 for member in members if member[3])
        significant_after = state[5] - 1 if state[13] else state[5]
        connection.execute(
            """INSERT INTO cmd_personal_initiative_support_receipt
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, state[0], state[9], state[3], target_id, state[6],
             state[2], dice[0], dice[1], state[8], modifier, total, state[12],
             effect, bonus, affected, state[5] if state[13] else None,
             significant_after if state[13] else None))
        for actor_id, before, base, communicated in members:
            after = before + bonus if communicated else before
            if communicated:
                if support_code == "tactics":
                    connection.execute(
                        """UPDATE enc_personal_combatant
                           SET initiative_base=%s+%s,initiative_current=%s,
                               tactics_bonus=%s,tactics_bonus_suspended=false
                           WHERE encounter_id=%s AND actor_id=%s""",
                        (base, bonus, after, bonus, state[0], actor_id))
                else:
                    connection.execute(
                        """UPDATE enc_personal_combatant
                           SET initiative_current=%s,
                               leadership_bonus=leadership_bonus+%s
                           WHERE encounter_id=%s AND actor_id=%s""",
                        (after, bonus, state[0], actor_id))
            connection.execute(
                """INSERT INTO cmd_personal_initiative_support_target
                   VALUES (%s,%s,%s,%s,%s)""",
                (command_id, actor_id, communicated, before, after))
        if state[13]:
            connection.execute(
                """UPDATE enc_personal_combatant
                   SET significant_actions_remaining=%s,
                       aim_target_actor_id=NULL,aim_modifier=0
                   WHERE encounter_id=%s AND actor_id=%s""",
                (significant_after, state[0], state[3]))
        if support_code == "tactics":
            connection.execute(
                """UPDATE enc_personal_unit_commander SET tactics_resolved=true
                   WHERE encounter_id=%s AND side_code=%s""",
                (state[0], state[4]))
        connection.execute(
            """INSERT INTO cmd_domain_event
               (command_id,event_order,event_type) VALUES
               (%s,1,'personal_initiative_support_applied')""", (command_id,))
        connection.execute(
            """UPDATE cmd_command SET command_status='completed',
                      completed_at=clock_timestamp() WHERE command_id=%s""",
            (command_id,))
        return _load_support(connection, command_id, public_id, False)
