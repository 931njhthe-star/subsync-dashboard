"""Tutor 응답 품질과 provider 사용량 집계."""

from __future__ import annotations

import pandas as pd

from dashboard.analytics.data_loader import DashboardData


def feedback_breakdown(data: DashboardData) -> pd.DataFrame:
    """좋아요·아쉬움 피드백 수와 비율을 반환한다."""

    ratings = data.user_feedback["rating"].astype(str).str.lower()
    if ratings.empty:
        return pd.DataFrame(columns=["rating", "count", "share"])
    counts = ratings.value_counts().rename_axis("rating").reset_index(name="count")
    counts["share"] = (counts["count"] / counts["count"].sum() * 100).round(1)
    return counts


def provider_summary(data: DashboardData) -> pd.DataFrame:
    """provider별 질문 수·평균 지연시간을 반환한다."""

    frame = data.tutor_messages.copy()
    if frame.empty:
        return pd.DataFrame(columns=["provider", "questions", "avg_latency_ms"])
    if "sender" in frame:
        frame = frame[frame["sender"].astype(str).str.lower().eq("tutor")]
    frame["provider"] = frame["provider"].replace("", "unknown")
    result = (
        frame.groupby("provider", as_index=False)
        .agg(
            questions=("id", "count"),
            avg_latency_ms=("latency_ms", "mean"),
        )
        .sort_values("questions", ascending=False)
    )
    result["avg_latency_ms"] = result["avg_latency_ms"].round(1)
    return result.reset_index(drop=True)


__all__ = ["feedback_breakdown", "provider_summary"]
