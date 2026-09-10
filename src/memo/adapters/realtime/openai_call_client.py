import json

import httpx

from memo.domain.realtime.ports import CallCreation, RealtimeCallPort

REALTIME_MODEL = "gpt-realtime-2.1-mini"
CALLS_PATH = "/v1/realtime/calls"


class RealtimeUpstreamError(RuntimeError):
    """Represent a failed or malformed OpenAI call-creation response."""


class OpenAIRealtimeCallClient(RealtimeCallPort):
    def __init__(self, http_client: httpx.AsyncClient, api_key: str) -> None:
        self._http_client = http_client
        self._api_key = api_key

    async def create_call(self, offer_sdp: str) -> CallCreation:
        """Forward a browser SDP offer without exposing the server API key."""
        session = json.dumps(
            {
                "type": "realtime",
                "model": REALTIME_MODEL,
                "audio": {
                    "input": {"turn_detection": {"type": "semantic_vad"}},
                    "output": {"voice": "marin"},
                },
            }
        )
        response = await self._http_client.post(
            CALLS_PATH,
            headers={"Authorization": f"Bearer {self._api_key}"},
            files={
                "sdp": ("offer.sdp", offer_sdp, "application/sdp"),
                "session": ("session.json", session, "application/json"),
            },
        )
        if not response.is_success:
            raise RealtimeUpstreamError(
                f"OpenAI realtime call creation failed with status {response.status_code}"
            )
        location = response.headers.get("Location")
        call_id = location.rstrip("/").rsplit("/", 1)[-1] if location else ""
        if not call_id:
            raise RealtimeUpstreamError("OpenAI response omitted the realtime call identifier")
        return CallCreation(call_id=call_id, answer_sdp=response.text)
