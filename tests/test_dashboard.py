from __future__ import annotations

from dashboard.analytics.data_loader import dashboard_data_from_payload, summarize_metrics


def test_dashboard_payload_is_normalized_into_typed_frames() -> None:
    data = dashboard_data_from_payload(
        {
            "users": [{"id": "u1", "created_at": "2026-09-01T00:00:00Z", "is_active": True}],
            "video_history": [
                {
                    "user_id": "u1",
                    "video_id": "v1",
                    "video_title": "Space",
                    "watch_duration_sec": 1800,
                    "updated_at": "2026-09-02T00:00:00Z",
                }
            ],
            "saved_words": [{"word": "orbit", "created_at": "2026-09-02T00:00:00Z"}],
        },
        source="test",
    )

    assert data.source == "test"
    assert data.users.loc[0, "id"] == "u1"
    assert data.video_history.loc[0, "watch_duration_sec"] == 1800
    assert str(data.video_history["updated_at"].dtype).startswith("datetime64")
    assert "click_events" in data.frames
    assert data.click_events.empty


def test_summary_metrics_are_safe_for_empty_optional_tables() -> None:
    data = dashboard_data_from_payload(
        {
            "users": [{"id": "u1", "is_active": True}],
            "video_history": [{"video_id": "v1", "watch_duration_sec": 3600}],
            "saved_words": [{"word": "orbit"}],
            "click_events": [{"word": "orbit"}, {"word": "launch"}],
            "tutor_messages": [],
            "user_feedback": [],
            "system_logs": [],
        }
    )

    metrics = summarize_metrics(data)

    assert metrics["total_users"] == 1
    assert metrics["active_users"] == 1
    assert metrics["watch_hours"] == 1.0
    assert metrics["saved_words"] == 1
    assert metrics["word_clicks"] == 2
    assert metrics["tutor_questions"] == 0
    assert metrics["tutor_helpful_rate"] is None
    assert metrics["error_rate"] is None
