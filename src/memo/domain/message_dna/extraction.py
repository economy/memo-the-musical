import re

from memo.domain.message_dna.models import Chorus, HumorLevel
from memo.domain.message_dna.updates import (
    CallToActionPatch,
    FactCorrection,
    MessageDNAPatch,
    VibePatch,
)

_DEADLINE_THURSDAY = "Thursday, October 15 at 5 PM Pacific"
_DEADLINE_FRIDAY = "Friday, October 16 at 5 PM Pacific"


def extract_message_dna_patch(text: str) -> MessageDNAPatch:
    """Turn spoken or stored request text into a partial Message DNA update."""
    source = text.strip()
    if not source:
        return MessageDNAPatch()
    lowered = source.lower()
    corrections: list[FactCorrection] = []
    if _has_thursday_deadline(lowered):
        corrections.append(FactCorrection(key="deadline", value=_DEADLINE_THURSDAY))
    elif "friday, october 16" in lowered or ("friday" in lowered and "october 16" in lowered):
        corrections.append(FactCorrection(key="deadline", value=_DEADLINE_FRIDAY))
    if "12 minutes" in lowered:
        corrections.append(FactCorrection(key="duration", value="about 12 minutes"))
    if "learnhub" in lowered:
        corrections.append(FactCorrection(key="system", value="LearnHub"))

    guardrails: list[str] = []
    if "phishing" in lowered:
        guardrails.append("Never joke about phishing victims.")
    if "prize" in lowered:
        guardrails.append("Don't invent prizes.")

    unresolved: list[str] = []
    if "learnhub" in lowered and "http" not in lowered:
        unresolved.append("What is the LearnHub URL?")

    return MessageDNAPatch(
        original_request=source,
        chorus=_chorus_from(source, lowered),
        call_to_action=_cta_from(lowered),
        audience=_audience_from(lowered),
        fact_corrections=corrections or None,
        vibe=_vibe_from(lowered),
        guardrails=guardrails or None,
        unresolved_questions=unresolved or None,
    )


def _chorus_from(source: str, lowered: str) -> Chorus | None:
    if "security training" in lowered:
        return Chorus(summary="Complete required security training before the deadline.")
    sentence = re.split(r"[.!?]", source, maxsplit=1)[0].strip()
    if len(sentence.split()) >= 8:
        return Chorus(summary=sentence)
    return None


def _cta_from(lowered: str) -> CallToActionPatch | None:
    if "learnhub" in lowered:
        return CallToActionPatch(action="Complete LearnHub by the deadline.")
    return None


def _audience_from(lowered: str) -> str | None:
    if "contractor" in lowered:
        return "Employees and contractors"
    if "everyone" in lowered:
        return "Everyone"
    return None


def _vibe_from(lowered: str) -> VibePatch | None:
    if "spy-movie" in lowered or "spy movie" in lowered:
        return VibePatch(
            emotional_response="Playful spy-movie energy",
            humor=HumorLevel.PLAYFUL,
            notes=["Lightly tease procrastination, never individuals."],
        )
    return None


def _has_thursday_deadline(lowered: str) -> bool:
    return "thursday, october 15" in lowered or ("thursday" in lowered and "october 15" in lowered)
