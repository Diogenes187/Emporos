from __future__ import annotations

from dataclasses import dataclass
import random

import psycopg


@dataclass(frozen=True)
class SocialContentSelection:
    command_public_id: str
    encounter_public_id: str
    content_kind: str
    d66_result: int
    content_code: str
    content_name: str
    referee_choice: bool
    replayed: bool


@dataclass(frozen=True)
class PatronRequirement:
    kind: str
    reference: str
    skill_rule_code: str | None = None


@dataclass(frozen=True)
class PatronObjective:
    actor_role_reference: str
    objective_kind: str
    objective_reference: str
    priority: int = 3
    actor_public_id: str | None = None


@dataclass(frozen=True)
class PatronBriefResult:
    command_public_id: str
    brief_public_id: str
    revision_number: int
    requirement_count: int
    truth_variant_count: int
    npc_objective_count: int
    replayed: bool


def _load(connection: psycopg.Connection, command_id: int, public_id, replayed: bool) -> SocialContentSelection:
    row = connection.execute(
        """SELECT e.public_id,s.content_kind,s.d66_result,s.content_code,
                  s.content_name,s.referee_choice
           FROM enc_social_content_selection s
           JOIN enc_encounter e USING(encounter_id)
           WHERE s.command_id=%s""", (command_id,),
    ).fetchone()
    return SocialContentSelection(str(public_id), str(row[0]), row[1], row[2], row[3], row[4], row[5], replayed)


