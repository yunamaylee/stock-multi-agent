import httpx

from app.config import settings
from app.errors.app_error import create_repo_error


BASE_URL = "https://api.perplexity.ai"


async def fetch_news(ticker: str, company_name: str) -> dict:
    # 종목 관련 최신 뉴스/공시 조회
    try:
        api_key = (settings.perplexity_api_key or "").strip()
        if not api_key:
            raise create_repo_error(
                code="REPO/PERPLEXITY/FETCH_NEWS",
                message="PERPLEXITY_API_KEY(perplexity_api_key)가 설정되어 있지 않습니다.",
                cause=ValueError("Missing perplexity_api_key"),
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a financial news analyst. Return only factual, recent news and SEC filings. Be concise.",
                        },
                        {
                            "role": "user",
                            "content": f"Find the latest news, SEC filings, and catalysts for {company_name} ({ticker}) stock. Focus on any announcements that could cause significant price movement.",
                        },
                    ],
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as http_error:
                # Include response payload for quick diagnosis (401/429/400/etc.)
                body = ""
                try:
                    body = response.text
                except Exception:
                    body = "<unavailable>"
                raise create_repo_error(
                    code="REPO/PERPLEXITY/FETCH_NEWS",
                    message=f"Perplexity API 오류 (status={response.status_code}): {body[:500]}",
                    cause=http_error,
                )

            return response.json()
    except Exception as error:
        if isinstance(error, Exception) and getattr(error, "code", None) == "REPO/PERPLEXITY/FETCH_NEWS":
            raise
        raise create_repo_error(code="REPO/PERPLEXITY/FETCH_NEWS", cause=error)