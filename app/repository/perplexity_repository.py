import httpx

from app.config import settings
from app.errors.app_error import create_repo_error


BASE_URL = "https://api.perplexity.ai"


async def fetch_news(ticker: str, company_name: str) -> dict:
    # 종목 관련 최신 뉴스/공시 조회
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.perplexity_api_key}",
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
            response.raise_for_status()
            return response.json()
    except Exception as error:
        raise create_repo_error(
            code="REPO/PERPLEXITY/FETCH_NEWS",
            cause=error,
        )