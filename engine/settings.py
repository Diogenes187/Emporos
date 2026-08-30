"""Relational, audited campaign setting startup."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import psycopg

from engine.sectors import import_sector_command

SETTING_CHOICES = {'ledger_reach','generate_original','import_own','uncharted'}

@dataclass(frozen=True)
class CampaignSettingResult:
    command_public_id: str
    campaign_public_id: str
    startup_choice: str
    sector_public_id: str | None
    replayed: bool

def _load(c, command_id, command_public_id, replayed):
    row=c.execute("""SELECT campaign.public_id,receipt.startup_choice,sector.public_id
      FROM cmd_campaign_setting_receipt receipt
      JOIN camp_campaign campaign USING(campaign_id)
      LEFT JOIN cmd_sector_import_receipt imported ON imported.command_id=receipt.sector_import_command_id
      LEFT JOIN loc_location sector ON sector.location_id=imported.sector_location_id
      WHERE receipt.command_id=%s""",(command_id,)).fetchone()
    return CampaignSettingResult(str(command_public_id),str(row[0]),row[1],str(row[2]) if row[2] else None,replayed)

def _template_tab(c):
    package=c.execute("""SELECT p.setting_package_id,t.setting_sector_template_id,t.sector_name,t.sector_x,t.sector_y
      FROM setting_package p JOIN setting_sector_template t USING(setting_package_id)
      WHERE p.setting_code='ledger-reach' AND p.setting_version='1.0.0'""").fetchone()
    if not package: raise RuntimeError('Ledger Reach setting package is not installed')
    rows=c.execute("SELECT system_name,hex_code,uwp FROM setting_system_template WHERE setting_sector_template_id=%s ORDER BY row_order",(package[1],)).fetchall()
    content='Name\tHex\tUWP\n'+''.join(f'{name}\t{hex_code}\t{uwp}\n' for name,hex_code,uwp in rows)
    return package[0],package[2],package[3],package[4],content.encode()

def _generated_tab(campaign_public_id):
    digest=hashlib.sha256(str(campaign_public_id).encode()).digest()
    stems=('Aster','Brass','Cinder','Dawn','Ember','Far','Gale','Hearth','Ilex','Jade','Keel','Lumen')
    suffixes=(' Gate',' Haven',' Reach',' Rest',' Crown',' Drift',' Point',' Vale')
    rows=[]
    for i in range(8):
        name=stems[digest[i]%len(stems)]+suffixes[digest[i+8]%len(suffixes)]
        col=1+(digest[i+16]%32); row=1+(digest[i+24]%40)
        starport='ABCDEX'[digest[i]%6]
        codes='0123456789ABCDEF'
        limits=(11,16,11,11,16,16)
        profile=''.join(codes[digest[(i+j+1)%32]%limit] for j,limit in enumerate(limits))
        uwp=starport+profile+'-'+codes[digest[(i+7)%32]%16]
        rows.append((name,f'{col:02d}{row:02d}',uwp))
    # Stable collision repair keeps the import constraint honest.
    used=set(); repaired=[]
    for name,hex_code,uwp in rows:
        col,row=int(hex_code[:2]),int(hex_code[2:])
        while (col,row) in used: row=row%40+1
        used.add((col,row)); repaired.append((name,f'{col:02d}{row:02d}',uwp))
    return ('Original Frontier '+str(campaign_public_id)[:8],
            ('Name\tHex\tUWP\n'+''.join(f'{n}\t{h}\t{u}\n' for n,h,u in repaired)).encode())

def initialize_campaign_setting_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,startup_choice:str)->CampaignSettingResult:
    if startup_choice not in SETTING_CHOICES: raise ValueError('Unknown campaign setting choice')
    with c.transaction():
        old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
        if old:
            if old[2:]!=('initialize_campaign_setting','completed'): raise RuntimeError('Idempotency key belongs to another command')
            return _load(c,old[0],old[1],True)
        campaign=c.execute("SELECT campaign_id,public_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s AND campaign_status='active' FOR UPDATE",(campaign_public_id,initiator_reference)).fetchone()
        if not campaign: raise PermissionError('Campaign is absent or not controlled by this player')
        if c.execute('SELECT 1 FROM camp_campaign_setting WHERE campaign_id=%s',(campaign[0],)).fetchone(): raise RuntimeError('Campaign setting is already initialized')
        command_id,command_public_id=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('initialize_campaign_setting',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone()
        package_id=import_result=None
        provenance,rights,export='unknown','unknown_rights',False
        if startup_choice=='ledger_reach':
            package_id,name,x,y,content=_template_tab(c)
            provenance,rights,export='emporos_original','emporos_original',True
            import_result=import_sector_command(c,initiator_reference=initiator_reference,idempotency_key=idempotency_key+':sector',campaign_public_id=campaign_public_id,sector_name=name,sector_x=x,sector_y=y,source_filename='ledger-reach-1.0.0.tab',content=content,provenance_class=provenance,rights_class=rights,export_permitted=export,setting_package_id=package_id)
        elif startup_choice=='generate_original':
            name,content=_generated_tab(campaign[1])
            provenance,rights='generated_original','emporos_original'
            import_result=import_sector_command(c,initiator_reference=initiator_reference,idempotency_key=idempotency_key+':sector',campaign_public_id=campaign_public_id,sector_name=name,sector_x=0,sector_y=0,source_filename='emporos-generated.tab',content=content,provenance_class=provenance,rights_class=rights,export_permitted=False)
        elif startup_choice=='import_own': provenance,rights='user_supplied','private_non_exportable'
        sector_id=import_command_id=None
        if import_result:
            import_command_id=c.execute('SELECT command_id FROM cmd_command WHERE public_id=%s',(import_result.command_public_id,)).fetchone()[0]
            sector_id=c.execute('SELECT sector_location_id FROM cmd_sector_import_receipt WHERE command_id=%s',(import_command_id,)).fetchone()[0]
        starting_world_id=None
        if sector_id:
            starting_world_id=c.execute("""SELECT body.location_id
              FROM loc_star_system system
              JOIN loc_celestial_body body ON body.system_location_id=system.location_id
               AND body.campaign_id=system.campaign_id AND body.body_kind='planet'
              JOIN loc_world_profile profile ON profile.location_id=body.location_id
               AND profile.campaign_id=body.campaign_id
              WHERE system.campaign_id=%s AND system.sector_location_id=%s
              ORDER BY system.hex_column,system.hex_row,body.orbit_order LIMIT 1""",(campaign[0],sector_id)).fetchone()[0]
        c.execute("INSERT INTO camp_campaign_setting(campaign_id,startup_choice,setting_package_id,sector_location_id,provenance_class,rights_class,export_permitted,starting_world_location_id,current_world_location_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(campaign[0],startup_choice,package_id,sector_id,provenance,rights,export,starting_world_id,starting_world_id))
        c.execute("INSERT INTO cmd_campaign_setting_receipt(command_id,campaign_id,startup_choice,setting_package_id,sector_import_command_id) VALUES(%s,%s,%s,%s,%s)",(command_id,campaign[0],startup_choice,package_id,import_command_id))
        c.execute("INSERT INTO cmd_domain_event(command_id,event_order,event_type) VALUES(%s,1,'campaign_setting_initialized')",(command_id,))
        c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(command_id,))
        return _load(c,command_id,command_public_id,False)
