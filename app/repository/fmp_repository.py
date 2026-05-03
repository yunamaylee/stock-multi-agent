import httpx
from datetime import date, timedelta

from app.config import settings
from app.errors.app_error import create_repo_error


BASE_URL = "https://financialmodelingprep.com/stable"


async def fetch_share_float(ticker: str) -> dict:
    # float, 유통주식수 조회
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/shares-float",
                params={"symbol": ticker, "apikey": settings.fmp_api_key},
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                return {}
            return data[0] if isinstance(data, list) else data
    except Exception as error:
        raise create_repo_error(code="REPO/FMP/FETCH_SHARE_FLOAT", cause=error)


async def fetch_historical_price(ticker: str, target_date: date) -> dict:
    # 최근 5일 일봉 OHLCV 조회
    try:
        from_date = target_date - timedelta(days=5)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/historical-price-eod/full",
                params={
                    "symbol": ticker,
                    "from": str(from_date),
                    "to": str(target_date),
                    "apikey": settings.fmp_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                return {}
            return data[0] if isinstance(data, list) else data
    except Exception as error:
        raise create_repo_error(code="REPO/FMP/FETCH_HISTORICAL_PRICE", cause=error)


async def fetch_intraday_price(ticker: str, target_date: date) -> dict:
    # 5분봉 인트라데이 데이터 조회
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/historical-chart/5min",
                params={
                    "symbol": ticker,
                    "from": str(target_date),
                    "to": str(target_date),
                    "apikey": settings.fmp_api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                return {}
            return data[0] if isinstance(data, list) else data
    except Exception as error:
        raise create_repo_error(code="REPO/FMP/FETCH_INTRADAY_PRICE", cause=error)


async def fetch_aftermarket_price(ticker: str) -> dict:
    # 애프터마켓 시세 조회
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/aftermarket-quote",
                params={"symbol": ticker, "apikey": settings.fmp_api_key},
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                return {}
            return data[0] if isinstance(data, list) else data
    except Exception as error:
        raise create_repo_error(code="REPO/FMP/FETCH_AFTERMARKET_PRICE", cause=error)


async def fetch_quote(ticker: str) -> dict:
    # 현재가, 시총 조회
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/quote",
                params={"symbol": ticker, "apikey": settings.fmp_api_key},
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                return {}
            return data[0] if isinstance(data, list) else data
    except Exception as error:
        raise create_repo_error(code="REPO/FMP/FETCH_QUOTE", cause=error)


async def fetch_dynamic(endpoint: str, ticker: str, extra_params: dict = None) -> dict:
    # RAG가 선택한 엔드포인트로 동적 데이터 조회
    try:
        params = {"symbol": ticker, "apikey": settings.fmp_api_key}
        if extra_params:
            params.update(extra_params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/{endpoint}",
                params=params,
            )
            response.raise_for_status()
            data = response.json()
            if not data:
                return {}
            return data[0] if isinstance(data, list) else data
    except Exception as error:
        raise create_repo_error(code="REPO/FMP/FETCH_DYNAMIC", cause=error)