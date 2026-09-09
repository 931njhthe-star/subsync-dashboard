# SubSync Dashboard

YouTube 이중 자막 학습 서비스 SubSync의 내부 운영·분석용 Streamlit 대시보드입니다.
사용자, AI Tutor 사용량, API 호출 상태를 기간별로 확인할 수 있으며, 기본적으로
FastAPI 백엔드의 Dashboard API를 통해 운영 데이터를 조회합니다.

이 저장소는 `subsync-backend`와 별도 프로세스·별도 저장소로 실행됩니다.
애플리케이션 진입점은 `dashboard/app.py`이며, 백엔드가 제공하는 JSON 응답을
`DashboardData` 표준 DataFrame 계약으로 변환해 화면에 사용합니다.

## 구현된 기능

- 대시보드 홈: 선택 기간의 사용자 수와 AI 호출 수, 일별 AI 사용량, 최근 AI 활동,
  provider별 호출 비중을 표시합니다.
- AI 사용량: 모델·사용자 필터, 총 토큰, 평균 응답시간, 요청 수, 오류율, P95 응답시간,
  provider별 호출량, 일별 토큰 추이와 상세 요청 내역을 제공합니다.
- API 호출: 엔드포인트·사용자 필터, 요청 수, 성공률, 평균 응답시간, 오류 요청,
  엔드포인트별 집계, 최근 호출과 상태 코드를 제공합니다.
- 기간별 조회: 화면마다 조회 기간을 따로 유지하며, 선택한 기간을 FastAPI Dashboard API에
  `from_date`와 `to_date`로 전달합니다.
- 데이터 정규화: Dashboard API 응답 또는 Supabase 원본 데이터를 동일한 DataFrame 구조로
  변환해 기존 화면·분석 코드가 같은 계약을 사용하도록 합니다.
- 안전한 샘플 실행: 외부 서비스 없이 `dashboard/data/demo_data.json`으로 화면과 테스트를
  확인할 수 있습니다.
- 캐시: Streamlit rerun 사이의 데이터 snapshot을 60초 동안 캐시합니다. Supabase secret은
  캐시 인자와 화면·로그에 포함하지 않습니다.

## 로컬 실행

### 요구 사항

