"""Unified AI Provider Service — support OpenAI and Ollama for text generation & embeddings."""
import json
import logging
from collections.abc import AsyncGenerator

import httpx

from core.config import settings

import os

logger = logging.getLogger(__name__)


def _get_api_key() -> str:
    """Get non-empty OpenAI API Key from environment or settings."""
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        key = (settings.OPENAI_API_KEY or "").strip()
    return key


async def generate_text(prompt: str, temperature: float = 0.1) -> str:
    """Synchronous/Single-response LLM completion for both OpenAI and Ollama."""
    provider = (settings.AI_PROVIDER or "openai").lower()

    if provider == "openai":
        api_key = _get_api_key()
        if not api_key:
            logger.warning("OPENAI_API_KEY is not set. Requests to OpenAI may fail.")

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": settings.OPENAI_LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Only set temperature if not default (1.0) and model supports custom temperature
        model_name = (settings.OPENAI_LLM_MODEL or "").lower()
        if temperature != 1.0 and not any(model_name.startswith(p) for p in ("gpt-5", "o1", "o3", "o-")):
            payload["temperature"] = temperature

        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""

    else:
        # Fallback to Ollama
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        payload = {
            "model": settings.LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")


async def stream_chat_response(
    prompt: str,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """Stream SSE tokens ('data: {\"token\": \"...\"}\\n\\n') for OpenAI or Ollama."""
    provider = (settings.AI_PROVIDER or "openai").lower()

    if provider == "openai":
        api_key = _get_api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": settings.OPENAI_LLM_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        model_name = (settings.OPENAI_LLM_MODEL or "").lower()
        if temperature != 1.0 and not any(model_name.startswith(p) for p in ("gpt-5", "o1", "o3", "o-")):
            payload["temperature"] = temperature
        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"

        full_response = ""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                full_response += token
                                yield f"data: {json.dumps({'token': token})}\n\n"
                        except json.JSONDecodeError:
                            continue

        yield "data: [DONE]\n\n"

    else:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
        payload = {
            "model": settings.LLM_MODEL,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }

        full_response = ""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        full_response += token
                        yield f"data: {json.dumps({'token': token})}\n\n"
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

        yield "data: [DONE]\n\n"


async def get_embedding(text_input: str) -> list[float]:
    """Generate single vector embedding (768 float values)."""
    provider = (settings.AI_PROVIDER or "openai").lower()

    if provider == "openai":
        api_key = _get_api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        payload = {
            "model": settings.OPENAI_EMBED_MODEL,
            "input": text_input,
            "dimensions": int(settings.OPENAI_EMBED_DIMENSIONS),
        }
        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["data"][0]["embedding"]

    else:
        url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/embeddings"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={"model": settings.EMBED_MODEL, "prompt": text_input},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Batch generate vector embeddings (768 float values per text)."""
    if not texts:
        return []

    provider = (settings.AI_PROVIDER or "openai").lower()

    if provider == "openai":
        api_key = _get_api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings"

        batch_size = 100
        results: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": settings.OPENAI_EMBED_MODEL,
                "input": batch,
                "dimensions": int(settings.OPENAI_EMBED_DIMENSIONS),
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # Ensure ordered by index
                batch_res = [item["embedding"] for item in sorted(data["data"], key=lambda x: x["index"])]
                results.extend(batch_res)

        return results

    else:
        from langchain_ollama import OllamaEmbeddings

        embeddings_model = OllamaEmbeddings(
            model=settings.EMBED_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

        batch_size = 32
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = await embeddings_model.aembed_documents(batch)
            results.extend(batch_embeddings)
        return results
