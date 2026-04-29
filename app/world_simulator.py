import json
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class SimulationResult:
    events: list[dict[str, Any]]
    state_updates: list[dict[str, Any]]
    narrative: str
    reason: str


async def simulate_world_step(world_store, graph_store, model_config=None, step_goal: str = "advance the world naturally") -> SimulationResult:
    prompt = f"""
You are a world simulation engine for a persistent roleplay/story AI.
Simulate the next plausible world step based only on existing world state, recent events, and knowledge graph facts.

Rules:
- Do not resolve major conflicts too quickly.
- Prefer small believable consequences over dramatic random twists.
- Keep causal continuity.
- Generate events that can affect later dialogue.
- Return strict JSON only.

Return format:
{{
  "events": [
    {{
      "title": "short event title",
      "description": "what happens next",
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
  "narrative": "short prose summary of the simulated development",
  "reason": "why this step follows from current state"
}}

Goal:
{step_goal}

World context:
{world_store.context(limit_events=12)}

Knowledge graph:
{json.dumps(graph_store.graph, ensure_ascii=False, indent=2)[:12000]}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return SimulationResult(events=[], state_updates=[], narrative="", reason="invalid_json")

    return SimulationResult(
        events=data.get("events", []) if isinstance(data.get("events", []), list) else [],
        state_updates=data.get("state_updates", []) if isinstance(data.get("state_updates", []), list) else [],
        narrative=str(data.get("narrative", ""))[:1200],
        reason=str(data.get("reason", ""))[:800],
    )


def apply_simulation(world_store, simulation: SimulationResult):
    for update in simulation.state_updates:
        if not isinstance(update, dict):
            continue
        key = str(update.get("key", "")).strip()
        if not key:
            continue
        world_store.set_state(
            key=key,
            value=str(update.get("value", "")),
            confidence=_confidence(update.get("confidence", 0.75)),
            evidence=str(update.get("evidence", "simulation"))[:300],
        )

    for event in simulation.events:
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
            confidence=_confidence(event.get("confidence", 0.75)),
        )


def simulation_context(simulation: SimulationResult):
    lines = []
    if simulation.narrative:
        lines.append("Simulated world development:")
        lines.append(simulation.narrative)
    if simulation.reason:
        lines.append("Simulation rationale:")
        lines.append(simulation.reason)
    return "\n".join(lines)


def _confidence(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except Exception:
        return 0.75


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
