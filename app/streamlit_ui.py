from __future__ import annotations
from pathlib import Path
import streamlit as st
from app.engine import AssistantEngine


def _render_candidates(decision: dict):
    st.warning(f"'{decision['phrase']}' нь 100% тодорхой биш байна.")
    options = ["-- сонгох --"] + [c["real_name"] for c in decision.get("candidates", [])]
    return st.selectbox(f"Сонгох ({decision['phrase']})", options, key=f"select_{decision['phrase']}")


def make_streamlit_selector(container):
    selections = {}
    def selector(decision: dict, label: str = "parameter"):
        with container:
            chosen = _render_candidates(decision)
        if chosen and chosen != "-- сонгох --":
            selections[decision['phrase']] = chosen
            return chosen
        return None
    selector.selections = selections
    return selector


def run_app():
    st.set_page_config(page_title="Hybrid AI Simulation Assistant", layout="wide")
    st.title("Hybrid AI Simulation Assistant")
    st.caption("Model-driven simulation + model explanation + real-world web search + methodology explanation")

    if "engine" not in st.session_state:
        try:
            st.session_state.engine = AssistantEngine()
        except Exception as e:
            st.error(str(e))
            st.stop()

    engine = st.session_state.engine

    q = st.text_area("Асуултаа бичнэ үү", height=120, placeholder="Ж: Салхины чадал ямар нөлөөтэй вэ?")
    confirm_box = st.container()
    selector = make_streamlit_selector(confirm_box)

    col1, col2 = st.columns([1, 1])
    run_btn = col1.button("Run")
    sample_btn = col2.button("Жишээ асуултууд")

    if sample_btn:
        st.info("Жишээ: 'Сургуультай холбоотой parameter list гарга', 'Салхины чадал ямар нөлөөтэй вэ?', 'Монгол Улсын суурилагдсан салхины чадлын сүүлийн статистик' гэх мэт.")

    if run_btn and q.strip():
        result = engine.answer(q.strip(), confirm_selector=selector)
        st.subheader("Хариулт")
        st.write(result.get("answer", ""))

        if result.get("table_df") is not None:
            st.subheader("Хүснэгт")
            st.dataframe(result["table_df"], use_container_width=True)

        if result.get("stats_df") is not None and not result["stats_df"].empty:
            st.subheader("Статистик")
            st.dataframe(result["stats_df"], use_container_width=True)

        if result.get("baseline_df") is not None:
            st.subheader("Baseline")
            st.dataframe(result["baseline_df"].head(50), use_container_width=True)

        if result.get("scenario_df") is not None:
            st.subheader("Scenario")
            st.dataframe(result["scenario_df"].head(50), use_container_width=True)

        if result.get("plot_paths"):
            st.subheader("Графикууд")
            for p in result["plot_paths"]:
                st.image(str(Path(p)))

        if result.get("excel_path"):
            st.success(f"Excel saved: {result['excel_path']}")
