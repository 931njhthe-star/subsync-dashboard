"""대시보드에 표시되는 한국어 라벨과 표 변환을 관리한다."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


PAGE_LABELS: Mapping[str, str] = {
    "Dashboard": "대시보드",
    "User Management": "사용자 관리",
    "AI Conversations": "AI 대화 내역",
    "Word Management": "단어 관리",
    "AI Usage": "AI 사용량",
    "API Calls": "API 호출",
    # 이전 분석 화면 키도 외부 호출·기존 테스트와의 호환성을 위해 유지한다.
    "Overview": "개요",
    "Learning Activity": "학습 활동",
    "Tutor Quality": "튜터 품질",
    "System Logs": "시스템 로그",
}

SOURCE_LABELS: Mapping[str, str] = {
    "demo": "샘플 데이터",
    "auto": "자동 선택",
    "json": "자료 파일",
    "supabase": "수파베이스",
}

SEVERITY_LABELS: Mapping[str, str] = {
    "info": "정보",
    "warning": "경고",
    "error": "오류",
    "critical": "심각",
}

EVENT_TYPE_LABELS: Mapping[str, str] = {
    "tutor.ask": "튜터 질문",
    "tutor.proactive": "튜터 알림",
    "tutor.feedback": "튜터 평가",
    "caption.fetch": "자막 불러오기",
    "word.click": "단어 조회",
    "word.save": "단어 저장",
    "history.update": "시청 기록 갱신",
    "system.error": "시스템 오류",
    "post /api/v1/tutor/ask": "튜터 질문 API",
    "post /api/v1/tutor/proactive": "튜터 알림 API",
    "post /api/v1/tutor/feedback": "튜터 평가 API",
    "get /api/v1/dict/hover": "단어 조회 API",
}

RATING_LABELS: Mapping[str, str] = {
    "up": "도움됨",
    "down": "아쉬움",
    "helpful": "도움됨",
    "not_helpful": "아쉬움",
}

PROVIDER_LABELS: Mapping[str, str] = {
    "stub": "기본 응답",
    "gemini": "제미나이",
    "google": "제미나이",
    "groq": "그록",
    "grok": "그록",
    "xai": "그록",
    "unknown": "알 수 없음",
}

LOG_MESSAGE_LABELS: Mapping[str, str] = {
    "Tutor response completed": "튜터 응답 완료",
    "Caption source loaded": "자막 원천 불러옴",
    "Provider quota fallback": "제공자 할당량 초과로 대체 응답 사용",
    "API request completed": "API 요청 완료",
    "API request failed": "API 요청 실패",
}

TABLE_COLUMN_LABELS: Mapping[str, Mapping[str, str]] = {
    "activity": {
        "date": "날짜",
        "watch_hours": "시청 시간 (시간)",
        "word_clicks": "단어 클릭 수",
        "tutor_questions": "튜터 질문 수",
    },
    "words": {
        "word": "단어",
        "clicks": "클릭 수",
        "saves": "저장 수",
        "total": "합계",
    },
    "videos": {
        "video_id": "영상 식별자",
        "video_title": "영상 제목",
        "watch_hours": "시청 시간 (시간)",
        "last_timestamp": "마지막 위치 (초)",
    },
    "feedback": {
        "rating": "평가",
        "count": "응답 수",
        "share": "비율 (%)",
    },
    "providers": {
        "provider": "제공자",
        "model": "모델",
        "questions": "질문 수",
        "requests": "호출 수",
        "input_tokens": "입력 토큰",
        "output_tokens": "출력 토큰",
        "total_tokens": "총 토큰",
        "avg_latency_ms": "평균 응답시간 (밀리초)",
    },
    "logs": {
        "created_at": "발생 시각 (협정 세계시)",
        "severity": "심각도",
        "event_type": "이벤트 유형",
        "status_code": "상태 코드",
        "latency_ms": "응답시간 (밀리초)",
        "message": "메시지",
    },
}


def _mapped_label(mapping: Mapping[str, str], value: Any, fallback: str) -> str:
    """값을 화면용 라벨로 변환한다."""

    key = "" if value is None else str(value).strip().lower()
    return mapping.get(key, fallback)


def page_label(value: Any) -> str:
    """내부 페이지 키를 한국어 메뉴명으로 변환한다."""

    return PAGE_LABELS.get(str(value), "기타 화면")


def source_label(value: Any) -> str:
    """내부 데이터 원천 키를 한국어 표시명으로 변환한다."""

    key = str(value).split(":", 1)[0].strip().lower()
    return SOURCE_LABELS.get(key, "기타 데이터")


def severity_label(value: Any) -> str:
    """로그 심각도를 한국어로 변환한다."""

    return _mapped_label(SEVERITY_LABELS, value, "기타 심각도")


def event_type_label(value: Any) -> str:
    """로그 이벤트 유형을 한국어로 변환한다."""

    return _mapped_label(EVENT_TYPE_LABELS, value, "기타 이벤트")


def rating_label(value: Any) -> str:
    """피드백 평가값을 한국어로 변환한다."""

    return _mapped_label(RATING_LABELS, value, "기타 평가")


def provider_label(value: Any) -> str:
    """AI 제공자 값을 한국어로 변환한다."""

    return _mapped_label(PROVIDER_LABELS, value, "기타 제공자")


def log_message_label(value: Any) -> str:
    """알려진 시스템 로그 메시지를 한국어로 변환한다."""

    return LOG_MESSAGE_LABELS.get(str(value), "기록된 시스템 메시지")


def translate_frame_columns(frame: pd.DataFrame, table: str) -> pd.DataFrame:
    """분석 프레임의 컬럼명을 화면용 한국어로 바꾼 복사본을 반환한다."""

    return frame.rename(columns=TABLE_COLUMN_LABELS.get(table, {})).copy()


def feedback_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """피드백 표의 값과 컬럼명을 화면용으로 변환한다."""

    display = translate_frame_columns(frame, "feedback")
    if "평가" in display:
        display["평가"] = display["평가"].map(rating_label)
    return display


def provider_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """제공자 표의 값과 컬럼명을 화면용으로 변환한다."""

    display = translate_frame_columns(frame, "providers")
    if "제공자" in display:
        display["제공자"] = display["제공자"].map(provider_label)
    for column in ("입력 토큰", "출력 토큰", "총 토큰"):
        if column in display:
            display[column] = display[column].map(
                lambda value: "-" if pd.isna(value) else f"{int(value):,}"
            )
    latency_column = "평균 응답시간 (밀리초)"
    if latency_column in display:
        display[latency_column] = display[latency_column].map(
            lambda value: "-" if pd.isna(value) else round(float(value), 1)
        )
    return display


def system_log_display_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """시스템 로그 표의 값과 컬럼명을 화면용으로 변환한다."""

    display = translate_frame_columns(frame, "logs")
    if "심각도" in display:
        display["심각도"] = display["심각도"].map(severity_label)
    if "이벤트 유형" in display:
        display["이벤트 유형"] = display["이벤트 유형"].map(event_type_label)
    if "메시지" in display:
        display["메시지"] = display["메시지"].map(log_message_label)
    return display


__all__ = [
    "event_type_label",
    "feedback_display_frame",
    "log_message_label",
    "page_label",
    "provider_display_frame",
    "provider_label",
    "rating_label",
    "severity_label",
    "source_label",
    "system_log_display_frame",
    "translate_frame_columns",
]
