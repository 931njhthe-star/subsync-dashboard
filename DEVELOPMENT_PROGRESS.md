# SubSync Dashboard 개발 진행 보고서

## 현재 구조

- 저장소 위치: `C:\Users\rlagn\Desktop\project\subsync-dashboard`
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

- 개요: 활성 사용자, 누적 시청 시간, 저장 단어, 튜터 질문 KPI
- 학습 활동: 단어 클릭·저장 순위와 영상별 시청시간
- 튜터 품질: 평가 비율, 평균 응답시간, 오류율, 제공자별 성능
- 시스템 로그: 심각도·이벤트 유형 필터와 로그 파일 내려받기
- 메뉴·차트·표 헤더·상태 메시지·로그 표시값 한국어화

### 독립 저장소 분리

- `subsync-backend/dashboard/`의 대시보드 코드와 전용 테스트를 분리
- 대시보드 전용 `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example` 구성
- 대시보드 전용 샘플 자료와 실행 README 구성
- Streamlit 의존성을 backend에서 제거
- backend의 기존 대시보드 파일 및 전용 테스트 제거
- backend API 코드와 frontend 저장소는 수정하지 않음

### 검증

- 대시보드 테스트: 9개 통과
- Streamlit 화면 실행 테스트: 통과
- 실제 Streamlit 서버 health: `ok`
- Python `compileall`: 통과
- `uv lock --check`: 통과
- `git diff --check`: 통과
- 초기 커밋: `Create standalone Streamlit dashboard`

## 실행 방법

PowerShell:

```powershell
Set-Location "C:\Users\rlagn\Desktop\project\subsync-dashboard"
uv sync
uv run streamlit run dashboard/app.py
```

## 데이터 연결 정책

현재 backend의 관리자 인증·분석 전용 API가 완성되기 전까지는 샘플 자료와 로컬 자료 파일로 화면을 검증합니다. 실제 사용자 데이터 연결 전에는 관리자 권한, JWT/RLS, 읽기 전용 API 계약을 확정해야 합니다.

`SUPABASE_KEY` 및 기타 비밀값은 `.env`, Streamlit secrets 또는 배포 환경의 secret으로만 주입하며 저장소에 기록하지 않습니다.

## 다음 작업

1. backend 담당자와 분석 전용 읽기 API 계약 확정
2. 관리자 인증 및 권한 검증 연결
3. 실제 이벤트·시청기록·저장단어·튜터 피드백 데이터 연동
4. 운영 배포 환경에서 Streamlit과 FastAPI를 별도 서비스로 배포
5. [완료] 공개 GitHub 원격 저장소 생성 및 `main` 브랜치 push (`https://github.com/teach97/subsync-dashboard`)
