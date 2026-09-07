from __future__ import annotations

import pandas as pd

from dashboard.components.display_labels import (
    event_type_label,
    feedback_display_frame,
    page_label,
    provider_display_frame,
    source_label,
    system_log_display_frame,
    translate_frame_columns,
)


def test_navigation_and_source_labels_are_korean() -> None:
    assert page_label("Overview") == "개요"
    assert page_label("Learning Activity") == "학습 활동"
    assert page_label("Tutor Quality") == "튜터 품질"
    assert page_label("System Logs") == "시스템 로그"
    assert source_label("demo") == "샘플 데이터"
    assert source_label("json:export.json") == "자료 파일"


def test_display_frames_translate_headers_and_known_values() -> None:
    words = translate_frame_columns(
        pd.DataFrame([{"word": "scale", "clicks": 2, "saves": 1, "total": 3}]),
        "words",
    )
    assert list(words.columns) == ["단어", "클릭 수", "저장 수", "합계"]

    feedback = feedback_display_frame(
        pd.DataFrame([{"rating": "up", "count": 2, "share": 100.0}])
    )
    assert list(feedback.columns) == ["평가", "응답 수", "비율 (%)"]
    assert feedback.loc[0, "평가"] == "도움됨"

    providers = provider_display_frame(
        pd.DataFrame([{"provider": "stub", "questions": 1, "avg_latency_ms": 80.0}])
    )
    assert list(providers.columns) == ["제공자", "질문 수", "평균 응답시간 (밀리초)"]
    assert providers.loc[0, "제공자"] == "기본 응답"


def test_system_log_values_are_translated_without_changing_filter_keys() -> None:
    assert event_type_label("tutor.ask") == "튜터 질문"
    logs = system_log_display_frame(
        pd.DataFrame(
            [
                {
                    "created_at": "2026-09-06T00:00:00Z",
                    "severity": "warning",
                    "event_type": "caption.fetch",
                    "status_code": 429,
                    "latency_ms": 120,
                    "message": "Provider quota fallback",
                }
            ]
        )
    )
    assert list(logs.columns) == [
        "발생 시각 (협정 세계시)",
        "심각도",
        "이벤트 유형",
        "상태 코드",
        "응답시간 (밀리초)",
        "메시지",
    ]
    assert logs.loc[0, "심각도"] == "경고"
    assert logs.loc[0, "이벤트 유형"] == "자막 불러오기"
    assert logs.loc[0, "메시지"] == "제공자 할당량 초과로 대체 응답 사용"
