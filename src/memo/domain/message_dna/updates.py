from pydantic import Field, StrictStr

from memo.domain.message_dna.models import (
    CallToAction,
    Chorus,
    DeliveryContext,
    StrictModel,
    TranscriptEntry,
    Vibe,
)


class FactCorrection(StrictModel):
    key: StrictStr = Field(min_length=1)
    value: StrictStr = Field(min_length=1)


class MessageDNAPatch(StrictModel):
    original_request: StrictStr | None = None
    business_context: StrictStr | None = None
    chorus: Chorus | None = None
    call_to_action: CallToAction | None = None
    audience: StrictStr | None = None
    fact_corrections: list[FactCorrection] | None = None
    vibe: Vibe | None = None
    guardrails: list[StrictStr] | None = None
    delivery: DeliveryContext | None = None
    assumptions: list[StrictStr] | None = None
    unresolved_questions: list[StrictStr] | None = None
    transcript: list[TranscriptEntry] | None = None
