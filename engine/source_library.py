"""Complete page-accounted campaign source ingestion without database file blobs."""
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re
import psycopg
from pypdf import PdfReader
@dataclass(frozen=True)
class SourceIngestionResult:
 command_public_id:str;document_public_id:str;page_count:int;extracted_pages:int;review_pages:int;status:str;replayed:bool
def _load(c,cid,pub,replayed):
 r=c.execute("SELECT document.public_id,receipt.page_count,receipt.extracted_page_count,receipt.review_page_count,receipt.ingestion_status FROM cmd_campaign_source_ingestion_receipt receipt JOIN camp_source_document document USING(source_document_id) WHERE receipt.command_id=%s",(cid,)).fetchone();return SourceIngestionResult(str(pub),str(r[0]),r[1],r[2],r[3],r[4],replayed)
def _pdf_pages(content):
 reader=PdfReader(BytesIO(content));pages=[]
 for page in reader.pages:
  try:text=(page.extract_text() or '').strip();resources=page.get('/Resources');xobjects=resources.get('/XObject') if resources else None;visual=bool(xobjects)
  except Exception:text='';visual=True
  pages.append((text,'extracted' if text else 'empty',visual))
 return pages
def ingest_campaign_source_command(c:psycopg.Connection,*,initiator_reference:str,idempotency_key:str,campaign_public_id:str,title:str,source_kind:str,original_filename:str,media_type:str,content:bytes,storage_root:Path)->SourceIngestionResult:
 if source_kind not in ('adventure','sourcebook','handout','notes'):raise ValueError('Unsupported campaign source kind')
 if media_type not in ('application/pdf','text/plain'):raise ValueError('Only PDF and plain-text campaign sources are supported')
 if not content:raise ValueError('Campaign source is empty')
 digest=sha256(content).hexdigest();safe=re.sub(r'[^A-Za-z0-9._-]+','_',Path(original_filename).name);relative=Path(digest[:2])/(digest+'-'+safe)
 pages=_pdf_pages(content) if media_type=='application/pdf' else [((content.decode('utf-8-sig')).strip(),'extracted',False)]
 if not pages:raise ValueError('Campaign source has no pages')
 review=sum(1 for text,status,visual in pages if status!='extracted' or visual);status='ready' if review==0 else 'needs_review';target=storage_root/relative
 with c.transaction():
  old=c.execute("SELECT command_id,public_id,command_type,command_status FROM cmd_command WHERE initiator_reference=%s AND idempotency_key=%s FOR UPDATE",(initiator_reference,idempotency_key)).fetchone()
  if old:
   if old[2:]!=('ingest_campaign_source','completed'):raise RuntimeError('Idempotency key belongs to another command')
   return _load(c,old[0],old[1],True)
  campaign=c.execute("SELECT campaign_id FROM camp_campaign WHERE public_id=%s AND owner_reference=%s",(campaign_public_id,initiator_reference)).fetchone()
  if not campaign:raise PermissionError('Campaign is not controlled by this authority')
  duplicate=c.execute("SELECT public_id FROM camp_source_document WHERE campaign_id=%s AND content_sha256=%s",(campaign[0],digest)).fetchone()
  if duplicate:raise ValueError('This source file is already installed in the campaign')
  cid,pub=c.execute("INSERT INTO cmd_command(command_type,initiator_reference,idempotency_key) VALUES('ingest_campaign_source',%s,%s) RETURNING command_id,public_id",(initiator_reference,idempotency_key)).fetchone();document,dpub=c.execute("INSERT INTO camp_source_document(campaign_id,title,source_kind,original_filename,media_type,content_sha256,byte_count,page_count,ingestion_status,stored_relative_path,source_command_id) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING source_document_id,public_id",(campaign[0],title.strip(),source_kind,Path(original_filename).name,media_type,digest,len(content),len(pages),status,str(relative),cid)).fetchone()
  for number,(text,state,visual) in enumerate(pages,1):c.execute("INSERT INTO camp_source_page(source_document_id,campaign_id,page_number,text_content,text_sha256,character_count,extraction_status,visual_review_required,review_status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",(document,campaign[0],number,text,sha256(text.encode()).hexdigest(),len(text),state,visual,'pending' if visual or state!='extracted' else 'verified'))
  c.execute("INSERT INTO cmd_campaign_source_ingestion_receipt VALUES(%s,%s,%s,%s,%s,%s,%s)",(cid,campaign[0],document,len(pages),sum(1 for _,state,_ in pages if state=='extracted'),review,status));c.execute("INSERT INTO cmd_domain_event VALUES(%s,1,'campaign_source_ingested')",(cid,));c.execute("UPDATE cmd_command SET command_status='completed',completed_at=clock_timestamp() WHERE command_id=%s",(cid,))
 target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists():target.write_bytes(content)
 return _load(c,cid,pub,False)
