from hashlib import sha256
import json
from ai.providers import provider_from_environment
from engine.source_review import review_campaign_source_page_command
ALLOWED={None,'unreadable','partial_text','damaged_file','unsupported_content'}
def review_next_text_page(c,*,initiator_reference,document_public_id,idempotency_key,provider=None):
 page=c.execute("SELECT document.campaign_id,page.page_number,page.text_content FROM camp_source_document document JOIN camp_campaign campaign USING(campaign_id) JOIN camp_source_page page USING(source_document_id,campaign_id) WHERE document.public_id=%s AND campaign.owner_reference=%s AND page.review_status='pending' AND NOT page.visual_review_required ORDER BY page.page_number LIMIT 1",(document_public_id,initiator_reference)).fetchone()
 if not page:raise ValueError('No text-only source page awaits private review')
 client=provider or provider_from_environment();prompt='Review this extracted RPG source page privately. Determine only whether extraction is coherent and complete enough to use. Do not summarize plot content. Return JSON exactly as {"text_verified":true,"issue_code":null,"private_note":"brief technical note"}. Allowed issue_code: unreadable, partial_text, damaged_file, unsupported_content, or null.\n\nPAGE TEXT:\n'+page[2];invocation=c.execute("INSERT INTO ai_model_invocation(campaign_id,provider_code,model_name,purpose_code,input_sha256,invocation_status) VALUES(%s,%s,%s,'source_text_review',%s,'pending') RETURNING model_invocation_id",(page[0],client.provider_code,client.model,sha256(prompt.encode()).hexdigest())).fetchone()[0]
 try:
  result=client.chat(messages=[{'role':'system','content':'You are a private source-ingestion verifier. Output JSON only and never produce a plot summary.'},{'role':'user','content':prompt}],json_output=True,max_tokens=300);data=json.loads(result.content);verified=data.get('text_verified') is True;issue=data.get('issue_code');note=str(data.get('private_note',''))[:1000]
  if issue not in ALLOWED:raise ValueError('AI reviewer returned an unsupported issue code')
  if not verified and issue is None:issue='partial_text'
  c.execute("UPDATE ai_model_invocation SET provider_code=%s,model_name=%s,output_sha256=%s,invocation_status='completed',prompt_tokens=%s,completion_tokens=%s,completed_at=clock_timestamp() WHERE model_invocation_id=%s",(result.provider,result.model,sha256(result.content.encode()).hexdigest(),result.prompt_tokens,result.completion_tokens,invocation));review_campaign_source_page_command(c,initiator_reference=initiator_reference,idempotency_key=idempotency_key,document_public_id=document_public_id,page_number=page[1],text_verified=verified,visual_verified=False,generic_issue_code=issue,private_review_note=note);return page[1],verified
 except Exception as exc:c.execute("UPDATE ai_model_invocation SET invocation_status='failed',error_code=%s,completed_at=clock_timestamp() WHERE model_invocation_id=%s",(exc.__class__.__name__,invocation));raise
