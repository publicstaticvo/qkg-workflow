import re
import json
import aiohttp
import jsonschema
import unicodedata
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from config import LLMServerInfo
from session_manager import SessionManager, RateLimit
from utils import extract_json


def should_retry(exception: BaseException) -> bool:
    if isinstance(exception, NameError): return False
    if isinstance(exception, TypeError): return False
    if isinstance(exception, AttributeError): return False
    if isinstance(exception, KeyboardInterrupt): return False
    if isinstance(exception, NotImplementedError): return False
    return True


class AsyncLLMClient:

    PROMPT: str = ""
    SCHEMA: dict = {}

    def __init__(self, info: LLMServerInfo, sampling_params: dict, timeout: int = 600):
        self.url = f"{info.base_url.rstrip('/')}/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {info.api_key}",
            "Content-Type": "application/json"
        }
        self.sampling_params = sampling_params
        self.model = info.model
        self.timeout = timeout

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1.5, min=1, max=10),
        retry=retry_if_exception(should_retry)
    )
    async def _post(self, payload: dict, context: dict) -> dict:        
        try:
            async with RateLimit.LLM_SEMAPHORE:
                body = json.dumps(payload).encode("utf-8")
                async with SessionManager.get().post(self.url, data=body, headers=self.headers,
                                                     timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._availability(content, context)
        except Exception as e:
            print("LLMFunctino", type(e), str(e))
            raise
        
    def _availability(self, response, context):
        text = extract_json(response)
        jsonschema.validate(text, self.SCHEMA)
        return text
    
    def _organize_inputs(self, inputs: dict):
        return [{"role": "user", "content": self.PROMPT.format(**inputs)}], {}

    async def call(self, messages: list = [], inputs: dict = {}, context: dict = {}, **kwargs) -> dict | None:
        if not messages:
            messages, new_context = self._organize_inputs(inputs)
            context = {**context, **new_context}
        for x in messages:
            x['content'] = unicodedata.normalize("NFKC", x['content'])
        payload = {"model": self.model, "messages": messages, **self.sampling_params} | kwargs
        return await self._post(payload, context)
