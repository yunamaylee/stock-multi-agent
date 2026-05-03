from __future__ import annotations

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    ticker: str = Field(..., description="종목 티커")
    date: datetime.date = Field(..., description="분석 날짜 (미국 기준)")
    session: str = Field("regular", description="장 구분: pre_market / regular / both / after_hours")


class CaseRequest(BaseModel):
    ticker: str = Field(..., description="종목 티커")
    date: datetime.date = Field(..., description="급등/급락 날짜 (미국 기준)")
    outcome: str = Field(..., description="결과: surge / dump / neutral")
    session: str = Field(..., description="장 구분: pre_market / regular / both / after_hours")
    note: Optional[str] = Field(None, description="메모 (선택)")