import asyncio

from memo.domain.realtime.ports import SidebandAttacher, SidebandSession


class SidebandRegistryError(RuntimeError):
    """Represent a failed sideband attachment without leaking SDK details."""


class SidebandSessionRegistry:
    def __init__(self, attacher: SidebandAttacher) -> None:
        self._attacher = attacher
        self._sessions: dict[str, SidebandSession] = {}
        self._lock = asyncio.Lock()

    @property
    def active_call_ids(self) -> set[str]:
        """Return a snapshot of calls currently managed by this process."""
        return set(self._sessions)

    async def start(self, call_id: str, project_id: str) -> None:
        """Attach and register one existing call, replacing stale duplicates safely."""
        try:
            session = await self._attacher.attach(call_id, project_id)
        except Exception as error:
            raise SidebandRegistryError("Sideband attachment failed") from error
        async with self._lock:
            previous = self._sessions.pop(call_id, None)
            self._sessions[call_id] = session
        if previous is not None:
            await previous.close()

    async def stop(self, call_id: str) -> None:
        """Close and remove a registered sideband session when present."""
        async with self._lock:
            session = self._sessions.pop(call_id, None)
        if session is not None:
            await session.close()

    async def close_all(self) -> None:
        """Close all sessions during application shutdown."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            await session.close()
