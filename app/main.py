from fastapi import FastAPI

from app.router.stock_router import router as stock_router
from app.errors.handlers import register_exception_handlers


app = FastAPI(
    title="stock-multi-agent",
    description="RAG 기반 멀티에이전트 급등주 분석 시스템",
    version="0.1.0",
)

register_exception_handlers(app)

app.include_router(stock_router)


@app.get("/health")
async def health_check() -> dict:
    # 서버 상태 확인
    return {"status": "ok"}