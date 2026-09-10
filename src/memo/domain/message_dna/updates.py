from pydantic import Field, StrictStr

from memo.domain.message_dna.models import (
    Chorus,
    HumorLevel,
    StrictModel,
    TranscriptEntry,
)


class FactCorrection(StrictModel):
    key: StrictStr = Field(min_length=1)
    value: StrictStr = Field(min_length=1)


class CallToActionPatch(StrictModel):
    action: StrictStr | None = Field(default=None, min_length=1)
    url: StrictStr | None = None


class VibePatch(StrictModel):
    emotional_response: StrictStr | None = None
    humor: HumorLevel | None = None
    notes: list[StrictStr] | None = None


class DeliveryContextPatch(StrictModel):
    channel: StrictStr | None = None
    duration: StrictStr | None = None
    deadline: StrictStr | None = None
    context: StrictStr | None = None


class MessageDNAPatch(StrictModel):
    original_request: StrictStr | None = None
    business_context: StrictStr | None = None
    chorus: Chorus | None = None
    call_to_action: CallToActionPatch | None = None
    audience: StrictStr | None = None
    fact_corrections: list[FactCorrection] | None = None
    vibe: VibePatch | None = None
    guardrails: list[StrictStr] | None = None
    delivery: DeliveryContextPatch | None = None
    assumptions: list[StrictStr] | None = None
    unresolved_questions: list[StrictStr] | None = None
    transcript: list[TranscriptEntry] | None = None
