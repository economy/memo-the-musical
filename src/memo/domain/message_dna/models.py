from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictStr

SCHEMA_VERSION = 1


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class MessagePreset(StrEnum):
    TRAINING = "training"
    ANNOUNCEMENT = "announcement"
    PRODUCT = "product"
    REPORT = "report"
    GENERAL = "general"


class FactStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class HumorLevel(StrEnum):
    NONE = "none"
    LIGHT = "light"
    PLAYFUL = "playful"


class TranscriptRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class Chorus(StrictModel):
    summary: StrictStr = Field(min_length=1)


class CallToAction(StrictModel):
    action: StrictStr = Field(min_length=1)
    url: StrictStr | None = None


class LockedFact(StrictModel):
    id: StrictStr
    key: StrictStr = Field(min_length=1)
    value: StrictStr = Field(min_length=1)
    status: FactStatus = FactStatus.ACTIVE
    supersedes_id: StrictStr | None = None
    superseded_by_id: StrictStr | None = None
    recorded_at: datetime

    @classmethod
    def new(
        cls,
        *,
        key: str,
        value: str,
        supersedes_id: str | None = None,
    ) -> "LockedFact":
        """Create an active exact fact while preserving its correction link."""
        return cls(
            id=str(uuid4()),
            key=key,
            value=value,
            supersedes_id=supersedes_id,
            recorded_at=datetime.now(UTC),
        )


class Vibe(StrictModel):
    emotional_response: StrictStr | None = None
    humor: HumorLevel = HumorLevel.LIGHT
    notes: list[StrictStr] = Field(default_factory=list)


class DeliveryContext(StrictModel):
    channel: StrictStr | None = None
    duration: StrictStr | None = None
    deadline: StrictStr | None = None
    context: StrictStr | None = None


class TranscriptEntry(StrictModel):
    role: TranscriptRole
    text: StrictStr = Field(min_length=1)
    occurred_at: datetime


class MessageDNA(StrictModel):
    original_request: StrictStr | None = None
    business_context: StrictStr | None = None
    chorus: Chorus | None = None
    call_to_action: CallToAction | None = None
    audience: StrictStr | None = None
    locked_facts: list[LockedFact] = Field(default_factory=lambda: list[LockedFact]())
    vibe: Vibe = Field(default_factory=Vibe)
    guardrails: list[StrictStr] = Field(default_factory=list)
    delivery: DeliveryContext = Field(default_factory=DeliveryContext)
    assumptions: list[StrictStr] = Field(default_factory=list)
    unresolved_questions: list[StrictStr] = Field(default_factory=list)
    transcript: list[TranscriptEntry] = Field(default_factory=lambda: list[TranscriptEntry]())


class Project(StrictModel):
    id: StrictStr
    title: StrictStr = Field(min_length=1)
    preset: MessagePreset
    message_dna: MessageDNA = Field(default_factory=MessageDNA)
    schema_version: int = SCHEMA_VERSION
    created_at: datetime
    updated_at: datetime

    @classmethod
    def new(cls, *, title: str, preset: MessagePreset) -> "Project":
        """Create a versioned local project with empty Message DNA."""
        now = datetime.now(UTC)
        return cls(
            id=str(uuid4()),
            title=title,
            preset=preset,
            created_at=now,
            updated_at=now,
        )
