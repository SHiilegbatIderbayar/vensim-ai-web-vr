from __future__ import annotations
import re
import pandas as pd

from app.config import MODEL_PATH
from app.intents import extract_intent
from app.model_utils import (
    load_model,
    load_model_doc,
    split_doc,
    simplify_doc,
    build_model_catalog_text,
    resolve_runtime_name,
    get_baseline_param_value,
    detect_model_time_horizon,
)
from app.matching import match_phrases_to_entities, rank_entities_by_keyword
from app.simulation import (
    run_baseline_and_scenario,
    build_param_updates,
    goal_seek_parameter,
)
from app.analysis import (
    resolve_year_window,
    summarize_series,
    build_baseline_value_text,
    build_stats_table,
    build_simulation_facts,
)
from app.answers import (
    explain_simulation,
    explain_from_model_context,
    explain_methodology,
    answer_real_world,
    explain_goal_seek,
)
from app.exporter import (
    export_simulation_excel,
    export_table_excel,
    save_plot,
)


class AssistantEngine:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path or MODEL_PATH
        self.model = load_model(self.model_path)
        self.doc_df = load_model_doc(self.model)

        self.constants_df, self.variables_df = split_doc(self.doc_df)
        self.constant_records = simplify_doc(self.constants_df)
        self.variable_records = simplify_doc(self.variables_df)

        self.constant_map = {r["real_name"]: r for r in self.constant_records}
        self.variable_map = {r["real_name"]: r for r in self.variable_records}

        self.catalog_text = build_model_catalog_text(
            self.constant_records,
            self.variable_records,
        )
        self.model_horizon = detect_model_time_horizon(self.model)

        self.sessions: dict[str, dict] = {}

    # -----------------------------------
    # memory
    # -----------------------------------
    def _get_session(self, session_id: str) -> dict:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "last_intent": None,
                "last_run": None,
                "pending_simulation": None,
                "last_answer": None,
                "last_dashboard_sync": None,
                "last_kpi_real_name": None,
            }
        return self.sessions[session_id]

    def _shorten(self, text: str, limit: int = 260) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def _append_history(self, mem: dict, role: str, text: str):
        mem["history"].append({"role": role, "text": self._shorten(text, 500)})
        mem["history"] = mem["history"][-8:]

    def _history_context(self, mem: dict) -> str:
        history = mem.get("history", [])
        if not history:
            return ""
        lines = ["Conversation history:"]
        for item in history[-4:]:
            lines.append(f"- {item['role']}: {item['text']}")
        return "\n".join(lines)

    def _base_result(self, answer: str = "", intent: dict | None = None) -> dict:
        return {
            "answer": answer,
            "intent": intent or {},
            "suggestions": [],
            "table_df": None,
            "stats_df": None,
            "trials_df": None,
            "baseline_df": None,
            "scenario_df": None,
            "excel_path": None,
            "plot_paths": [],
            "param_decisions": [],
            "kpi_decisions": [],
            "model_horizon": self.model_horizon,
            "dashboard_sync": None,
            "_memory_updates": {},
        }

    def _choose_from_decision(self, decision: dict, confirm_selector=None, label: str = "parameter"):
        if decision.get("status") == "matched":
            return decision.get("selected")
        if decision.get("status") == "needs_confirmation" and confirm_selector:
            return confirm_selector(decision, label)
        return None

    def get_model_horizon_text(self) -> str:
        h = self.model_horizon
        return (
            f"Detected model horizon: "
            f"{h.get('start')} - {h.get('end')} "
            f"(step={h.get('step')}, source={h.get('source')})"
        )

    # -----------------------------------
    # year / model-time helpers
    # -----------------------------------
    def _extract_absolute_years(self, text: str) -> list[int]:
        if not text:
            return []

        years = []
        for m in re.findall(r"\b(19\d{2}|20\d{2}|21\d{2})\b", text):
            try:
                years.append(int(m))
            except Exception:
                pass
        return years

    def _model_looks_relative_time(self) -> bool:
        h = self.model_horizon or {}
        start = h.get("start")
        end = h.get("end")
        step = h.get("step")

        if start is None or end is None:
            return False

        try:
            start = float(start)
            end = float(end)
        except Exception:
            return False

        if 0 <= start <= 5 and end <= 200:
            return True

        if step in [1, 1.0, "1", "1.0"] and start >= 0 and end <= 200:
            return True

        return False

    def _build_relative_time_warning(self, question: str) -> str | None:
        abs_years = self._extract_absolute_years(question)
        if not abs_years:
            return None

        if not self._model_looks_relative_time():
            return None

        h = self.model_horizon or {}
        start = h.get("start")
        end = h.get("end")
        step = h.get("step")

        return (
            "Таны асуултад absolute year (жишээ нь 2027) орсон байна. "
            f"Гэхдээ энэ model-ийн хугацаа {start}–{end}, step={step} тул "
            "absolute year-ийг автоматаар хөрвүүлж simulation хийхгүй. "
            "Model бүрийн суурь он өөр байж болдог. "
            "Иймээс асуултаа model-ийн өөрийн хугацаагаар дахин өгнө үү. "
            f"Жишээ нь {start}–{end} доторх хугацаагаар асууна уу."
        )

    def _with_year_guard(self, question: str, result: dict) -> dict | None:
        warning = self._build_relative_time_warning(question)
        if warning:
            result["answer"] = warning
            return result
        return None

    # -----------------------------------
    # response-style rewrite
    # -----------------------------------
    def _detect_response_style_request(self, question: str) -> str | None:
        q = (question or "").strip().lower()

        if not q:
            return None

        if any(x in q for x in ["хураангуй", "товч", "summarize", "summary"]):
            return "summary"

        if any(x in q for x in ["дэлгэрэнгүй", "дэлгэрүүл", "detailed", "expand"]):
            return "detailed"

        if any(x in q for x in ["зөвхөн тоо", "тоон утга", "numeric", "numbers only"]):
            return "numeric_only"

        if any(x in q for x in ["тайлбартай", "илүү тайлбар", "interpret", "explain more"]):
            return "explained"

        if any(x in q for x in ["бодлогын", "policy", "шийдвэр", "recommendation"]):
            return "policy"

        return None

    def _rewrite_last_answer(self, question: str, session_id: str, style: str):
        mem = self._get_session(session_id)
        last_answer = (mem.get("last_answer") or "").strip()
        last_intent = mem.get("last_intent") or {}
        last_dashboard_sync = mem.get("last_dashboard_sync")

        result = self._base_result(intent={"intent_type": "response_style_rewrite", "style": style})

        if not last_answer:
            result["answer"] = "Өмнөх хариулт олдсонгүй. Эхлээд асуултаа асуугаад, дараа нь хариултын хэлбэрээ сонгоно уу."
            return result

        style_instruction_map = {
            "summary": (
                "Rewrite the previous answer as a concise Mongolian summary. "
                "Keep only the main conclusion and 2-3 supporting points."
            ),
            "detailed": (
                "Rewrite the previous answer in more detailed Mongolian. "
                "Add context, reasoning, and clearer interpretation without inventing facts."
            ),
            "numeric_only": (
                "Rewrite the previous answer in Mongolian focusing mainly on numeric values, metrics, comparisons, and final figures. "
                "Keep explanation minimal."
            ),
            "explained": (
                "Rewrite the previous answer in clear Mongolian with interpretation for a normal reader. "
                "Explain what the result means in practical terms."
            ),
            "policy": (
                "Rewrite the previous answer in Mongolian from a policy and decision-making perspective. "
                "Include implications and short recommendations when appropriate."
            ),
        }

        context = (
            f"New user request: {question}\n"
            f"Previous detected intent: {last_intent}\n"
            f"Previous answer:\n{last_answer}\n\n"
            f"Instruction:\n{style_instruction_map.get(style, style_instruction_map['summary'])}\n"
        )

        rewritten = explain_from_model_context(question, context)
        result["answer"] = rewritten
        result["dashboard_sync"] = last_dashboard_sync
        return result

    # -----------------------------------
    # intent helpers
    # -----------------------------------
    def _is_general_system_dynamics_question(self, question: str) -> bool:
        q = (question or "").strip().lower()
        keywords = [
            "system dynamic",
            "system dynamics",
            "систем динамик",
            "loop гэж юу",
            "feedback loop",
            "causal loop",
            "cld",
        ]
        return any(k in q for k in keywords)

    def _should_use_history_for_intent(self, question: str) -> bool:
        q = (question or "").strip()
        if not q:
            return False

        short_followup = len(q) <= 80
        followup_words = ["тэгвэл", "мөн", "бас", "харин", "тэр", "энэ", "ингэхэд", "үргэлжлүүлээд"]
        return short_followup or any(w in q.lower() for w in followup_words)

    def _normalize_phrase_for_kpi_match(self, text: str) -> str:
        q = (text or "").strip()

        replacements = [
            r"\bгаргаж өг(өөч)?\b",
            r"\bгарга\b",
            r"\bүзүүл\b",
            r"\bүзүүлээч\b",
            r"\bтооцоол\b",
            r"\bтооцоолж өг\b",
            r"\bчадах уу\b",
            r"\bболох уу\b",
            r"\bуу\b",
            r"\bвэ\b",
            r"\bхэд вэ\b",
            r"\bтайлбарла\b",
            r"\bтайлбарлаж өг\b",
            r"\bутгыг\b",
            r"\bутга\b",
            r"\bдундажыг\b",
            r"\bдундажийг\b",
            r"\bдундаж\b",
            r"\bөсөлтийн\b",
            r"\bөсөлт\b",
            r"\bхэмжээг\b",
            r"\bхэмжээ\b",
            r"\bгарч байна\b",
            r"\bөгч чадах уу\b",
        ]

        cleaned = q
        for pattern in replacements:
            cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"[?.,!]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -–—")

        if cleaned.endswith("ын"):
            cleaned = cleaned[:-2].strip()
        if cleaned.endswith("ийн"):
            cleaned = cleaned[:-3].strip()

        return cleaned.strip()

    def _rule_based_intent_override(self, question: str) -> dict | None:
        q = (question or "").strip()
        ql = q.lower()

        if not q:
            return None

        if any(x in ql for x in ["simulation", "сценар", "өөрчлөвөл", "өөрчлөлт оруул", "нөлөөлөл", "нөлөө үзүүлэх"]):
            return None

        avg_markers = [
            "дундаж",
            "дундажыг",
            "дундажийг",
            "өсөлтийн дундаж",
            "average",
            "mean",
        ]
        value_markers = [
            "утга",
            "утгыг",
            "хэд вэ",
            "гаргаж өг",
            "гарга",
            "үзүүл",
            "show",
            "value",
        ]
        explain_markers = [
            "тайлбарла",
            "тайлбарлаж өг",
            "юу гэсэн үг",
            "impact",
            "нөлөө",
        ]

        if any(m in ql for m in avg_markers):
            phrase = self._normalize_phrase_for_kpi_match(q)
            return {
                "intent_type": "query_average_value",
                "focus_variable_phrase": phrase or q,
                "requested_kpis": [phrase or q],
                "parameter_changes": [],
                "keyword": None,
                "year_start": None,
                "year_end": None,
                "need_equation": False,
                "explanation_language": "mn",
                "goal_seek": None,
            }

        if any(m in ql for m in explain_markers) and not self._is_general_system_dynamics_question(q):
            phrase = self._normalize_phrase_for_kpi_match(q)
            return {
                "intent_type": "explain_variable",
                "focus_variable_phrase": phrase or q,
                "requested_kpis": [phrase or q],
                "parameter_changes": [],
                "keyword": None,
                "year_start": None,
                "year_end": None,
                "need_equation": False,
                "explanation_language": "mn",
                "goal_seek": None,
            }

        if any(m in ql for m in value_markers):
            phrase = self._normalize_phrase_for_kpi_match(q)
            return {
                "intent_type": "query_current_value",
                "focus_variable_phrase": phrase or q,
                "requested_kpis": [phrase or q],
                "parameter_changes": [],
                "keyword": None,
                "year_start": None,
                "year_end": None,
                "need_equation": False,
                "explanation_language": "mn",
                "goal_seek": None,
            }

        return None

    def _apply_followup_memory(self, question: str, intent: dict, mem: dict) -> dict:
        q = (question or "").strip().lower()
        pending = mem.get("pending_simulation")
        last_run = mem.get("last_run")

        has_params = bool(intent.get("parameter_changes"))
        has_kpis = bool(intent.get("requested_kpis"))
        short_followup = len(question.strip()) <= 80
        followup_words = any(
            w in q for w in ["тэгвэл", "мөн", "бас", "харин", "тэр", "энэ", "үүнийг", "ингэвэл"]
        )

        # pending simulation байгаа үед user зөвхөн KPI нэр өгвөл simulation-аа үргэлжлүүлнэ
        if pending and not has_params and short_followup:
            intent["intent_type"] = "run_simulation"
            intent["parameter_changes"] = pending.get("parameter_changes", [])
            intent["year_start"] = intent.get("year_start") or pending.get("year_start")
            intent["year_end"] = intent.get("year_end") or pending.get("year_end")

            if has_kpis:
                intent["requested_kpis"] = intent.get("requested_kpis", [])
            else:
                intent["requested_kpis"] = [question]

            return intent

        # өмнөх simulation-ийн дараах follow-up
        if last_run and not has_params and (short_followup or followup_words):
            intent["intent_type"] = "run_simulation"
            intent["parameter_changes"] = last_run.get("parameter_changes", [])
            intent["year_start"] = intent.get("year_start") or last_run.get("year_start")
            intent["year_end"] = intent.get("year_end") or last_run.get("year_end")

            if has_kpis:
                intent["requested_kpis"] = intent.get("requested_kpis", [])
            elif question.strip():
                intent["requested_kpis"] = [question]
            else:
                intent["requested_kpis"] = last_run.get("requested_kpis", [])

            return intent

        # KPI-гаа солиод simulation үргэлжлүүлэх
        if pending and has_kpis and not has_params:
            intent["intent_type"] = "run_simulation"
            intent["parameter_changes"] = pending.get("parameter_changes", [])
            intent["year_start"] = intent.get("year_start") or pending.get("year_start")
            intent["year_end"] = intent.get("year_end") or pending.get("year_end")
            return intent

        if intent.get("intent_type") == "run_simulation" and not has_params and has_kpis and last_run:
            intent["parameter_changes"] = last_run.get("parameter_changes", [])
            intent["year_start"] = intent.get("year_start") or last_run.get("year_start")
            intent["year_end"] = intent.get("year_end") or last_run.get("year_end")
            return intent

        return intent

    def _update_memory(self, session_id: str, question: str, result: dict):
        mem = self._get_session(session_id)
        self._append_history(mem, "user", question)
        self._append_history(mem, "assistant", result.get("answer", ""))

        mem["last_intent"] = result.get("intent", {})
        mem["last_answer"] = result.get("answer", "")

        updates = result.get("_memory_updates", {})
        for k, v in updates.items():
            mem[k] = v

        if result.get("dashboard_sync") is not None:
            mem["last_dashboard_sync"] = result.get("dashboard_sync")

        kpi_decisions = result.get("kpi_decisions") or []
        selected_names = [x.get("selected") for x in kpi_decisions if x.get("selected")]
        if selected_names:
            mem["last_kpi_real_name"] = selected_names[0]

        if result.get("intent", {}).get("intent_type") == "run_simulation":
            mem["last_run"] = {
                "parameter_changes": result.get("intent", {}).get("parameter_changes", []),
                "year_start": result.get("intent", {}).get("year_start"),
                "year_end": result.get("intent", {}).get("year_end"),
                "requested_kpis": result.get("intent", {}).get("requested_kpis", []),
            }

    def _make_kpi_suggestions(self, items: list[dict]) -> list[dict]:
        out = []
        for item in items[:8]:
            out.append({
                "label": item.get("real_name", ""),
                "prompt": item.get("real_name", ""),
            })
        return out

    
    def _build_dashboard_sync_from_simulation(self, param_resolution: list[dict], kpi_decisions: list[dict], y0, y1):
        """
        Chatbot-аас гарсан simulation өөрчлөлтийг dashboard-д шууд тусгах payload.
        Шинэ бүтэц:
        {
            "parameters": {...},
            "variables": {...},
            "initial_values": {...},
            "focus_metric": "...",
            "window": {"start": y0, "end": y1}
        }
        """
        if not param_resolution:
            return None

        sync_payload = {
            "parameters": {},
            "variables": {},
            "initial_values": {},
            "focus_metric": None,
            "window": {"start": y0, "end": y1},
        }

        selected_kpi_real = None
        for item in kpi_decisions or []:
            if item.get("selected"):
                selected_kpi_real = item.get("selected")
                break

        if selected_kpi_real:
            sync_payload["focus_metric"] = selected_kpi_real

        try:
            from app.dashboard_config import PARAMETERS
            dashboard_param_real_to_key = {
                cfg["real_name"]: key for key, cfg in PARAMETERS.items()
            }
        except Exception:
            dashboard_param_real_to_key = {}

        for item in param_resolution:
            if item.get("status") != "ok":
                continue

            real_name = item.get("real_name")
            runtime_name = item.get("runtime_name")
            new_value = item.get("new_value")

            if new_value is None:
                continue

            if real_name in dashboard_param_real_to_key:
                sync_payload["parameters"][dashboard_param_real_to_key[real_name]] = float(new_value)
            elif real_name and str(real_name).strip().startswith("Анхны"):
                sync_payload["initial_values"][real_name] = float(new_value)
            elif runtime_name:
                sync_payload["variables"][runtime_name] = float(new_value)
            elif real_name:
                sync_payload["variables"][real_name] = float(new_value)

        if not (
            sync_payload["parameters"]
            or sync_payload["variables"]
            or sync_payload["initial_values"]
        ):
            return None

        return sync_payload

    # -----------------------------------
    # list / explain
    # -----------------------------------
    def list_all_parameters(self):
        rows = []
        for r in self.constant_records:
            baseline_value = get_baseline_param_value(self.model, r)
            rows.append({
                "real_name": r.get("real_name", ""),
                "initial_value": baseline_value,
            })

        out = pd.DataFrame(rows)
        path = export_table_excel("all_parameters", out)
        return out, path

    def list_all_kpis(self):
        rows = [{"real_name": r.get("real_name", "")} for r in self.variable_records]
        out = pd.DataFrame(rows)
        path = export_table_excel("all_kpis", out)
        return out, path

    def list_by_keyword(self, keyword: str, mode: str):
        records = self.constant_records if mode == "parameter" else self.variable_records
        items = rank_entities_by_keyword(keyword, records, entity_label=mode, top_n=10)

        if mode == "parameter":
            rows = []
            for item in items:
                real_name = item.get("real_name", "")
                record = self.constant_map.get(real_name)
                baseline_value = get_baseline_param_value(self.model, record) if record else None
                rows.append({
                    "real_name": real_name,
                    "initial_value": baseline_value,
                })
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame([{"real_name": item.get("real_name", "")} for item in items])

        path = export_table_excel(f"{mode}_{keyword}", df)
        return df, path

    def _resolve_single_variable(self, phrase: str, confirm_selector=None):
        decisions = match_phrases_to_entities([phrase], self.variable_records, "kpi")
        if not decisions:
            return None, decisions

        chosen_real = self._choose_from_decision(decisions[0], confirm_selector, label="kpi")
        if not chosen_real:
            return None, decisions

        record = self.variable_map[chosen_real]
        runtime = resolve_runtime_name(record)
        return {
            "real_name": chosen_real,
            "runtime_name": runtime,
            "record": record,
        }, decisions

    def query_value(
        self,
        question: str,
        phrase: str,
        average: bool = False,
        year_start=None,
        year_end=None,
        confirm_selector=None,
    ):
        result = self._base_result()

        guarded = self._with_year_guard(question, result)
        if guarded:
            return guarded

        resolved, decisions = self._resolve_single_variable(phrase, confirm_selector)
        if not resolved:
            result["answer"] = "Холбогдох variable/KPI тодорхой шийдэгдсэнгүй."
            result["kpi_decisions"] = decisions
            return result

        y0, y1 = resolve_year_window(year_start, year_end, self.model_horizon)
        baseline_df, _ = run_baseline_and_scenario(self.model_path, [resolved["runtime_name"]], {})

        series = baseline_df[resolved["runtime_name"]]
        summary = summarize_series(series, y0, y1)

        context = build_baseline_value_text(
            resolved["real_name"],
            summary,
            y0,
            y1,
            self.model_horizon,
        )

        record = resolved["record"]
        context += (
            f"\nUnits: {record.get('units')}\n"
            f"Comment: {record.get('comment')}\n"
            f"Equation: {record.get('equation')}\n"
        )

        if average:
            context += (
                "\nUser asks specifically for an average/mean interpretation. "
                "Prioritize mean_window and mean_all in the answer.\n"
            )

        answer = explain_from_model_context(question, context)

        result["answer"] = answer
        result["kpi_decisions"] = decisions
        result["baseline_df"] = baseline_df
        return result

    def explain_variable(
        self,
        question: str,
        phrase: str,
        confirm_selector=None,
        year_start=None,
        year_end=None,
    ):
        result = self._base_result()

        guarded = self._with_year_guard(question, result)
        if guarded:
            return guarded

        resolved, decisions = self._resolve_single_variable(phrase, confirm_selector)
        if not resolved:
            result["answer"] = "Холбогдох variable/KPI тодорхой шийдэгдсэнгүй."
            result["kpi_decisions"] = decisions
            return result

        record = resolved["record"]
        baseline_df, _ = run_baseline_and_scenario(self.model_path, [resolved["runtime_name"]], {})
        y0, y1 = resolve_year_window(year_start, year_end, self.model_horizon)
        summary = summarize_series(baseline_df[resolved["runtime_name"]], y0, y1)

        context = (
            f"Variable: {resolved['real_name']}\n"
            f"Units: {record.get('units')}\n"
            f"Comment: {record.get('comment')}\n"
            f"Equation: {record.get('equation')}\n"
            f"Detected Model Horizon: {self.model_horizon}\n"
            f"Analysis Window: {y0}-{y1}\n"
            f"Baseline Summary: {summary}\n"
        )

        answer = explain_from_model_context(question, context)

        result["answer"] = answer
        result["kpi_decisions"] = decisions
        result["baseline_df"] = baseline_df
        return result

    def explain_impact(
        self,
        question: str,
        phrase: str,
        confirm_selector=None,
        year_start=None,
        year_end=None,
    ):
        return self.explain_variable(
            question,
            phrase,
            confirm_selector,
            year_start=year_start,
            year_end=year_end,
        )

    # -----------------------------------
    # simulation
    # -----------------------------------
    def run_simulation(self, question: str, intent: dict, confirm_selector=None):
        result = self._base_result(intent=intent)

        guarded = self._with_year_guard(question, result)
        if guarded:
            return guarded

        param_changes = intent.get("parameter_changes", [])
        param_phrases = [x["param_phrase"] for x in param_changes]
        kpi_phrases = intent.get("requested_kpis", [])

        param_decisions = match_phrases_to_entities(param_phrases, self.constant_records, "parameter")
        kpi_decisions = match_phrases_to_entities(kpi_phrases, self.variable_records, "kpi") if kpi_phrases else []

        for d in param_decisions:
            if d.get("status") == "needs_confirmation" and confirm_selector:
                chosen = confirm_selector(d, "parameter")
                if chosen:
                    d["selected"] = chosen

        for d in kpi_decisions:
            if d.get("status") == "needs_confirmation" and confirm_selector:
                chosen = confirm_selector(d, "kpi")
                if chosen:
                    d["selected"] = chosen

        final_kpis = []
        for d in kpi_decisions:
            chosen = d.get("selected")
            if chosen and chosen in self.variable_map:
                final_kpis.append(resolve_runtime_name(self.variable_map[chosen]))

        result["param_decisions"] = param_decisions
        result["kpi_decisions"] = kpi_decisions

        if not final_kpis:
            suggested_items = rank_entities_by_keyword(question, self.variable_records, entity_label="kpi", top_n=8)
            suggested_df = pd.DataFrame([{"real_name": item.get("real_name", "")} for item in suggested_items])

            result["answer"] = (
                "Simulation хийх KPI тодорхой болоогүй байна. "
                "Доорх жагсаалтаас шинжлэх үзүүлэлтээ сонгоно уу. "
                "Жишээ нь: Хүн ам, ААН, Ажлын байр."
            )
            result["table_df"] = suggested_df
            result["suggestions"] = self._make_kpi_suggestions(suggested_items)
            result["_memory_updates"] = {
                "pending_simulation": {
                    "parameter_changes": param_changes,
                    "year_start": intent.get("year_start"),
                    "year_end": intent.get("year_end"),
                    "original_question": question,
                }
            }
            return result

        param_updates, param_resolution = build_param_updates(
            self.model_path,
            self.constant_map,
            param_decisions,
            param_changes,
        )

        y0, y1 = resolve_year_window(
            intent.get("year_start"),
            intent.get("year_end"),
            self.model_horizon,
        )

        baseline_df, scenario_df = run_baseline_and_scenario(
            self.model_path,
            final_kpis,
            param_updates,
        )

        stats_df = build_stats_table(final_kpis, baseline_df, scenario_df, y0, y1)
        facts = build_simulation_facts(
            question,
            y0,
            y1,
            param_resolution,
            kpi_decisions,
            stats_df,
            self.model_horizon,
        )

        answer = explain_simulation(question, facts)

        excel_path = export_simulation_excel(
            question,
            baseline_df,
            scenario_df,
            stats_df,
            {
                "question": question,
                "window": f"{y0}-{y1}",
                "detected_model_horizon": str(self.model_horizon),
                "param_updates": str(param_updates),
                "kpis": str(final_kpis),
            },
        )

        plot_paths = save_plot(baseline_df, scenario_df, final_kpis, y0, y1)

        result["answer"] = answer
        result["baseline_df"] = baseline_df
        result["scenario_df"] = scenario_df
        result["stats_df"] = stats_df
        result["excel_path"] = excel_path
        result["plot_paths"] = plot_paths
        result["_memory_updates"] = {
            "pending_simulation": None
        }
        result["dashboard_sync"] = self._build_dashboard_sync_from_simulation(
            param_resolution,
            kpi_decisions,
            y0,
            y1,
        )
        return result

    def goal_seek(self, question: str, intent: dict, confirm_selector=None):
        result_payload = self._base_result(intent=intent)

        guarded = self._with_year_guard(question, result_payload)
        if guarded:
            return guarded

        gs = intent.get("goal_seek") or {}
        param_phrase = gs.get("candidate_parameter_phrase") or ""
        kpi_phrase = gs.get("target_kpi_phrase") or ""

        p_decisions = match_phrases_to_entities([param_phrase], self.constant_records, "parameter")
        k_decisions = match_phrases_to_entities([kpi_phrase], self.variable_records, "kpi")

        if p_decisions and p_decisions[0].get("status") == "needs_confirmation" and confirm_selector:
            ch = confirm_selector(p_decisions[0], "parameter")
            if ch:
                p_decisions[0]["selected"] = ch

        if k_decisions and k_decisions[0].get("status") == "needs_confirmation" and confirm_selector:
            ch = confirm_selector(k_decisions[0], "kpi")
            if ch:
                k_decisions[0]["selected"] = ch

        result_payload["param_decisions"] = p_decisions
        result_payload["kpi_decisions"] = k_decisions

        if (
            not p_decisions
            or not p_decisions[0].get("selected")
            or not k_decisions
            or not k_decisions[0].get("selected")
        ):
            result_payload["answer"] = "Goal-seek хийх parameter эсвэл KPI шийдэгдсэнгүй."
            return result_payload

        p_record = self.constant_map[p_decisions[0]["selected"]]
        k_record = self.variable_map[k_decisions[0]["selected"]]

        p_runtime = resolve_runtime_name(p_record)
        k_runtime = resolve_runtime_name(k_record)

        base_val = get_baseline_param_value(self.model, p_record)

        gs_result = goal_seek_parameter(
            self.model_path,
            p_runtime,
            base_val,
            k_runtime,
            gs.get("target_direction", "reach"),
            gs.get("target_percent_change"),
            gs.get("search_min"),
            gs.get("search_max"),
            gs.get("steps", 21),
        )

        facts = (
            f"Question: {question}\n"
            f"Parameter: {p_decisions[0]['selected']} ({p_runtime})\n"
            f"KPI: {k_decisions[0]['selected']} ({k_runtime})\n"
            f"Detected Model Horizon: {self.model_horizon}\n"
            f"Baseline parameter value: {base_val}\n"
            f"Baseline KPI last: {gs_result['baseline_last']}\n"
            f"Target KPI value: {gs_result['target_value']}\n"
            f"Best trial: {gs_result['best']}\n"
        )

        answer = explain_goal_seek(question, facts)
        trials_path = export_table_excel(f"goal_seek_{p_runtime}_{k_runtime}", gs_result["trials"])

        result_payload["answer"] = answer
        result_payload["trials_df"] = gs_result["trials"]
        result_payload["excel_path"] = trials_path
        return result_payload

    # -----------------------------------
    # main answer
    # -----------------------------------
    def answer(self, question: str, session_id: str = "default_session", confirm_selector=None):
        mem = self._get_session(session_id)
        raw_question = (question or "").strip()

        style_request = self._detect_response_style_request(raw_question)
        if style_request:
            result = self._rewrite_last_answer(raw_question, session_id, style_request)
            self._update_memory(session_id, raw_question, result)
            return result

        rule_intent = self._rule_based_intent_override(raw_question)
        intent = rule_intent or extract_intent(raw_question)

        if self._should_use_history_for_intent(raw_question):
            history_context = self._history_context(mem)
            if history_context and not rule_intent:
                contextual_question = (
                    f"{history_context}\n\n"
                    f"Current user question:\n{raw_question}"
                )
                contextual_intent = extract_intent(contextual_question)
                if contextual_intent.get("intent_type") in {
                    "run_simulation",
                    "query_current_value",
                    "query_average_value",
                    "explain_variable",
                    "explain_impact",
                    "query_target_needed",
                }:
                    intent = contextual_intent

        intent = self._apply_followup_memory(raw_question, intent, mem)

        if self._is_general_system_dynamics_question(raw_question):
            result = self._base_result(
                answer=explain_methodology(raw_question),
                intent={"intent_type": "methodology_query"},
            )
            self._update_memory(session_id, raw_question, result)
            return result

        it = intent.get("intent_type")

        if it == "list_all_parameters":
            df, path = self.list_all_parameters()
            result = self._base_result(
                answer=f"Simulation хийх боломжтой parameter-уудын жагсаалт. {self.get_model_horizon_text()}",
                intent=intent,
            )
            result["table_df"] = df
            result["excel_path"] = path
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "list_parameters_by_keyword":
            df, path = self.list_by_keyword(intent.get("keyword") or raw_question, mode="parameter")
            result = self._base_result(
                answer=f"'{intent.get('keyword') or raw_question}' холбоотой parameter-уудыг оллоо.",
                intent=intent,
            )
            result["table_df"] = df
            result["excel_path"] = path
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "list_all_kpis":
            df, path = self.list_all_kpis()
            result = self._base_result(
                answer=f"Model дээрх KPI / output variable-уудын жагсаалт. {self.get_model_horizon_text()}",
                intent=intent,
            )
            result["table_df"] = df
            result["excel_path"] = path
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "list_kpis_by_keyword":
            df, path = self.list_by_keyword(intent.get("keyword") or raw_question, mode="kpi")
            result = self._base_result(
                answer=f"'{intent.get('keyword') or raw_question}' холбоотой KPI-уудыг оллоо.",
                intent=intent,
            )
            result["table_df"] = df
            result["excel_path"] = path
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "query_current_value":
            result = self.query_value(
                raw_question,
                intent.get("focus_variable_phrase") or (intent.get("requested_kpis") or [raw_question])[0],
                average=False,
                year_start=intent.get("year_start"),
                year_end=intent.get("year_end"),
                confirm_selector=confirm_selector,
            )
            result["intent"] = intent
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "query_average_value":
            result = self.query_value(
                raw_question,
                intent.get("focus_variable_phrase") or (intent.get("requested_kpis") or [raw_question])[0],
                average=True,
                year_start=intent.get("year_start"),
                year_end=intent.get("year_end"),
                confirm_selector=confirm_selector,
            )
            result["intent"] = intent
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "explain_variable":
            result = self.explain_variable(
                raw_question,
                intent.get("focus_variable_phrase") or raw_question,
                confirm_selector=confirm_selector,
                year_start=intent.get("year_start"),
                year_end=intent.get("year_end"),
            )
            result["intent"] = intent
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "explain_impact":
            result = self.explain_impact(
                raw_question,
                intent.get("focus_variable_phrase") or raw_question,
                confirm_selector=confirm_selector,
                year_start=intent.get("year_start"),
                year_end=intent.get("year_end"),
            )
            result["intent"] = intent
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "query_target_needed":
            result = self.goal_seek(raw_question, intent, confirm_selector=confirm_selector)
            result["intent"] = intent
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "real_world_query":
            result = self._base_result(
                answer=answer_real_world(raw_question),
                intent=intent,
            )
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "methodology_query":
            result = self._base_result(
                answer=explain_methodology(raw_question),
                intent=intent,
            )
            self._update_memory(session_id, raw_question, result)
            return result

        if it == "run_simulation":
            result = self.run_simulation(raw_question, intent, confirm_selector=confirm_selector)
            result["intent"] = intent
            self._update_memory(session_id, raw_question, result)
            return result

        result = self._base_result(
            answer=(
                "Асуултаа арай тодорхой бичнэ үү. "
                "Жишээ нь: parameter list, KPI list, simulation, дундаж утга, variable тайлбар гэж асууж болно."
            ),
            intent=intent,
        )
        self._update_memory(session_id, raw_question, result)
        return result