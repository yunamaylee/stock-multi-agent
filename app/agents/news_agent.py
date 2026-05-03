from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.repository import perplexity_repository
from app.rag.retriever import retrieve_similar_cases
from app.errors.app_error import wrap_app_error


llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    api_key=settings.anthropic_api_key,
)

SYSTEM_PROMPT = """
You are a news and catalyst analyst specializing in low-float momentum stocks.
You analyze recent news, SEC filings, and catalysts to determine whether
there is a narrative driving the stock's price movement.

Important insight: A catalyst increases the magnitude of a move,
but is NOT required for a surge. Structural setup (float, volume, short)
matters more than news.

Focus on:
- SEC filings (6-K, 8-K, S-1, reverse split notices)
- Recent news sentiment
- Sector theme (cannabis, AI, China stocks, solar, shipping etc.)
- Whether the catalyst is genuine or just noise

Respond in Korean. Be concise and direct.
Provide your opinion as one of: 긍정 / 중립 / 부정
Always end with: opinion: [긍정/중립/부정]
"""


async def analyze(ticker: str, target_date: date, company_name: str = "") -> dict:
    # Perplexity로 뉴스/공시 조회 및 분석
    try:
        news_data = await perplexity_repository.fetch_news(
            ticker=ticker,
            company_name=company_name if company_name else ticker,
        )

        news_content = _extract_news_content(news_data)

        similar_cases = await retrieve_similar_cases(
            query=f"news catalyst SEC filing reverse split {ticker}",
        )

        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(
                    ticker=ticker,
                    target_date=target_date,
                    news_content=news_content,
                    similar_cases=similar_cases,
                )),
            ]
        )

        return _parse_response(response.content)
    except Exception as error:
        wrap_app_error(
            error,
            source="agent",
            code="AGENT/NEWS/ANALYZE",
        )


def _extract_news_content(news_data: dict) -> str:
    # Perplexity 응답에서 뉴스 텍스트 추출
    choices = news_data.get("choices", [])
    if not choices:
        return "뉴스 없음"
    return choices[0].get("message", {}).get("content", "뉴스 없음")


def _build_prompt(
    ticker: str,
    target_date: date,
    news_content: str,
    similar_cases: list[dict],
) -> str:
    cases_text = "\n".join([
        f"- [{case['ticker']} | {case['date']} | {case['outcome']}]: {case['document'][:200]}"
        for case in similar_cases
    ])

    return f"""
ticker: {ticker}
date: {target_date}

[최신 뉴스/공시]
{news_content}

[유사 과거 사례]
{cases_text if cases_text else "없음"}

위 뉴스와 공시를 분석해서 급등을 촉발할 만한 촉매가 있는지 판단해줘.
호재가 없어도 구조적 조건이 갖춰지면 오를 수 있다는 점을 염두에 두고 분석해줘.
"""


def _parse_response(content: str) -> dict:
    opinion = "중립"
    for line in content.split("\n"):
        if line.startswith("opinion:"):
            opinion = line.replace("opinion:", "").strip()
    return {"opinion": opinion, "reason": content}