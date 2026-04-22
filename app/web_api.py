from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import OUTPUT_DIR
from app.dashboard_service import DashboardService
from app.engine import AssistantEngine

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Vensim AI Local Web App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://vensim-ai-web-vr.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=str(WEB_DIR)), name="assets")

engine = AssistantEngine()
dashboard_service = DashboardService(engine)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class DashboardRunRequest(BaseModel):
    parameters: dict[str, float | int] = Field(default_factory=dict)
    variables: dict[str, float | int] = Field(default_factory=dict)
    initial_values: dict[str, float | int] = Field(default_factory=dict)


class SimulateRequest(BaseModel):
    metric_key: str | None = None
    simulation_target: str | None = None
    simulation_year: int | None = None
    effect_percent: float | None = None
    parameters: dict[str, float | int] = Field(default_factory=dict)
    variables: dict[str, float | int] = Field(default_factory=dict)
    initial_values: dict[str, float | int] = Field(default_factory=dict)


def clean_value(v: Any):
    if v is None:
        return None
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    return v


def df_to_safe_records(df, limit=None):
    if df is None:
        return None

    out = df.copy()
    out = out.replace([float("inf"), float("-inf")], None)
    out = out.where(pd.notnull(out), None)

    if limit:
        out = out.head(limit)

    rows = out.to_dict(orient="records")
    cleaned = []
    for row in rows:
        cleaned.append({k: clean_value(v) for k, v in row.items()})
    return cleaned


def series_df_to_records(df):
    if df is None or df.empty:
        return []

    out = df.copy().reset_index()
    out = out.replace([float("inf"), float("-inf")], None)
    out = out.where(pd.notnull(out), None)

    records = []
    cols = list(out.columns)

    if len(cols) < 2:
        return records

    time_col = cols[0]

    for value_col in cols[1:]:
        metric_records = []
        for _, row in out[[time_col, value_col]].iterrows():
            metric_records.append(
                {
                    "time": clean_value(row[time_col]),
                    "value": clean_value(row[value_col]),
                }
            )

        records.append(
            {
                "metric": value_col,
                "series": metric_records,
            }
        )

    return records


def build_output_url(path_str: str | None):
    if not path_str:
        return None
    return f"/api/output-file?path={path_str}"


@app.get("/")
def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/style.css")
def style_file():
    return FileResponse(WEB_DIR / "style.css")


@app.get("/script.js")
def script_file():
    return FileResponse(WEB_DIR / "script.js")


@app.get("/api/health")
def health():
    return {"ok": True, "model_horizon": engine.model_horizon}


@app.get("/api/dashboard/init")
def dashboard_init():
    try:
        return JSONResponse(dashboard_service.get_dashboard_init())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/dashboard/run")
def dashboard_run(req: DashboardRunRequest):
    try:
        return JSONResponse(
            dashboard_service.run_dashboard(
                parameters=req.parameters,
                variables=req.variables,
                initial_values=req.initial_values,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/dashboard/config")
def dashboard_config():
    return dashboard_init()


@app.post("/api/dashboard/simulate")
def dashboard_simulate(req: SimulateRequest):
    """
    Chatbot -> dashboard sync endpoint.
    Шинэ логик:
    - parameters / variables / initial_values ирвэл түүнийг шууд scenario payload гэж үзнэ.
    - Хуучин effect_percent payload ирвэл simulation_target дээр parameter override болгож хөрвүүлнэ.
    """
    try:
        parameters = dict(req.parameters or {})
        variables = dict(req.variables or {})
        initial_values = dict(req.initial_values or {})

        if req.simulation_target and req.effect_percent is not None and not parameters:
            parameters[req.simulation_target] = req.effect_percent

        return JSONResponse(
            dashboard_service.run_dashboard(
                parameters=parameters,
                variables=variables,
                initial_values=initial_values,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/chat")
def chat(req: ChatRequest):
    try:
        result = engine.answer(
            req.message.strip(),
            session_id=req.session_id or "default_session",
        )

        excel_path = str(result["excel_path"]) if result.get("excel_path") else None
        plot_paths = [str(p) for p in result.get("plot_paths", [])]

        payload = {
            "answer": result.get("answer", ""),
            "intent": result.get("intent", {}),
            "suggestions": result.get("suggestions", []),
            "excel_path": excel_path,
            "excel_url": build_output_url(excel_path),
            "plot_paths": plot_paths,
            "plot_urls": [build_output_url(p) for p in plot_paths],
            "table_preview": df_to_safe_records(result.get("table_df"), limit=50),
            "stats": df_to_safe_records(result.get("stats_df")),
            "trials": df_to_safe_records(result.get("trials_df")),
            "baseline_series": series_df_to_records(result.get("baseline_df")),
            "scenario_series": series_df_to_records(result.get("scenario_df")),
            "param_decisions": result.get("param_decisions", []),
            "kpi_decisions": result.get("kpi_decisions", []),
            "model_horizon": result.get("model_horizon", {}),
            "dashboard_sync": result.get("dashboard_sync"),
        }
        return JSONResponse(payload)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/output-file")
def output_file(path: str = Query(...)):
    try:
        p = Path(path).resolve()
        out_dir = OUTPUT_DIR.resolve()

        if out_dir not in p.parents and p != out_dir:
            raise HTTPException(status_code=403, detail="Forbidden path")

        if not p.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(p)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
