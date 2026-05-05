from __future__ import annotations

from typing import Optional
from pydantic import BaseModel
from datetime import date


class AgentOpinion(BaseModel):
    opinion: str
    reason: str


class AnalysisResponse(BaseModel):
    ticker: str
    date: date
    decision: str
    score: int
    watch_condition: Optional[str] = None
    entry_strategy: Optional[str] = None
    target: Optional[str] = None
    stop_loss: Optional[str] = None
    hold_days: Optional[str] = None
    agents: dict[str, AgentOpinion]