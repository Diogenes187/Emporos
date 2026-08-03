from __future__ import annotations
from dataclasses import dataclass
import psycopg

@dataclass(frozen=True)
class SceneFact:
    slot_code:str; fact_value:str; source_reference:str|None=None
@dataclass(frozen=True)
class SceneSnapshotResult:
    command_public_id:str;scene_public_id:str;template_code:str;fact_count:int;replayed:bool

def _load(c,command_id,public_id,replayed):
    r=c.execute("SELECT s.public_id,x.scene_template_code,x.fact_count FROM cmd_scene_snapshot_receipt x JOIN camp_scene_snapshot s USING(scene_snapshot_id) WHERE x.command_id=%s",(command_id,)).fetchone();return SceneSnapshotResult(str(public_id),str(r[0]),r[1],r[2],replayed)

def create_scene_snapshot_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,template_code:str,scene_reference:str,facts:tuple[SceneFact,...],location_public_id:str|None=None,encounter_public_id:str|None=None,journey_public_id:str|None=None)->SceneSnapshotResult:
    if not scene_reference.strip() or not facts:raise ValueError('Scene reference and facts are required')
    with c.transaction():
        old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
        if old:
            if old[2:]!=('create_scene_snapshot','completed'):raise ValueError('Idempotency key belongs to another command')
            return _load(c,old[0],old[1],True)
        campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",(campaign_public_id,initiator_reference)).fetchone()
        if campaign is None:raise ValueError('Campaign is not owned by initiator')
        campaign_id=campaign[0]; refs=[]
        for table,public in (('loc_location',location_public_id),('enc_encounter',encounter_public_id),('journey_journey',journey_public_id)):
            if public:
                row=c.execute(f"SELECT { {'loc_location':'location_id','enc_encounter':'encounter_id','journey_journey':'journey_id'}[table] } FROM {table} WHERE public_id=%s AND campaign_id=%s",(public,campaign_id)).fetchone()
                if row is None:raise ValueError('Scene scope reference is outside campaign')
                refs.append(row[0])
            else:refs.append(None)
        command_id,command_public=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('create_scene_snapshot',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
        snapshot_id,snapshot_public=c.execute("INSERT INTO camp_scene_snapshot(campaign_id,scene_template_code,location_id,encounter_id,journey_id,scene_reference,created_by_reference) VALUES(%s,%s,%s,%s,%s,%s,%s) RETURNING scene_snapshot_id,public_id",(campaign_id,template_code,*refs,scene_reference.strip(),initiator_reference)).fetchone()
        for fact in facts:c.execute("INSERT INTO camp_scene_fact VALUES(%s,%s,%s,%s,%s)",(snapshot_id,campaign_id,fact.slot_code,fact.fact_value.strip(),fact.source_reference))
        c.execute("INSERT INTO cmd_scene_snapshot_receipt VALUES(%s,%s,%s,%s,%s)",(command_id,snapshot_id,campaign_id,template_code,len(facts)));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,));return SceneSnapshotResult(str(command_public),str(snapshot_public),template_code,len(facts),False)
