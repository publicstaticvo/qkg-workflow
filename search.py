import json
import random
import aiohttp, asyncio, aiofiles, io
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,           # 最大重试次数
    wait_exponential,             # 指数退避
    retry_if_exception,           # 遇到什么异常才重试
    retry_if_result,
)

from utils import yield_location
from pdf_parser import XMLPaperParser
from session_manager import openalex_search_paper, SessionManager, RateLimit


GROBID_URL = "http://172.18.36.90:8070"
parser = XMLPaperParser()


def grobid_should_retry(exception: Exception) -> bool:
    if isinstance(exception, asyncio.TimeoutError): return True
    if isinstance(exception, aiohttp.ServerDisconnectedError): return True
    if isinstance(exception, aiohttp.ClientResponseError): return exception.status in [429, 503]
    if isinstance(exception, aiohttp.ClientError): return True
    return False


async def process_paper(session: aiohttp.ClientSession, paper_meta: dict) -> Optional[dict]:
    """处理单篇论文：尝试所有 URL，返回第一个成功的"""
    
    # 为该论文的所有 URL 创建任务
    tasks = [asyncio.create_task(try_one_url(session, url)) for url in list(yield_location(paper_meta))]
    
    # 使用 as_completed 获取第一个成功的结果
    try:
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    # 取消其他任务
                    for other_task in tasks:
                        if not other_task.done():
                            other_task.cancel()                                
                    return result
            except asyncio.CancelledError:
                # 某些 task 被 cancel 时不会视为错误，继续尝试其他 task
                continue
            except Exception as e:
                print(f"URL failed: {e}")
                continue
    finally:
        # 确保所有任务都被清理
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        
    return None  # 所有 URL 都失败


async def try_one_url(session: aiohttp.ClientSession, url: str) -> Optional[dict]:
    """尝试从单个 URL 下载并解析论文"""
    async with RateLimit.PARSE_SEMAPHORE:  # 限流
        try:
            # 步骤1: 下载 PDF
            pdf_buffer = await download_pdf(session, url)
            if not pdf_buffer: return            
            # 步骤2: 通过 GROBID 解析
            xml_text = await parse_with_grobid(session, pdf_buffer)
            if not xml_text: return            
            # 步骤3: 用 XMLPaperParser 解析 XML
            paper = await asyncio.to_thread(parser.parse, xml_text)
            # abstract
            abstract = " ".join(p.text for p in paper.abstract.paragraphs) if paper.abstract else None            
            return {"title": paper.title, "abstract": abstract, "url": url, "structure": paper.get_skeleton()}        
        except KeyboardInterrupt: raise            
        except Exception: pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_result(lambda x: x is None)
)
async def download_pdf(session: aiohttp.ClientSession, url: str, timeout: int = 60):
    """下载 PDF 文件"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            content = await resp.read()
            return io.BytesIO(content)
    except KeyboardInterrupt: raise
    except aiohttp.ClientResponseError as e:
        if e.status in [400, 401, 403, 404]: raise
        elif e.status not in [503, 418, 429]: print(f"Download failed {url}: {e}")
    except Exception as e:
        print(f"Download failed {url}: {e}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(grobid_should_retry),
    reraise=True
)
async def parse_with_grobid(session: aiohttp.ClientSession, pdf_buffer: io.BytesIO) -> Optional[str]:
    """通过 GROBID 解析 PDF（带重试）"""
    url = f"{GROBID_URL}/api/processFulltextDocument"
    try:
        # 添加随机延迟避免过载
        await asyncio.sleep(2 * random.random())
        
        # 重置 buffer 位置
        pdf_buffer.seek(0)
        
        # 构造 multipart/form-data
        data = aiohttp.FormData()
        data.add_field('input', pdf_buffer.read(), filename='paper.pdf', content_type='application/pdf')
        
        async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=600)) as resp:
            resp.raise_for_status()
            return await resp.text()
            
    except KeyboardInterrupt:
        raise
    except asyncio.TimeoutError:
        print("GROBID timeout, will retry")
        raise
    except aiohttp.ClientResponseError as e:
        if e.status in [429, 503]: print(f"GROBID client error: {e.status}, will retry")
        else: print(f"GROBID client error: {e.status}, wont retry")
        raise
    except Exception as e:
        print(f"GROBID unexpected error: {e}")
        return
    

async def parse_pdf_file(session: aiohttp.ClientSession, pdf_file: str) -> Optional[str]:
    """通过 GROBID 解析 PDF（带重试）"""
    url = f"{GROBID_URL}/api/processFulltextDocument"
    try:
        # 添加随机延迟避免过载
        await asyncio.sleep(2 * random.random())

        async with aiofiles.open(pdf_file, "rb") as f:
            pdf_buffer = await f.read()
        
        # 构造 multipart/form-data
        data = aiohttp.FormData()
        data.add_field('input', pdf_buffer, filename='paper.pdf', content_type='application/pdf')
        
        async with RateLimit.PARSE_SEMAPHORE:
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=600)) as resp:
                resp.raise_for_status()
                xml_text = await resp.text()
        
        if not xml_text: return {}
        paper = await asyncio.to_thread(parser.parse, xml_text)
        abstract = " ".join(p.text for p in paper.abstract.paragraphs) if paper.abstract else None
        return {"title": paper.title, "abstract": abstract, "url": pdf_file, "structure": paper.get_skeleton()}
            
    except KeyboardInterrupt:
        raise
    except Exception as e:
        return


async def searchquery(query_id: int, query: str, papers_per_query: int = 200):
    """主入口：搜索并下载论文"""
    print(f"Searching papers for {query} ...")
    
    # 1. 调用异步搜索 OpenAlex
    filters = {"default.search": query, "concepts.id": "C192562407"}
    search_result = await openalex_search_paper("works", filter=filters, per_page=papers_per_query)
    search_result = search_result.get("results", [])
    print(f"Search papers for {query}, get {len(search_result)} results")
        
    # 2. 并发处理所有论文的所有 URL，每处理成功一个就ainvoke一个子图
    session = SessionManager.get()
    papers = []
    async def process_single_paper(i, paper_meta):
        if not paper_meta: return False
        try:
            paper_data = await process_paper(session, paper_meta)  # title, abstract, url, skeleton
            if paper_data:
                print(f"Paper {paper_meta['title']} ready. Ainvoke a generate loop.")
                with open(f"papers/Paper_q{query_id}p{i}.json", "w") as f: 
                    paper_data['id'] = f"q{query_id}p{i}"
                    if not paper_data['title']: paper_data['title'] = paper_meta['title']
                    json.dump(paper_data, f, indent=2, ensure_ascii=False)
                papers.append(paper_data)
                # await selectnode(query_id, query, i, paper_data)              
                print(f"Paper {paper_meta['title']} loop concludes.")
        except Exception as e:
            print(f"Metadata {i} of query id {query_id} query {query} fails an {e}")

    tasks = []
    for i, paper_meta in enumerate(search_result):
        # 为每篇论文创建任务（内部会尝试所有 URL）
        tasks.append(asyncio.create_task(process_single_paper(i, paper_meta)))
    
    await asyncio.gather(*tasks, return_exceptions=True)
    return papers
