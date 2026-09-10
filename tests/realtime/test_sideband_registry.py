import logging

import pytest

from memo.domain.realtime.ports import SidebandAttacher, SidebandSession
from memo.services.sideband_registry import SidebandSessionRegistry


class FakeSession(SidebandSession):
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        """Record lifecycle closure without external I/O."""
        self.closed = True


class FakeAttacher(SidebandAttacher):
    def __init__(self) -> None:
        self.attachments: list[tuple[str, str]] = []
        self.session = FakeSession()

    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Record the existing-call attachment contract."""
        self.attachments.append((call_id, project_id))
        return self.session


class FailingCloseSession(SidebandSession):
    async def close(self) -> None:
        """Simulate an SDK cleanup exception."""
        raise RuntimeError("secret transport diagnostic")


class PerCallAttacher(SidebandAttacher):
    def __init__(self) -> None:
        self.good_session = FakeSession()

    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Return one failing and one healthy session."""
        if call_id == "rtc_failing":
            return FailingCloseSession()
        return self.good_session


async def test_registry_attaches_and_tracks_existing_call() -> None:
    attacher = FakeAttacher()
    registry = SidebandSessionRegistry(attacher)

    await registry.start("rtc_123", "project_456")

    assert attacher.attachments == [("rtc_123", "project_456")]
    assert registry.active_call_ids == {"rtc_123"}

    await registry.stop("rtc_123")
    assert attacher.session.closed is True
    assert registry.active_call_ids == set()


async def test_close_all_continues_after_session_cleanup_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    attacher = PerCallAttacher()
    registry = SidebandSessionRegistry(attacher)
    await registry.start("rtc_failing", "project_1")
    await registry.start("rtc_healthy", "project_2")

    with caplog.at_level(logging.ERROR):
        await registry.close_all()

    assert registry.active_call_ids == set()
    assert attacher.good_session.closed is True
    assert "Realtime sideband session cleanup failed" in caplog.text
    assert "secret transport diagnostic" not in caplog.text
