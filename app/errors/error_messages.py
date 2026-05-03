# 클라이언트·로그용 메시지 (코드로 원인 레이어 추적)
ERROR_DISPLAY_MESSAGES: dict[str, str] = {
    "APP/UNHANDLED": "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    # repository
    "REPO/FMP/FETCH_SHARE_FLOAT": "유통주식 데이터를 불러오는 중 문제가 발생했습니다.",
    "REPO/FMP/FETCH_HISTORICAL_PRICE": "일봉 시세를 불러오는 중 문제가 발생했습니다.",
    "REPO/FMP/FETCH_INTRADAY_PRICE": "분봉 시세를 불러오는 중 문제가 발생했습니다.",
    "REPO/FMP/FETCH_AFTERMARKET_PRICE": "애프터마켓 시세를 불러오는 중 문제가 발생했습니다.",
    "REPO/FMP/FETCH_QUOTE": "시세 요약을 불러오는 중 문제가 발생했습니다.",
    "REPO/FMP/FETCH_DYNAMIC": "FMP 동적 요청을 처리하는 중 문제가 발생했습니다.",
    "REPO/DARKFINA/FETCH_SHORT_DATA": "공매도 데이터를 불러오는 중 문제가 발생했습니다.",
    "REPO/PERPLEXITY/FETCH_NEWS": "뉴스 데이터를 불러오는 중 문제가 발생했습니다.",
    "REPO/VECTOR/SAVE_CASE": "사례 저장 중 문제가 발생했습니다.",
    "REPO/VECTOR/SEARCH_SIMILAR_CASES": "유사 사례 검색 중 문제가 발생했습니다.",
    "REPO/VECTOR/SAVE_FMP_DOC": "FMP 문서 적재 중 문제가 발생했습니다.",
    "REPO/VECTOR/SEARCH_FMP_DOCS": "FMP 문서 검색 중 문제가 발생했습니다.",
    # service
    "SERVICE/ANALYSIS/ANALYZE_STOCK": "종목 분석을 완료하지 못했습니다.",
    "SERVICE/ANALYSIS/SAVE_CASE": "사례 저장을 완료하지 못했습니다.",
    "SERVICE/ANALYSIS/LOAD_FMP_DOCS": "FMP 문서 적재 작업을 완료하지 못했습니다.",
    # graph
    "GRAPH/TRADING/RUN_ANALYSIS": "분석 파이프라인 실행 중 문제가 발생했습니다.",
    # agents
    "AGENT/FLOAT/ANALYZE": "유통주식 분석 단계에서 문제가 발생했습니다.",
    "AGENT/VOLUME/ANALYZE": "거래량 분석 단계에서 문제가 발생했습니다.",
    "AGENT/SHORT/ANALYZE": "공매도 분석 단계에서 문제가 발생했습니다.",
    "AGENT/MOMENTUM/ANALYZE": "모멘텀 분석 단계에서 문제가 발생했습니다.",
    "AGENT/NEWS/ANALYZE": "뉴스 분석 단계에서 문제가 발생했습니다.",
    "AGENT/TRADER/ANALYZE": "트레이더 에이전트 단계에서 문제가 발생했습니다.",
    "AGENT/RISK/ANALYZE": "리스크 검토 단계에서 문제가 발생했습니다.",
    # rag
    "RAG/EMBEDDER/EMBED_CASE": "사례 임베딩 중 문제가 발생했습니다.",
    "RAG/RETRIEVER/RETRIEVE_SIMILAR_CASES": "유사 사례 조회 중 문제가 발생했습니다.",
    "RAG/RETRIEVER/RETRIEVE_FMP_ENDPOINT": "FMP 엔드포인트 문서 조회 중 문제가 발생했습니다.",
}


def display_message_for_code(code: str, fallback: str) -> str:
    return ERROR_DISPLAY_MESSAGES.get(code, fallback)
