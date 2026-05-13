import json
import re
from dataclasses import dataclass
from typing import Literal

from .providers import call_model

MemoryAction = Literal["ignore", "write", "core", "short_term"]


@dataclass
class MemoryDecision:
    action: MemoryAction
    memory: str
    importance: float
    reason: str


async def decide_memory(user_input: str, assistant_reply: str, model_config=None) -> MemoryDecision:
    local = _fast_memory_decision(user_input, assistant_reply)
    if local is not None:
        return local

    prompt = f"""
You are a memory decision engine for a long-term roleplay AI system.
Decide whether the exchange contains durable memory.

Rules:
- ignore: trivial, temporary, or not useful later
- short_term: useful only for the current scene
- write: durable user/character/world fact
- core: identity, permanent preference, relationship, or major world fact

Return strict JSON only:
{{
  "action": "ignore|short_term|write|core",
  "memory": "concise memory text",
  "importance": 0.0,
  "reason": "short reason"
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
        return MemoryDecision(action="ignore", memory="", importance=0.0, reason="invalid_json")

    action = data.get("action", "ignore")
    if action not in {"ignore", "write", "core", "short_term"}:
        action = "ignore"

    memory = str(data.get("memory", "")).strip()
    importance = float(data.get("importance", 0.0))
    importance = max(0.0, min(1.0, importance))
    reason = str(data.get("reason", ""))[:300]

    if not memory and action != "ignore":
        action = "ignore"

    return MemoryDecision(action=action, memory=memory, importance=importance, reason=reason)


def decision_to_tier(action: MemoryAction) -> str:
    if action == "core":
        return "core"
    if action == "short_term":
        return "short_term"
    return "long_term"


def _fast_memory_decision(user_input: str, assistant_reply: str) -> MemoryDecision | None:
    text = f"{user_input.strip()}\n{assistant_reply.strip()}".strip()
    if not text:
        return MemoryDecision("ignore", "", 0.0, "empty_exchange")

    reply = assistant_reply.strip()
    if len(reply) < 24:
        return MemoryDecision("ignore", "", 0.0, "reply_too_short")

    if len(text) < 60:
        return MemoryDecision("ignore", "", 0.0, "exchange_too_small")

    low = text.lower()
    trivial_patterns = [
        r"^(好|嗯|哦|行|好的|知道了|收到)[。！! ]*$",
        r"^(yes|ok|okay|sure|got it)[.! ]*$",
    ]
    if any(re.match(pattern, reply, re.IGNORECASE) for pattern in trivial_patterns):
        return MemoryDecision("ignore", "", 0.0, "trivial_reply")

    keywords = [
        "在", "位于", "去了", "来到", "离开", "告诉", "知道", "发现", "藏在", "获得", "失去",
        "关系", "怀疑", "信任", "敌人", "目标", "计划", "秘密", "钟楼", "酒馆", "后巷",
        "location", "goal", "trust", "enemy", "secret", "plan", "told", "found", "heard",
    ]
    if not any(keyword in text for keyword in keywords):
        return MemoryDecision("ignore", "", 0.0, "no_durable_signal")

    return None


def _extract_json(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return text
    return text[start:end + 1]
