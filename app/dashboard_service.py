from __future__ import annotations

import math
import re
from typing import Any

from app.dashboard_config import CHARTS, CHART_ORDER, DISPLAY_YEAR_OFFSET, PARAMETERS
from app.engine import AssistantEngine
from app.model_utils import get_baseline_param_value, resolve_runtime_name
from app.simulation import run_baseline_and_scenario


class DashboardService:
    def __init__(self, engine: AssistantEngine):
        self.engine = engine

    def _safe_float(self, value: Any, default: float | None = None) -> float | None:
        try:
            if value is None:
                return default
            fv = float(value)
            if math.isnan(fv) or math.isinf(fv):
                return default
            return fv
        except Exception:
            return default

    def _parse_limits(self, limits_value: Any) -> tuple[float | None, float | None, float | None]:
        if limits_value is None:
            return None, None, None
        text = str(limits_value).strip()
        if not text:
            return None, None, None
        nums = re.findall(r"-?\d+(?:\.\d+)?", text)
        if not nums:
            return None, None, None
        values = [self._safe_float(x) for x in nums]
        values = [x for x in values if x is not None]
        if not values:
            return None, None, None
        min_v = values[0] if len(values) >= 1 else None
        max_v = values[1] if len(values) >= 2 else None
        step_v = values[2] if len(values) >= 3 else None
        return min_v, max_v, step_v

    def _get_constant_doc_row(self, real_name: str):
        df = self.engine.constants_df
        if "Real Name" not in df.columns:
            return None
        matches = df.loc[df["Real Name"].astype(str) == real_name]
        if matches.empty:
            return None
        return matches.iloc[0]

    def _chart_runtime_map(self) -> dict[str, str]:
        runtime_map: dict[str, str] = {}
        for chart_key in CHART_ORDER:
            chart_cfg = CHARTS[chart_key]
            record = self.engine.variable_map.get(chart_cfg["real_name"])
            if not record:
                raise ValueError(f"Chart variable not found in model: {chart_cfg['real_name']}")
            runtime_map[chart_key] = resolve_runtime_name(record)
        return runtime_map

    def _build_parameter_meta(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for key, cfg in PARAMETERS.items():
            record = self.engine.constant_map.get(cfg["real_name"])
            if not record:
                raise ValueError(f"Parameter constant not found in model: {cfg['real_name']}")

            baseline = get_baseline_param_value(self.engine.model, record)
            doc_row = self._get_constant_doc_row(cfg["real_name"])
            doc_limits = doc_row.get("Limits") if doc_row is not None and "Limits" in doc_row else None
            min_v, max_v, step_v = self._parse_limits(doc_limits)

            if min_v is None:
                min_v = cfg["fallback_min"]
            if max_v is None:
                max_v = cfg["fallback_max"]
            if step_v is None:
                step_v = cfg["fallback_step"]
            if baseline is None:
                baseline = cfg["fallback_default"]

            items.append(
                {
                    "key": key,
                    "label": cfg["label"],
                    "real_name": cfg["real_name"],
                    "runtime_name": resolve_runtime_name(record),
                    "unit": cfg["unit"],
                    "value_format": cfg["value_format"],
                    "min": min_v,
                    "max": max_v,
                    "step": step_v,
                    "default": baseline,
                    "value": baseline,
                }
            )
        return items

    def _series_to_lists(self, baseline_df, scenario_df, runtime_name: str) -> tuple[list[Any], list[float | None], list[float | None]]:
        labels: list[Any] = []
        baseline_values: list[float | None] = []
        scenario_values: list[float | None] = []

        for idx in baseline_df.index.tolist():
            label = idx
            try:
                label = float(idx)
                if label.is_integer():
                    label = int(label)
                if isinstance(label, (int, float)) and DISPLAY_YEAR_OFFSET:
                    label = label + DISPLAY_YEAR_OFFSET
            except Exception:
                pass
            labels.append(label)

        for value in baseline_df[runtime_name].tolist():
            baseline_values.append(self._safe_float(value, None))
        for value in scenario_df[runtime_name].tolist():
            scenario_values.append(self._safe_float(value, None))

        return labels, baseline_values, scenario_values

    def _build_charts_payload(self, baseline_df, scenario_df, runtime_map: dict[str, str]) -> dict[str, Any]:
        charts: dict[str, Any] = {}
        for chart_key in CHART_ORDER:
            cfg = CHARTS[chart_key]
            runtime_name = runtime_map[chart_key]
            labels, baseline_values, scenario_values = self._series_to_lists(
                baseline_df,
                scenario_df,
                runtime_name,
            )
            charts[chart_key] = {
                "label": cfg["label"],
                "real_name": cfg["real_name"],
                "canvas_id": cfg["canvas_id"],
                "unit": cfg["unit"],
                "labels": labels,
                "baseline": baseline_values,
                "scenario": scenario_values,
            }
        return charts

    def _resolve_parameter_updates(
        self,
        parameters: dict[str, Any] | None,
        params_meta: list[dict[str, Any]],
    ) -> tuple[dict[str, float], list[dict[str, Any]]]:
        params_by_key = {item["key"]: item for item in params_meta}
        params_by_runtime = {item["runtime_name"]: item for item in params_meta}
        params_by_real = {item["real_name"]: item for item in params_meta}

        updates: dict[str, float] = {}
        resolved_parameters: list[dict[str, Any]] = []

        for raw_key, raw_value in (parameters or {}).items():
            meta = params_by_key.get(raw_key) or params_by_runtime.get(raw_key) or params_by_real.get(raw_key)
            if not meta:
                continue

            value = self._safe_float(raw_value, None)
            if value is None:
                value = meta["default"]

            min_v = self._safe_float(meta["min"], None)
            max_v = self._safe_float(meta["max"], None)
            if min_v is not None:
                value = max(min_v, value)
            if max_v is not None:
                value = min(max_v, value)

            updates[meta["runtime_name"]] = float(value)
            resolved_parameters.append(
                {
                    "key": meta["key"],
                    "label": meta["label"],
                    "real_name": meta["real_name"],
                    "runtime_name": meta["runtime_name"],
                    "value": float(value),
                    "unit": meta["unit"],
                    "source": "parameter",
                }
            )

        return updates, resolved_parameters

    def _resolve_generic_overrides(
        self,
        values: dict[str, Any] | None,
        source_label: str,
    ) -> tuple[dict[str, float], list[dict[str, Any]]]:
        updates: dict[str, float] = {}
        resolved: list[dict[str, Any]] = []

        for raw_key, raw_value in (values or {}).items():
            value = self._safe_float(raw_value, None)
            if value is None:
                continue

            updates[str(raw_key)] = float(value)
            resolved.append(
                {
                    "key": str(raw_key),
                    "runtime_name": str(raw_key),
                    "value": float(value),
                    "source": source_label,
                }
            )

        return updates, resolved

    def get_dashboard_init(self) -> dict[str, Any]:
        runtime_map = self._chart_runtime_map()
        params_meta = self._build_parameter_meta()
        return_columns = [runtime_map[key] for key in CHART_ORDER]

        baseline_df, scenario_df = run_baseline_and_scenario(
            self.engine.model_path,
            return_columns,
            params={},
            variable_overrides={},
            initial_value_overrides={},
        )

        return {
            "model_horizon": self.engine.model_horizon,
            "parameters": params_meta,
            "chart_order": CHART_ORDER,
            "charts": self._build_charts_payload(baseline_df, scenario_df, runtime_map),
        }

    def run_dashboard(
        self,
        parameters: dict[str, Any] | None = None,
        variables: dict[str, Any] | None = None,
        initial_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        runtime_map = self._chart_runtime_map()
        params_meta = self._build_parameter_meta()

        parameter_updates, resolved_parameters = self._resolve_parameter_updates(parameters, params_meta)
        variable_updates, resolved_variables = self._resolve_generic_overrides(variables, "variable")
        initial_updates, resolved_initial_values = self._resolve_generic_overrides(initial_values, "initial_value")

        return_columns = [runtime_map[key] for key in CHART_ORDER]

        baseline_df, scenario_df = run_baseline_and_scenario(
            self.engine.model_path,
            return_columns,
            params=parameter_updates,
            variable_overrides=variable_updates,
            initial_value_overrides=initial_updates,
        )

        charts_payload = self._build_charts_payload(baseline_df, scenario_df, runtime_map)

        return {
            "model_horizon": self.engine.model_horizon,
            "parameters": resolved_parameters,
            "variables": resolved_variables,
            "initial_values": resolved_initial_values,
            "chart_order": CHART_ORDER,
            "charts": charts_payload,
        }