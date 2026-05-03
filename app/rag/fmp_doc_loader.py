import os
import asyncio
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.errors.app_error import create_repo_error
from app.repository.fmp_repository import BASE_URL


def get_chroma_client() -> chromadb.Client:
    # ChromaDB 클라이언트 생성 (절대경로 사용)
    abs_path = os.path.abspath(settings.chroma_db_path)
    return chromadb.PersistentClient(
        path=abs_path,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_collection(client: chromadb.Client, collection_name: str) -> chromadb.Collection:
    # 컬렉션 조회 또는 생성 (코사인 유사도 사용)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def _save_case_sync(documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
    client = get_chroma_client()
    collection = get_collection(client, "surge_cases")
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)


def _save_fmp_doc_sync(documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
    client = get_chroma_client()
    collection = get_collection(client, "fmp_docs")
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)


def _search_similar_cases_sync(query: str, n_results: int) -> dict:
    client = get_chroma_client()
    collection = get_collection(client, "surge_cases")
    return collection.query(query_texts=[query], n_results=n_results)


def _search_fmp_docs_sync(query: str, n_results: int) -> dict:
    client = get_chroma_client()
    collection = get_collection(client, "fmp_docs")
    return collection.query(query_texts=[query], n_results=n_results)


async def save_case(documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
    # 급등/급락 사례 벡터 저장
    try:
        await asyncio.to_thread(_save_case_sync, documents, metadatas, ids)
    except Exception as error:
        raise create_repo_error(code="REPO/VECTOR/SAVE_CASE", cause=error)


async def save_fmp_doc(documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
    # FMP API 문서 벡터 저장
    try:
        await asyncio.to_thread(_save_fmp_doc_sync, documents, metadatas, ids)
    except Exception as error:
        raise create_repo_error(code="REPO/VECTOR/SAVE_FMP_DOC", cause=error)


async def search_similar_cases(query: str, n_results: int = 3) -> dict:
    # 유사 급등/급락 사례 검색
    try:
        return await asyncio.to_thread(_search_similar_cases_sync, query, n_results)
    except Exception as error:
        raise create_repo_error(code="REPO/VECTOR/SEARCH_SIMILAR_CASES", cause=error)


async def search_fmp_docs(query: str, n_results: int = 3) -> dict:
    # FMP API 문서 검색
    try:
        return await asyncio.to_thread(_search_fmp_docs_sync, query, n_results)
    except Exception as error:
        raise create_repo_error(code="REPO/VECTOR/SEARCH_FMP_DOCS", cause=error)


# RAG용: 실제 호출 경로(fmp_repository.fetch_dynamic)와 동일한 endpoint 문자열만 사용
_FMP_ENDPOINT_CATALOG: list[tuple[str, str]] = [
    (
        "shares-float",
        """
FMP stable API endpoint shares-float. Query parameters: symbol (ticker), apikey.
Returns free float, float shares, and outstanding shares for low-float and liquidity analysis.
Use for: float rotation, tradable float, share structure, short squeeze float context.
""".strip(),
    ),
    (
        "historical-price-eod/full",
        """
FMP stable API historical-price-eod/full. Parameters: symbol, from, to, apikey.
End-of-day OHLCV candles for multiple days: open, high, low, close, volume, vwap, change percent.
Use for: daily trend, breakout, box pattern, prior day context, EOD momentum.
""".strip(),
    ),
    (
        "historical-chart/5min",
        """
FMP stable API historical-chart/5min. Parameters: symbol, from, to, apikey (single calendar day range).
Five-minute intraday bars for regular session price action and volatility.
Use for: intraday momentum, VCP, range expansion, 5-minute chart studies, premarket is out of scope for this path.
""".strip(),
    ),
    (
        "aftermarket-quote",
        """
FMP stable API aftermarket-quote. Parameters: symbol, apikey.
After-hours and extended session quote data following the regular close.
Use for: after hours session, AH price, post-market trade, evening move validation.
""".strip(),
    ),
    (
        "quote",
        """
FMP stable API quote. Parameters: symbol, apikey.
Lightweight real-time or delayed quote: last price, change, volume, market cap, company name.
Use for: quick reference quote, market cap check, confirming current tape vs historical bars.
""".strip(),
    ),
]


def _catalog_documents() -> tuple[list[str], list[dict], list[str]]:
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []
    for endpoint, text in _FMP_ENDPOINT_CATALOG:
        safe_id = "fmp_" + endpoint.replace("/", "_").replace("-", "_")
        documents.append(text)
        metadatas.append({"endpoint": endpoint, "base_url": BASE_URL})
        ids.append(safe_id)
    return documents, metadatas, ids


async def load_fmp_docs() -> None:
    # 앱에서 쓰는 FMP stable 엔드포인트 요약을 벡터 DB에 적재 (외부 사이트 크롤링 없음)
    documents, metadatas, ids = _catalog_documents()
    await save_fmp_doc(documents=documents, metadatas=metadatas, ids=ids)