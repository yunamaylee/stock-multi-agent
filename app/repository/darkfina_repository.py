# app/repository/darkfina_repository.py

from playwright.async_api import async_playwright

from app.errors.app_error import create_repo_error


BASE_URL = "https://darkfina.crazyrabbit.co"


async def fetch_short_data(ticker: str) -> dict:
    # Playwright로 공매도 데이터 크롤링
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(f"{BASE_URL}/short/{ticker}")

            # 데이터 로딩 완료 대기
            await page.wait_for_selector(
                "text=Short Interest",
                timeout=15000,
            )
            await page.wait_for_function(
                "() => !document.body.innerText.includes('데이터를 불러오는 중')",
                timeout=15000,
            )

            short_interest = await _extract_text(page, "Short Interest")
            ctb = await _extract_text(page, "CTB (연이율)")
            days_to_cover = await _extract_text(page, "Days to Cover")
            utilization = await _extract_text(page, "이용률")
            shares_outstanding = await _extract_text(page, "Shares Outstanding")
            float_shares = await _extract_text(page, "Float Shares")

            daily_data = await _extract_daily_table(page)
            short_interest_history = await _extract_short_interest_table(page)

            await browser.close()

            return {
                "ticker": ticker,
                "short_interest": short_interest,
                "ctb": ctb,
                "days_to_cover": days_to_cover,
                "utilization": utilization,
                "shares_outstanding": shares_outstanding,
                "float_shares": float_shares,
                "daily_data": daily_data,
                "short_interest_history": short_interest_history,
            }
    except Exception as error:
        raise create_repo_error(
            code="REPO/DARKFINA/FETCH_SHORT_DATA",
            cause=error,
        )


async def _extract_text(page, label: str) -> str:
    # 라벨 옆 값 추출
    try:
        element = page.locator(f"text={label}").locator("..").locator("xpath=following-sibling::*[1]")
        return await element.inner_text(timeout=5000)
    except Exception:
        return ""


async def _extract_daily_table(page) -> list[dict]:
    # 공매도 거래량 일별 데이터 추출
    try:
        rows = await page.locator("text=공매도 거래량 일별 데이터").locator("..").locator("table tr").all()
        result = []
        for row in rows[1:]:  # 헤더 제외
            cells = await row.locator("td").all_inner_texts()
            if len(cells) >= 4:
                result.append({
                    "date": cells[0],
                    "short_volume": cells[1],
                    "total_volume": cells[2],
                    "short_ratio": cells[3],
                    "status": cells[4] if len(cells) > 4 else "",
                })
        return result
    except Exception:
        return []


async def _extract_short_interest_table(page) -> list[dict]:
    # Short Interest 변화 테이블 추출
    try:
        rows = await page.locator("text=Short Interest 변화").locator("..").locator("table tr").all()
        result = []
        for row in rows[1:]:  # 헤더 제외
            cells = await row.locator("td").all_inner_texts()
            if len(cells) >= 5:
                result.append({
                    "date": cells[0],
                    "short_percent": cells[1],
                    "short_position": cells[2],
                    "shares_out": cells[3],
                    "float": cells[4],
                    "days_to_cover": cells[5] if len(cells) > 5 else "",
                    "change": cells[6] if len(cells) > 6 else "",
                })
        return result
    except Exception:
        return []