- Python 3.11 이상
- [uv](https://docs.astral.sh/uv/)
- 권장 모드에서는 실행 중인 SubSync FastAPI backend

### 설치

PowerShell 기준입니다.

```powershell
uv sync
Copy-Item .env.example .env
```

### FastAPI Dashboard API 모드

FastAPI backend를 먼저 실행한 뒤 대시보드를 시작합니다.

```powershell
$env:SUBSYNC_DASHBOARD_SOURCE = "dashboard_api"
$env:DASHBOARD_API_URL = "http://127.0.0.1:8000"
uv run streamlit run dashboard/app.py
```

### 샘플 데이터 모드

백엔드나 Supabase 없이 화면을 확인할 때 사용합니다.

```powershell
$env:SUBSYNC_DASHBOARD_SOURCE = "demo"
uv run streamlit run dashboard/app.py
```

실행 후 브라우저에서 `http://localhost:8501`을 엽니다.

## 시스템 구성 및 데이터 조회 흐름

권장 운영 경로는 대시보드가 Supabase에 직접 접근하지 않고 FastAPI 백엔드를 통해 데이터를
읽는 방식입니다.

```text
Streamlit Dashboard
        │ HTTP REST API (JSON)
        ▼
FastAPI Dashboard API
        │ server-side access
        ▼
Supabase PostgreSQL
```

호환성 확인이나 별도 개발 환경에서는 대시보드가 Supabase PostgREST를 직접 조회하는
레거시 모드도 사용할 수 있습니다.

```text
Streamlit Dashboard ── HTTP ──▶ Supabase PostgREST
              (legacy-supabase / direct-supabase)
```

`dashboard/dashboard_api.py`는 FastAPI의 세 Dashboard API 응답을 화면용 snapshot으로
변환하고, `dashboard/analytics/data_loader.py`는 날짜·수치·파생 frame을 표준화합니다.

사이드바 조회 기간은 화면마다 따로 유지되며, 현재 화면의 기간만 해당 API 조회에
전달됩니다.

```powershell
# FastAPI Dashboard API 모드
$env:SUBSYNC_DASHBOARD_SOURCE = "dashboard_api"
$env:DASHBOARD_API_URL = "https://subsync-backend-4bmh.onrender.com/"
uv run streamlit run dashboard/app.py
```

기존 Streamlit의 Supabase 직접 조회가 필요할 때만
`SUBSYNC_DASHBOARD_SOURCE=legacy-supabase` 또는 `direct-supabase`를 사용할 수 있습니다.

권장 `dashboard_api` 모드에서는 Streamlit에 Supabase 키를 설정하지 않습니다. FastAPI
서버의 `.env`에 Supabase 서버용 `SUPABASE_URL`과 `SUPABASE_SECRET_KEY`를 설정합니다.

Supabase 직접 조회 모드에서만 대시보드 프로세스 환경변수 또는 배포 환경의 secret store로
`SUPABASE_SECRET_KEY`를 주입합니다. 실제 키는 캐시 키·화면·브라우저·로그·소스 저장소에
넣지 않습니다. 새 `sb_secret_...` 키는 서버 전용 고권한 키이므로 외부 배포 시 대시보드
자체도 관리자 인증이나 사내망으로 보호해야 합니다.

## 데이터 소스 모드

| 모드 | 용도 | 필요한 설정 |
| --- | --- | --- |
| `dashboard_api` | 권장. FastAPI Dashboard API를 통한 운영 데이터 조회 | `DASHBOARD_API_URL` |
| `demo` | 외부 서비스 없이 샘플 데이터로 화면 확인 | 없음 |
| `legacy-supabase` | 기존 방식의 Supabase 직접 조회 | `SUPABASE_URL` + 서버 전용 키 |
| `direct-supabase` | `legacy-supabase`와 동일한 직접 조회 호환 alias | `SUPABASE_URL` + 서버 전용 키 |

현재 Streamlit 진입점의 기본 모드는 `dashboard_api`입니다. 데이터 로더 내부에는
`json`, `auto`, `supabase` 로더도 있어 테스트·재사용이 가능하지만, 일반적인 화면 실행은
위 표의 모드를 사용합니다.

## 실제 Supabase schema 매핑

Supabase 직접 조회 모드와 FastAPI 응답의 기준이 되는 `public` schema 테이블은 다음
6개입니다.

| Supabase 테이블 | 대시보드 반영 |
| --- | --- |
| `users` | 전체 사용자 수 |
| `login_history` | 조회 기간 내 고유 로그인 사용자 |
| `saved_words` | 저장 단어와 상위 단어 |
| `ai_conversations` | Tutor 질문·답변 및 `feedback` JSONB |
| `llm_usage` | provider·model별 호출 수와 입력·출력·총 토큰 |
| `api_logs` | API 유형·상태 코드·응답시간·오류율·시스템 로그 |

`saved_words.saved_at`은 기존 분석 계약의 `created_at`으로 변환합니다.
`ai_conversations`는 Tutor 메시지·피드백 frame으로, `api_logs`는 시스템 로그 frame으로
파생합니다. Supabase 조회는 실제 컬럼만 선택하고 테이블별 `id` 오름차순 페이지네이션으로
최대 50,000행까지 읽습니다.

필수 테이블 누락, 인증·권한 오류, 네트워크 오류, 잘못된 응답은 오류로 처리하며 조용히
빈 live frame으로 바꾸지 않습니다. 현재 schema에 없는 `video_history`, `click_events`
지표는 샘플 숫자로 대체하지 않고 `-` 또는 빈 상태로 표시합니다.

## 화면

- **대시보드**: 기간 내 사용자 수와 AI 호출 수, 일별 AI 사용량, 최근 AI 활동,
  provider별 호출 비중
- **AI 사용량**: 모델·사용자 필터, provider별 호출량, 총·입력·출력 토큰,
  평균 응답시간, 오류율, P95, 일별 토큰 추이와 상세 내역
- **API 호출**: 엔드포인트·사용자 필터, 호출량, 성공률, 평균 응답시간, 오류 요청,
  엔드포인트별 집계, 최근 상태 코드와 429 rate limit 경고

## Dashboard API 기준

`SUBSYNC_DASHBOARD_SOURCE=dashboard_api`일 때 화면은 FastAPI Dashboard API의 다음
응답만 사용합니다. 날짜 범위는 시작일과 종료일을 모두 포함합니다.

| 화면 데이터 | Method | 경로 | 추가 파라미터 |
| --- | --- | --- | --- |
| 홈 요약 | GET | `/api/v1/dashboard/overview` | `recent_limit=10` |
| AI 사용량 | GET | `/api/v1/dashboard/usage` | 없음 |
| API 호출 | GET | `/api/v1/dashboard/api-calls` | `recent_limit=100` |

세 요청에는 공통으로 다음 query parameter가 포함됩니다.

```text
from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
```

AI 사용량의 모델·사용자 필터는 조회한 응답 데이터에 적용됩니다. 별도의 Gemini·Grok
API 키나 LLM 요약 호출은 필요하지 않습니다. API가 오류 상태 코드나 올바르지 않은
JSON을 반환하면 빈 화면으로 숨기지 않고 오류를 표시합니다.

## 프로젝트 구조

```text
subsync-dashboard/
├── dashboard/
│   ├── app.py                       # Streamlit 애플리케이션 진입점
│   ├── dashboard_api.py             # FastAPI Dashboard API client·응답 adapter
│   ├── analytics/
│   │   ├── data_loader.py           # demo·JSON·Supabase 데이터 로딩·정규화
│   │   ├── user_patterns.py         # 사용자·학습 활동 집계
│   │   └── ai_quality_eval.py       # Tutor 품질·provider 분석
│   ├── components/
│   │   ├── admin_pages.py           # AI 사용량·API 호출 화면
│   │   ├── home_dashboard.py         # Dashboard 홈 화면
│   │   ├── display_labels.py         # 한국어 라벨·표 변환
│   │   ├── feedback_view.py          # 피드백 표시 호환 component
│   │   ├── kpi_metrics.py            # KPI 카드 호환 component
│   │   └── realtime_logs.py          # 시스템 로그 표시 호환 component
│   ├── data/
│   │   └── demo_data.json            # 로컬 샘플 데이터
│   └── styles.py                     # 공통 Streamlit CSS
├── tests/                            # 화면·adapter·분석·Supabase mapping 테스트
├── .env.example                      # 환경변수 예시
├── pyproject.toml                    # 프로젝트·의존성 정의
├── uv.lock                           # uv dependency lock
├── DEVELOPMENT_PROGRESS.md           # 개발 진행 및 운영 메모
└── README.md
```

현재 Streamlit 메뉴에는 `Dashboard`, `AI Usage`, `API Calls`가 등록되어 있습니다.
`components/`의 일부 분석·로그 component는 기존 DataFrame 계약과 호환성을 위해 유지됩니다.

## 테스트

```powershell
uv lock --check
uv run pytest -q
uv run python -m compileall -q dashboard tests
git diff --check
```

테스트는 다음 범위를 포함합니다.

- Streamlit demo 화면 렌더링 및 프로젝트 루트 실행
- FastAPI Dashboard API 응답 adapter와 날짜 query parameter
- Supabase 실제 schema mapping, 페이지네이션, 오류 응답 처리
- KPI·분석 집계, 한국어 라벨과 화면 표시 형식

외부 provider나 실제 Supabase에 의존하지 않도록 fake client와 local fixture를 사용합니다.

## 환경 변수

기준 파일은 [.env.example](.env.example)입니다. 실제 secret은 저장소·브라우저·화면·로그에
넣지 않고, 배포 환경에서는 플랫폼 secret store 또는 Streamlit secrets를 사용합니다.

| 그룹 | 변수 | 용도 |
| --- | --- | --- |
| 실행 모드 | `SUBSYNC_DASHBOARD_SOURCE` | `dashboard_api`, `demo`, `legacy-supabase`, `direct-supabase` 선택 |
| 백엔드 연결 | `DASHBOARD_API_URL` | FastAPI backend base URL. `.env.example` 기본값은 `http://127.0.0.1:8000` |
| 백엔드 연결 | `DASHBOARD_API_TIMEOUT_SECONDS` | Dashboard API 요청 timeout(초). 기본값 8 |
| Supabase 직접 조회 | `SUPABASE_URL` | legacy 직접 조회용 Supabase project URL |
| Supabase 직접 조회 | `SUPABASE_SECRET_KEY` | 서버 전용 Supabase secret key |
| Supabase 직접 조회 | `SUPABASE_KEY` | 기존 설정과의 호환용 key alias |

권장 `dashboard_api` 모드에서는 Supabase 키를 대시보드 프로세스에 설정할 필요가 없습니다.
FastAPI backend가 Supabase 접근과 권한 경계를 담당합니다.

## 보안 및 운영 주의사항

- 이 대시보드는 현재 별도 관리자 로그인 UI를 제공하지 않습니다. FastAPI Dashboard API도
  관리자 인증이 연결되기 전인 개발용 계약이므로, 운영 배포 시 사내망·접근 제어·관리자
  인증을 별도로 적용해야 합니다.
- `SUPABASE_SECRET_KEY`와 legacy `SUPABASE_KEY`는 RLS를 우회할 수 있는 서버 전용 자격
  증명입니다. 브라우저 번들, 화면, 로그, 캐시, 저장소에 노출하지 않습니다.
- Streamlit 캐시에는 Supabase 원문 key를 넣지 않습니다. 현재 데이터 snapshot 캐시 TTL은
  60초이며, 즉시 반영이 필요한 운영 지표는 backend 반영 지연도 함께 확인합니다.
- `429` API 응답이 존재하면 API 호출 화면에서 rate limit 경고를 표시합니다. backend의
  provider fallback·재시도·호출 제한 정책을 함께 확인합니다.


## 변경 시 체크리스트

- Dashboard API 응답 변경: `dashboard/dashboard_api.py`, 화면 adapter와 관련 테스트를 함께
  갱신합니다.
- Supabase schema 변경: `dashboard/analytics/data_loader.py`의 테이블·컬럼 mapping과
  `tests/test_supabase_mapping.py`를 함께 갱신합니다.
- 화면·지표 변경: 해당 component, 한국어 label, Streamlit 화면 테스트를 함께 확인합니다.
- 의존성 변경: `uv`로 의존성을 갱신하고 `uv.lock`을 커밋합니다.
- 커밋 전 `git status`, `git diff`, `git diff --check`로 secret과 의도하지 않은 변경을
  확인합니다.
