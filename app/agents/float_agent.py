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
You are a float analyst specializing in low-float momentum stocks.
You analyze share float, insider ownership, and liquidity to determine
whether a stock has the structural setup for a significant price surge.

Respond in Korean. Be concise and direct.
Provide your opinion as one of: 긍정 / 중립 / 부정
Always end with: opinion: [긍정/중립/부정]
"""


async def analyze(ticker: str, target_date: date) -> dict:
    # RAG로 필요한 엔드포인트 검색 후 데이터 조회 및 분석
    try:
        # 1. RAG로 float 관련 FMP 엔드포인트 검색
        fmp_endpoints = await retrieve_fmp_endpoint(
            query="float shares outstanding insider ownership low float",
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

        # 3. fallback: RAG 결과 없으면 기본 엔드포인트 사용
        if not data_results:
            data_results["shares-float"] = await fmp_repository.fetch_share_float(ticker=ticker)

        # 4. 유사 과거 사례 검색
        similar_cases = await retrieve_similar_cases(
            query=f"low float structure insider ownership {ticker}",
        )

        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(
                    ticker=ticker,
                    target_date=target_date,
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
            code="AGENT/FLOAT/ANALYZE",
        )


def _build_prompt(
    ticker: str,
    target_date: date,
    data_results: dict,
    fmp_endpoints: list[dict],
    similar_cases: list[dict],
) -> str:
    # 분석 프롬프트 생성
    endpoints_used = "\n".join([
        f"- {ep['endpoint']}: {ep['base_url']}"
        for ep in fmp_endpoints
    ])

    data_text = "\n".join([
        f"[{endpoint}]\n{data}"
        for endpoint, data in data_results.items()
    ])

    cases_text = "\n".join([
        f"- [{case['ticker']} | {case['date']} | {case['outcome']}]: {case['document'][:200]}"
        for case in similar_cases
    ])

    return f"""
ticker: {ticker}
date: {target_date}

[사용된 FMP 엔드포인트]
{endpoints_used if endpoints_used else "기본 엔드포인트 사용"}

[조회된 데이터]
{data_text}

[유사 과거 사례]
{cases_text if cases_text else "없음"}

위 데이터를 분석해서 이 종목의 float 구조가 급등에 유리한지 판단해줘.
"""


def _parse_response(content: str) -> dict:
    # LLM 응답에서 opinion 추출
    opinion = "중립"
    for line in content.split("\n"):
        if line.startswith("opinion:"):
            opinion = line.replace("opinion:", "").strip()
    return {"opinion": opinion, "reason": content}