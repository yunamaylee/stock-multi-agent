from app.repository.vector_repository import search_similar_cases
from app.rag.fmp_doc_loader import search_fmp_docs
from app.errors.app_error import wrap_app_error


async def retrieve_similar_cases(query: str, n_results: int = 5) -> list[dict]:
    # 쿼리와 유사한 급등/급락 사례 검색
    try:
        results = await search_similar_cases(query=query, n_results=n_results)
        return _parse_case_results(results)
    except Exception as error:
        wrap_app_error(
            error,
            source="rag",
            code="RAG/RETRIEVER/RETRIEVE_SIMILAR_CASES",
        )


async def retrieve_fmp_endpoint(query: str, n_results: int = 3) -> list[dict]:
    # 필요한 FMP 엔드포인트 검색
    try:
        results = await search_fmp_docs(query=query, n_results=n_results)
        return _parse_fmp_results(results)
    except Exception as error:
        wrap_app_error(
            error,
            source="rag",
            code="RAG/RETRIEVER/RETRIEVE_FMP_ENDPOINT",
        )


def _parse_case_results(results: dict) -> list[dict]:
    # ChromaDB 급등/급락 사례 응답 파싱
    parsed = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        parsed.append({
            "document": document,
            "ticker": metadata.get("ticker"),
            "date": metadata.get("date"),
            "outcome": metadata.get("outcome", "unknown"),
            "session": metadata.get("session", "unknown"),
            "similarity": round(1 - distance, 4),
        })

    return parsed


def _parse_fmp_results(results: dict) -> list[dict]:
    # ChromaDB FMP 문서 응답 파싱
    parsed = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        parsed.append({
            "document": document,
            "endpoint": metadata.get("endpoint"),
            "base_url": metadata.get("base_url"),
            "similarity": round(1 - distance, 4),
        })

    return parsed