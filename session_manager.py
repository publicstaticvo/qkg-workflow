import json
import random
import asyncio, aiohttp
from tenacity import (
    retry,
    stop_after_attempt,           # 最大重试次数
    wait_exponential,             # 指数退避
    retry_if_exception,           # 遇到什么异常才重试
)
from typing import Optional

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
}
email_pool = [
    "dailyyulun@gmail.com",
    "fqpcvtjj@hotmail.com",
    "ts.yu@siat.ac.cn",
    "yutianshu.yts@alibaba-inc.com",
    "yts17@mails.tsinghua.edu.cn"
    "yutianshu2025@ia.ac.cn",
    "yutianshu25@ucas.ac.cn",
    "dailyyulun@163.com",
    "lundufiles@163.com",
    "lundufiles123@163.com"
]
RETRY_EXCEPTION_TYPES = [
    aiohttp.ClientError, 
    asyncio.TimeoutError, 
    aiohttp.ServerDisconnectedError, 
    json.JSONDecodeError
]
OPENALEX_SELECT = 'id,title,best_oa_location,locations'


class RateLimit:
    SEARCH_SEMAPHORE = asyncio.Semaphore(4)                # 搜索 API
    LLM_SEMAPHORE = asyncio.Semaphore(20)       # LLM
    PARSE_SEMAPHORE = asyncio.Semaphore(4)                 # GROBID docker镜像本地解析


class SessionManager:
    _global_session: Optional[aiohttp.ClientSession] = None
    
    @classmethod
    async def init(cls):
        """进入上下文时调用"""
        if cls._global_session is None:
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=20, ttl_dns_cache=300)
            cls._global_session = aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=60)
            )
    
    @classmethod
    async def close(cls):
        """退出上下文时调用"""
        if cls._global_session and not cls._global_session.closed:
            await cls._global_session.close()
            cls._global_session = None
    
    @classmethod
    def get(cls) -> aiohttp.ClientSession:
        """获取全局 session"""
        if cls._global_session is None:
            raise RuntimeError("SessionManager not initialized")
        return cls._global_session


# api_utils.py
def should_retry(exception: BaseException) -> bool:
    if any(isinstance(exception, x) for x in RETRY_EXCEPTION_TYPES): return True
    if isinstance(exception, aiohttp.ClientResponseError) and exception.status not in [400, 401, 403, 404]: return True
    return False

@retry(
    # 重试 3 次
    stop=stop_after_attempt(3),
    # 指数退避：2^n * base，这里 1s → 2s → 4s
    wait=wait_exponential(multiplier=1, exp_base=2, min=1, max=10),
    # 仅在网络 / 超时 / 5xx 等场景重试
    retry=retry_if_exception(should_retry),
    # 让 tenacity 支持协程
    reraise=True
)
async def async_request_template(
    method: str,
    url: str,
    headers: dict = None,
    parameters: dict = None
) -> dict:
    """使用全局 session"""
    session = SessionManager.get()
    
    headers = headers or {}
    parameters = parameters or {}
    
    if method.lower() == "post":
        headers.setdefault("Content-Type", "application/json")
        async with session.post(url, headers=headers, json=parameters) as resp:
            resp.raise_for_status()
            return await resp.json()
    else:
        async with session.get(url, headers=headers, params=parameters) as resp:
            resp.raise_for_status()
            return await resp.json()


async def openalex_search_paper(
        endpoint: str,
        filter: dict = None,
        do_sample: bool = False,
        per_page: int = 1,
        add_email: bool | str = True,
        **request_kwargs
    ) -> dict:
    """使用 async_request_template，间接使用全局 session"""
    assert per_page <= 200, "Per page is at most 200"
    # 整理参数
    url = f"https://api.openalex.org/{endpoint}"
    if filter:
        # filter
        filter_string = ",".join([f"{k}:{v}" for k, v in filter.items()])
        request_kwargs["filter"] = filter_string
    if do_sample:
        # use per_page as num_samples
        request_kwargs['sample'] = per_page
        request_kwargs['seed'] = random.randint(0, 32767)        
    if add_email:
        request_kwargs['mailto'] = add_email if isinstance(add_email, str) else random.choice(email_pool)
    if per_page > 25: 
        request_kwargs['per-page'] = per_page
    request_kwargs['select'] = OPENALEX_SELECT
    # Go!
    async with RateLimit.SEARCH_SEMAPHORE:
        return await async_request_template("get", url, None, request_kwargs)
