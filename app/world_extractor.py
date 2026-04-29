import json
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class WorldExtraction:
    events: list[dict[str, Any]]
    state_updates: list[dict[str, Any]]
    reason: str


async def extract_world_events(user_input: str, assistant_reply: str, model_config=None) -> WorldExtraction:
    prompt = f"""
You are a world-model event extractor for a persistent AI roleplay/story system.
Extract world events and durable state changes from the exchange.

Event schema:
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

State update schema:
{{
  "key": "state_key",
  "value": "state_value",
  "confidence": 0.0,
  "evidence": "why"
}}

Rules:
- Extract only events or state changes likely useful later.
- Do not invent events.
- Use stable entity ids like user, current_character, enemy_faction, snow_mountain.
- Return strict JSON only.

Return format:
{{
  "events": [],
  "state_updates": [],
  "reason": "short summary"
}}

User message:
{user_input}

Assistant reply:
{assistant_reply}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return WorldExtraction(events=[], state_updates=[], reason="invalid_json")

    events = data.get("events", []) if isinstance(data.get("events", []), list) else []
    state_updates = data.get("state_updates", []) if isinstance(data.get("state_updates", []), list) else []
    return WorldExtraction(events=events, state_updates=state_updates, reason=str(data.get("reason", ""))[:500])


def apply_world_extraction(world_store, extraction: WorldExtraction):
    for update in extraction.state_updates:
        if not isinstance(update, dict):
            continue
        key = str(update.get("key", "")).strip()
        if not key:
            continue
        world_store.set_state(
            key=key,
            value=str(update.get("value", "")),
            confidence=_confidence(update.get("confidence", 0.8)),
            evidence=str(update.get("evidence", ""))[:300],
        )

    for event in extraction.events:
        if not isinstance(event, dict):
            continue
        title = str(event.get("title", "")).strip()
        description = str(event.get("description", "")).strip()
        if not title or not description:
            continue
        effects = event.get("effects", [])
        if not isinstance(effects, list):
            effects = []
        world_store.add_event(
            title=title,
            description=description,
            participants=event.get("participants", []) if isinstance(event.get("participants", []), list) else [],
            location=str(event.get("location", "")),
            effects=effects,
            confidence=_confidence(event.get("confidence", 0.8)),
        )


def _confidence(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.8


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
