from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.repository import fmp_repository
from app.rag.retriever import retrieve_similar_cases, retrieve_fmp_endpoint
from app.errors.app_error import wrap_app_error


llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    api_key=settings.anthropic_api_key,
)

SYSTEM_PROMPT = """
You are a volume analyst specializing in low-float momentum stocks.
You analyze price and volume patterns to determine whether a stock's
buying pressure is still alive — the key question is whether the main
player (주포) has left or is still holding.

Focus on:
- OBV (On-Balance Volume) slope
- Volume dry-up pattern (거래량 수렴)
- Pre-market vs regular session vs after-hours volume
- Turnover rate (손바뀜율)

Respond in Korean. Be concise and direct.
Provide your opinion as one of: 긍정 / 중립 / 부정
Always end with: opinion: [긍정/중립/부정]
"""


async def analyze(ticker: str, target_date: date, session: str = "regular") -> dict:
    # RAG로 필요한 엔드포인트 검색 후 거래량 분석
    try:
        # 1. 세션에 따라 다른 쿼리로 RAG 검색
        if session == "after_hours":
            rag_query = "aftermarket quote trade volume price after hours"
        elif session == "pre_market":
            rag_query = "premarket intraday 1min 5min historical chart volume"
        else:
            rag_query = "intraday historical chart 5min volume OHLCV price"

        fmp_endpoints = await retrieve_fmp_endpoint(
            query=rag_query,
            n_results=2,
        )

        # 2. 검색된 엔드포인트로 데이터 조회
        data_results = {}
        for ep in fmp_endpoints:
            endpoint = ep.get("endpoint", "")
            if endpoint:
                result = await fmp_repository.fetch_dynamic(
                    endpoint=endpoint,
                    ticker=ticker,
                )
                data_results[endpoint] = result

        # 3. fallback
        if not data_results:
            if session == "after_hours":
                data_results["aftermarket-quote"] = await fmp_repository.fetch_aftermarket_price(ticker=ticker)
            else:
                data_results["historical-price-eod"] = await fmp_repository.fetch_historical_price(
                    ticker=ticker, target_date=target_date
                )
                data_results["historical-chart-5min"] = await fmp_repository.fetch_intraday_price(
                    ticker=ticker, target_date=target_date
                )

        similar_cases = await retrieve_similar_cases(
            query=f"volume alive 주포 turnover rate {session} {ticker}",
        )

        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(
                    ticker=ticker,
                    target_date=target_date,
                    session=session,
                    data_results=data_results,
                    fmp_endpoints=fmp_endpoints,
                    similar_cases=similar_cases,
                )),
            ]
        )

        return _parse_response(response.content)
    except Exception as error:
        wrap_app_error(
            error,
            source="agent",
            code="AGENT/VOLUME/ANALYZE",
        )


def _build_prompt(
    ticker: str,
    target_date: date,
    session: str,
    data_results: dict,
    fmp_endpoints: list[dict],
    similar_cases: list[dict],
) -> str:
    endpoints_used = "\n".join([
        f"- {ep['endpoint']}: {ep['base_url']}"
        for ep in fmp_endpoints
    ])

    data_text = "\n".join([
        f"[{endpoint}]\n{data}"
        for endpoint, data in data_results.items()
    ])

    cases_text = "\n".join([
        f"- [{case['ticker']} | {case['date']} | {case['outcome']} | {case['session']}]: {case['document'][:200]}"
        for case in similar_cases
    ])

    return f"""
ticker: {ticker}
date: {target_date}
session: {session}

[사용된 FMP 엔드포인트]
{endpoints_used if endpoints_used else "기본 엔드포인트 사용"}

[조회된 데이터]
{data_text}

[유사 과거 사례]
{cases_text if cases_text else "없음"}

위 데이터를 분석해서 거래량이 살아있는지, 주포가 아직 나가지 않았는지 판단해줘.
세션({session})에 맞는 거래량 패턴을 분석해줘.
"""


def _parse_response(content: str) -> dict:
    opinion = "중립"
    for line in content.split("\n"):
        if line.startswith("opinion:"):
            opinion = line.replace("opinion:", "").strip()
    return {"opinion": opinion, "reason": content}