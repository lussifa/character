import os
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

    if provider == "mock":
        return _mock_reply(prompt)

    if provider == "openai_compatible":
        return await _openai_compatible(prompt=prompt, system=system, model=model, base_url=base_url)

    if provider == "ollama":
        return await _ollama(prompt=prompt, system=system, model=model)

    raise ProviderError(f"Unsupported provider: {provider}")

def _mock_reply(prompt: str) -> str:
    clipped = prompt.replace("\n", " ")[:220]
    return f"[Mock AI] I understand the scene context. Responding in character based on: {clipped}"

async def _openai_compatible(prompt: str, system: str, model: str, base_url: str) -> str:
    key = _env("OPENAI_API_KEY")
    if not base_url:
        base_url = "https://api.openai.com"
    base_url = base_url.rstrip("/")
    if not key:
        raise ProviderError("OPENAI_API_KEY is required for openai_compatible provider")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        response = await client.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.85},
        )
        response.raise_for_status()
        payload = response.json()
        return payload["choices"][0]["message"]["content"]

async def _ollama(prompt: str, system: str, model: str) -> str:
    ollama_url = _env("OLLAMA_URL", "http://localhost:11434").rstrip("/")
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
