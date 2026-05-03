from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.errors.app_error import wrap_app_error


llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    api_key=settings.anthropic_api_key,
)

SYSTEM_PROMPT = """
You are a discretionary trader synthesizing analyst opinions on low-float momentum stocks.

Read all analyst views (float, volume, short, momentum, news) and produce ONE actionable plan
before risk review.

Rules:
- Prefer alignment across agents; flag conflict explicitly.
- decision must be exactly one of: 진입 / 중립 / 패스
- confidence: 0-100 (integer)
- entry_condition: one short Korean phrase (when you would act)

Respond in Korean. End with these exact lines:
trade_decision: [진입/중립/패스]
confidence: [0-100]
entry_condition: [...]
"""


async def analyze(
    ticker: str,
    target_date: date,
    float_opinion: dict,
    volume_opinion: dict,
    short_opinion: dict,
    momentum_opinion: dict,
    news_opinion: dict,
) -> dict:
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(
                    ticker=ticker,
                    target_date=target_date,
                    float_opinion=float_opinion,
                    volume_opinion=volume_opinion,
                    short_opinion=short_opinion,
                    momentum_opinion=momentum_opinion,
                    news_opinion=news_opinion,
                )),
            ]
        )
        return _parse_response(response.content)
    except Exception as error:
        wrap_app_error(
            error,
            source="agent",
            code="AGENT/TRADER/ANALYZE",
        )


def _build_prompt(
    ticker: str,
    target_date: date,
    float_opinion: dict,
    volume_opinion: dict,
    short_opinion: dict,
    momentum_opinion: dict,
    news_opinion: dict,
) -> str:
    return f"""
## {ticker} ({target_date})

### Analysts
- float: {float_opinion.get("opinion", "")} — {float_opinion.get("reason", "")[:400]}
- volume: {volume_opinion.get("opinion", "")} — {volume_opinion.get("reason", "")[:400]}
- short: {short_opinion.get("opinion", "")} — {short_opinion.get("reason", "")[:400]}
- momentum: {momentum_opinion.get("opinion", "")} — {momentum_opinion.get("reason", "")[:400]}
- news: {news_opinion.get("opinion", "")} — {news_opinion.get("reason", "")[:400]}

위를 종합해 trade_decision, confidence, entry_condition을 제시하라.
"""


def _parse_response(content: str) -> dict:
    trade_decision = "중립"
    confidence = "50"
    entry_condition = "미정"

    for line in content.split("\n"):
        line = line.strip()
        if line.lower().startswith("trade_decision:"):
            trade_decision = line.split(":", 1)[1].strip()
        elif line.lower().startswith("confidence:"):
            confidence = line.split(":", 1)[1].strip()
        elif line.lower().startswith("entry_condition:"):
            entry_condition = line.split(":", 1)[1].strip()

    return {
        "opinion": trade_decision,
        "reason": content,
        "trade_decision": trade_decision,
        "confidence": confidence,
        "entry_condition": entry_condition,
    }
