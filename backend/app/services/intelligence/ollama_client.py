import httpx

from app.core.config import settings


class OllamaError(Exception):
    """Raised whenever Ollama is unreachable, times out, or errors.

    Callers (the agent orchestrator) catch this and degrade gracefully
    instead of letting a connection failure crash the request.
    """


class OllamaClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.ollama_request_timeout_seconds

    async def chat(
        self, messages: list[dict], tools: list[dict] | None = None, model: str | None = None
    ) -> dict:
        payload: dict = {
            "model": model or settings.ollama_chat_model,
            "stream": False,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools

        return await self._post("/api/chat", payload)

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        if not texts:
            return []

        payload = {"model": model or settings.ollama_embedding_model, "input": texts}
        data = await self._post("/api/embed", payload)

        embeddings = data.get("embeddings")
        if not embeddings:
            raise OllamaError(f"Ollama embeddings response had no 'embeddings' field: {data}")
        return embeddings

    async def _post(self, path: str, payload: dict) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}{path}", json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise OllamaError(f"Ollama request to {path} timed out after {self.timeout}s") from exc
        except httpx.ConnectError as exc:
            raise OllamaError(
                f"Could not connect to Ollama at {self.base_url} -- is it running?"
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama returned HTTP {exc.response.status_code} for {path}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaError(f"Ollama request to {path} failed: {exc}") from exc
