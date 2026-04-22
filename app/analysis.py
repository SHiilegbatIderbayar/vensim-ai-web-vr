from __future__ import annotations
import pandas as pd


def resolve_year_window(year_start, year_end, model_horizon: dict | None = None):
    """
    Resolve the analysis window.
    Priority:
    1) explicit user years
    2) detected model horizon
    3) fallback horizon already embedded in model_horizon
    """
    if model_horizon is None:
        model_horizon = {"start": 0, "end": 100}

    base_start = model_horizon.get("start", 0)
    base_end = model_horizon.get("end", 100)

    y0 = year_start if year_start is not None else base_start
    y1 = year_end if year_end is not None else base_end
    if y0 > y1:
        y0, y1 = y1, y0
    return y0, y1


def safe_pct_change(a, b):
    if a is None or b is None or a == 0:
        return None
    return (b - a) / a * 100.0


def compute_window_cagr(series: pd.Series, y0, y1):
    s = series.loc[y0:y1].dropna()
    if len(s) < 2:
        return None
    v0 = float(s.iloc[0])
    v1 = float(s.iloc[-1])
    try:
        n = max(1, float(s.index[-1]) - float(s.index[0]))
    except Exception:
        n = max(1, len(s) - 1)
    if v0 == 0:
        return None
    return (v1 / v0) ** (1 / n) - 1


def summarize_series(series: pd.Series, y0, y1) -> dict:
    s = series.dropna()
    w = series.loc[y0:y1].dropna() if len(series.index) else pd.Series(dtype=float)
    return {
        "start": float(s.iloc[0]) if not s.empty else None,
        "end": float(s.iloc[-1]) if not s.empty else None,
        "mean_all": float(s.mean()) if not s.empty else None,
        "mean_window": float(w.mean()) if not w.empty else None,
        "min_all": float(s.min()) if not s.empty else None,
        "max_all": float(s.max()) if not s.empty else None,
        "window_start": float(w.iloc[0]) if not w.empty else None,
        "window_end": float(w.iloc[-1]) if not w.empty else None,
        "cagr_window": compute_window_cagr(series, y0, y1),
    }


def build_stats_table(kpis: list[str], baseline_df: pd.DataFrame, scenario_df: pd.DataFrame, y0, y1):
    rows = []
    for kpi in kpis:
        if kpi not in baseline_df.columns or kpi not in scenario_df.columns:
            continue
        bsum = summarize_series(baseline_df[kpi], y0, y1)
        ssum = summarize_series(scenario_df[kpi], y0, y1)
        rows.append({
            "KPI": kpi,
            "Baseline_start": bsum["start"],
            "Scenario_start": ssum["start"],
            "Baseline_end": bsum["end"],
            "Scenario_end": ssum["end"],
            "End_%change": safe_pct_change(bsum["end"], ssum["end"]),
            "Baseline_mean_all": bsum["mean_all"],
            "Scenario_mean_all": ssum["mean_all"],
            "Mean_all_%change": safe_pct_change(bsum["mean_all"], ssum["mean_all"]),
            f"Baseline_mean_{y0}_{y1}": bsum["mean_window"],
            f"Scenario_mean_{y0}_{y1}": ssum["mean_window"],
            f"Mean_{y0}_{y1}_%change": safe_pct_change(bsum["mean_window"], ssum["mean_window"]),
            f"Baseline_window_start_{y0}": bsum["window_start"],
            f"Scenario_window_start_{y0}": ssum["window_start"],
            f"Baseline_window_end_{y1}": bsum["window_end"],
            f"Scenario_window_end_{y1}": ssum["window_end"],
            f"Baseline_CAGR_{y0}_{y1}": (bsum["cagr_window"] * 100) if bsum["cagr_window"] is not None else None,
            f"Scenario_CAGR_{y0}_{y1}": (ssum["cagr_window"] * 100) if ssum["cagr_window"] is not None else None,
        })
    return pd.DataFrame(rows)


def build_baseline_value_text(variable_name: str, summary: dict, y0, y1, model_horizon: dict | None = None) -> str:
    horizon_text = ""
    if model_horizon:
        horizon_text = (
            f"Detected Model Horizon: {model_horizon.get('start')} - {model_horizon.get('end')} "
            f"(step={model_horizon.get('step')}, source={model_horizon.get('source')})\n"
        )
    return (
        f"Variable: {variable_name}\n"
        f"Window: {y0}-{y1}\n"
        f"{horizon_text}"
        f"Start: {summary.get('start')}\n"
        f"End: {summary.get('end')}\n"
        f"Mean(all): {summary.get('mean_all')}\n"
        f"Mean(window): {summary.get('mean_window')}\n"
        f"Window Start: {summary.get('window_start')}\n"
        f"Window End: {summary.get('window_end')}\n"
        f"Min(all): {summary.get('min_all')}\n"
        f"Max(all): {summary.get('max_all')}\n"
        f"CAGR(window): {summary.get('cagr_window')}\n"
    )


def build_simulation_facts(question, y0, y1, param_resolution, kpi_decisions, stats_df, model_horizon: dict | None = None):
    lines = [f"Question: {question}", f"Window: {y0}-{y1}"]
    if model_horizon:
        lines.append(
            f"Detected Model Horizon: start={model_horizon.get('start')} end={model_horizon.get('end')} "
            f"step={model_horizon.get('step')} source={model_horizon.get('source')}"
        )
    lines.append("Parameter Resolution:")
    for x in param_resolution:
        lines.append(str(x))
    lines.append("KPI Resolution:")
    for x in kpi_decisions:
        lines.append(str(x))
    lines.append("Stats:")
    lines.append(stats_df.to_string(index=False) if not stats_df.empty else "No stats")
    return "\n".join(lines)
