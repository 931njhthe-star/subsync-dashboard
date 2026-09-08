# SubSync Dashboard

SubSync의 내부 운영·분석용 Streamlit 대시보드입니다. Chrome Extension과 FastAPI backend와는 별도 프로세스·별도 저장소로 실행합니다.

## 실행

PowerShell:

```powershell
Set-Location "C:\Users\Playdata\Desktop\프로젝트\subsync-dashboard\subsync-dashboard"
uv sync
uv run streamlit run dashboard/app.py
```

브라우저에서 `http://localhost:8501`을 엽니다.

Supabase 접속 환경변수가 없으면 기본 화면은 저장소에 포함된 안전한 샘플 자료를 사용합니다. 샘플 자료는 실제 사용자 데이터로 표시하지 않습니다.

## 데이터 원천

이 대시보드는 Supabase를 유일한 데이터 원천으로 사용합니다. 사이드바의 데이터
원천 선택 메뉴는 제공하지 않으며, 연결 실패 시 샘플 데이터로 대체하지 않고
오류를 표시합니다. 조회 기간 필터는 모든 관리자 화면에 공통으로 적용됩니다.

```powershell
# 실제 Supabase 자료를 사용하는 모드
$env:SUBSYNC_DASHBOARD_SOURCE = "supabase"
$env:SUPABASE_URL = "https://xlzfuotapkdvyuqdmmxz.supabase.co"
$env:SUPABASE_SECRET_KEY = "<sb_secret_server_key>"
uv run streamlit run dashboard/app.py
```

`SUPABASE_SECRET_KEY`와 기타 비밀값은 대시보드 프로세스 환경변수 또는 배포 환경의 secret store에서만 주입합니다. 로컬 개발에서는 프로젝트 루트 `.env`도 서버 프로세스 시작 시 읽습니다. 실제 키는 캐시 키·화면·브라우저·다운로드 파일·소스 저장소에 넣지 않습니다. 새 `sb_secret_...` 키는 서버 전용 고권한 키이므로, 외부에 배포할 때는 대시보드 자체도 관리자 인증이나 사내망으로 보호해야 합니다. 전체 운영 데이터를 표시하려면 별도 승인된 서버 측 읽기 경계를 우선 고려합니다. 레거시 `service_role` 키를 새 설정에 사용하지 않습니다.

## 실제 Supabase schema 매핑

현재 프로젝트의 `public` schema에 있는 다음 6개 테이블을 조회합니다.

| Supabase 테이블 | 대시보드 반영 |
| --- | --- |
| `users` | 전체 사용자 수 |
| `login_history` | 조회 기간 내 고유 로그인 사용자 |
| `saved_words` | 저장 단어와 상위 단어 |
| `ai_conversations` | Tutor 질문·답변 및 `feedback` JSONB |
| `llm_usage` | provider·model별 호출 수와 입력·출력·총 토큰 |
| `api_logs` | API 유형·상태 코드·응답시간·오류율·시스템 로그 |

`saved_words.saved_at`은 기존 분석 계약의 `created_at`으로 변환합니다. `ai_conversations`와 `api_logs`는 기존 화면의 Tutor 메시지·피드백·시스템 로그 frame으로 파생합니다. Supabase 조회는 실제 컬럼만 선택하고 테이블별 페이지네이션으로 최대 50,000행까지 읽습니다. 필수 테이블 누락, 인증·권한 오류, 네트워크 오류, 잘못된 응답은 오류로 처리하며 조용히 빈 live frame으로 바꾸지 않습니다. 현재 schema에 없는 `video_history`, `click_events` 지표는 샘플 숫자로 대체하지 않고 `-` 또는 빈 상태로 표시합니다.

## 화면

- **대시보드**: 전체 사용자·AI 호출, 일별 사용량과 최근 AI 활동
- **AI 사용량**: 모델·사용자 필터, 제공자별 호출량, 토큰·응답시간·오류율·P95와 일별 추이
- **API 호출**: 엔드포인트별 호출량, 성공률·오류 요청·평균 latency와 최근 상태 코드

## 구조

```text
subsync-dashboard/
├── dashboard/
│   ├── app.py
│   ├── analytics/
│   ├── components/
│   └── data/demo_data.json
├── tests/
├── pyproject.toml
└── README.md
```

## 테스트

```powershell
uv lock --check
uv run pytest -q
uv run python -m compileall -q dashboard tests
git diff --check
```
