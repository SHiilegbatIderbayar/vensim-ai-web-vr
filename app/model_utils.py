from __future__ import annotations
import math
from typing import Any
import pandas as pd
import pysd
from app.config import MODEL_PATH, FALLBACK_WINDOW_START, FALLBACK_WINDOW_END


def load_model(model_path: str | None = None):
    return pysd.read_vensim(model_path or MODEL_PATH)


def load_model_doc(model) -> pd.DataFrame:
    doc_df = model.doc.copy()
    if doc_df.empty:
        raise ValueError("model.doc хоосон байна.")
    return doc_df


def split_doc(doc_df: pd.DataFrame):
    type_col = doc_df["Type"].astype(str).str.lower()
    constants_df = doc_df.loc[type_col == "constant"].copy()
    variables_df = doc_df.loc[type_col != "constant"].copy()
    return constants_df, variables_df


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def simplify_doc(df: pd.DataFrame) -> list[dict]:
    cols = [c for c in ["Real Name", "Py Name", "Type", "Units", "Comment", "Equation"] if c in df.columns]
    out = []
    for _, row in df[cols].iterrows():
        out.append({
            "real_name": _safe_str(row.get("Real Name")),
            "py_name": _safe_str(row.get("Py Name")) or None,
            "type": _safe_str(row.get("Type")),
            "units": _safe_str(row.get("Units")) or None,
            "comment": _safe_str(row.get("Comment")) or None,
            "equation": _safe_str(row.get("Equation")) or None,
        })
    return out


def find_record_by_real_name(records: list[dict], real_name: str) -> dict | None:
    for r in records:
        if r.get("real_name") == real_name:
            return r
    return None


def build_model_catalog_text(constants: list[dict], variables: list[dict], max_items: int = 300) -> str:
    lines = ["CONSTANTS:"]
    for r in constants[:max_items]:
        lines.append(
            f"- real_name={r['real_name']} | py_name={r.get('py_name')} | units={r.get('units')} | comment={r.get('comment')}"
        )
    lines.append("VARIABLES:")
    for r in variables[:max_items]:
        lines.append(
            f"- real_name={r['real_name']} | py_name={r.get('py_name')} | units={r.get('units')} | comment={r.get('comment')}"
        )
    return "\n".join(lines)


def resolve_runtime_name(record: dict) -> str:
    return record.get("real_name") or record.get("py_name") or ""


def _safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _normalize_time_value(v):
    try:
        fv = float(v)
        if fv.is_integer():
            return int(fv)
        return fv
    except Exception:
        return v


def detect_model_time_horizon(model) -> dict:
    """
    Try multiple strategies to detect the model time horizon.
    Returns a dict with start/end/step/index_type/source.
    """
    candidates = {
        "start": ["INITIAL TIME", "initial_time", "initial_time()"],
        "end": ["FINAL TIME", "final_time", "final_time()"],
        "step": ["TIME STEP", "time_step", "time_step()"],
    }
    values = {"start": None, "end": None, "step": None}

    for key, names in candidates.items():
        for name in names:
            try:
                if hasattr(model, "components") and hasattr(model.components, name):
                    attr = getattr(model.components, name)
                    values[key] = _safe_float(attr() if callable(attr) else attr, values[key])
                    if values[key] is not None:
                        break
            except Exception:
                pass
            try:
                if hasattr(model, name):
                    attr = getattr(model, name)
                    values[key] = _safe_float(attr() if callable(attr) else attr, values[key])
                    if values[key] is not None:
                        break
            except Exception:
                pass

    if values["start"] is not None and values["end"] is not None:
        start = _normalize_time_value(values["start"])
        end = _normalize_time_value(values["end"])
        step = _normalize_time_value(values["step"] if values["step"] is not None else 1)
        if start > end:
            start, end = end, start
        return {
            "start": start,
            "end": end,
            "step": step,
            "index_type": "numeric",
            "source": "model_components",
        }

    try:
        df = model.run()
        idx = df.index.tolist()
        if idx:
            start = _normalize_time_value(idx[0])
            end = _normalize_time_value(idx[-1])
            step = None
            if len(idx) > 1:
                try:
                    step = _normalize_time_value(float(idx[1]) - float(idx[0]))
                except Exception:
                    step = None
            if start > end:
                start, end = end, start
            return {
                "start": start,
                "end": end,
                "step": step,
                "index_type": type(idx[0]).__name__,
                "source": "baseline_run_index",
            }
    except Exception:
        pass

    start = _normalize_time_value(FALLBACK_WINDOW_START)
    end = _normalize_time_value(FALLBACK_WINDOW_END)
    if start > end:
        start, end = end, start
    return {
        "start": start,
        "end": end,
        "step": 1,
        "index_type": "fallback",
        "source": "env_fallback",
    }


def get_baseline_param_value(model, record: dict):
    candidates = [record.get("real_name"), record.get("py_name")]
    for c in candidates:
        if not c:
            continue
        try:
            if hasattr(model, "get_series_data"):
                val = model.get_series_data(c)
                if val is not None:
                    return float(val)
        except Exception:
            pass
        try:
            if hasattr(model, "components") and hasattr(model.components, c):
                v = getattr(model.components, c)()
                return float(v)
        except Exception:
            pass
        try:
            res = model.run(return_columns=[c])
            if c in res.columns:
                return float(res[c].dropna().iloc[0])
        except Exception:
            pass
    return None


def get_variable_series(model_path: str, var_name: str) -> pd.Series:
    model = load_model(model_path)
    df = model.run(return_columns=[var_name])
    return df[var_name]
