import json
import re
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class GraphExtraction:
    entities: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    reason: str


async def extract_graph(user_input: str, assistant_reply: str, model_config=None) -> GraphExtraction:
    prompt = f"""
You are a knowledge graph extractor for a persistent roleplay AI system.
Extract stable entities, attributes, and relations from this exchange.

Entity schema:
{{
  "entity_id": "stable_snake_case_id",
  "name": "display name",
  "type": "person|character|place|group|item|concept|event|unknown",
  "attributes": {{"key": "value"}}
}}

Relation schema:
{{
  "source_id": "entity_id",
  "relation": "short_verb_or_relation",
  "target_id": "entity_id",
  "confidence": 0.0,
  "evidence": "short quote or reason"
}}

Rules:
- Use stable ids such as user, current_character, snow_mountain.
- Extract only facts likely useful in future conversations.
- Do not invent facts.
- Return strict JSON only.

Return format:
{{
  "entities": [],
  "relations": [],
  "reason": "short extraction summary"
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
        return GraphExtraction(entities=[], relations=[], reason="invalid_json")

    entities = _clean_entities(data.get("entities", []))
    relations = _clean_relations(data.get("relations", []))
    return GraphExtraction(entities=entities, relations=relations, reason=str(data.get("reason", ""))[:500])


def apply_graph_extraction(graph_store, extraction: GraphExtraction):
    for entity in extraction.entities:
        graph_store.upsert_entity(
            entity_id=entity["entity_id"],
            name=entity.get("name", entity["entity_id"]),
            entity_type=entity.get("type", "unknown"),
            attributes=entity.get("attributes", {}),
        )

    for relation in extraction.relations:
        graph_store.add_relation(
            source_id=relation["source_id"],
            relation=relation["relation"],
            target_id=relation["target_id"],
            confidence=relation.get("confidence", 0.8),
            evidence=relation.get("evidence", ""),
        )


def _clean_entities(items):
    cleaned = []
    if not isinstance(items, list):
        return cleaned
    for item in items:
        if not isinstance(item, dict):
            continue
        entity_id = _stable_id(str(item.get("entity_id") or item.get("name") or ""))
        if not entity_id:
            continue
        attrs = item.get("attributes", {})
        if not isinstance(attrs, dict):
            attrs = {}
        cleaned.append({
            "entity_id": entity_id,
            "name": str(item.get("name") or entity_id),
            "type": str(item.get("type") or "unknown"),
            "attributes": {str(k): str(v) for k, v in attrs.items()},
        })
    return cleaned


def _clean_relations(items):
    cleaned = []
    if not isinstance(items, list):
        return cleaned
    for item in items:
        if not isinstance(item, dict):
            continue
        source_id = _stable_id(str(item.get("source_id") or ""))
        target_id = _stable_id(str(item.get("target_id") or ""))
        relation = _stable_id(str(item.get("relation") or "related_to"))
        if not source_id or not target_id:
            continue
        try:
            confidence = float(item.get("confidence", 0.8))
        except Exception:
            confidence = 0.8
        cleaned.append({
            "source_id": source_id,
            "relation": relation,
            "target_id": target_id,
            "confidence": max(0.0, min(1.0, confidence)),
            "evidence": str(item.get("evidence", ""))[:300],
        })
    return cleaned


def _stable_id(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9_\u4e00-\u9fff]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:80]


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
