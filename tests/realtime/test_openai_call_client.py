import httpx
import pytest

from memo.adapters.realtime.openai_call_client import OpenAIRealtimeCallClient


@pytest.mark.asyncio
async def test_call_client_forwards_multipart_sdp_and_extracts_call_id() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        assert request.url.path == "/v1/realtime/calls"
        assert "multipart/form-data" in request.headers["content-type"]
        assert b"gpt-realtime-2.1-mini" in body
        assert b"v=0\r\no=browser-offer" in body
        return httpx.Response(
            201,
            text="v=0\r\no=openai-answer",
            headers={"Location": "/v1/realtime/calls/rtc_123"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://api.openai.com",
    ) as http:
        client = OpenAIRealtimeCallClient(http, api_key="server-secret")
        result = await client.create_call("v=0\r\no=browser-offer")

    assert result.call_id == "rtc_123"
    assert result.answer_sdp == "v=0\r\no=openai-answer"
