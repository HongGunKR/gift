"""가격 데이터에 대한 기술적 지표 계산 유틸리티."""

from typing import Dict, Iterable, Tuple

import pandas as pd


def prepare_price_frame(df: pd.DataFrame, ma_windows: Iterable[int] = (5, 20, 60)) -> pd.DataFrame:
    """
    이동평균, 거래량 평균 등을 추가한 데이터프레임을 반환합니다.
    """
    enriched = df.copy()
    for window in ma_windows:
        enriched[f"MA{window}"] = enriched["종가"].rolling(window).mean()
    enriched["거래량MA20"] = enriched["거래량"].rolling(20).mean()
    return enriched


def _safe_pct(base: float, comparison: float) -> float:
    if base in (0, None):
        return 0.0
    try:
        return (comparison / base - 1) * 100
    except ZeroDivisionError:
        return 0.0


def compute_indicator_snapshot(
    df: pd.DataFrame,
    ma_windows: Tuple[int, ...] = (5, 20, 60),
) -> Dict[str, float]:
    """
    이동평균 괴리율, 거래량 변화, 52주 고저 대비 위치 등을 정리합니다.
    """
    if df.empty:
        return {}

    latest = df.iloc[-1]
    close = float(latest["종가"])
    volume = float(latest["거래량"])

    ma_values = {}
    for window in ma_windows:
        raw_value = df[f"MA{window}"].iloc[-1] if f"MA{window}" in df.columns else None
        ma_values[window] = float(raw_value) if pd.notna(raw_value) else 0.0
    ma_gaps = {window: _safe_pct(ma_values[window], close) for window in ma_windows}

    volume_ma_series = df.get("거래량MA20")
    volume_avg20 = float(volume_ma_series.iloc[-1]) if volume_ma_series is not None and pd.notna(volume_ma_series.iloc[-1]) else 0.0
    volume_gap = _safe_pct(volume_avg20, volume) if volume_avg20 else 0.0

    high_52 = float(df["종가"].max())
    low_52 = float(df["종가"].min())
    distance_high = _safe_pct(high_52, close)
    distance_low = _safe_pct(low_52, close)

    recent_returns = {}
    for window in (5, 20, 60):
        if len(df) > window:
            base = float(df["종가"].iloc[-(window + 1)])
            recent_returns[window] = _safe_pct(base, close)
        else:
            recent_returns[window] = 0.0

    snapshot = {
        "close": close,
        "volume": volume,
        "volume_avg20": volume_avg20,
        "volume_gap_pct": volume_gap,
        "high_52": high_52,
        "low_52": low_52,
        "distance_high_pct": distance_high,
        "distance_low_pct": distance_low,
    }

    for window in ma_windows:
        snapshot[f"ma_{window}"] = ma_values.get(window, 0.0)
        snapshot[f"ma_gap_{window}_pct"] = ma_gaps.get(window, 0.0)

    for window, value in recent_returns.items():
        snapshot[f"return_{window}_pct"] = value

    return snapshot
