"""Audited Traveller/Cepheus sector text import."""
from __future__ import annotations
from dataclasses import dataclass
import csv, hashlib, io
import psycopg

@dataclass(frozen=True)
class SectorImportResult:
 command_public_id:str;campaign_public_id:str;sector_public_id:str
 sector_name:str;system_count:int;source_sha256:str;replayed:bool

def _digit(value:str)->int:
    if len(value)!=1 or value.upper() not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        raise ValueError(f"Invalid extended hexadecimal digit: {value}")
    return "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ".index(value.upper())

def _rows(content:bytes):
    try: text=content.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise ValueError("Sector file must be UTF-8 text") from exc
    lines=[(number,line) for number,line in enumerate(text.splitlines(),1) if line.strip() and not line.lstrip().startswith(("#","//"))]
    if not lines: raise ValueError("Sector file contains no systems")
    delimiter="\t" if "\t" in lines[0][1] else ","
    reader=csv.DictReader(io.StringIO("\n".join(line for _,line in lines)),delimiter=delimiter)
    fields={field.strip().lower():field for field in (reader.fieldnames or [])}
    required={"hex","name","uwp"}
    if not required.issubset(fields): raise ValueError("Sector file needs Name, Hex, and UWP columns")
    result=[]
    for index,row in enumerate(reader,2):
        name=(row[fields["name"]] or "").strip();hex_code=(row[fields["hex"]] or "").strip();uwp=(row[fields["uwp"]] or "").strip().upper()
        if not name or len(hex_code)!=4 or not hex_code.isdigit(): raise ValueError(f"Invalid system identity on data row {index}")
        column,row_number=int(hex_code[:2]),int(hex_code[2:])
        if not 1<=column<=32 or not 1<=row_number<=40: raise ValueError(f"Hex outside 0140-3240 on data row {index}")
        if len(uwp)!=9 or uwp[7]!="-" or uwp[0] not in "ABCDEFGHX": raise ValueError(f"Invalid UWP on data row {index}")
        values=tuple(_digit(value) for value in uwp[1:7]+uwp[8])
        if any(value>15 for value in values[:6]) or values[6]>35: raise ValueError(f"UWP value out of range on data row {index}")
        result.append((index,name,hex_code,column,row_number,uwp,values))
    if not result: raise ValueError("Sector file contains no system rows")
    return result

def _load(c,cid,pub,replayed):
    row=c.execute("SELECT campaign.public_id,sector.public_id,sector.name,receipt.imported_system_count,receipt.source_sha256 FROM cmd_sector_import_receipt receipt JOIN camp_campaign campaign USING(campaign_id) JOIN loc_location sector ON sector.location_id=receipt.sector_location_id WHERE receipt.command_id=%s",(cid,)).fetchone()
    return SectorImportResult(str(pub),str(row[0]),str(row[1]),row[2],row[3],row[4],replayed)

def import_sector_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,sector_name:str,sector_x:int,sector_y:int,source_filename:str,content:bytes)->SectorImportResult:
    name=sector_name.strip();filename=source_filename.strip();parsed=_rows(content);digest=hashlib.sha256(content).hexdigest()
    if not name: raise ValueError("Sector name cannot be blank")
    if not filename: raise ValueError("Source filename cannot be blank")
    with c.transaction():
        old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
        if old:
            if old[2:] != ('import_sector','completed'): raise RuntimeError("Idempotency key belongs to another command")
            return _load(c,old[0],old[1],True)
        campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s AND campaign_status='active' FOR UPDATE",(campaign_public_id,initiator_reference)).fetchone()
        if not campaign: raise PermissionError("Campaign is absent or not controlled by this player")
        types=dict(c.execute("SELECT location_type_code,location_type_rule_id FROM rule_location_type WHERE location_type_code IN('sector','star-system','main-world')").fetchall())
        if len(types)!=3: raise RuntimeError("Location catalogue is incomplete")
        cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('import_sector',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
        sector,sector_pub=c.execute("INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,%s) RETURNING location_id,public_id",(campaign[0],types['sector'],name)).fetchone()
        c.execute("INSERT INTO loc_sector VALUES(%s,%s,%s,%s)",(sector,campaign[0],sector_x,sector_y))
        c.execute("INSERT INTO cmd_sector_import_receipt VALUES(%s,%s,%s,%s,%s,%s,%s)",(cid,campaign[0],sector,filename,digest,len(content),len(parsed)))
        for order,(line,system_name,hex_code,column,row_number,uwp,values) in enumerate(parsed,1):
            system=c.execute("INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,%s) RETURNING location_id",(campaign[0],types['star-system'],system_name)).fetchone()[0]
            c.execute("INSERT INTO loc_star_system(location_id,campaign_id,sector_location_id,hex_column,hex_row) VALUES(%s,%s,%s,%s,%s)",(system,campaign[0],sector,column,row_number))
            c.execute("INSERT INTO loc_containment(campaign_id,parent_location_id,child_location_id,source_command_id) VALUES(%s,%s,%s,%s)",(campaign[0],sector,system,cid))
            world=c.execute("INSERT INTO loc_location(campaign_id,location_type_rule_id,name) VALUES(%s,%s,%s) RETURNING location_id",(campaign[0],types['main-world'],system_name)).fetchone()[0]
            c.execute("INSERT INTO loc_celestial_body(location_id,campaign_id,system_location_id,body_kind,orbit_order) VALUES(%s,%s,%s,'planet',1)",(world,campaign[0],system))
            c.execute("INSERT INTO loc_containment(campaign_id,parent_location_id,child_location_id,source_command_id) VALUES(%s,%s,%s,%s)",(campaign[0],system,world,cid))
            c.execute("INSERT INTO loc_world_profile(location_id,campaign_id,revision_number,starport_code,size_code,atmosphere_code,hydrographics_code,population_code,government_code,law_level_code,technology_level) VALUES(%s,%s,1,%s,%s,%s,%s,%s,%s,%s,%s)",(world,campaign[0],uwp[0],*values))
            c.execute("INSERT INTO cmd_sector_import_system VALUES(%s,%s,%s,%s,%s,%s,%s)",(cid,order,system,world,line,hex_code,uwp))
        c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'sector_imported')",(cid,))
        c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
        return _load(c,cid,pub,False)
