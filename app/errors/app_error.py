from __future__ import annotations

from typing import Any, Literal, NoReturn, Optional

ErrorSource = Literal["repository", "service", "agent", "graph", "rag"]


class AppError(Exception):
    """레이어·코드·원인을 묶어 추적 가능한 애플리케이션 예외."""

    def __init__(
        self,
        *,
        source: ErrorSource,
        code: str,
        message: str,
        cause: Optional[BaseException] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.source = source
        self.code = code
        self.message = message
        self.cause = cause
        self.context = context

    def __str__(self) -> str:
        return f"[{self.source}] {self.code}: {self.message}"


def create_repo_error(
    code: str,
    cause: Exception,
    *,
    message: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> AppError:
    base_message = message if message is not None else str(cause)
    return AppError(
        source="repository",
        code=code,
        message=base_message,
        cause=cause,
        context=context,
    )


def wrap_app_error(
    error: BaseException,
    *,
    source: ErrorSource,
    code: str,
    message: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> NoReturn:
    """비즈니스/에이전트 등 상위 레이어에서 예외를 AppError로 통일."""
    if isinstance(error, AppError):
        raise error
    cause = error if isinstance(error, Exception) else None
    raise AppError(
        source=source,
        code=code,
        message=message if message is not None else str(error),
        cause=cause,
        context=context,
    )
