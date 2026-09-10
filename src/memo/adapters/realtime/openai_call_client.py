import json

import httpx

from memo.domain.realtime.constants import (
    REALTIME_CALLS_PATH,
    REALTIME_MODEL,
    REALTIME_VAD_TYPE,
    REALTIME_VOICE,
    SDP_FORM_FIELD,
    SDP_MEDIA_TYPE,
    SESSION_FORM_FIELD,
)
from memo.domain.realtime.ports import CallCreation, RealtimeCallPort
from memo.domain.realtime.session_tools import INITIAL_REALTIME_SESSION


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
                **INITIAL_REALTIME_SESSION,
                "model": REALTIME_MODEL,
                "audio": {
                    "input": {"turn_detection": {"type": REALTIME_VAD_TYPE}},
                    "output": {"voice": REALTIME_VOICE},
                },
            }
        )
        try:
            response = await self._http_client.post(
                REALTIME_CALLS_PATH,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={
                    SDP_FORM_FIELD: (None, offer_sdp, SDP_MEDIA_TYPE),
                    SESSION_FORM_FIELD: (None, session, "application/json"),
                },
            )
        except httpx.RequestError as error:
            raise RealtimeUpstreamError("OpenAI realtime call creation request failed") from error
        if not response.is_success:
            raise RealtimeUpstreamError(
                f"OpenAI realtime call creation failed with status {response.status_code}"
            )
        location: str = response.headers.get("Location", "")
        location_path = location.strip().partition("?")[0].rstrip("/")
        call_id = location_path.rsplit("/", 1)[-1] if location_path else ""
        if not call_id:
            raise RealtimeUpstreamError("OpenAI response omitted the realtime call identifier")
        return CallCreation(call_id=call_id, answer_sdp=response.text)
