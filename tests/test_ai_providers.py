import os,unittest
from unittest.mock import patch
from ai.providers import OpenAICompatibleProvider,provider_from_environment
class ProviderTests(unittest.TestCase):
 def test_openai_compatible_request_and_usage(self):
  seen={}
  def transport(url,body,headers):seen.update(url=url,body=body,headers=headers);return {'model':'test-model-v2','choices':[{'message':{'content':'{"ok":true}'}}],'usage':{'prompt_tokens':12,'completion_tokens':3}}
  provider=OpenAICompatibleProvider(provider_code='test',base_url='https://example.invalid/v1',api_key='secret',model='test-model',transport=transport);result=provider.chat(messages=[{'role':'user','content':'json please'}],json_output=True,max_tokens=50)
  self.assertEqual(seen['url'],'https://example.invalid/v1/chat/completions');self.assertEqual(seen['body']['response_format'],{'type':'json_object'});self.assertEqual(result.model,'test-model-v2');self.assertEqual((result.prompt_tokens,result.completion_tokens),(12,3))
 def test_deepseek_is_default_but_overridable(self):
  with patch.dict(os.environ,{'DEEPSEEK_API_KEY':'key'},clear=True):
   provider=provider_from_environment();self.assertEqual(provider.provider_code,'deepseek');self.assertEqual(provider.base_url,'https://api.deepseek.com');self.assertEqual(provider.model,'deepseek-v4-flash')
  with patch.dict(os.environ,{'EMPOROS_AI_PROVIDER':'other','EMPOROS_AI_API_KEY':'key','EMPOROS_AI_BASE_URL':'https://other.test/v1','EMPOROS_AI_MODEL':'other-model'},clear=True):
   provider=provider_from_environment();self.assertEqual((provider.provider_code,provider.model),('other','other-model'))
if __name__=='__main__':unittest.main()
