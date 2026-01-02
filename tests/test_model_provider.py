import asyncio
import httpx
import pytest

from ap.models import OpenAIModelProvider


class _MockStream(httpx.AsyncByteStream):
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def __aiter__(self):  # type: ignore[override]
        for line in self._lines:
            yield line.encode()


def _mock_transport(lines: list[str]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ANN001
        return httpx.Response(200, request=request, stream=_MockStream(lines))

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_openai_provider_streams_tokens_and_cleans_up():
    lines = [
        "data: {\"choices\":[{\"delta\":{\"content\":\"Hello \"}}]}",
        "data: {\"choices\":[{\"delta\":{\"content\":\"world\"}}]}",
        "data: [DONE]",
    ]
    client = httpx.AsyncClient(transport=_mock_transport(lines))
    provider = OpenAIModelProvider(api_key="test-key", client=client)

    cancel_event = asyncio.Event()
    tokens = []
    async for token in provider.stream("stream-1", "hello", cancel_event):
        tokens.append(token)

    assert tokens == ["Hello ", "world"]
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_provider_cancel_stops_stream():
    lines = [
        "data: {\"choices\":[{\"delta\":{\"content\":\"Hello \"}}]}",
        "data: {\"choices\":[{\"delta\":{\"content\":\"world\"}}]}",
    ]
    client = httpx.AsyncClient(transport=_mock_transport(lines))
    provider = OpenAIModelProvider(api_key="test-key", client=client)

    cancel_event = asyncio.Event()
    stream = provider.stream("stream-2", "hello", cancel_event)
    first = await stream.__anext__()
    cancel_event.set()
    remaining = [token async for token in stream]

    assert first == "Hello "
    assert remaining == []
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_provider_missing_key_reports_down():
    provider = OpenAIModelProvider(api_key=None)
    health = await provider.health_check()
    assert health.status == "down"
    assert health.reason == "missing_api_key"
