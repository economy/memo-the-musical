import asyncio
import logging
from contextlib import suppress

from agents.realtime import RealtimeRunner, RealtimeSession

from memo.domain.realtime.constants import REALTIME_VOICE
from memo.domain.realtime.ports import SidebandAttacher, SidebandSession
from memo.services.realtime_agent import RealtimeAgentFactory
from memo.services.transcript_ingest import TranscriptIngestor

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
    def __init__(
        self,
        agent_factory: RealtimeAgentFactory,
        ingestor: TranscriptIngestor,
        api_key: str,
    ) -> None:
        self._agent_factory = agent_factory
        self._ingestor = ingestor
        self._api_key = api_key

    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Attach the current Agents SDK WebSocket model by existing WebRTC call ID."""
        self._ingestor.ingest_text(project_id, "")
        agent = self._agent_factory.create(project_id)
        runner = RealtimeRunner(
            starting_agent=agent,
            config={
                "model_settings": {
                    "tool_choice": "required",
                    "audio": {"output": {"voice": REALTIME_VOICE}},
                }
            },
        )
        session = await runner.run(model_config={"call_id": call_id, "api_key": self._api_key})
        await session.enter()
        task = asyncio.create_task(self._consume_events(session, project_id))
        return AgentsSDKSidebandSession(session, task)

    async def _consume_events(self, session: RealtimeSession, project_id: str) -> None:
        try:
            async for event in session:
                if event.type == "tool_start":
                    LOGGER.info("Realtime tool started")
                elif event.type == "tool_end":
                    LOGGER.info("Realtime tool finished")
                elif event.type == "error":
                    LOGGER.error("Realtime sideband reported an error")
                elif event.type == "history_added":
                    spoken = _user_transcript(event.item)
                    if spoken:
                        self._ingestor.ingest_text(project_id, spoken)
            LOGGER.info("Realtime sideband event stream ended")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            LOGGER.error(
                "Realtime sideband event stream failed; error_type=%s",
                type(error).__name__,
            )


def _user_transcript(item: object) -> str:
    if getattr(item, "role", None) != "user":
        return ""
    parts: list[str] = []
    for content in getattr(item, "content", []) or []:
        spoken = getattr(content, "transcript", None) or getattr(content, "text", None)
        if spoken:
            parts.append(spoken)
    return " ".join(parts).strip()
