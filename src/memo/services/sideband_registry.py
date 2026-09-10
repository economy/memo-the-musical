import asyncio
import logging

from memo.domain.realtime.constants import SIDEBAND_ATTACH_TIMEOUT_SECONDS
from memo.domain.realtime.ports import SidebandAttacher, SidebandSession

LOGGER = logging.getLogger(__name__)


class SidebandRegistryError(RuntimeError):
    """Represent a failed sideband attachment without leaking SDK details."""


class SidebandTimeoutError(SidebandRegistryError):
    """Represent an attachment that exceeded the configured safe timeout."""


class SidebandSessionRegistry:
    def __init__(
        self,
        attacher: SidebandAttacher,
        attach_timeout_seconds: float = SIDEBAND_ATTACH_TIMEOUT_SECONDS,
    ) -> None:
        self._attacher = attacher
        self._attach_timeout_seconds = attach_timeout_seconds
        self._sessions: dict[str, SidebandSession] = {}
        self._lock = asyncio.Lock()

    @property
    def active_call_ids(self) -> set[str]:
        """Return a snapshot of calls currently managed by this process."""
        return set(self._sessions)

    async def start(self, call_id: str, project_id: str) -> None:
        """Attach and register one existing call, replacing stale duplicates safely."""
        try:
            async with asyncio.timeout(self._attach_timeout_seconds):
                session = await self._attacher.attach(call_id, project_id)
        except TimeoutError as error:
            LOGGER.warning("Realtime sideband attachment timed out")
            raise SidebandTimeoutError("Sideband attachment timed out") from error
        except Exception as error:
            LOGGER.error(
                "Realtime sideband attachment failed; error_type=%s",
                type(error).__name__,
            )
            raise SidebandRegistryError("Sideband attachment failed") from error
        async with self._lock:
            previous = self._sessions.pop(call_id, None)
            self._sessions[call_id] = session
        if previous is not None:
            await self._close_safely(previous)

    async def stop(self, call_id: str) -> None:
        """Close and remove a registered sideband session when present."""
        async with self._lock:
            session = self._sessions.pop(call_id, None)
        if session is not None:
            await self._close_safely(session)

    async def close_all(self) -> None:
        """Close all sessions during application shutdown."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            await self._close_safely(session)

    @staticmethod
    async def _close_safely(session: SidebandSession) -> None:
        try:
            await session.close()
        except Exception as error:
            LOGGER.error(
                "Realtime sideband session cleanup failed; error_type=%s",
                type(error).__name__,
            )
