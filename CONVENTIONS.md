# stock-multi-agent 작성 규칙

실행·환경 변수는 `README.md`를 참고합니다. 이 문서는 **코드 구조·에러·네이밍·import**를 정의하며, 사람과 AI 도구가 동일한 기준으로 맞추기 위한 것입니다.

---

## 원칙

### 의존성 최소화

- 모듈 간 의존을 줄여 수정 범위를 예측 가능하게 합니다.
- 여러 곳에서 쓰일 때만 공용 모듈로 뺍니다. 한 화면(엔드포인트) 전용 로직은 해당 레이어 근처에 둡니다.

### 단일 책임

- 한 파일·한 함수는 **한 가지 역할**만 담당합니다.
- 역할이 늘어나면 파일·함수를 나누고, 이름만 봐도 무엇을 하는지 드러나게 짓습니다.
- **데이터 접근**(HTTP·DB·벡터·브라우저)은 `repository` 또는 RAG 저장/검색 유틸에 두고, **유스케이스 조합**은 `service`, **HTTP 바인딩**은 `router`에 둡니다.

### 가독성 우선

- 성능에 큰 영향이 없으면 **읽기 쉬운 코드**를 우선합니다. (AI가 맥락을 이어가기 쉽게)
- LangGraph·에이전트 체인처럼 디버깅 비용이 큰 부분은, 불필요한 추상화보다 **흐름이 한눈에 보이게** 유지합니다.

---

## 프로젝트 구조

| 경로 | 역할 |
|------|------|
| `app/main.py` | FastAPI 앱 생성, 라우터·예외 핸들러 등록 |
| `app/config.py` | 설정(환경 변수) |
| `app/router/` | API 라우트. 요청/응답 모델 연결, **비즈니스 조합 없음** |
| `app/service/` | 유스케이스: 여러 레포·그래프·RAG를 **조합**해 결과 반환 |
| `app/repository/` | 외부 API·스토리지 등 **I/O 단일 동작** (FMP, Perplexity, 벡터, 크롤링 등) |
| `app/graph/` | LangGraph 정의 및 `run_analysis` 같은 파이프라인 진입점 |
| `app/agents/` | 개별 에이전트 분석 단계 |
| `app/rag/` | 임베딩·리트리버·FMP 문서 적재 등 RAG 보조 로직 |
| `app/models/` | Pydantic 요청/응답 스키마 |
| `app/errors/` | `AppError`, 메시지 맵, FastAPI 예외 핸들러 |

### 레이어 호출 방향

- `router` → `service` (필요 시 `models`)
- `service` → `graph` / `agents` / `repository` / `rag`
- `graph` → `agents` (및 간접적으로 `repository` 등)
- `repository`·RAG 내부 저장 함수는 **다른 레이어를 역참조하지 않음**

관리용 엔드포인트라도 **라우터에서 RAG/레포를 직접 부르지 않고**, `service`에 메서드를 두고 호출합니다.

---

## 에러 처리 (추적 가능)

### 공통 예외: `AppError`

- 필드: `source`, `code`, `message`, `cause`, `context`(선택)
- `source`는 **어느 레이어에서 래핑했는지**를 나타냅니다.
  - `repository`: 외부 I/O·벡터·크롤링 등
  - `service`: 유스케이스
  - `agent`: 개별 에이전트
  - `graph`: LangGraph 파이프라인
  - `rag`: 임베딩·리트리버 등 RAG 계층

### 코드 네이밍

- 형식: `도메인/모듈/동작` 대문자와 `/` (예: `REPO/FMP/FETCH_QUOTE`, `SERVICE/ANALYSIS/ANALYZE_STOCK`, `AGENT/NEWS/ANALYZE`)
- 새 예외를 도입할 때는 **`app/errors/error_messages.py`**에 사용자용 문구를 같은 코드 키로 추가합니다.

### 사용 패턴

- 레포지토리(및 순수 I/O): `raise create_repo_error("REPO/...", cause=error)`
- 그 외 레이어: `wrap_app_error(error, source="...", code="...")` — 이미 `AppError`면 그대로 전파

### HTTP 응답

- `register_exception_handlers`가 통일된 본문을 반환합니다: `{"error": {"source", "code", "message"}}`
- `message`는 가능하면 **표시용 문구**(맵에 정의된 값). 내부 원인은 로그·`cause`로 추적합니다.
- 상태 코드: `source === "repository"` → **502**, 그 외 `AppError` → **500**, 미처리 예외 → **500** (`APP/UNHANDLED`)

---

## 네이밍

### 모듈·파일

- **snake_case** (`analysis_service.py`, `fmp_repository.py`)

### 함수

- 동사/구문 형태 (`analyze_stock`, `fetch_quote`, `run_analysis`)
- 비공개 헬퍼는 선행 `_` (`_build_response`)

### 상수

- 모듈 상단 **대문자 SNAKE_CASE** (예: `BASE_URL`)

---

## import 순서

1. 표준 라이브러리 (`datetime`, `typing`, …)
2. 서드파티 (`fastapi`, `httpx`, `langgraph`, …)
3. 로컬 `app.*` — **패키지 알파벳 순** (`app.agents`, `app.errors`, `app.graph`, …)

같은 그룹 안에서는 한 줄 한 import 또는 isort 규칙에 맞게 정렬합니다.

---

## 조건식

- **`else` 남용 대신 early return**으로 가드한 뒤, 아래에는 정상 경로만 두는 것을 권장합니다.
- 중첩이 깊어지면 함수 분리를 우선합니다.

---

## 함수·파라미터

### 서비스·레포지토리·그래프 진입 함수

- 인자가 늘어날수록 **키워드 인자**와 명시적 시그니처를 사용합니다.

```python
async def analyze_stock(
    ticker: str,
    target_date: date,
    session: str = "regular",
) -> AnalysisResponse:
    ...
```

### 작은 순수 유틸

- 파라미터 객체 하나(`TypedDict` 또는 dataclass)로 묶어도 됩니다. 재사용·필드 추가에 유리합니다.

---

## 라우터 작성

- 검증은 Pydantic 모델에 맡깁니다.
- 엔드포인트 본문은 짧게: `service` 호출 → 응답 반환.
- 성공 응답만 라우터에 두고, 실패는 `AppError`/핸들러로 일원화합니다.

---

## AI·협업 시 체크리스트

새 기능을 넣을 때:

1. I/O는 `repository` / RAG 저장·검색에만 둘 것인가?
2. 조합·트랜잭션 의미는 `service`인가?
3. 새 실패 경로에 `code`와 `error_messages.py` 항목을 추가했는가?
4. `source`가 실제 래핑 레이어와 일치하는가?
5. 라우터가 레포/RAG를 직접 import하지 않는가?

이 문서와 어긋나는 PR은 구조를 먼저 맞춘 뒤 로직을 논의합니다.
