import asyncio
import logging
from contextlib import suppress

from agents.realtime import RealtimeRunner, RealtimeSession

from memo.domain.realtime.ports import SidebandAttacher, SidebandSession
from memo.services.realtime_agent import RealtimeAgentFactory

LOGGER = logging.getLogger(__name__)


class AgentsSDKSidebandSession(SidebandSession):
    def __init__(self, session: RealtimeSession, task: asyncio.Task[None]) -> None:
        self._session = session
        self._task = task

    async def close(self) -> None:
        """Close the SDK connection and stop its event-consumer task."""
        try:
            await self._session.close()
        finally:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task


class AgentsSDKSidebandAttacher(SidebandAttacher):
    def __init__(self, agent_factory: RealtimeAgentFactory, api_key: str) -> None:
        self._agent_factory = agent_factory
        self._api_key = api_key

    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Attach the current Agents SDK WebSocket model by existing WebRTC call ID."""
        agent = self._agent_factory.create(project_id)
        runner = RealtimeRunner(starting_agent=agent)
        session = await runner.run(model_config={"call_id": call_id, "api_key": self._api_key})
        await session.enter()
        task = asyncio.create_task(self._consume_events(session))
        return AgentsSDKSidebandSession(session, task)

    @staticmethod
    async def _consume_events(session: RealtimeSession) -> None:
        try:
            async for _ in session:
                pass
            LOGGER.info("Realtime sideband event stream ended")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            LOGGER.error(
                "Realtime sideband event stream failed; error_type=%s",
                type(error).__name__,
            )
