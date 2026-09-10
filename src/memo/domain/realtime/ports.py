from abc import ABC, abstractmethod

from pydantic import StrictStr

from memo.domain.message_dna.models import StrictModel


class CallCreation(StrictModel):
    call_id: StrictStr
    answer_sdp: StrictStr


class RealtimeCallPort(ABC):
    @abstractmethod
    async def create_call(self, offer_sdp: str) -> CallCreation:
        """Create a WebRTC call and return its answer and server call identifier."""


class SidebandSession(ABC):
    @abstractmethod
    async def close(self) -> None:
        """Close the sideband session and release its background work."""


class SidebandAttacher(ABC):
    @abstractmethod
    async def attach(self, call_id: str, project_id: str) -> SidebandSession:
        """Attach server-side agent controls to an existing realtime call."""
