"""사용자 학습 행동을 대시보드용 집계표로 변환한다."""

from __future__ import annotations

import pandas as pd

from dashboard.analytics.data_loader import DashboardData


def _event_day(frame: pd.DataFrame, column: str = "created_at") -> pd.Series:
    """UTC timestamp를 날짜 단위로 변환한다."""

    if frame.empty:
        return pd.Series(dtype="object")
    return frame[column].dt.strftime("%Y-%m-%d")


def _tutor_activity_from_api_logs(data: DashboardData) -> pd.DataFrame:
    """ai_conversations가 없을 때 api_logs에서 Tutor 질문 활동을 계산한다."""

    logs = data.api_logs.copy()
    if logs.empty or "api_name" not in logs:
        return pd.DataFrame(columns=["date", "tutor_questions"])
    names = logs["api_name"].astype(str).str.lower()
    logs = logs.loc[names.str.contains("tutor/ask|tutor\\.ask", regex=True, na=False)].copy()
    if logs.empty:
        return pd.DataFrame(columns=["date", "tutor_questions"])
    statuses = pd.to_numeric(logs.get("status_code"), errors="coerce")
    success = logs.get("success")
    if success is None:
        success = statuses.lt(400)
    else:
        success = success.fillna(statuses.lt(400)).astype(bool)
    logs = logs.loc[success].copy()
    if logs.empty:
        return pd.DataFrame(columns=["date", "tutor_questions"])
    logs["date"] = logs["requested_at"].dt.strftime("%Y-%m-%d")
    return logs.groupby("date", as_index=False).size().rename(columns={"size": "tutor_questions"})


def daily_activity(data: DashboardData) -> pd.DataFrame:
    """날짜별 시청시간·단어 클릭·Tutor 질문 집계를 반환한다."""

    watch = data.video_history.copy()
    if not watch.empty:
        watch_date = "updated_at" if not watch["updated_at"].isna().all() else "created_at"
        watch["date"] = _event_day(watch, watch_date)
        watch = watch.groupby("date", as_index=False)["watch_duration_sec"].sum()
        watch["watch_hours"] = watch.pop("watch_duration_sec") / 3_600
    else:
        watch = pd.DataFrame(columns=["date", "watch_hours"])

    clicks = data.click_events.copy()
    if not clicks.empty:
        clicks["date"] = _event_day(clicks)
        clicks = clicks.groupby("date", as_index=False).size().rename(columns={"size": "word_clicks"})
    else:
        clicks = pd.DataFrame(columns=["date", "word_clicks"])

    tutor = data.tutor_messages.copy()
    if not tutor.empty and "sender" in tutor:
        tutor["sender"] = tutor["sender"].astype(str).str.lower()
        tutor = tutor[tutor["sender"].eq("user")].copy()
    if not tutor.empty:
        tutor["date"] = _event_day(tutor)
        tutor = tutor.groupby("date", as_index=False).size().rename(columns={"size": "tutor_questions"})
    else:
        # api_logs는 요청 관측값이고 ai_conversations는 대화 관측값이므로,
        # 대화 row가 있는 경우에는 API log를 다시 더하지 않아 중복을 막는다.
        tutor = _tutor_activity_from_api_logs(data)

    result = watch.merge(clicks, on="date", how="outer").merge(tutor, on="date", how="outer")
    if result.empty:
        return pd.DataFrame(columns=["date", "watch_hours", "word_clicks", "tutor_questions"])
    for column in ("watch_hours", "word_clicks", "tutor_questions"):
        result[column] = result[column].fillna(0)
    return result.sort_values("date").reset_index(drop=True)


def top_words(data: DashboardData, limit: int = 10) -> pd.DataFrame:
    """클릭·저장 횟수를 합산한 상위 단어 표를 반환한다."""

    clicks = data.click_events["word"].astype(str).str.strip().replace("", pd.NA).dropna()
    saves = data.saved_words["word"].astype(str).str.strip().replace("", pd.NA).dropna()
    click_counts = clicks.value_counts().rename("clicks")
    save_counts = saves.value_counts().rename("saves")
    result = pd.concat([click_counts, save_counts], axis=1).fillna(0)
    if result.empty:
        return pd.DataFrame(columns=["word", "clicks", "saves", "total"])
    result["total"] = result["clicks"] + result["saves"]
    return result.sort_values(["total", "clicks"], ascending=False).head(limit).reset_index(names="word")


def video_summary(data: DashboardData, limit: int = 10) -> pd.DataFrame:
    """영상별 누적 시청시간과 마지막 위치 표를 반환한다."""

    frame = data.video_history.copy()
    if frame.empty:
        return pd.DataFrame(columns=["video_id", "video_title", "watch_hours", "last_timestamp"])
    frame["video_title"] = frame["video_title"].replace("", "제목 미확인")
    result = (
        frame.groupby(["video_id", "video_title"], dropna=False, as_index=False)
        .agg(
            watch_hours=("watch_duration_sec", lambda values: round(values.sum() / 3_600, 1)),
            last_timestamp=("last_timestamp", "max"),
        )
        .sort_values("watch_hours", ascending=False)
        .head(limit)
    )
    return result.reset_index(drop=True)


__all__ = ["daily_activity", "top_words", "video_summary"]
