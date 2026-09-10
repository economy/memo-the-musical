import httpx

from memo.adapters.realtime.openai_call_client import RealtimeUpstreamError
from memo.app import create_app
from memo.domain.realtime.ports import (
    CallCreation,
    RealtimeCallPort,
    SidebandAttacher,
    SidebandSession,
)
from memo.services.sideband_registry import SidebandSessionRegistry


class RouteFakeSession(SidebandSession):
    async def close(self) -> None:
        """Close without external resources."""


class RouteFakeAttacher(SidebandAttacher):
    def __init__(self) -> None:
        self.attachments: list[tuple[str, str]] = []

    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Capture route-triggered sideband attachment."""
        self.attachments.append((call_id, project_id))
        return RouteFakeSession()


class FailingAttacher(SidebandAttacher):
    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Simulate an SDK attachment failure."""
        raise ValueError("SDK rejected call_id")


class RouteFakeCallClient(RealtimeCallPort):
    def __init__(self) -> None:
        self.offers: list[str] = []

    async def create_call(self, offer_sdp: str) -> CallCreation:
        """Return a deterministic answer for the route contract."""
        self.offers.append(offer_sdp)
        return CallCreation(call_id="rtc_route", answer_sdp="v=0\r\no=answer")


class FailingCallClient(RealtimeCallPort):
    async def create_call(self, offer_sdp: str) -> CallCreation:
        """Simulate a credential-safe upstream failure."""
        raise RealtimeUpstreamError("OpenAI realtime call creation failed with status 401")


async def test_sdp_endpoint_forwards_offer_and_starts_sideband() -> None:
    call_client = RouteFakeCallClient()
    attacher = RouteFakeAttacher()
    app = create_app(call_client, SidebandSessionRegistry(attacher))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="v=0\r\no=offer",
            headers={"Content-Type": "application/sdp"},
        )

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/sdp"
    assert response.text == "v=0\r\no=answer"
    assert call_client.offers == ["v=0\r\no=offer"]
    assert attacher.attachments == [("rtc_route", "project_123")]


async def test_sdp_endpoint_reports_upstream_http_failure() -> None:
    attacher = RouteFakeAttacher()
    app = create_app(FailingCallClient(), SidebandSessionRegistry(attacher))

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="v=0\r\no=offer",
            headers={"Content-Type": "application/sdp"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "OpenAI realtime call creation failed with status 401"}
    assert attacher.attachments == []


async def test_sdp_endpoint_reports_sideband_failure() -> None:
    app = create_app(
        RouteFakeCallClient(),
        SidebandSessionRegistry(FailingAttacher()),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="v=0\r\no=offer",
            headers={"Content-Type": "application/sdp"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Realtime sideband attachment failed"}
