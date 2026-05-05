from datetime import date
from typing import Optional

from app.errors.app_error import wrap_app_error
from app.graph.trading_graph import run_analysis
from app.models.response import AnalysisResponse, AgentOpinion
from app.rag.embedder import embed_case
from app.rag.fmp_doc_loader import load_fmp_docs as load_fmp_docs_to_vector
from app.repository import darkfina_repository, fmp_repository


async def analyze_stock(
    ticker: str,
    target_date: date,
    session: str = "regular",
) -> AnalysisResponse:
    # 종목 분석 유스케이스
    try:
        final_state = await run_analysis(
            ticker=ticker,
            target_date=target_date,
            session=session,
        )

        return _build_response(
            ticker=ticker,
            target_date=target_date,
            final_state=final_state,
        )
    except Exception as error:
        wrap_app_error(
            error,
            source="service",
            code="SERVICE/ANALYSIS/ANALYZE_STOCK",
        )


async def load_fmp_docs() -> None:
    # FMP 엔드포인트 요약을 벡터 DB에 적재 (관리용)
    try:
        await load_fmp_docs_to_vector()
    except Exception as error:
        wrap_app_error(
            error,
            source="service",
            code="SERVICE/ANALYSIS/LOAD_FMP_DOCS",
        )


async def save_case(
    ticker: str,
    target_date: date,
    outcome: str,
    session: str,
    note: Optional[str] = None,
) -> None:
    # 사례 저장 유스케이스
    try:
        float_data, historical_data, short_data, intraday_data = await _fetch_case_data(
            ticker=ticker,
            target_date=target_date,
            session=session,
        )

        await embed_case(
            ticker=ticker,
            target_date=target_date,
            outcome=outcome,
            session=session,
            float_data=float_data,
            volume_data=historical_data,
            short_data=short_data,
            momentum_data=intraday_data,
            news_data="",
            note=note,
        )
    except Exception as error:
        wrap_app_error(
            error,
            source="service",
            code="SERVICE/ANALYSIS/SAVE_CASE",
        )


async def _fetch_case_data(
    ticker: str,
    target_date: date,
    session: str,
) -> tuple:
    # 세션에 따라 다른 인트라데이 데이터 수집
    import asyncio

    if session == "after_hours":
        intraday_coro = fmp_repository.fetch_aftermarket_price(ticker=ticker)
    else:
        intraday_coro = fmp_repository.fetch_intraday_price(
            ticker=ticker,
            target_date=target_date,
        )

    results = await asyncio.gather(
        fmp_repository.fetch_share_float(ticker=ticker),
        fmp_repository.fetch_historical_price(ticker=ticker, target_date=target_date),
        darkfina_repository.fetch_short_data(ticker=ticker),
        intraday_coro,
    )
    return results


def _build_response(
    ticker: str,
    target_date: date,
    final_state: dict,
) -> AnalysisResponse:
    # 최종 상태를 응답 모델로 변환
    final_opinion = final_state.get("final_opinion", {})

    return AnalysisResponse(
        ticker=ticker,
        date=target_date,
        decision=final_opinion.get("decision", "패스"),
        score=final_opinion.get("score", 0),
        watch_condition=final_opinion.get("watch_condition"),
        entry_strategy=final_opinion.get("entry_strategy"),
        target=final_opinion.get("target"),
        stop_loss=final_opinion.get("stop_loss"),
        hold_days=final_opinion.get("hold_days"),
        agents={
            "float_agent": AgentOpinion(
                opinion=final_state.get("float_opinion", {}).get("opinion", ""),
                reason=final_state.get("float_opinion", {}).get("reason", ""),
            ),
            "volume_agent": AgentOpinion(
                opinion=final_state.get("volume_opinion", {}).get("opinion", ""),
                reason=final_state.get("volume_opinion", {}).get("reason", ""),
            ),
            "short_agent": AgentOpinion(
                opinion=final_state.get("short_opinion", {}).get("opinion", ""),
                reason=final_state.get("short_opinion", {}).get("reason", ""),
            ),
            "momentum_agent": AgentOpinion(
                opinion=final_state.get("momentum_opinion", {}).get("opinion", ""),
                reason=final_state.get("momentum_opinion", {}).get("reason", ""),
            ),
            "news_agent": AgentOpinion(
                opinion=final_state.get("news_opinion", {}).get("opinion", ""),
                reason=final_state.get("news_opinion", {}).get("reason", ""),
            ),
            "trader_agent": AgentOpinion(
                opinion=final_state.get("trader_opinion", {}).get("opinion", ""),
                reason=final_state.get("trader_opinion", {}).get("reason", ""),
            ),
            "risk_agent": AgentOpinion(
                opinion=final_opinion.get("opinion", ""),
                reason=final_opinion.get("reason", ""),
            ),
        },
    )