from app.config import AUTO_MATCH_THRESHOLD, CONFIRM_THRESHOLD
from app.openai_utils import response_json

MATCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "phrase": {"type": "string"},
                    "status": {"type": "string", "enum": ["matched", "needs_confirmation", "not_found"]},
                    "selected": {"type": ["string", "null"]},
                    "selected_py_name": {"type": ["string", "null"]},
                    "candidates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "real_name": {"type": "string"},
                                "py_name": {"type": ["string", "null"]},
                                "type": {"type": "string"},
                                "units": {"type": ["string", "null"]},
                                "comment": {"type": ["string", "null"]},
                                "confidence": {"type": "number"}
                            },
                            "required": ["real_name", "py_name", "type", "units", "comment", "confidence"]
                        }
                    }
                },
                "required": ["phrase", "status", "selected", "selected_py_name", "candidates"]
            }
        }
    },
    "required": ["decisions"]
}

RANK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "real_name": {"type": "string"},
                    "py_name": {"type": ["string", "null"]},
                    "type": {"type": "string"},
                    "units": {"type": ["string", "null"]},
                    "comment": {"type": ["string", "null"]},
                    "relevance_score": {"type": "number"}
                },
                "required": ["real_name", "py_name", "type", "units", "comment", "relevance_score"]
            }
        }
    },
    "required": ["items"]
}


def match_phrases_to_entities(phrases: list[str], entity_records: list[dict], entity_label: str) -> list[dict]:
    if not phrases:
        return []
    entity_text = "\n".join([
        f"- real_name={r['real_name']} | py_name={r.get('py_name')} | type={r['type']} | units={r.get('units')} | comment={r.get('comment')}"
        for r in entity_records[:400]
    ])
    prompt = f"""
For each user phrase, choose up to 5 best {entity_label} candidates from the list.
Use semantic meaning, units, comments, and naming.

If top candidate confidence >= {AUTO_MATCH_THRESHOLD}, set status matched and selected.
If top confidence >= {CONFIRM_THRESHOLD} but lower than auto threshold, use needs_confirmation.
Otherwise use not_found.

Phrases:
{phrases}

Entities:
{entity_text}
"""
    data = response_json(
        input_messages=[
            {"role": "system", "content": f"Match user phrases to model {entity_label}s."},
            {"role": "user", "content": prompt},
        ],
        schema_name=f"match_{entity_label}",
        schema=MATCH_SCHEMA,
    )
    return data["decisions"]


def rank_entities_by_keyword(keyword: str, entity_records: list[dict], entity_label: str = "parameter", top_n: int = 10) -> list[dict]:
    entity_text = "\n".join([
        f"- real_name={r['real_name']} | py_name={r.get('py_name')} | type={r['type']} | units={r.get('units')} | comment={r.get('comment')}"
        for r in entity_records[:400]
    ])
    prompt = f"""
Rank the top {top_n} most relevant {entity_label}s for this keyword/topic.

Keyword:
{keyword}

Entities:
{entity_text}
"""
    data = response_json(
        input_messages=[
            {"role": "system", "content": f"Rank model {entity_label}s by keyword relevance."},
            {"role": "user", "content": prompt},
        ],
        schema_name=f"rank_{entity_label}",
        schema=RANK_SCHEMA,
    )
    return data["items"][:top_n]
