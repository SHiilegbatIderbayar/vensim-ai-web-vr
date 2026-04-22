from __future__ import annotations

import numpy as np
import pandas as pd

from app.model_utils import load_model, get_baseline_param_value, resolve_runtime_name


def _clean_override_dict(values: dict | None) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    if not values:
        return cleaned

    for key, value in values.items():
        if key is None:
            continue
        try:
            cleaned[str(key)] = float(value)
        except Exception:
            continue
    return cleaned


def build_scenario_params(
    params: dict | None = None,
    variable_overrides: dict | None = None,
    initial_value_overrides: dict | None = None,
) -> dict[str, float]:
    """
    PySD run(params=...) руу явуулах нэгтгэсэн override dict.
    Энд:
    - parameters
    - variables
    - initial_values
    бүгд scenario-ийн override гэж үзнэ.
    """
    merged: dict[str, float] = {}
    merged.update(_clean_override_dict(params))
    merged.update(_clean_override_dict(variable_overrides))
    merged.update(_clean_override_dict(initial_value_overrides))
    return merged


def run_baseline_and_scenario(
    model_path: str,
    kpis: list[str],
    params: dict[str, float] | None = None,
    variable_overrides: dict[str, float] | None = None,
    initial_value_overrides: dict[str, float] | None = None,
):
    baseline_model = load_model(model_path)
    scenario_model = load_model(model_path)

    baseline_df = baseline_model.run(return_columns=kpis)

    scenario_params = build_scenario_params(
        params=params,
        variable_overrides=variable_overrides,
        initial_value_overrides=initial_value_overrides,
    )

    if scenario_params:
        scenario_df = scenario_model.run(params=scenario_params, return_columns=kpis)
    else:
        scenario_df = baseline_df.copy()

    return baseline_df, scenario_df


def build_param_updates(
    model_path: str,
    model_records: dict[str, dict],
    param_decisions: list[dict],
    param_changes: list[dict],
) -> tuple[dict[str, float], list[dict]]:
    model = load_model(model_path)
    updates: dict[str, float] = {}
    resolution: list[dict] = []
    phrase_to_change = {x["param_phrase"]: x for x in param_changes}

    for decision in param_decisions:
        phrase = decision["phrase"]
        chosen_real = decision.get("selected")
        if not chosen_real:
            resolution.append(
                {
                    "phrase": phrase,
                    "status": decision["status"],
                    "runtime_name": None,
                    "new_value": None,
                }
            )
            continue

        record = model_records.get(chosen_real)
        if not record:
            resolution.append(
                {
                    "phrase": phrase,
                    "status": "not_found",
                    "runtime_name": None,
                    "new_value": None,
                }
            )
            continue

        runtime_name = resolve_runtime_name(record)
        change = phrase_to_change.get(phrase)
        if not change:
            continue

        base_val = get_baseline_param_value(model, record)
        new_val = change["value"]

        if change["operation"] == "delta":
            if base_val is None:
                resolution.append(
                    {
                        "phrase": phrase,
                        "status": "baseline_unknown_for_delta",
                        "runtime_name": runtime_name,
                        "baseline_value": None,
                        "new_value": None,
                    }
                )
                continue
            new_val = base_val + change["value"]

        updates[runtime_name] = float(new_val)
        resolution.append(
            {
                "phrase": phrase,
                "status": "ok",
                "runtime_name": runtime_name,
                "real_name": chosen_real,
                "baseline_value": base_val,
                "new_value": float(new_val),
                "operation": change["operation"],
                "raw_value": change["value"],
            }
        )

    return updates, resolution


def goal_seek_parameter(
    model_path: str,
    parameter_runtime_name: str,
    baseline_param_value: float | None,
    target_kpi_runtime_name: str,
    target_direction: str,
    target_percent_change: float | None,
    search_min: float | None,
    search_max: float | None,
    steps: int = 21,
):
    if baseline_param_value is None:
        raise ValueError("Goal-seek хийхэд baseline parameter value олдсонгүй.")

    min_val = search_min if search_min is not None else baseline_param_value * 0.5
    max_val = search_max if search_max is not None else baseline_param_value * 1.5
    if min_val == max_val:
        max_val = min_val + 1.0

    base_model = load_model(model_path)
    baseline_df = base_model.run(return_columns=[target_kpi_runtime_name])
    baseline_last = float(baseline_df[target_kpi_runtime_name].dropna().iloc[-1])

    target_value = baseline_last
    if target_percent_change is not None:
        if target_direction == "decrease":
            target_value = baseline_last * (1 - target_percent_change)
        elif target_direction == "increase":
            target_value = baseline_last * (1 + target_percent_change)

    records = []
    best = None
    grid = np.linspace(min_val, max_val, steps)

    for v in grid:
        m = load_model(model_path)
        df = m.run(params={parameter_runtime_name: float(v)}, return_columns=[target_kpi_runtime_name])
        last_val = float(df[target_kpi_runtime_name].dropna().iloc[-1])
        error = abs(last_val - target_value)
        row = {
            "trial_value": float(v),
            "result_last": last_val,
            "target_value": target_value,
            "abs_error": error,
        }
        records.append(row)
        if best is None or error < best["abs_error"]:
            best = row

    return {
        "baseline_last": baseline_last,
        "target_value": target_value,
        "best": best,
        "trials": pd.DataFrame(records),
    }