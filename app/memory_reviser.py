import json
from dataclasses import dataclass
from typing import Literal

from .providers import call_model

RevisionAction = Literal["keep", "replace", "merge", "delete"]


@dataclass
class MemoryRevision:
    action: RevisionAction
    revised_memory: str
    importance: float
    reason: str


async def revise_memory(existing_memory: str, new_memory: str, model_config=None) -> MemoryRevision:
    prompt = f"""
You are a memory revision engine for a long-term AI roleplay system.
A new memory may update, contradict, refine, or duplicate an existing memory.

Choose one action:
- keep: existing memory is still better; ignore the new memory
- replace: new memory corrects or supersedes the existing memory
- merge: both contain useful compatible details; produce one concise combined memory
- delete: existing memory is wrong or no longer useful, and new memory should not be stored

Return strict JSON only:
{{
  "action": "keep|replace|merge|delete",
  "revised_memory": "final memory text, empty only for delete/keep",
  "importance": 0.0,
  "reason": "short reason"
}}

Existing memory:
{existing_memory}

New memory:
{new_memory}
""".strip()

    raw = await call_model(prompt, system="Return only valid JSON.", model_config=model_config)
    try:
        data = json.loads(_extract_json(raw))
    except Exception:
        return MemoryRevision(
            action="merge",
            revised_memory=f"{existing_memory}\nUpdated/related memory: {new_memory}",
            importance=0.5,
            reason="invalid_json_default_merge",
        )

    action = data.get("action", "merge")
    if action not in {"keep", "replace", "merge", "delete"}:
        action = "merge"

    revised_memory = str(data.get("revised_memory", "")).strip()
    importance = float(data.get("importance", 0.5))
    importance = max(0.0, min(1.0, importance))
    reason = str(data.get("reason", ""))[:300]

    if action in {"replace", "merge"} and not revised_memory:
        revised_memory = new_memory if action == "replace" else f"{existing_memory}\nUpdated/related memory: {new_memory}"

    return MemoryRevision(action=action, revised_memory=revised_memory, importance=importance, reason=reason)


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
