from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.repository import fmp_repository, darkfina_repository
from app.rag.retriever import retrieve_similar_cases, retrieve_fmp_endpoint
from app.errors.app_error import wrap_app_error


llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    api_key=settings.anthropic_api_key,
)

SYSTEM_PROMPT = """
You are a short squeeze analyst specializing in low-float momentum stocks.
You analyze short interest, days to cover, CTB, and borrow rates to determine
the probability of a short squeeze.

Note: Short interest data comes from DarkFina (FINRA/ChartExchange source).
FMP data supplements with quote and float information.

Focus on:
- Short interest % of float
- Days to cover
- CTB (Cost to Borrow)
- Short volume ratio trend
- Whether shorts are trapped

Respond in Korean. Be concise and direct.
Provide your opinion as one of: 긍정 / 중립 / 부정
Always end with: opinion: [긍정/중립/부정]
"""


async def analyze(ticker: str, target_date: date) -> dict:
    # DarkFina 공매도 데이터 + FMP 보조 데이터 조회 및 분석
    try:
        # 1. DarkFina에서 공매도 데이터 (핵심)
        short_data = await darkfina_repository.fetch_short_data(ticker=ticker)

        # 2. RAG로 보조 FMP 엔드포인트 검색
        fmp_endpoints = await retrieve_fmp_endpoint(
            query="quote market cap shares outstanding float short interest",
            n_results=1,
        )

        fmp_data = {}
        for ep in fmp_endpoints:
            endpoint = ep.get("endpoint", "")
            if endpoint:
                result = await fmp_repository.fetch_dynamic(
                    endpoint=endpoint,
                    ticker=ticker,
                )
                fmp_data[endpoint] = result

        if not fmp_data:
            fmp_data["quote"] = await fmp_repository.fetch_quote(ticker=ticker)

        similar_cases = await retrieve_similar_cases(
            query=f"short squeeze CTB days to cover float squeeze {ticker}",
        )

        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(
                    ticker=ticker,
                    target_date=target_date,
                    short_data=short_data,
                    fmp_data=fmp_data,
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
            code="AGENT/SHORT/ANALYZE",
        )


def _build_prompt(
    ticker: str,
    target_date: date,
    short_data: dict,
    fmp_data: dict,
    fmp_endpoints: list[dict],
    similar_cases: list[dict],
) -> str:
    endpoints_used = "\n".join([
        f"- {ep['endpoint']}: {ep['base_url']}"
        for ep in fmp_endpoints
    ])

    fmp_text = "\n".join([
        f"[{endpoint}]\n{data}"
        for endpoint, data in fmp_data.items()
    ])

    cases_text = "\n".join([
        f"- [{case['ticker']} | {case['date']} | {case['outcome']}]: {case['document'][:200]}"
        for case in similar_cases
    ])

    return f"""
ticker: {ticker}
date: {target_date}

[DarkFina 공매도 데이터]
short_interest: {short_data.get("short_interest")}
ctb: {short_data.get("ctb")}
days_to_cover: {short_data.get("days_to_cover")}
utilization: {short_data.get("utilization")}
float_shares: {short_data.get("float_shares")}
recent_short_ratio: {short_data.get("daily_data", [])[:3]}

[FMP 보조 데이터]
{fmp_text}

[사용된 FMP 엔드포인트]
{endpoints_used if endpoints_used else "기본 엔드포인트 사용"}

[유사 과거 사례]
{cases_text if cases_text else "없음"}

위 데이터를 분석해서 숏스퀴즈 가능성이 있는지 판단해줘.
"""


def _parse_response(content: str) -> dict:
    opinion = "중립"
    for line in content.split("\n"):
        if line.startswith("opinion:"):
            opinion = line.replace("opinion:", "").strip()
    return {"opinion": opinion, "reason": content}