from datetime import date
from typing import Optional

from app.repository.vector_repository import save_case
from app.errors.app_error import wrap_app_error


async def embed_case(
    ticker: str,
    target_date: date,
    outcome: str,
    session: str,
    float_data: dict,
    volume_data: dict,
    short_data: dict,
    momentum_data: dict,
    news_data: str,
    note: Optional[str] = None,
) -> None:
    # 사례를 자연어로 변환 후 벡터 DB에 저장
    try:
        document = _build_document(
            ticker=ticker,
            target_date=target_date,
            outcome=outcome,
            session=session,
            float_data=float_data,
            volume_data=volume_data,
            short_data=short_data,
            momentum_data=momentum_data,
            news_data=news_data,
            note=note,
        )

        metadata = {
            "ticker": ticker,
            "date": str(target_date),
            "outcome": outcome,
            "session": session,
        }

        case_id = f"{ticker}_{target_date}_{outcome}_{session}"

        await save_case(
            documents=[document],
            metadatas=[metadata],
            ids=[case_id],
        )
    except Exception as error:
        wrap_app_error(
            error,
            source="rag",
            code="RAG/EMBEDDER/EMBED_CASE",
        )


def _build_document(
    ticker: str,
    target_date: date,
    outcome: str,
    session: str,
    float_data: dict,
    volume_data: dict,
    short_data: dict,
    momentum_data: dict,
    news_data: str,
    note: Optional[str],
) -> str:
    # FMP 실제 필드명 기반으로 자연어 문서 생성

    # float 데이터
    float_shares = float_data.get("floatShares", "unknown")
    free_float = float_data.get("freeFloat", "unknown")
    outstanding = float_data.get("outstandingShares", "unknown")

    # 일봉 데이터
    close = volume_data.get("close", "unknown")
    volume = volume_data.get("volume", "unknown")
    change_percent = volume_data.get("changePercent", "unknown")
    vwap = volume_data.get("vwap", "unknown")
    high = volume_data.get("high", "unknown")
    low = volume_data.get("low", "unknown")
    open_price = volume_data.get("open", "unknown")

    # darkfina 숏 데이터
    short_interest = short_data.get("short_interest", "unknown")
    ctb = short_data.get("ctb", "unknown")
    days_to_cover = short_data.get("days_to_cover", "unknown")
    utilization = short_data.get("utilization", "unknown")

    # 일별 숏 데이터 (최근 3일)
    daily_short = short_data.get("daily_data", [])[:3]
    daily_short_text = " | ".join([
        f"{d.get('date')}: 숏비율 {d.get('short_ratio')} ({d.get('status')})"
        for d in daily_short
    ])

    return f"""
ticker: {ticker}
date: {target_date}
outcome: {outcome}
session: {session}
float shares: {float_shares}
free float: {free_float}%
outstanding shares: {outstanding}
open: {open_price}, high: {high}, low: {low}, close: {close}
change percent: {change_percent}%
vwap: {vwap}
volume: {volume}
short interest: {short_interest}
ctb: {ctb}
days to cover: {days_to_cover}
utilization: {utilization}
recent short ratio: {daily_short_text}
news: {news_data}
note: {note if note else "없음"}
""".strip()