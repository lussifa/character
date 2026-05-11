import os
import json
import re
import httpx

DEFAULT_TIMEOUT = 120.0

class ProviderError(RuntimeError):
    pass

def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()

async def call_model(prompt: str, system: str = "", model_config=None) -> str:
    provider = (getattr(model_config, "provider", None) or _env("PROVIDER", "mock")).lower()
    model = getattr(model_config, "model", None) or _env("MODEL_NAME", "mock-roleplay")
    base_url = getattr(model_config, "base_url", None) or _env("OPENAI_BASE_URL", "")
    api_key = getattr(model_config, "api_key", None) or _env("OPENAI_API_KEY", "")

    if provider == "mock":
        return _mock_reply(prompt)

    if provider == "openai_compatible":
        return await _openai_compatible(
            prompt=prompt,
            system=system,
            model=model,
            base_url=base_url,
            api_key=api_key,
        )

    if provider == "ollama":
        return await _ollama(prompt=prompt, system=system, model=model, base_url=base_url)

    raise ProviderError(f"Unsupported provider: {provider}")

def _mock_reply(prompt: str) -> str:
    if '"speakers"' in prompt and "speaker scheduler" in prompt.lower():
        return json.dumps({"speakers": _mock_speakers(prompt)}, ensure_ascii=False)

    if '"action": "ignore|short_term|write|core"' in prompt:
        memory = _mock_memory_text(prompt)
        if not memory:
            return json.dumps({"action": "ignore", "memory": "", "importance": 0.0, "reason": "No durable fact detected."})
        return json.dumps({
            "action": "write",
            "memory": memory,
            "importance": 0.55,
            "reason": "Mock provider stored a concise durable exchange summary.",
        }, ensure_ascii=False)

    if '"entities": []' in prompt and '"relations": []' in prompt:
        return json.dumps({"entities": [], "relations": [], "reason": "Mock provider does not infer graph facts."})

    if '"events": []' in prompt and '"state_updates": []' in prompt:
        return json.dumps({
            "events": [],
            "state_updates": [],
            "narrative": "",
            "reason": "Mock provider does not advance world state.",
        })

    if '"facts": [' in prompt and "knowledge-graph reasoning" in prompt.lower():
        return json.dumps({"facts": []})

    if '"action": "keep|replace|merge|delete"' in prompt:
        return json.dumps({
            "action": "merge",
            "revised_memory": _mock_revision_text(prompt),
            "importance": 0.55,
            "reason": "Mock provider merged related memories.",
        }, ensure_ascii=False)

    clipped = prompt.replace("\n", " ")[:220]
    return f"[Mock AI] I understand the scene context. Responding in character based on: {clipped}"


def _mock_speakers(prompt: str) -> list[dict[str, object]]:
    max_speakers = _mock_int_field(prompt, "max_speakers", default=2)
    ids = []
    for match in re.finditer(r'"character_id"\s*:\s*"([^"]+)"', prompt):
        character_id = match.group(1)
        if character_id not in ids:
            ids.append(character_id)
    return [
        {
            "character_id": character_id,
            "priority": max(0.1, 1.0 - index * 0.1),
            "reason": "Mock scheduler selected the next active character.",
        }
        for index, character_id in enumerate(ids[:max_speakers])
    ]


def _mock_memory_text(prompt: str) -> str:
    user_message = _section(prompt, "User message:", "Assistant reply:").strip()
    assistant_reply = _section(prompt, "Assistant reply:", "").strip()
    if len(user_message) < 20 and len(assistant_reply) < 50:
        return ""
    return f"Recent exchange summary: user said {user_message[:180]!r}; assistant replied {assistant_reply[:180]!r}."


def _mock_revision_text(prompt: str) -> str:
    existing = _section(prompt, "Existing memory:", "New memory:").strip()
    new = _section(prompt, "New memory:", "").strip()
    if not existing:
        return new
    if not new or new in existing:
        return existing
    return f"{existing}\nUpdated/related memory: {new}"


def _mock_int_field(prompt: str, field: str, default: int) -> int:
    match = re.search(rf'"{re.escape(field)}"\s*:\s*(\d+)', prompt)
    if not match:
        return default
    try:
        return int(match.group(1))
    except ValueError:
        return default


def _section(text: str, start_marker: str, end_marker: str) -> str:
    start = text.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    if not end_marker:
        return text[start:]
    end = text.find(end_marker, start)
    if end == -1:
        return text[start:]
    return text[start:end]

async def _openai_compatible(prompt: str, system: str, model: str, base_url: str, api_key: str) -> str:
    if not base_url:
        base_url = "https://api.openai.com/v1"
    base_url = base_url.rstrip("/")
    if not api_key:
        raise ProviderError("API key is required for openai_compatible provider")

    endpoint = f"{base_url}/chat/completions" if base_url.endswith("/v1") else f"{base_url}/v1/chat/completions"

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.85},
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

async def _ollama(prompt: str, system: str, model: str, base_url: str = "") -> str:
    ollama_url = (base_url or _env("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
    if model == "mock-roleplay":
        model = _env("OLLAMA_MODEL", "llama2")

    final_prompt = prompt if not system else f"{system}\n\n{prompt}"
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": final_prompt, "stream": False},
        )
        response.raise_for_status()
        return response.json().get("response", "")

async def extract_memory(user_input: str, assistant_reply: str, model_config=None) -> str:
    if len(user_input.strip()) < 30 and len(assistant_reply.strip()) < 80:
        return ""

    prompt = f"""
Extract durable long-term memory from this roleplay/chat exchange.
Only return facts that will help future conversations. If nothing important should be remembered, return EMPTY.

User message:
{user_input}

Assistant reply:
{assistant_reply}
""".strip()

    try:
        summary = await call_model(prompt, system="You are a precise memory extraction engine.", model_config=model_config)
    except Exception:
        summary = user_input[:180]

    summary = summary.strip()
    if not summary or summary.upper() == "EMPTY":
        return ""
    return summary[:500]
