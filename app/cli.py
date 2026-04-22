from __future__ import annotations
import sys
from app.engine import AssistantEngine

STOP_WORDS = {"exit", "quit", "q", "stop", "дуусгах", "болих", "гар"}


def cli_confirm_selector(decision: dict, label: str = "parameter"):
    print(f"\n'{decision['phrase']}' нь 100% тодорхой биш байна. Боломжит {label}-ууд:")
    for i, c in enumerate(decision.get("candidates", []), start=1):
        print(f"{i}. {c['real_name']} | py_name={c.get('py_name')} | units={c.get('units')} | confidence={c.get('confidence')}")
        if c.get("comment"):
            print(f"   comment: {c['comment']}")
    ans = input("Зөв хувилбарын дугаар (эсвэл ENTER): ").strip()
    if ans.isdigit():
        idx = int(ans)
        if 1 <= idx <= len(decision.get("candidates", [])):
            return decision["candidates"][idx - 1]["real_name"]
    return None


def print_result(result: dict):
    print("\n=== ХАРИУЛТ ===")
    print(result.get("answer", ""))
    if result.get("excel_path"):
        print(f"\n[EXCEL] {result['excel_path']}")
    if result.get("plot_paths"):
        print("[PLOTS]")
        for p in result["plot_paths"]:
            print(p)
    if result.get("table_df") is not None:
        print("\n=== TABLE PREVIEW ===")
        print(result["table_df"].head(20).to_string(index=False))
    if result.get("stats_df") is not None and not result["stats_df"].empty:
        print("\n=== STATS ===")
        print(result["stats_df"].to_string(index=False))


def main():
    try:
        engine = AssistantEngine()
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    print("=== Hybrid AI Simulation Assistant ===")
    print("Горимууд: parameter list, KPI list, simulation, model explanation, real-world stats, methodology explanation")
    print("Гарах: exit / quit / болих")

    while True:
        q = input("\nАсуулт: ").strip()
        if not q or q.lower() in STOP_WORDS:
            print("Дууслаа.")
            break
        try:
            result = engine.answer(q, confirm_selector=cli_confirm_selector)
            print_result(result)
        except Exception as e:
            print(f"[ERROR] {e}")
