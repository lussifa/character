import json
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class LLMInferredFact:
    source_id: str
    relation: str
    target_id: str
    confidence: float
    evidence: str
    reasoning: str


async def infer_graph_with_llm(graph_store, model_config=None, max_entities=80, max_relations=160) -> list[LLMInferredFact]:
    entities = list(graph_store.graph.get("entities", {}).values())[:max_entities]
    relations = graph_store.graph.get("relations", [])[:max_relations]

    prompt = f"""
You are a cautious knowledge-graph reasoning engine for a roleplay AI system.
Infer useful implicit facts from the existing graph.

Rules:
- Do not invent unsupported facts.
- Infer only relationship, attitude, obligation, allegiance, conflict, trust, or world-state implications.
- Each inferred fact must be grounded in explicit evidence from the graph.
- Use stable entity ids that already exist in the graph.
- Return strict JSON only.

Return format:
{{
  "facts": [
    {{
      "source_id": "existing_entity_id",
      "relation": "short_snake_case_relation",
      "target_id": "existing_entity_id",
      "confidence": 0.0,
      "evidence": "which graph facts support this",
      "reasoning": "brief explanation"
    }}
  ]
}}

Entities:
{json.dumps(entities, ensure_ascii=False, indent=2)}

Relations:
{json.dumps(relations, ensure_ascii=False, indent=2)}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return []

    existing_entities = set(graph_store.graph.get("entities", {}).keys())
    facts = []
    for item in data.get("facts", []):
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_id", "")).strip()
        target_id = str(item.get("target_id", "")).strip()
        relation = str(item.get("relation", "")).strip()
        if source_id not in existing_entities or target_id not in existing_entities or not relation:
            continue
        try:
            confidence = float(item.get("confidence", 0.5))
        except Exception:
            confidence = 0.5
        facts.append(LLMInferredFact(
            source_id=source_id,
            relation=relation[:80],
            target_id=target_id,
            confidence=max(0.0, min(1.0, confidence)),
            evidence=str(item.get("evidence", ""))[:500],
            reasoning=str(item.get("reasoning", ""))[:500],
        ))
    return _dedupe(facts)


def apply_llm_inferences(graph_store, facts: list[LLMInferredFact], min_confidence=0.55):
    applied = []
    for fact in facts:
        if fact.confidence < min_confidence:
            continue
        graph_store.add_relation(
            source_id=fact.source_id,
            relation=fact.relation,
            target_id=fact.target_id,
            confidence=fact.confidence,
            evidence=f"LLM inference: {fact.evidence}; reasoning: {fact.reasoning}",
        )
        applied.append(fact)
    return applied


def llm_reasoning_context(facts: list[LLMInferredFact], graph_store, limit=30):
    entity_name = lambda eid: graph_store.graph.get("entities", {}).get(eid, {}).get("name", eid)
    lines = []
    for fact in facts[:limit]:
        lines.append(
            f"- {entity_name(fact.source_id)} {fact.relation} {entity_name(fact.target_id)} "
            f"(confidence={fact.confidence:.2f}; evidence={fact.evidence})"
        )
    return "\n".join(lines)


def _dedupe(facts: list[LLMInferredFact]) -> list[LLMInferredFact]:
    seen = set()
    result = []
    for fact in facts:
        key = (fact.source_id, fact.relation, fact.target_id)
        if key in seen:
            continue
        seen.add(key)
        result.append(fact)
    return result


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
