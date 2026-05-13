import json
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class UnifiedExtraction:
    entities: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    events: list[dict[str, Any]]
    state_updates: list[dict[str, Any]]
    reason: str


async def extract_structured_updates(user_input: str, assistant_reply: str, model_config=None) -> UnifiedExtraction:
    prompt = f"""
You are a structured extractor for a persistent multi-character roleplay/world simulation system.
Extract only durable, future-useful facts from this exchange.

Return strict JSON only:
{{
  "entities": [
    {{
      "entity_id": "stable_snake_case_id",
      "name": "display name",
      "type": "person|character|place|group|item|concept|event|unknown",
      "attributes": {{"key": "value"}}
    }}
  ],
  "relations": [
    {{
      "source_id": "entity_id",
      "relation": "short_snake_case_relation",
      "target_id": "entity_id",
      "confidence": 0.0,
      "evidence": "short evidence"
    }}
  ],
  "events": [
    {{
      "title": "short event title",
      "description": "what happened",
      "participants": ["entity_id"],
      "location": "place or empty",
      "effects": [
        {{"key": "state_key", "value": "state_value", "confidence": 0.0, "evidence": "why"}}
      ],
      "confidence": 0.0
    }}
  ],
  "state_updates": [
    {{"key": "state_key", "value": "state_value", "confidence": 0.0, "evidence": "why"}}
  ],
  "reason": "short summary"
}}

Rules:
- Do not invent facts.
- Extract only things likely useful later.
- Use stable ids where possible.
- If nothing durable is present, return empty arrays.

User message:
{user_input}

Assistant reply:
{assistant_reply}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return UnifiedExtraction([], [], [], [], "invalid_json")

    entities = data.get("entities", []) if isinstance(data.get("entities", []), list) else []
    relations = data.get("relations", []) if isinstance(data.get("relations", []), list) else []
    events = data.get("events", []) if isinstance(data.get("events", []), list) else []
    state_updates = data.get("state_updates", []) if isinstance(data.get("state_updates", []), list) else []
    reason = str(data.get("reason", ""))[:500]
    return UnifiedExtraction(entities, relations, events, state_updates, reason)


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