def select_social_content_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, encounter_public_id: str, random_source=None,
) -> SocialContentSelection:
    rng = random_source or random.SystemRandom()
    with connection.transaction():
        existing = connection.execute(
            """SELECT command_id,public_id,command_type,command_status
               FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s
               FOR UPDATE""", (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("select_social_content", "completed"):
                raise ValueError("Idempotency key belongs to another command")
            return _load(connection, existing[0], existing[1], True)
        encounter = connection.execute(
            """SELECT e.encounter_id,e.campaign_id,t.encounter_type_code
               FROM enc_encounter e JOIN camp_campaign c USING(campaign_id)
               JOIN rule_encounter_type t ON t.rule_id=e.encounter_type_rule_id
               WHERE e.public_id=%s AND c.owner_reference=%s FOR UPDATE OF e""",
            (encounter_public_id, initiator_reference),
        ).fetchone()
        if encounter is None:
            raise ValueError("Encounter is not owned by initiator")
        if encounter[2] not in ("patron", "rumor"):
            raise ValueError("Encounter must be patron or rumor type")
        command_id, public_id = connection.execute(
            """INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key)
               VALUES('select_social_content',%s,%s) RETURNING command_id,public_id""",
            (initiator_reference, idempotency_key),
        ).fetchone()
        tens, ones = rng.randint(1, 6), rng.randint(1, 6)
        for order, value in enumerate((tens, ones), 1):
            connection.execute(
                """INSERT INTO cmd_random_draw(command_id,draw_group,draw_order,die_sides,result)
                   VALUES(%s,'task',%s,6,%s)""", (command_id, order, value),
            )
        d66 = tens * 10 + ones
        table = "rule_patron_role_roll" if encounter[2] == "patron" else "rule_rumor_content_roll"
        referee_choice = connection.execute(
            f"SELECT referee_choice FROM {table} WHERE d66_result=%s", (d66,),
        ).fetchone()[0]
        connection.execute(
            """INSERT INTO cmd_social_content_selection_receipt
               (command_id,campaign_id,encounter_id,content_kind,tens_die,ones_die,d66_result,patron_d66_result,rumor_d66_result,referee_choice)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (command_id, encounter[1], encounter[0], encounter[2], tens, ones, d66,
             d66 if encounter[2] == "patron" else None,
             d66 if encounter[2] == "rumor" else None, referee_choice),
        )
        connection.execute(
            "UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",
            (command_id,),
        )
        return _load(connection, command_id, public_id, False)


def _load_patron_brief(connection: psycopg.Connection, command_id: int, public_id, replayed: bool) -> PatronBriefResult:
    row = connection.execute(
        """SELECT b.public_id,r.revision_number,x.requirement_count,
                  x.truth_variant_count,x.npc_objective_count
           FROM cmd_patron_brief_receipt x
           JOIN camp_patron_brief b USING(patron_brief_id)
           JOIN camp_patron_brief_revision r USING(patron_brief_revision_id)
           WHERE x.command_id=%s""", (command_id,),
    ).fetchone()
    return PatronBriefResult(str(public_id), str(row[0]), row[1], row[2], row[3], row[4], replayed)


def create_patron_brief_command(
    connection: psycopg.Connection, *, initiator_reference: str,
    idempotency_key: str, campaign_public_id: str, brief_code: str,
    patron_name_reference: str, role_reference: str, reward_summary: str,
    player_mission_summary: str, requirements: tuple[PatronRequirement, ...],
    truth_variants: tuple[str, ...], objectives: tuple[PatronObjective, ...],
    patron_actor_public_id: str | None = None, patron_d66_result: int | None = None,
) -> PatronBriefResult:
    if not all((brief_code.strip(), patron_name_reference.strip(), role_reference.strip(), reward_summary.strip(), player_mission_summary.strip())):
        raise ValueError("Patron brief core references are required")
    if not requirements or len(truth_variants) < 2 or not objectives:
        raise ValueError("Patron brief requires requirements, at least two truths, and objectives")
    with connection.transaction():
        existing = connection.execute(
            "SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",
            (initiator_reference, idempotency_key),
        ).fetchone()
        if existing:
            if existing[2:] != ("create_patron_brief", "completed"):
                raise ValueError("Idempotency key belongs to another command")
            return _load_patron_brief(connection, existing[0], existing[1], True)
        campaign = connection.execute(
            "SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",
            (campaign_public_id, initiator_reference),
        ).fetchone()
        if campaign is None: raise ValueError("Campaign is not owned by initiator")
        campaign_id = campaign[0]
        patron_actor_id = None
        if patron_actor_public_id:
            actor = connection.execute("SELECT actor_id FROM actor_actor WHERE public_id=%s AND campaign_id=%s", (patron_actor_public_id, campaign_id)).fetchone()
            if actor is None: raise ValueError("Patron actor is outside campaign")
            patron_actor_id = actor[0]
        command_id, command_public = connection.execute(
            "INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('create_patron_brief',%s,%s) RETURNING command_id,public_id",
            (initiator_reference, idempotency_key),
        ).fetchone()
        brief_id, brief_public = connection.execute(
            "INSERT INTO camp_patron_brief(campaign_id,brief_code) VALUES(%s,%s) RETURNING patron_brief_id,public_id",
            (campaign_id, brief_code.strip()),
        ).fetchone()
        revision_id = connection.execute(
            """INSERT INTO camp_patron_brief_revision
               (patron_brief_id,campaign_id,revision_number,patron_actor_id,patron_d66_result,patron_name_reference,role_reference,reward_summary,player_mission_summary,created_by_reference)
               VALUES(%s,%s,1,%s,%s,%s,%s,%s,%s,%s) RETURNING patron_brief_revision_id""",
            (brief_id, campaign_id, patron_actor_id, patron_d66_result, patron_name_reference.strip(), role_reference.strip(), reward_summary.strip(), player_mission_summary.strip(), initiator_reference),
        ).fetchone()[0]
        for order, requirement in enumerate(requirements, 1):
            skill_id = None
            if requirement.kind == "skill":
                if not requirement.skill_rule_code: raise ValueError("Skill requirement needs a rule code")
                skill = connection.execute("SELECT s.rule_id FROM rule_skill s JOIN rule_rule r USING(rule_id) WHERE r.rule_code=%s", (requirement.skill_rule_code,)).fetchone()
                if skill is None: raise ValueError("Unknown skill rule")
                skill_id = skill[0]
            connection.execute("INSERT INTO camp_patron_requirement VALUES(%s,%s,%s,%s,%s,%s)", (revision_id, campaign_id, order, requirement.kind, skill_id, requirement.reference.strip()))
        for order, summary in enumerate(truth_variants, 1):
            connection.execute("INSERT INTO camp_patron_truth_variant VALUES(%s,%s,%s,%s)", (revision_id, campaign_id, order, summary.strip()))
        for order, objective in enumerate(objectives, 1):
            actor_id = None
            if objective.actor_public_id:
                actor = connection.execute("SELECT actor_id FROM actor_actor WHERE public_id=%s AND campaign_id=%s", (objective.actor_public_id, campaign_id)).fetchone()
                if actor is None: raise ValueError("Objective actor is outside campaign")
                actor_id = actor[0]
            connection.execute("INSERT INTO camp_patron_npc_objective VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", (revision_id, campaign_id, order, actor_id, objective.actor_role_reference.strip(), objective.objective_kind, objective.objective_reference.strip(), objective.priority))
        connection.execute("INSERT INTO cmd_patron_brief_receipt VALUES(%s,%s,%s,%s,%s,%s,%s)", (command_id, brief_id, revision_id, campaign_id, len(requirements), len(truth_variants), len(objectives)))
        connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s", (command_id,))
        return PatronBriefResult(str(command_public), str(brief_public), 1, len(requirements), len(truth_variants), len(objectives), False)
