from __future__ import annotations
from pathlib import Path
from datetime import datetime
import re
import pandas as pd
import matplotlib.pyplot as plt
from app.config import OUTPUT_DIR


def safe_stem(text: str) -> str:
    stem = re.sub(r"[^0-9A-Za-zА-Яа-яӨөҮүЁё _-]+", "", text)[:60].strip().replace(" ", "_")
    return stem or "result"


def export_simulation_excel(question: str, baseline_df: pd.DataFrame, scenario_df: pd.DataFrame, stats_df: pd.DataFrame, meta: dict | None = None) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{safe_stem(question)}_{ts}.xlsx"
    meta_df = pd.DataFrame([meta or {}])
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        baseline_df.to_excel(writer, sheet_name="Baseline")
        scenario_df.to_excel(writer, sheet_name="Scenario")
        if stats_df is not None and not stats_df.empty:
            stats_df.to_excel(writer, sheet_name="Stats", index=False)
        meta_df.to_excel(writer, sheet_name="Meta", index=False)
    return out_path


def export_table_excel(name: str, df: pd.DataFrame) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"{safe_stem(name)}_{ts}.xlsx"
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)
    return out_path


def save_plot(baseline_df: pd.DataFrame, scenario_df: pd.DataFrame, kpis: list[str], y0: int, y1: int) -> list[Path]:
    paths: list[Path] = []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    for kpi in kpis:
        if kpi not in baseline_df.columns or kpi not in scenario_df.columns:
            continue
        plt.figure(figsize=(10, 4))
        baseline_df.loc[y0:y1, kpi].plot(label="Baseline")
        scenario_df.loc[y0:y1, kpi].plot(label="Scenario")
        plt.title(f"{kpi} ({y0}-{y1})")
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        p = OUTPUT_DIR / f"{safe_stem(kpi)}_{ts}.png"
        plt.savefig(p, dpi=150)
        plt.close()
        paths.append(p)
    return paths
