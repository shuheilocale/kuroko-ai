"""Unified async LLM client supporting Ollama and llama.cpp server."""

import logging
from dataclasses import dataclass
from typing import Literal

import httpx
import ollama

logger = logging.getLogger(__name__)

LLMBackend = Literal["ollama", "llamacpp"]


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    content: str


class LLMClient:
    """Async LLM client that abstracts Ollama and llama.cpp backends."""

    def __init__(
        self,
        backend: LLMBackend = "ollama",
        model: str = "qwen3.5:9b",
        llamacpp_url: str = "http://127.0.0.1:8080",
    ):
        self.backend = backend
        self.model = model
        self.llamacpp_url = llamacpp_url.rstrip("/")
        self._ollama = ollama.AsyncClient()
        self._http = httpx.AsyncClient(timeout=120.0)

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 512,
        think: bool = False,
    ) -> ChatResponse:
        if self.backend == "llamacpp":
            return await self._chat_llamacpp(
                messages, temperature, max_tokens
            )
        return await self._chat_ollama(
            messages, temperature, max_tokens, think
        )

    async def _chat_ollama(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        think: bool,
    ) -> ChatResponse:
        response = await self._ollama.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            think=think,
        )
        msg = response["message"]
        content = (
            getattr(msg, "content", "") or msg.get("content", "")
        )
        return ChatResponse(content=content)

    async def _chat_llamacpp(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> ChatResponse:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = await self._http.post(
            f"{self.llamacpp_url}/v1/chat/completions",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return ChatResponse(content=content)

    async def health_check(self) -> bool:
        """Check if the backend is available."""
        if self.backend == "llamacpp":
            return await self._health_llamacpp()
        return await self._health_ollama()

    async def _health_ollama(self) -> bool:
        try:
            result = await self._ollama.list()
            models = (
                result.models
                if hasattr(result, "models")
                else result.get("models", [])
            )
            available = [
                getattr(m, "model", None) or m.get("model", "")
                for m in models
            ]
            return any(self.model in m for m in available)
        except Exception:
            return False

    async def _health_llamacpp(self) -> bool:
        try:
            resp = await self._http.get(
                f"{self.llamacpp_url}/health"
            )
            return resp.status_code == 200
        except Exception:
            return False

    @staticmethod
    def list_ollama_models() -> dict[str, str]:
        """List available Ollama models with display labels.

        Returns dict of {model_id: display_label}.
        """
        try:
            client = ollama.Client()
            result = client.list()
            models = (
                result.models
                if hasattr(result, "models")
                else result.get("models", [])
            )
            out = {}
            for m in models:
                name = (
                    getattr(m, "model", None)
                    or m.get("model", "")
                )
                size_bytes = (
                    getattr(m, "size", 0)
                    or m.get("size", 0)
                )
                params = (
                    getattr(
                        getattr(m, "details", None),
                        "parameter_size", "",
                    )
                    if hasattr(m, "details")
                    else ""
                )
                if size_bytes:
                    gb = size_bytes / (1024 ** 3)
                    label = f"{name} ({params}, {gb:.1f}GB)" if params else f"{name} ({gb:.1f}GB)"
                else:
                    label = name
                out[name] = label
            return out
        except Exception:
            return {}

    async def close(self):
        await self._http.aclose()
