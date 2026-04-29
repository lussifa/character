import json
from dataclasses import dataclass
from typing import Any

from .providers import call_model


@dataclass
class ReflectionPlan:
    operations: list[dict[str, Any]]
    reason: str


async def reflect_memories(memories: list[dict], model_config=None) -> ReflectionPlan:
    compact = []
    for m in memories:
        compact.append({
            "memory_id": m.get("memory_id"),
            "text": m.get("text"),
            "tier": m.get("tier"),
            "importance": m.get("importance"),
            "access_count": m.get("access_count", 0),
        })

    prompt = f"""
You are a memory reflection engine for a persistent AI roleplay system.
Review the memory list and propose cleanup operations.

Allowed operations:
- delete: remove low-value, obsolete, or duplicate memory
- merge: combine multiple related memories into one
- promote_to_core: convert important permanent memory to core
- demote_to_long_term: convert over-promoted core memory to long_term
- keep: explicitly keep a memory as-is

Return strict JSON only:
{{
  "operations": [
    {{
      "op": "delete|merge|promote_to_core|demote_to_long_term|keep",
      "memory_ids": ["..."],
      "text": "new merged text or empty",
      "importance": 0.0,
      "reason": "short reason"
    }}
  ],
  "reason": "overall reflection summary"
}}

Memories:
{json.dumps(compact, ensure_ascii=False, indent=2)}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return ReflectionPlan(operations=[], reason="invalid_json")

    ops = data.get("operations", [])
    if not isinstance(ops, list):
        ops = []
    return ReflectionPlan(operations=ops, reason=str(data.get("reason", ""))[:500])


def apply_reflection_plan(store, plan: ReflectionPlan, embedder):
    changed = False
    by_id = {m.get("memory_id"): m for m in store.data}

    for op in plan.operations:
        action = op.get("op")
        ids = op.get("memory_ids", []) or []
        if not isinstance(ids, list):
            continue

        if action == "delete":
            before = len(store.data)
            store.data = [m for m in store.data if m.get("memory_id") not in set(ids)]
            changed = changed or len(store.data) != before

        elif action == "promote_to_core":
            for mid in ids:
                if mid in by_id:
                    by_id[mid]["tier"] = "core"
                    by_id[mid]["importance"] = max(float(by_id[mid].get("importance", 0.5)), 0.85)
                    changed = True

        elif action == "demote_to_long_term":
            for mid in ids:
                if mid in by_id:
                    by_id[mid]["tier"] = "long_term"
                    changed = True

        elif action == "merge":
            text = str(op.get("text", "")).strip()
            if not text or not ids:
                continue
            existing = [by_id[mid] for mid in ids if mid in by_id]
            if not existing:
                continue
            primary = existing[0]
            primary["text"] = text
            primary["embedding"] = embedder.embed(text).tolist()
            primary["importance"] = max(float(op.get("importance", 0.6)), max(float(m.get("importance", 0.5)) for m in existing))
            primary["tier"] = _strongest_tier([m.get("tier", "long_term") for m in existing])
            remove_ids = {m.get("memory_id") for m in existing[1:]}
            store.data = [m for m in store.data if m.get("memory_id") not in remove_ids]
            changed = True

    if changed:
        store._rewrite()
    return changed


def _strongest_tier(tiers):
    rank = {"short_term": 0, "long_term": 1, "core": 2}
    return max(tiers, key=lambda t: rank.get(t, 1)) if tiers else "long_term"


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
