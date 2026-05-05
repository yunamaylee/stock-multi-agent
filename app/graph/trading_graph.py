import asyncio
from datetime import date
from typing import TypedDict

from langgraph.graph import StateGraph, END

from app.agents import (
    float_agent,
    volume_agent,
    short_agent,
    momentum_agent,
    news_agent,
    trader_agent,
    risk_agent,
)
from app.errors.app_error import wrap_app_error


class AgentState(TypedDict):
    ticker: str
    target_date: date
    session: str
    float_opinion: dict
    volume_opinion: dict
    short_opinion: dict
    momentum_opinion: dict
    news_opinion: dict
    trader_opinion: dict
    final_opinion: dict
    price_data: dict


async def run_analysts_parallel(state: AgentState) -> AgentState:
    results = await asyncio.gather(
        float_agent.analyze(
            ticker=state["ticker"],
            target_date=state["target_date"],
        ),
        volume_agent.analyze(
            ticker=state["ticker"],
            target_date=state["target_date"],
            session=state["session"],
        ),
        short_agent.analyze(
            ticker=state["ticker"],
            target_date=state["target_date"],
        ),
        momentum_agent.analyze(
            ticker=state["ticker"],
            target_date=state["target_date"],
            session=state["session"],
        ),
        news_agent.analyze(
            ticker=state["ticker"],
            target_date=state["target_date"],
        ),
    )

    volume_opinion = results[1]
    price_data = {
        "close": volume_opinion.get("close"),
        "open": volume_opinion.get("open"),
        "high": volume_opinion.get("high"),
        "low": volume_opinion.get("low"),
        "vwap": volume_opinion.get("vwap"),
        "volume": volume_opinion.get("volume"),
        "change_percent": volume_opinion.get("change_percent"),
    }

    return {
        **state,
        "float_opinion": results[0],
        "volume_opinion": volume_opinion,
        "short_opinion": results[2],
        "momentum_opinion": results[3],
        "news_opinion": results[4],
        "price_data": price_data,
    }


async def run_trader_agent(state: AgentState) -> AgentState:
    opinion = await trader_agent.analyze(
        ticker=state["ticker"],
        target_date=state["target_date"],
        float_opinion=state["float_opinion"],
        volume_opinion=state["volume_opinion"],
        short_opinion=state["short_opinion"],
        momentum_opinion=state["momentum_opinion"],
        news_opinion=state["news_opinion"],
    )
    return {**state, "trader_opinion": opinion}


async def run_risk_agent(state: AgentState) -> AgentState:
    opinion = await risk_agent.analyze(
        ticker=state["ticker"],
        target_date=state["target_date"],
        session=state["session"],
        float_opinion=state["float_opinion"],
        volume_opinion=state["volume_opinion"],
        short_opinion=state["short_opinion"],
        momentum_opinion=state["momentum_opinion"],
        news_opinion=state["news_opinion"],
        trader_opinion=state["trader_opinion"],
        price_data=state.get("price_data"),
    )
    return {**state, "final_opinion": opinion}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("analysts", run_analysts_parallel)
    graph.add_node("trader", run_trader_agent)
    graph.add_node("risk", run_risk_agent)

    graph.set_entry_point("analysts")
    graph.add_edge("analysts", "trader")
    graph.add_edge("trader", "risk")
    graph.add_edge("risk", END)

    return graph.compile()


async def run_analysis(
    ticker: str,
    target_date: date,
    session: str = "regular",
) -> dict:
    try:
        graph = build_graph()

        initial_state: AgentState = {
            "ticker": ticker,
            "target_date": target_date,
            "session": session,
            "float_opinion": {},
            "volume_opinion": {},
            "short_opinion": {},
            "momentum_opinion": {},
            "news_opinion": {},
            "trader_opinion": {},
            "final_opinion": {},
            "price_data": {},
        }

        return await graph.ainvoke(initial_state)
    except Exception as error:
        wrap_app_error(
            error,
            source="graph",
            code="GRAPH/TRADING/RUN_ANALYSIS",
        )