from __future__ import annotations

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
    agents: dict[str, AgentOpinion]