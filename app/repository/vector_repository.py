import os
import asyncio
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings
from app.errors.app_error import create_repo_error


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
    collection.upsert(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )


def _search_similar_cases_sync(query: str, n_results: int) -> dict:
    client = get_chroma_client()
    collection = get_collection(client, "surge_cases")
    return collection.query(
        query_texts=[query],
        n_results=n_results,
    )


async def save_case(documents: list[str], metadatas: list[dict], ids: list[str]) -> None:
    # 급등 사례 벡터 저장
    try:
        await asyncio.to_thread(_save_case_sync, documents, metadatas, ids)
    except Exception as error:
        raise create_repo_error(
            code="REPO/VECTOR/SAVE_CASE",
            cause=error,
        )


async def search_similar_cases(query: str, n_results: int = 3) -> dict:
    # 유사 급등 사례 검색
    try:
        return await asyncio.to_thread(_search_similar_cases_sync, query, n_results)
    except Exception as error:
        raise create_repo_error(
            code="REPO/VECTOR/SEARCH_SIMILAR_CASES",
            cause=error,
        )