# SubSync Dashboard 개발 진행 보고서

## 현재 구조

- 저장소 위치: `C:\Users\Playdata\Desktop\프로젝트\subsync-dashboard\subsync-dashboard`
- 실행 앱: `dashboard/app.py`
- 실행 방식: FastAPI와 독립된 Streamlit 프로세스
- 기본 데이터: 저장소 내부 샘플 자료
- 기본 접속 주소: `http://localhost:8501`

```text
subsync-dashboard/
├── dashboard/
│   ├── app.py
│   ├── analytics/
│   ├── components/
│   └── data/demo_data.json
├── tests/
├── pyproject.toml
├── uv.lock
├── README.md
└── DEVELOPMENT_PROGRESS.md
```

## 완료 내역

### 대시보드 화면

- 개요: 기간 내 로그인 사용자, 누적 시청 시간, 저장 단어, 튜터 질문 KPI
- 학습 활동: 단어 클릭·저장 순위와 영상별 시청시간
- 튜터 품질: 평가 비율, 전체 Tutor API 평균 응답시간, 오류율, provider·model별 사용량·토큰
- 시스템 로그: `api_logs` 기반 심각도·API 유형 필터와 로그 파일 내려받기
- 메뉴·차트·표 헤더·상태 메시지·로그 표시값 한국어화

### 독립 저장소 분리

- `subsync-backend/dashboard/`의 대시보드 코드와 전용 테스트를 분리
- 대시보드 전용 `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example` 구성
- 대시보드 전용 샘플 자료와 실행 README 구성
- Streamlit 의존성을 backend에서 제거
- backend의 기존 대시보드 파일 및 전용 테스트 제거
- backend API 코드와 frontend 저장소는 수정하지 않음

### 검증

- 대시보드 테스트: 23개 통과
- Streamlit 화면 실행 테스트: 통과
- 실제 Streamlit 서버 health: `ok`
- Python `compileall`: 통과
- `uv lock --check`: 통과
- `git diff --check`: 통과
- 초기 커밋: `Create standalone Streamlit dashboard`

### Supabase 실제 schema 반영

- `users`, `login_history`, `saved_words`, `ai_conversations`, `llm_usage`, `api_logs`를 실제 조회 목록으로 사용합니다.
- `saved_words.saved_at`은 기존 분석 계약의 `created_at`으로 변환합니다.
- `ai_conversations`의 질문·답변·JSONB feedback은 Tutor 메시지·피드백 화면으로 변환합니다.
- `api_logs`는 시스템 로그로 변환하며 Tutor 질문 수·평균 응답시간·오류율을 보완합니다.
- `llm_usage`는 provider·model별 호출 수와 입력·출력·총 토큰으로 표시합니다.
- 현재 schema에 없는 `video_history`, `click_events` 지표는 샘플 숫자로 대체하지 않고 `-` 또는 빈 상태로 표시합니다.
- 현재 RLS 정책은 인증된 사용자의 소유 row 조회 기준이므로, 전체 운영 데이터를 표시하려면 별도 승인된 서버 측 읽기 경계가 필요합니다. 서비스 키는 코드·브라우저·저장소에 넣지 않습니다.


PowerShell:

```powershell
Set-Location "C:\Users\Playdata\Desktop\프로젝트\subsync-dashboard\subsync-dashboard"
uv sync
uv run streamlit run dashboard/app.py
```

## 데이터 연결 정책

기본 실행은 샘플 자료이며, `SUPABASE_URL`과 `SUPABASE_KEY`가 함께 설정된 `auto` 또는 `supabase` 모드에서만 PostgREST를 조회합니다. REST 주소는 `https://xlzfuotapkdvyuqdmmxz.supabase.co`이며, 실제 Supabase schema의 6개 운영 테이블을 실제 컬럼 선택·페이지네이션으로 읽어 기존 분석 화면의 표준 frame으로 변환합니다. 필수 테이블 누락, 인증·권한 오류, 네트워크 오류, 잘못된 응답은 부분 자료로 숨기지 않습니다. 없는 영상 시청·클릭 테이블은 미측정 상태로 유지합니다.

현재 Supabase RLS는 인증된 사용자의 소유 row 조회 기준입니다. 전체 운영 데이터를 표시하려면 관리자 권한과 승인된 서버 측 읽기 전용 API 또는 reporting view를 별도로 확정해야 합니다. `SUPABASE_KEY` 및 기타 비밀값은 대시보드 프로세스 환경변수 또는 배포 환경의 secret store에서만 주입하며, 애플리케이션은 `.env` 파일이나 Streamlit secrets를 자동으로 읽지 않습니다. 비밀값은 저장소·브라우저에 기록하지 않습니다.

## 다음 작업

1. backend 담당자와 분석 전용 읽기 API 계약 확정
2. 관리자 인증 및 권한 검증 연결
3. 영상 시청·단어 클릭 데이터를 추가할 경우 실제 테이블 또는 API 계약을 확정하고 frame을 확장
4. 운영 배포 환경에서 Streamlit과 FastAPI를 별도 서비스로 배포
5. [완료] 공개 GitHub 원격 저장소 생성 및 `main` 브랜치 push (`https://github.com/teach97/subsync-dashboard`)
