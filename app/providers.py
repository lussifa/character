import httpx
import os

async def call_model(prompt):
    provider = os.getenv("PROVIDER", "mock")

    if provider == "mock":
        return f"[AI Reply] {prompt[:100]}"

    if provider == "openai_compatible":
        url = os.getenv("OPENAI_BASE_URL")
        key = os.getenv("OPENAI_API_KEY")
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            return r.json()["choices"][0]["message"]["content"]

    if provider == "ollama":
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama2", "prompt": prompt}
            )
            return r.json().get("response", "")

    return "No provider configured"
