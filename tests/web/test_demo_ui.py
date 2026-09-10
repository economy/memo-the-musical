from html import unescape
from pathlib import Path

import httpx

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.app import create_app
from memo.domain.demo.constants import (
    REPLAY_DEMO_PROJECT_ID,
    SECURITY_DEMO_PROJECT_ID,
    SECURITY_DEMO_TEXT,
)
from memo.domain.message_dna.models import FactStatus, MessagePreset
from memo.domain.realtime.ports import (
    CallCreation,
    RealtimeCallPort,
    SidebandAttacher,
    SidebandSession,
)
from memo.services.demo_seed import ensure_demo_projects
from memo.services.message_dna_service import MessageDNAService
from memo.services.sideband_registry import SidebandSessionRegistry


class DemoSession(SidebandSession):
    async def close(self) -> None:
        """Close without resources."""


class DemoAttacher(SidebandAttacher):
    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Return a no-op session for demo route tests."""
        return DemoSession()


class DemoCallClient(RealtimeCallPort):
    async def create_call(self, offer_sdp: str) -> CallCreation:
        """Return a no-op call for demo route tests."""
        return CallCreation(call_id="demo-call", answer_sdp="unused")


def build_demo_app(tmp_path: Path) -> tuple[httpx.ASGITransport, SQLiteProjectRepository]:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    ensure_demo_projects(service)
    app = create_app(
        DemoCallClient(),
        SidebandSessionRegistry(DemoAttacher()),
        service,
    )
    return httpx.ASGITransport(app=app), repository


async def test_demo_page_renders_studio_identity(tmp_path: Path) -> None:
    transport, repository = build_demo_app(tmp_path)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        page = await client.get("/")
        script = await client.get("/static/js/realtime.js")

    assert page.status_code == 200
    assert "Memo: The Musical" in page.text
    assert "The Chorus" in page.text
    assert "Do This" in page.text
    assert "Sacred Lyrics" in page.text
    assert "Vibe Check" in page.text
    assert "Legal Says No" in page.text
    assert "Earworm Readiness" in page.text
    assert 'id="presenter-rail"' in page.text
    assert 'id="session-badge"' in page.text
    assert 'id="start-call"' in page.text
    assert 'id="demo-transcript"' in page.text
    assert 'id="replay-fallback"' in page.text
    assert SECURITY_DEMO_TEXT in unescape(page.text)
    assert f'value="{SECURITY_DEMO_PROJECT_ID}"' in page.text
    assert "tailwindcss.com" in page.text
    assert "WebSocket" not in page.text
    assert "WebSocket" not in script.text
    assert "RTCPeerConnection" in script.text
    assert "conversation.item.create" in script.text
    repository.close()


async def test_demo_page_lists_preset_choices(tmp_path: Path) -> None:
    transport, repository = build_demo_app(tmp_path)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        page = await client.get("/")

    for preset in ("training", "announcement", "product", "report"):
        assert f'data-preset="{preset}"' in page.text
    repository.close()


async def test_project_routes_create_list_and_select(tmp_path: Path) -> None:
    transport, repository = build_demo_app(tmp_path)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        listed = await client.get("/api/projects")
        created = await client.post("/api/projects", json={"preset": "announcement"})
        selected = await client.post(f"/api/projects/select/{created.json()['id']}")

    assert listed.status_code == 200
    assert any(item["id"] == SECURITY_DEMO_PROJECT_ID for item in listed.json())
    assert created.status_code == 201
    assert created.json()["preset"] == MessagePreset.ANNOUNCEMENT
    assert selected.status_code == 200
    assert selected.json()["mode"] == "live"
    assert selected.cookies["memo_active_project"] == created.json()["id"]
    repository.close()


async def test_replay_route_labels_mode_and_sets_cookie(tmp_path: Path) -> None:
    transport, repository = build_demo_app(tmp_path)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/projects/replay")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": REPLAY_DEMO_PROJECT_ID,
        "mode": "replay",
    }
    assert response.cookies["memo_active_project"] == REPLAY_DEMO_PROJECT_ID
    repository.close()


async def test_dna_fragment_renders_replay_correction_history(tmp_path: Path) -> None:
    transport, repository = build_demo_app(tmp_path)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        fragment = await client.get(f"/fragments/dna/{REPLAY_DEMO_PROJECT_ID}")

    assert fragment.status_code == 200
    assert "Friday, October 16 at 5 PM Pacific" in fragment.text
    assert "Thursday, October 15 at 5 PM Pacific" in fragment.text
    assert "superseded" in fragment.text.lower()
    assert "What is the LearnHub URL?" in fragment.text
    assert "Ready for Composer" in fragment.text
    assert "REPLAY" in fragment.text
    repository.close()


async def test_replay_project_reloads_exact_correction_history(tmp_path: Path) -> None:
    database = tmp_path / "memo.db"
    repository = SQLiteProjectRepository(database)
    service = MessageDNAService(repository)
    ensure_demo_projects(service)
    repository.close()

    reopened = SQLiteProjectRepository(database)
    project = reopened.get(REPLAY_DEMO_PROJECT_ID)
    assert project is not None
    old_fact, corrected_fact = project.message_dna.locked_facts
    assert old_fact.status is FactStatus.SUPERSEDED
    assert corrected_fact.status is FactStatus.ACTIVE
    assert old_fact.superseded_by_id == corrected_fact.id
    assert corrected_fact.supersedes_id == old_fact.id
    assert project.message_dna.chorus is not None
    assert project.message_dna.call_to_action is not None
    assert project.message_dna.audience == "Employees and contractors"
    assert project.message_dna.guardrails
    assert project.message_dna.unresolved_questions == ["What is the LearnHub URL?"]
    reopened.close()
