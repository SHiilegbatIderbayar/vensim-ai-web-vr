import json
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_MODEL

JSON_SCHEMA_WRAPPER = {
    "type": "json_schema",
}


def get_client() -> OpenAI:
    if not OPENAI_API_KEY or OPENAI_API_KEY == "put_your_openai_api_key_here":
        raise RuntimeError("OPENAI_API_KEY тохируулаагүй байна. .env файлд API key-гээ оруулна уу.")
    return OpenAI(api_key=OPENAI_API_KEY)


def response_text(input_messages, tools=None, model: str | None = None) -> str:
    client = get_client()
    resp = client.responses.create(
        model=model or OPENAI_MODEL,
        input=input_messages,
        tools=tools or [],
    )
    return getattr(resp, "output_text", "") or ""


def response_json(input_messages, schema_name: str, schema: dict, tools=None, model: str | None = None) -> dict:
    client = get_client()
    resp = client.responses.create(
        model=model or OPENAI_MODEL,
        input=input_messages,
        tools=tools or [],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
    )
    text = getattr(resp, "output_text", "") or "{}"
    return json.loads(text)
