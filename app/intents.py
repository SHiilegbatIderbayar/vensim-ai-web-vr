from app.openai_utils import response_json

INTENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intent_type": {
            "type": "string",
            "enum": [
                "run_simulation",
                "list_all_parameters",
                "list_parameters_by_keyword",
                "list_all_kpis",
                "list_kpis_by_keyword",
                "query_current_value",
                "query_average_value",
                "explain_variable",
                "explain_impact",
                "query_target_needed",
                "real_world_query",
                "methodology_query",
                "help"
            ]
        },
        "requested_kpis": {"type": "array", "items": {"type": "string"}},
        "parameter_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "param_phrase": {"type": "string"},
                    "operation": {"type": "string", "enum": ["set", "delta"]},
                    "value": {"type": "number"}
                },
                "required": ["param_phrase", "operation", "value"]
            }
        },
        "keyword": {"type": ["string", "null"]},
        "focus_variable_phrase": {"type": ["string", "null"]},
        "year_start": {"type": ["integer", "null"]},
        "year_end": {"type": ["integer", "null"]},
        "need_equation": {"type": "boolean"},
        "explanation_language": {"type": "string"},
        "goal_seek": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "target_kpi_phrase": {"type": "string"},
                "target_direction": {"type": "string", "enum": ["increase", "decrease", "reach"]},
                "target_percent_change": {"type": ["number", "null"]},
                "candidate_parameter_phrase": {"type": "string"},
                "candidate_operation": {"type": "string", "enum": ["set", "delta"]},
                "search_min": {"type": ["number", "null"]},
                "search_max": {"type": ["number", "null"]},
                "steps": {"type": "integer"}
            },
            "required": [
                "target_kpi_phrase",
                "target_direction",
                "target_percent_change",
                "candidate_parameter_phrase",
                "candidate_operation",
                "search_min",
                "search_max",
                "steps"
            ]
        }
    },
    "required": [
        "intent_type",
        "requested_kpis",
        "parameter_changes",
        "keyword",
        "focus_variable_phrase",
        "year_start",
        "year_end",
        "need_equation",
        "explanation_language",
        "goal_seek"
    ]
}


def extract_intent(question: str) -> dict:
    prompt = f"""
You are an intent extraction engine for a model-aware simulation assistant.

Classify the user question into one intent_type.

Guidance:
- Use run_simulation when the user asks 'if X changes, what happens' or requests a what-if scenario.
- Use list_all_parameters for requests asking what parameters can be simulated.
- Use list_parameters_by_keyword when the user asks for parameters related to a keyword/topic.
- Use list_all_kpis for requests asking what outputs/KPIs are available.
- Use list_kpis_by_keyword when the user asks for KPIs related to a topic.
- Use query_current_value when the user asks current/start/end value or 'how much is X'.
- Use query_average_value when the user asks average, typical, mean over time.
- Use explain_variable when the user asks what a variable means or asks for formula/equation/definition.
- Use explain_impact when the user asks what impact/effect/influence a variable has.
- Use query_target_needed when the user asks 'to reduce/increase KPI by X%, how much of parameter is needed'.
- Use real_world_query when user asks for real-world latest/current statistics or facts outside the model.
- Use methodology_query when user asks for the meaning of a method, term, phrase, or concept.
- Use help only for generic help.

For percentages:
- '30% болго' => set 0.30
- '30%-иар өсгө' => delta 0.30
- '30 хувь бууруулахад' in a target question usually means target_percent_change=0.30, target_direction='decrease'

Question:
{question}
"""
    return response_json(
        input_messages=[
            {"role": "system", "content": "Extract structured intent only."},
            {"role": "user", "content": prompt},
        ],
        schema_name="user_intent",
        schema=INTENT_SCHEMA,
    )
