"""Campaign-safe gameplay skill training."""
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class SkillTrainingResult:
    command_public_id: str
    actor_public_id: str
    skill_rule_code: str
    campaign_week: int
    completed_weeks: int
    required_weeks: int
    skill_level_after: int | None
    replayed: bool

def _load(c, command_id, public_id, replayed):
    row=c.execute("""SELECT actor.public_id,rule.rule_code,r.campaign_week,r.week_number,
      r.required_weeks,r.skill_level_after FROM cmd_skill_training_week_receipt r
      JOIN actor_actor actor USING(actor_id) JOIN rule_rule rule ON rule.rule_id=r.skill_rule_id
      WHERE r.command_id=%s""",(command_id,)).fetchone()
    return SkillTrainingResult(str(public_id),str(row[0]),row[1],row[2],row[3],row[4],row[5],replayed)

def allocate_skill_training_week_command(connection: psycopg.Connection, *, initiator_reference: str,
        idempotency_key: str, actor_public_id: str, skill_rule_code: str) -> SkillTrainingResult:
    with connection.transaction():
        old=connection.execute("""SELECT command_id,public_id,command_type,command_status FROM cmd_command
          WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE""",(initiator_reference,idempotency_key)).fetchone()
        if old:
            if old[2:] != ('allocate_skill_training_week','completed'):
                raise RuntimeError('Idempotency key belongs to another command')
            return _load(connection,old[0],old[1],True)
        state=connection.execute("""SELECT a.actor_id,a.campaign_id,c.day_number,a.concurrency_version,s.rule_id,
          sk.skill_level FROM actor_actor a JOIN camp_clock c USING(campaign_id)
          JOIN rule_rule s ON s.rule_code=%s JOIN rule_skill rs ON rs.rule_id=s.rule_id
          LEFT JOIN actor_skill sk ON sk.actor_id=a.actor_id AND sk.skill_rule_id=s.rule_id
          WHERE a.public_id=%s AND a.controller_reference=%s FOR UPDATE OF a,c""",
          (skill_rule_code,actor_public_id,initiator_reference)).fetchone()
        if not state: raise ValueError('Actor, controlled skill, or campaign clock not found')
        week=state[2]//7
        forbidden=connection.execute("SELECT forbidden_skill_rule_id FROM rule_gameplay_skill_training").fetchone()
        if not forbidden: raise ValueError('Gameplay skill-training rule is not installed')
        if state[4]==forbidden[0]: raise ValueError('Jack of All Trades cannot be learned')
        project=connection.execute("""SELECT training_project_id,skill_rule_id,completed_weeks,required_weeks,
          starting_skill_level FROM camp_skill_training_project WHERE actor_id=%s AND training_status='active' FOR UPDATE""",(state[0],)).fetchone()
        if project and project[1]!=state[4]: raise ValueError('Actor is already training another skill')
        if project and project[4]!=state[5]:
            raise ValueError('Skill level changed during the active training project')
        if not project:
            total=connection.execute("SELECT COALESCE(sum(skill_level),0)::integer FROM actor_skill WHERE actor_id=%s",(state[0],)).fetchone()[0]
            desired=0 if state[5] is None else state[5]+1
            required=max(1,total+desired)
            pid=connection.execute("""INSERT INTO camp_skill_training_project
              (actor_id,skill_rule_id,starting_skill_level,desired_skill_level,skill_total_at_start,required_weeks,started_campaign_week)
              VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING training_project_id""",
              (state[0],state[4],state[5],desired,total,required,week)).fetchone()[0]
            project=(pid,state[4],0,required,state[5])
        if connection.execute("SELECT 1 FROM cmd_skill_training_week_receipt WHERE actor_id=%s AND campaign_week=%s",(state[0],week)).fetchone():
            raise ValueError('Actor has already trained a skill this campaign week')
        number=project[2]+1; after=(0 if state[5] is None else state[5]+1) if number==project[3] else None
        command_id,public_id=connection.execute("""INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key)
          VALUES ('allocate_skill_training_week',%s,%s) RETURNING command_id,public_id""",(initiator_reference,idempotency_key)).fetchone()
        connection.execute("""UPDATE camp_skill_training_project SET completed_weeks=%s,
          training_status=CASE WHEN %s=required_weeks THEN 'completed' ELSE 'active' END,
          completed_campaign_week=CASE WHEN %s=required_weeks THEN %s END WHERE training_project_id=%s""",
          (number,number,number,week,project[0]))
        connection.execute("""INSERT INTO cmd_skill_training_week_receipt VALUES
          (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,clock_timestamp())""",
          (command_id,project[0],state[0],state[4],week,number,project[3],state[5],after,state[3],state[3]+1))
        if after is not None:
            connection.execute("""INSERT INTO actor_skill VALUES (%s,%s,%s) ON CONFLICT(actor_id,skill_rule_id)
              DO UPDATE SET skill_level=EXCLUDED.skill_level""",(state[0],state[4],after))
        connection.execute("UPDATE actor_actor SET concurrency_version=concurrency_version+1 WHERE actor_id=%s",(state[0],))
        connection.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
        return _load(connection,command_id,public_id,False)
