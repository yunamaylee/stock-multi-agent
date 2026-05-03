from fastapi import APIRouter
from app.models.request import AnalysisRequest, CaseRequest
from app.models.response import AnalysisResponse
from app.service import analysis_service

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.post("/admin/load-fmp-docs")
async def load_fmp_docs_endpoint() -> dict:
    # FMP API 문서 적재 (서비스 레이어에서 오케스트레이션)
    await analysis_service.load_fmp_docs()
    return {"message": "FMP API 문서 로드 완료"}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_stock(request: AnalysisRequest) -> AnalysisResponse:
    # 종목 분석 요청
    return await analysis_service.analyze_stock(
        ticker=request.ticker,
        target_date=request.date,
        session=request.session,
    )


@router.post("/cases")
async def save_case(request: CaseRequest) -> dict:
    # 사례 저장 요청
    await analysis_service.save_case(
        ticker=request.ticker,
        target_date=request.date,
        outcome=request.outcome,
        session=request.session,
        note=request.note,
    )
    return {
        "message": f"{request.ticker} ({request.date}) [{request.outcome}/{request.session}] 사례 저장 완료"
    }