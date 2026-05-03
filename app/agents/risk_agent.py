from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.rag.retriever import retrieve_similar_cases
from app.errors.app_error import wrap_app_error


llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    api_key=settings.anthropic_api_key,
)

SYSTEM_PROMPT = """
You are a senior risk manager at a proprietary trading firm specializing in
low-float momentum stocks.

You receive the Trader's decision and must stress-test it against
historical surge/dump patterns from memory.

Your role (inspired by TradingAgents Bull/Bear debate):

BULL perspective: Find evidence supporting the Trader's BUY decision
BEAR perspective: Find evidence against it, especially from dump cases
SYNTHESIS: Final ruling based on pattern similarity to historical cases

Critical rule:
- Compare ONLY against retrieved historical cases
- surge cases supporting BUY → higher score
- dump cases matching current setup → lower score
- No hardcoded rules or thresholds

If no historical cases exist → decision: 중립, score: 50

Output Format:
BULL: [evidence from surge cases]
BEAR: [evidence from dump cases]
SYNTHESIS: [which side won]
decision: [진입/중립/패스]
score: [0-100]
"""


async def analyze(
    ticker: str,
    target_date: date,
    float_opinion: dict,
    volume_opinion: dict,
    short_opinion: dict,
    momentum_opinion: dict,
    news_opinion: dict,
    trader_opinion: dict,
) -> dict:
    # Trader 결정을 과거 패턴과 비교해 최종 승인/거부
    try:
        similarity_query = f"""
float: {float_opinion.get("opinion")}
volume: {volume_opinion.get("opinion")}
short: {short_opinion.get("opinion")}
momentum: {momentum_opinion.get("opinion")}
news: {news_opinion.get("opinion")}
trader_decision: {trader_opinion.get("trade_decision")}
""".strip()

        similar_cases = await retrieve_similar_cases(
            query=similarity_query,
            n_results=5,
        )

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
                    trader_opinion=trader_opinion,
                    similar_cases=similar_cases,
                )),
            ]
        )

        return _parse_response(response.content)
    except Exception as error:
        wrap_app_error(
            error,
            source="agent",
            code="AGENT/RISK/ANALYZE",
        )


def _build_prompt(
    ticker: str,
    target_date: date,
    float_opinion: dict,
    volume_opinion: dict,
    short_opinion: dict,
    momentum_opinion: dict,
    news_opinion: dict,
    trader_opinion: dict,
    similar_cases: list[dict],
) -> str:
    surge_cases = [c for c in similar_cases if c.get("outcome") == "surge"]
    dump_cases = [c for c in similar_cases if c.get("outcome") == "dump"]
    unknown_cases = [c for c in similar_cases if c.get("outcome") not in ("surge", "dump")]

    def fmt(cases):
        if not cases:
            return "없음"
        return "\n".join([
            f"- [{c['ticker']} | {c['date']} | {c['session']} | sim:{c['similarity']}]\n  {c['document'][:300]}"
            for c in cases
        ])

    return f"""
## Setup: {ticker} ({target_date})

### Trader Decision
decision: {trader_opinion.get("trade_decision")}
confidence: {trader_opinion.get("confidence")}
entry_condition: {trader_opinion.get("entry_condition")}
rationale: {trader_opinion.get("reason", "")[:200]}

### Analyst Summary
float: {float_opinion.get("opinion")} | volume: {volume_opinion.get("opinion")}
short: {short_opinion.get("opinion")} | momentum: {momentum_opinion.get("opinion")}
news: {news_opinion.get("opinion")}

### Historical Memory — Surge Cases
{fmt(surge_cases)}

### Historical Memory — Dump Cases
{fmt(dump_cases)}

### Historical Memory — Unknown
{fmt(unknown_cases)}

Trader said {trader_opinion.get("trade_decision")}.
Use Bull/Bear debate structure to stress-test this decision.
Base your ruling ONLY on similarity to historical cases above.
"""


def _parse_response(content: str) -> dict:
    decision = "중립"
    score = 50

    for line in content.split("\n"):
        if line.startswith("decision:"):
            decision = line.replace("decision:", "").strip()
        if line.startswith("score:"):
            score_str = line.replace("score:", "").strip()
            score = int(score_str) if score_str.isdigit() else 50

    return {
        "opinion": decision,
        "reason": content,
        "decision": decision,
        "score": score,
    }