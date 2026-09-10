import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI

from memo.adapters.realtime.openai_call_client import RealtimeUpstreamError
from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.app import create_app
from memo.domain.message_dna.models import MessagePreset, Project
from memo.domain.realtime.ports import (
    CallCreation,
    RealtimeCallPort,
    SidebandAttacher,
    SidebandSession,
)
from memo.services.message_dna_service import MessageDNAService
from memo.services.sideband_registry import SidebandSessionRegistry


class RouteFakeSession(SidebandSession):
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        """Close without external resources."""
        self.closed = True


class RouteFakeAttacher(SidebandAttacher):
    def __init__(self) -> None:
        self.attachments: list[tuple[str, str]] = []
        self.session = RouteFakeSession()

    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Capture route-triggered sideband attachment."""
        self.attachments.append((call_id, project_id))
        return self.session


class FailingAttacher(SidebandAttacher):
    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Simulate an SDK attachment failure."""
        raise ValueError("SDK rejected call_id")


class SlowAttacher(SidebandAttacher):
    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Wait long enough to trigger the bounded attachment timeout."""
        await asyncio.sleep(1)
        return RouteFakeSession()


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


def build_app(
    call_client: RealtimeCallPort,
    attacher: SidebandAttacher,
    *,
    known_project: bool = True,
    attach_timeout_seconds: float = 5,
) -> tuple[FastAPI, SQLiteProjectRepository]:
    repository = SQLiteProjectRepository(Path(":memory:"))
    service = MessageDNAService(repository)
    if known_project:
        project = Project.new(title="Route test", preset=MessagePreset.GENERAL)
        project_data = project.model_dump()
        project_data["id"] = "project_123"
        service.create_project(Project.model_validate(project_data))
    registry = SidebandSessionRegistry(
        attacher,
        attach_timeout_seconds=attach_timeout_seconds,
    )
    return create_app(call_client, registry, service), repository


async def test_sdp_endpoint_forwards_offer_and_starts_sideband() -> None:
    call_client = RouteFakeCallClient()
    attacher = RouteFakeAttacher()
    app, repository = build_app(call_client, attacher)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="v=0\r\no=offer",
            headers={"Content-Type": "Application/SDP; charset=utf-8"},
        )

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/sdp"
    assert response.text == "v=0\r\no=answer"
    assert call_client.offers == ["v=0\r\no=offer"]
    assert attacher.attachments == [("rtc_route", "project_123")]
    assert response.headers["x-memo-call-id"] == "rtc_route"
    repository.close()


async def test_sdp_endpoint_reports_upstream_http_failure() -> None:
    attacher = RouteFakeAttacher()
    app, repository = build_app(FailingCallClient(), attacher)

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
    repository.close()


async def test_sdp_endpoint_reports_sideband_failure() -> None:
    app, repository = build_app(RouteFakeCallClient(), FailingAttacher())

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
    repository.close()


async def test_sdp_endpoint_rejects_unsupported_media_type() -> None:
    call_client = RouteFakeCallClient()
    app, repository = build_app(call_client, RouteFakeAttacher())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="not sdp",
            headers={"Content-Type": "text/plain"},
        )

    assert response.status_code == 415
    assert response.json() == {"detail": "Expected application/sdp"}
    assert call_client.offers == []
    repository.close()


async def test_sdp_endpoint_rejects_oversized_body() -> None:
    call_client = RouteFakeCallClient()
    app, repository = build_app(call_client, RouteFakeAttacher())

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="v" * 65_537,
            headers={"Content-Type": "application/sdp"},
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "SDP offer exceeds 65536 bytes"}
    assert call_client.offers == []
    repository.close()


async def test_sdp_endpoint_rejects_unknown_project_before_openai_call() -> None:
    call_client = RouteFakeCallClient()
    app, repository = build_app(
        call_client,
        RouteFakeAttacher(),
        known_project=False,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/realtime/calls?project_id=missing",
            content="v=0\r\no=offer",
            headers={"Content-Type": "application/sdp"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}
    assert call_client.offers == []
    repository.close()


async def test_sdp_endpoint_returns_stable_timeout_error() -> None:
    app, repository = build_app(
        RouteFakeCallClient(),
        SlowAttacher(),
        attach_timeout_seconds=0.001,
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

    assert response.status_code == 504
    assert response.json() == {"detail": "Realtime sideband attachment timed out"}
    repository.close()


async def test_delete_call_stops_registered_sideband_session() -> None:
    attacher = RouteFakeAttacher()
    app, repository = build_app(RouteFakeCallClient(), attacher)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        created = await client.post(
            "/api/realtime/calls?project_id=project_123",
            content="v=0\r\no=offer",
            headers={"Content-Type": "application/sdp"},
        )
        response = await client.delete(f"/api/realtime/calls/{created.headers['x-memo-call-id']}")

    assert response.status_code == 204
    assert attacher.session.closed is True
    repository.close()
