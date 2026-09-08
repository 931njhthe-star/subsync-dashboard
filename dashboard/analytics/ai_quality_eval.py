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
    """provider별 사용량 또는 legacy Tutor 메시지 성능을 반환한다."""

    usage = data.llm_usage.copy()
    if not usage.empty:
        usage["provider"] = usage["provider"].fillna("").replace("", "unknown")
        usage["model"] = usage["model_name"].fillna("").replace("", "unknown")
        result = (
            usage.groupby(["provider", "model"], as_index=False)
            .agg(
                requests=("id", "count"),
                input_tokens=("input_tokens", lambda values: values.sum(min_count=1)),
                output_tokens=("output_tokens", lambda values: values.sum(min_count=1)),
                total_tokens=("total_tokens", lambda values: values.sum(min_count=1)),
            )
            .sort_values("requests", ascending=False)
        )
        # llm_usage와 api_logs 사이에 요청 correlation key가 없어 provider별
        # latency를 임의로 결합하지 않는다. 화면에서는 미측정 상태를 '-'로 표시한다.
        result["avg_latency_ms"] = pd.NA
        return result[
            [
                "provider",
                "model",
                "requests",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "avg_latency_ms",
            ]
        ].reset_index(drop=True)

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
