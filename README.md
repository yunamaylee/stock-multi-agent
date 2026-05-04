# stock-multi-agent

**저유동·모멘텀·페니스탁** 맥락에서 멀티 에이전트와 RAG를 묶어 분석 의견·점수를 돌려주는 **FastAPI 백엔드**입니다.

---

## Background

같은 주제로 **개발 방향을 백 번 넘게** 갈아엎었습니다. 

만들고, 테스트하고, 지우기를 백번넘게 반복했습니다. 
<br/>
<br/>
<br/>
룰도, 알고리즘도 그럴듯했습니다. 실제 트레이더들의 알고리즘을 알아내기 위해 논문, Reddit, StockTwits등을 뒤졌습니다. 

수치가 틀린 건 아니었던 것 같습니다. 그런데 숫자만으로는 부족했습니다. 
<br/>
float이 작아도 세션이 다르면 이야기가 달라집니다. 뉴스가 비슷해도 공매도 구조가 다르면 방향이 갈렸습니다. 
<br/>
<br/>
<br/>
데이터와 데이터 사이에 깔리는 한 줄의 규칙으로는 다 담기 어려운 맥락이 빠지면, 같은 숫자도 다른 말을 한다는 것을 알게 되었습니다.

그래서 과거에 실제로 벌어진 사례와, 지금 쓰는 시세 API가 무엇을 의미하는지에 대한 설명을 같은 자리에 두고, 
<br/>
여러 에이전트가 그 위에서 판단하게 하는 백엔드를 만들었습니다.

---

## What it does

- **입력**: 티커·날짜·세션(`pre_market` / `regular` / `both` / `after_hours`).
- **출력**: 에이전트별 의견, 최종 `decision`·`score` 등 (`POST /stocks/analyze`).
- **사례 축적**: 유사 장면 RAG용 텍스트는 **`POST /stocks/cases`**로 벡터 DB에 적재합니다.

과거 시점을 반복 호출해 라벨과 맞춰 보고 프롬프트·코퍼스를 고치는 루프를 전제로 합니다.

---

## Pipeline

```text
[병렬] FloatAgent, VolumeAgent, ShortAgent, MomentumAgent, NewsAgent
                          ↓
                    TraderAgent
                          ↓
                    RiskAgent → 최종 decision·score
```

`app/graph/trading_graph.py`: 노드 `analysts` → `trader` → `risk`. 애널리스트 5명은 `run_analysts_parallel` 안에서 `asyncio.gather`로 동시 실행합니다.

---

## Role mapping

퀀트·트레이딩 데스크에서 **역할을 나누는 방식**을 차용해, 각 단계에 맞는 시스템 프롬프트·컨텍스트를 붙였습니다. ([TradingAgents](https://arxiv.org/abs/2412.20138)의 조직형 멀티에이전트와도 맞닿습니다.)

| Org-style role | In this project | Code |
|----------------|-----------------|------|
| 유통·지분 구조 애널리스트 | 유통주식·플로트·유동성 | `app/agents/float_agent.py` |
| 플로우·세션 애널리스트 | 세션별 거래량·체결 흐름 | `app/agents/volume_agent.py` |
| 숏·공매도 애널리스트 | 공매도·론 (크롤링 + 시세 보조) | `app/agents/short_agent.py` |
| 모멘텀·차트 애널리스트 | 인트라데이 모멘텀·패턴 | `app/agents/momentum_agent.py` |
| 뉴스·촉매 애널리스트 | 뉴스·이벤트 (Perplexity) | `app/agents/news_agent.py` |
| 데스크 트레이더 | 다섯 브리핑 → **진입 / 중립 / 패스** 초안 | `app/agents/trader_agent.py` |
| 리스크·리서치 | surge/dump **사례 RAG**로 초안 검토 → 최종 `decision`·`score` | `app/agents/risk_agent.py` |

**Engineering**

- **RAG** — 사례·FMP 엔드포인트 설명을 Chroma에 두고, **다섯 애널리스트·리스크**에서 검색해 프롬프트에 붙입니다. `trader_agent`는 RAG를 직접 호출하지 않고 애널리스트 출력만 받습니다.
- **툴 체인** — FMP REST, Perplexity, Playwright(DarkFina)를 한 파이프라인에서 사용합니다.
- **프롬프트 경계** — 단계별 출력 형식·근거 범위(예: 리스크는 검색 사례만)를 고정합니다.
- **API** — FastAPI, Pydantic, OpenAPI `/docs`, 레이어별 예외·HTTP 상태 (`app/errors/`).
- **규약** — [`CONVENTIONS.md`](./CONVENTIONS.md)

---

## Domain-specific design

논문의 **역할 분담·리스크 검토** 흐름은 참고하고, **분석 축·데이터·RAG·툴**은 도메인에 맞게 다시 잡았습니다.

| Design point | Implementation |
|--------------|----------------|
| 다섯 축 애널리스트 | 유통·세션별 거래량·숏·모멘텀·뉴스 전용 에이전트·프롬프트 |
| 세션 입력 | Volume·Momentum·FMP·RAG 쿼리를 `session`에 맞게 분기 |
| 숏 데이터 | DarkFina(Playwright) + FMP 보조 |
| FMP 선택 | 엔드포인트 요약을 벡터 검색 후 `fetch_dynamic` 호출 |
| 과거 장면 | surge/dump/neutral 사례 임베딩·유사 검색 → 애널리스트·리스크 |
| 리스크 | 트레이더 출력 + 검색 사례 + BULL/BEAR 스타일 프롬프트 → `decision`·`score` |

---

## Tech stack

| Layer | Choice |
|------|--------|
| Language | Python 3.9+ recommended |
| API | FastAPI, Uvicorn |
| Orchestration | LangGraph |
| LLM | Claude `claude-sonnet-4-5`, LangChain `ChatAnthropic` |
| News | Perplexity `sonar-pro` |
| Vector DB | ChromaDB |
| Other | httpx, pydantic-settings, Playwright |

---

## Getting started

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # API 키·CHROMA_DB_PATH 등
uvicorn app.main:app --reload --port 8000
```

| Step | Method | Path |
|------|--------|------|
| 1 | POST | `/stocks/admin/load-fmp-docs` |
| 2 | POST | `/stocks/cases` (optional: embed cases) |
| 3 | POST | `/stocks/analyze` |

스키마·시험 호출: **`/docs`**. 환경 변수: `.env.example`, `app/config.py`.

---

## Project structure

```text
app/
├── agents/       # 7 agent modules
├── graph/        # LangGraph
├── rag/
├── repository/
├── router/
├── service/
├── models/
├── errors/
├── config.py
└── main.py
```

---

## Reference

Yijia Xiao, Edward Sun, Di Luo, Wei Wang. *TradingAgents: Multi-Agents LLM Financial Trading Framework.* [arXiv:2412.20138](https://arxiv.org/abs/2412.20138), 2024.
