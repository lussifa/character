import json
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class SpeakerTurn:
    character_id: str
    reason: str
    priority: float


async def schedule_speakers(user_input: str, multi_store, world_store=None, graph_store=None, model_config=None, max_speakers: int = 2) -> list[SpeakerTurn]:
    characters = multi_store.list_characters()
    if not characters:
        return []

    payload = {
        "user_input": user_input,
        "characters": characters,
        "relationships": multi_store.data.get("relationships", []),
        "world_context": world_store.context(limit_events=8) if world_store else "",
        "graph": graph_store.graph if graph_store else {},
        "max_speakers": max_speakers,
    }

    prompt = f"""
You are a speaker scheduler for a multi-character roleplay system.
Choose which characters should speak next and in what order.

Rules:
- Choose only existing active characters.
- Prefer characters whose goal, mood, relationship, or location makes them relevant.
- Do not choose everyone unless needed.
- Do not act as an autonomous agent; only decide speaking order.
- Return strict JSON only.

Return format:
{{
  "speakers": [
    {{"character_id": "id", "priority": 0.0, "reason": "why this character should speak"}}
  ]
}}

Context:
{json.dumps(payload, ensure_ascii=False, indent=2)[:16000]}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return _fallback_schedule(multi_store, max_speakers)

    valid_ids = {c["character_id"] for c in characters if c.get("state", {}).get("status", "active") == "active"}
    turns = []
    for item in data.get("speakers", []):
        if not isinstance(item, dict):
            continue
        cid = str(item.get("character_id", "")).strip()
        if cid not in valid_ids:
            continue
        try:
            priority = float(item.get("priority", 0.5))
        except Exception:
            priority = 0.5
        turns.append(SpeakerTurn(
            character_id=cid,
            priority=max(0.0, min(1.0, priority)),
            reason=str(item.get("reason", ""))[:300],
        ))

    turns.sort(key=lambda t: t.priority, reverse=True)
    if not turns:
        return _fallback_schedule(multi_store, max_speakers)
    return _dedupe(turns)[:max_speakers]


def scheduler_context(turns: list[SpeakerTurn], multi_store) -> str:
    lines = ["Scheduled speakers:"]
    for turn in turns:
        char = multi_store.get_character(turn.character_id) or {}
        lines.append(f"- {char.get('name', turn.character_id)} ({turn.character_id}), priority={turn.priority:.2f}: {turn.reason}")
    return "\n".join(lines)


def _fallback_schedule(multi_store, max_speakers):
    speakers = multi_store.choose_speakers(max_speakers=max_speakers)
    return [SpeakerTurn(character_id=cid, priority=0.5, reason="fallback active speaker") for cid in speakers]


def _dedupe(turns):
    seen = set()
    result = []
    for turn in turns:
        if turn.character_id in seen:
            continue
        seen.add(turn.character_id)
        result.append(turn)
    return result


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
