import re
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.rag.retriever import retrieve_similar_cases
from app.repository import fmp_repository
from app.errors.app_error import wrap_app_error


llm = ChatAnthropic(
    model="claude-sonnet-4-5",
    api_key=settings.anthropic_api_key,
    max_tokens=2048,
)

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _sanitize_text(value) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return _CONTROL_CHARS_RE.sub("", text)


def _get_current_market_session() -> str:
    """
    Determine US market session by current New York time.
    - 04:00–09:30 ET: pre_market
    - 09:30–16:00 ET: regular
    - otherwise: after_hours
    """
    now_et = datetime.now(ZoneInfo("America/New_York")).time()
    if time(4, 0) <= now_et < time(9, 30):
        return "pre_market"
    if time(9, 30) <= now_et < time(16, 0):
        return "regular"
    return "after_hours"


SYSTEM_PROMPT = """
You are a senior risk manager at a proprietary trading firm specializing in
low-float momentum stocks.

You receive the Trader's decision and must stress-test it against
historical surge/dump patterns from memory.

Your role (inspired by TradingAgents Bull/Bear debate):

BULL perspective: Find evidence supporting the Trader's 진입 decision
BEAR perspective: Find evidence against it, especially from dump cases
SYNTHESIS: Final ruling based on pattern similarity to historical cases

Critical rules:
- Compare ONLY against retrieved historical cases
- surge cases supporting 진입 → higher score
- dump cases matching current setup → lower score
- Keep analysis under 400 words
- Reserve last 200 tokens for strategy fields
- If no historical cases exist → use score 50 (중립, 근거 없음) and matching decision

Score rubric (you MUST set score in 0–100 and decision MUST match this band):
- 0–39: 패스 (강한 덤프 신호)
- 40–49: 패스 (약한 덤프 신호)
- 50: 중립 (근거 없음)
- 51–60: 중립 (약한 서지 신호)
- 61–100: 진입 (강한 서지 신호)

decision must always match the score band above (진입 / 중립 / 패스 only).

Strategy derivation rules:
ALL strategy fields must be derived DIRECTLY from the most similar historical cases.
Do NOT use hardcoded numbers or score ranges to determine strategy.

Current price data is provided. Use it to output DOLLAR amounts for target and stop_loss.
- target: current_price × (1 + surge_case_gain%) → output as $X.XX
- stop_loss: current_price × (1 - dump_case_loss%) → output as $X.XX
- watch_condition: use dollar price levels based on current price
- entry_strategy: derived from surge case pattern
- hold_days: derived from surge case duration

IMPORTANT: Your entire response MUST end with EXACTLY these lines in order.

For 패스 (score 0–49):
decision: 패스
score: 25

For 중립 (score 50–60):
decision: 중립
score: 55
watch_condition: [$X.XX 돌파 + 거래량 조건]
entry_strategy: [빠른진입빠른청산/눌림목버티기/연속보유]
target: [$X.XX]
stop_loss: [$X.XX]
hold_days: [당일/1~2일/3일+]

For 진입 (score 61–100):
decision: 진입
score: 75
entry_strategy: [빠른진입빠른청산/눌림목버티기/연속보유]
target: [$X.XX]
stop_loss: [$X.XX]
hold_days: [당일/1~2일/3일+]

Use DOLLAR amounts based on current price data. decision must match score band.
"""


