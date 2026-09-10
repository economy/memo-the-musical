from agents import function_tool
from agents.realtime import RealtimeAgent

from memo.domain.message_dna.models import Chorus, HumorLevel
from memo.domain.message_dna.updates import (
    CallToActionPatch,
    FactCorrection,
    MessageDNAPatch,
    VibePatch,
)
from memo.domain.realtime.session_tools import AGENT_INSTRUCTIONS
from memo.services.message_dna_service import MessageDNAService


class RealtimeAgentFactory:
    def __init__(self, message_service: MessageDNAService) -> None:
        self._message_service = message_service

    def create(self, project_id: str) -> RealtimeAgent[None]:
        """Create the single call-scoped agent with one injected state tool."""

        async def update_message_dna(
            chorus: str | None = None,
            call_to_action: str | None = None,
            audience: str | None = None,
            deadline: str | None = None,
            duration: str | None = None,
            vibe: str | None = None,
            humor: str | None = None,
            guardrails: str | None = None,
            locked_facts: str | None = None,
        ) -> str:
            """Save confirmed Message DNA fields into the live local project."""
            patch = _patch_from_flat_tool(
                chorus=chorus,
                call_to_action=call_to_action,
                audience=audience,
                deadline=deadline,
                duration=duration,
                vibe=vibe,
                humor=humor,
                guardrails=guardrails,
                locked_facts=locked_facts,
            )
            project = self._message_service.update_project(project_id, patch)
            return project.message_dna.model_dump_json()

        return RealtimeAgent(
            name="Memo",
            instructions=AGENT_INSTRUCTIONS,
            tools=[function_tool(update_message_dna, strict_mode=False)],
        )


def _patch_from_flat_tool(
    *,
    chorus: str | None,
    call_to_action: str | None,
    audience: str | None,
    deadline: str | None,
    duration: str | None,
    vibe: str | None,
    humor: str | None,
    guardrails: str | None,
    locked_facts: str | None,
) -> MessageDNAPatch:
    corrections: list[FactCorrection] = []
    if deadline:
        corrections.append(FactCorrection(key="deadline", value=deadline))
    if duration:
        corrections.append(FactCorrection(key="duration", value=duration))
    corrections.extend(_facts_from_pairs(locked_facts))
    humor_level = None
    if humor:
        try:
            humor_level = HumorLevel(humor)
        except ValueError:
            humor_level = None
    return MessageDNAPatch(
        chorus=Chorus(summary=chorus) if chorus else None,
        call_to_action=CallToActionPatch(action=call_to_action) if call_to_action else None,
        audience=audience,
        fact_corrections=corrections or None,
        vibe=VibePatch(emotional_response=vibe, humor=humor_level) if vibe or humor_level else None,
        guardrails=_split_lines(guardrails),
    )


def _facts_from_pairs(raw: str | None) -> list[FactCorrection]:
    corrections: list[FactCorrection] = []
    for item in _split_lines(raw) or []:
        key, separator, value = item.partition("=")
        if separator and key.strip() and value.strip():
            corrections.append(FactCorrection(key=key.strip(), value=value.strip()))
    return corrections


def _split_lines(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parts = [part.strip() for part in raw.replace("|", ";").split(";") if part.strip()]
    return parts or None
