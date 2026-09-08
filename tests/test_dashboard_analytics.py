from __future__ import annotations

import pandas as pd

from dashboard.analytics.ai_quality_eval import feedback_breakdown, provider_summary
from dashboard.analytics.data_loader import dashboard_data_from_payload, filter_by_date
from dashboard.analytics.user_patterns import daily_activity, top_words, video_summary


def sample_data():
    return dashboard_data_from_payload(
        {
            "users": [{"id": "u1", "is_active": True}],
            "video_history": [
                {
                    "video_id": "v1",
                    "video_title": "Space",
                    "watch_duration_sec": 3600,
                    "last_timestamp": 42,
                    "updated_at": "2026-09-05T00:00:00Z",
                }
            ],
            "saved_words": [{"word": "orbit", "created_at": "2026-09-05T00:00:00Z"}],
            "click_events": [
                {"word": "orbit", "created_at": "2026-09-05T00:00:00Z"},
                {"word": "launch", "created_at": "2026-09-05T00:00:00Z"},
            ],
            "tutor_messages": [
                {
                    "id": "tm1",
                    "sender": "user",
                    "provider": "stub",
                    "latency_ms": 0,
                    "created_at": "2026-09-05T00:00:00Z",
                },
                {
                    "id": "tm2",
                    "sender": "tutor",
                    "provider": "stub",
                    "latency_ms": 90,
                    "created_at": "2026-09-05T00:00:01Z",
                },
            ],
            "user_feedback": [{"rating": "up", "created_at": "2026-09-05T00:00:02Z"}],
            "system_logs": [],
        }
    )


def test_dashboard_analytics_builds_activity_word_and_video_views():
    data = sample_data()

    activity = daily_activity(data)
    words = top_words(data)
    videos = video_summary(data)

    assert activity.loc[0, "watch_hours"] == 1.0
    assert int(activity.loc[0, "word_clicks"]) == 2
    assert words.iloc[0]["word"] == "orbit"
    assert videos.iloc[0]["video_title"] == "Space"


def test_dashboard_analytics_filters_dates_and_summarizes_tutor_quality():
    data = sample_data()
    filtered = filter_by_date(data, pd.Timestamp("2026-09-05").date(), pd.Timestamp("2026-09-05").date())

    feedback = feedback_breakdown(filtered)
    providers = provider_summary(filtered)

    assert feedback.iloc[0]["rating"] == "up"
    assert providers.iloc[0]["provider"] == "stub"
    assert providers.iloc[0]["questions"] == 1