async def analyze(
    ticker: str,
    target_date: date,
    session: str = "regular",
    float_opinion: dict = None,
    volume_opinion: dict = None,
    short_opinion: dict = None,
    momentum_opinion: dict = None,
    news_opinion: dict = None,
    trader_opinion: dict = None,
    price_data: dict = None,
) -> dict:
    try:
        similarity_query = f"""
float: {_sanitize_text((float_opinion or {}).get("opinion"))}
volume: {_sanitize_text((volume_opinion or {}).get("opinion"))}
short: {_sanitize_text((short_opinion or {}).get("opinion"))}
momentum: {_sanitize_text((momentum_opinion or {}).get("opinion"))}
news: {_sanitize_text((news_opinion or {}).get("opinion"))}
trader_decision: {_sanitize_text((trader_opinion or {}).get("trade_decision"))}
""".strip()

        similar_cases = await retrieve_similar_cases(
            query=similarity_query,
            n_results=5,
        )

        # 입력 session과 무관하게 현재 시간(ET) 기준으로 가격 소스 결정
        realtime_price_data = {}
        try:
            current_session = _get_current_market_session()
            if current_session in ("pre_market", "after_hours"):
                quote = await fmp_repository.fetch_aftermarket_price(ticker=ticker)
                price = quote.get("askPrice") or quote.get("bidPrice")
            else:
                quote = await fmp_repository.fetch_quote(ticker=ticker)
                price = quote.get("price")

            if quote:
                realtime_price_data = {
                    "price": price,
                    "bid": quote.get("bidPrice") or quote.get("bid"),
                    "ask": quote.get("askPrice") or quote.get("ask"),
                    "open": quote.get("open"),
                    "high": quote.get("dayHigh") or quote.get("high"),
                    "low": quote.get("dayLow") or quote.get("low"),
                    "volume": quote.get("volume"),
                    "change_percent": quote.get("changesPercentage") or quote.get("changePercent"),
                }
        except Exception:
            # 실시간 가격 조회 실패 시 volume_opinion 데이터 fallback
            realtime_price_data = price_data or {}

        response = await llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_prompt(
                    ticker=ticker,
                    target_date=target_date,
                    float_opinion=float_opinion or {},
                    volume_opinion=volume_opinion or {},
                    short_opinion=short_opinion or {},
                    momentum_opinion=momentum_opinion or {},
                    news_opinion=news_opinion or {},
                    trader_opinion=trader_opinion or {},
                    similar_cases=similar_cases,
                    realtime_price_data=realtime_price_data,
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
    realtime_price_data: dict,
) -> str:
    surge_cases = [c for c in similar_cases if c.get("outcome") == "surge"]
    dump_cases = [c for c in similar_cases if c.get("outcome") == "dump"]
    unknown_cases = [c for c in similar_cases if c.get("outcome") not in ("surge", "dump")]

    def fmt(cases):
        if not cases:
            return "없음"
        return "\n".join([
            (
                f"- [{_sanitize_text(c.get('ticker'))} | {_sanitize_text(c.get('date'))} | "
                f"{_sanitize_text(c.get('session'))} | sim:{_sanitize_text(c.get('similarity'))}]\n  "
                f"{_sanitize_text(c.get('document'))[:200]}"
            )
            for c in cases
        ])

    price = realtime_price_data.get("price") or realtime_price_data.get("close", "unknown")
    high = realtime_price_data.get("high", "unknown")
    low = realtime_price_data.get("low", "unknown")
    volume = realtime_price_data.get("volume", "unknown")
    change_pct = realtime_price_data.get("change_percent", "unknown")

    # 현재 실시간 거래량이 있으면 명시 (에이전트들이 과거 데이터에 끌릴 수 있음)
    realtime_volume_note = ""
    if realtime_price_data.get("volume"):
        realtime_volume_note = (
            f"\n⚠️ 현재 실시간 거래량: {realtime_price_data.get('volume')}주 "
            f"(어제/과거 데이터와 다를 수 있음)"
        )

    return f"""
## Setup: {_sanitize_text(ticker)} ({_sanitize_text(target_date)})

### Current Real-Time Price Data (use for dollar-based targets)
- 현재가: ${price}
- 실시간 거래량: {volume}주 (오늘 누적 거래량)
{realtime_volume_note}
- 고점: ${high}
- 저점: ${low}
- 등락률: {change_pct}%

### Trader Decision
decision: {_sanitize_text(trader_opinion.get("trade_decision"))}
confidence: {_sanitize_text(trader_opinion.get("confidence"))}
entry_condition: {_sanitize_text(trader_opinion.get("entry_condition"))}
rationale: {_sanitize_text(trader_opinion.get("reason", ""))[:150]}

### Analyst Summary
float: {_sanitize_text(float_opinion.get("opinion"))} | volume: {_sanitize_text(volume_opinion.get("opinion"))}
short: {_sanitize_text(short_opinion.get("opinion"))} | momentum: {_sanitize_text(momentum_opinion.get("opinion"))}
news: {_sanitize_text(news_opinion.get("opinion"))}

### Historical Memory — Surge Cases
{fmt(surge_cases)}

### Historical Memory — Dump Cases
{fmt(dump_cases)}

### Historical Memory — Unknown
{fmt(unknown_cases)}

Trader said {_sanitize_text(trader_opinion.get("trade_decision"))}.
Be concise. Use Bull/Bear debate. Base ruling ONLY on historical cases above.

Use the current real-time price above to calculate DOLLAR amounts for target and stop_loss.
Derive ALL strategy fields from historical cases. Do NOT invent numbers.

End your reply with the exact lines matching the decision type per system prompt.
"""


def _decision_from_score(score: int) -> str:
    if score <= 49:
        return "패스"
    if 50 <= score <= 60:
        return "중립"
    return "진입"


def _parse_response(content: str) -> dict:
    content = _sanitize_text(content)
    decision_parsed: str | None = None
    score_parsed: int | None = None
    watch_condition_parsed: str | None = None
    entry_strategy_parsed: str | None = None
    target_parsed: str | None = None
    stop_loss_parsed: str | None = None
    hold_days_parsed: str | None = None

    for line in reversed(content.splitlines()):
        stripped = line.strip().strip("*").strip()
        lower = stripped.lower()

        if score_parsed is None and lower.startswith("score:"):
            numbers = re.findall(r"\d+", stripped)
            if numbers:
                score_parsed = min(100, max(0, int(numbers[0])))

        if decision_parsed is None and lower.startswith("decision:"):
            value = stripped.split(":", 1)[-1].strip()
            if value in ("진입", "중립", "패스"):
                decision_parsed = value

        if watch_condition_parsed is None and lower.startswith("watch_condition:"):
            watch_condition_parsed = stripped.split(":", 1)[-1].strip()

        if entry_strategy_parsed is None and lower.startswith("entry_strategy:"):
            entry_strategy_parsed = stripped.split(":", 1)[-1].strip()

        if target_parsed is None and lower.startswith("target:"):
            target_parsed = stripped.split(":", 1)[-1].strip()

        if stop_loss_parsed is None and lower.startswith("stop_loss:"):
            stop_loss_parsed = stripped.split(":", 1)[-1].strip()

        if hold_days_parsed is None and lower.startswith("hold_days:"):
            hold_days_parsed = stripped.split(":", 1)[-1].strip()

    score = 50 if score_parsed is None else score_parsed
    decision = _decision_from_score(score)

    return {
        "opinion": decision,
        "reason": content,
        "decision": decision,
        "score": score,
        "watch_condition": watch_condition_parsed,
        "entry_strategy": entry_strategy_parsed,
        "target": target_parsed,
        "stop_loss": stop_loss_parsed,
        "hold_days": hold_days_parsed,
    }