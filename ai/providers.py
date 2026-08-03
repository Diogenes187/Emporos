from dataclasses import dataclass
import json,os,urllib.request,urllib.error
@dataclass(frozen=True)
class ChatResult:content:str;provider:str;model:str;prompt_tokens:int|None;completion_tokens:int|None
@dataclass(frozen=True)
class ProviderCapabilities:json_output:bool=True;tool_calls:bool=True;image_input:bool=False
class OpenAICompatibleProvider:
 def __init__(self,*,provider_code,base_url,api_key,model,capabilities=ProviderCapabilities(),timeout=120,transport=None):self.provider_code=provider_code;self.base_url=base_url.rstrip('/');self.api_key=api_key;self.model=model;self.capabilities=capabilities;self.timeout=timeout;self.transport=transport or self._send
 def _send(self,url,body,headers):
  request=urllib.request.Request(url,data=json.dumps(body).encode(),headers=headers,method='POST')
  try:
   with urllib.request.urlopen(request,timeout=self.timeout) as response:return json.loads(response.read())
  except urllib.error.HTTPError as exc:raise RuntimeError(f'AI provider HTTP {exc.code}') from exc
 def chat(self,*,messages,json_output=False,max_tokens=1000):
  if json_output and not self.capabilities.json_output:raise ValueError('Configured AI provider does not support JSON output')
  body={'model':self.model,'messages':messages,'stream':False,'max_tokens':max_tokens}
  if json_output:body['response_format']={'type':'json_object'}
  data=self.transport(self.base_url+'/chat/completions',body,{'Authorization':'Bearer '+self.api_key,'Content-Type':'application/json'});content=data['choices'][0]['message']['content'];usage=data.get('usage') or {};return ChatResult(content,self.provider_code,data.get('model',self.model),usage.get('prompt_tokens'),usage.get('completion_tokens'))
def provider_from_environment():
 code=os.environ.get('EMPOROS_AI_PROVIDER','deepseek').strip().lower();base=os.environ.get('EMPOROS_AI_BASE_URL') or ('https://api.deepseek.com' if code=='deepseek' else '');key=os.environ.get('EMPOROS_AI_API_KEY') or (os.environ.get('DEEPSEEK_API_KEY') if code=='deepseek' else None);model=os.environ.get('EMPOROS_AI_MODEL') or ('deepseek-v4-flash' if code=='deepseek' else '')
 if not base or not key or not model:raise RuntimeError('AI provider requires base URL, API key, and model configuration')
 return OpenAICompatibleProvider(provider_code=code,base_url=base,api_key=key,model=model,capabilities=ProviderCapabilities(image_input=os.environ.get('EMPOROS_AI_IMAGE_INPUT','false').lower() in ('1','true','yes')))
