import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors.app_error import AppError, ErrorSource
from app.errors.error_messages import ERROR_DISPLAY_MESSAGES, display_message_for_code


def _http_status_for_app_error(source: ErrorSource) -> int:
    if source == "repository":
        return 502
    return 500


def _error_payload(*, source: str, code: str, message: str) -> dict[str, Any]:
    return {"error": {"source": source, "code": code, "message": message}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, error: AppError) -> JSONResponse:
        display = display_message_for_code(error.code, error.message)
        status = _http_status_for_app_error(error.source)
        return JSONResponse(
            status_code=status,
            content=_error_payload(
                source=error.source,
                code=error.code,
                message=display,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, error: Exception) -> JSONResponse:
        traceback.print_exc()
        fallback = ERROR_DISPLAY_MESSAGES["APP/UNHANDLED"]
        return JSONResponse(
            status_code=500,
            content=_error_payload(
                source="service",
                code="APP/UNHANDLED",
                message=fallback,
            ),
        )
