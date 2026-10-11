import httpx
import pytest

from app.services.intelligence.ollama_client import OllamaClient, OllamaError


@pytest.mark.asyncio
async def test_chat_raises_ollama_error_on_connect_failure(monkeypatch):
    async def fake_post(self, url, json=None):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = OllamaClient(base_url="http://localhost:11434", timeout=1)

    with pytest.raises(OllamaError) as exc_info:
        await client.chat([{"role": "user", "content": "hi"}])

    assert "running" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_chat_raises_ollama_error_on_timeout(monkeypatch):
    async def fake_post(self, url, json=None):
        raise httpx.ReadTimeout("too slow")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = OllamaClient(base_url="http://localhost:11434", timeout=1)

    with pytest.raises(OllamaError) as exc_info:
        await client.chat([{"role": "user", "content": "hi"}])

    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_embed_raises_on_missing_embeddings_field(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"error": "no embeddings support"}

    async def fake_post(self, url, json=None):
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = OllamaClient(base_url="http://localhost:11434", timeout=1)

    with pytest.raises(OllamaError):
        await client.embed(["some text"])


@pytest.mark.asyncio
async def test_embed_returns_empty_list_for_empty_input():
    client = OllamaClient(base_url="http://localhost:11434", timeout=1)
    result = await client.embed([])
    assert result == []
