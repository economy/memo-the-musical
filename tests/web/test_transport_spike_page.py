from pathlib import Path

import httpx

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.app import create_app
from memo.domain.demo.constants import SECURITY_DEMO_PROJECT_ID
from memo.domain.message_dna.models import MessagePreset, Project
from memo.domain.realtime.ports import (
    CallCreation,
    RealtimeCallPort,
    SidebandAttacher,
    SidebandSession,
)
from memo.services.message_dna_service import MessageDNAService
from memo.services.sideband_registry import SidebandSessionRegistry


class PageSession(SidebandSession):
    async def close(self) -> None:
        """Close without resources."""


class PageAttacher(SidebandAttacher):
    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Return a no-op session for page rendering."""
        return PageSession()


class PageCallClient(RealtimeCallPort):
    async def create_call(self, offer_sdp: str) -> CallCreation:
        """Return a no-op call for page rendering."""
        return CallCreation(call_id="unused", answer_sdp="unused")


async def test_page_exposes_browser_webrtc_controls_without_websocket(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Transport spike", preset=MessagePreset.GENERAL)
    project_data = project.model_dump()
    project_data["id"] = SECURITY_DEMO_PROJECT_ID
    service.create_project(Project.model_validate(project_data))
    app = create_app(
        PageCallClient(),
        SidebandSessionRegistry(PageAttacher()),
        service,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        page = await client.get("/")
        script = await client.get("/static/js/realtime.js")

    assert page.status_code == 200
    assert 'id="start-call"' in page.text
    assert 'id="remote-audio"' in page.text
    assert 'id="demo-transcript"' in page.text
    assert 'id="replay-fallback"' in page.text
    assert script.status_code == 200
    assert "RTCPeerConnection" in script.text
    assert "getUserMedia" in script.text
    assert "createDataChannel" in script.text
    assert 'method: "DELETE"' in script.text
    assert "X-Memo-Call-ID" in script.text
    assert "WebSocket" not in script.text
    repository.close()
