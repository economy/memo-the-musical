from agents import function_tool
from agents.realtime import RealtimeAgent

from memo.domain.message_dna.updates import MessageDNAPatch
from memo.services.message_dna_service import MessageDNAService

AGENT_INSTRUCTIONS = """
Turn the user's business ramble into accurate Message DNA.
Preserve dates, names, numbers, URLs, claims, and mandated wording as exact facts.
Never invent facts; record uncertainty as assumptions or unresolved questions.
Ask one high-value question at a time, prioritizing CTA, audience, facts, and guardrails.
Use concise humor for normal messages. Be direct and neutral for sensitive topics.
Call update_message_dna whenever confirmed information changes.
""".strip()


class RealtimeAgentFactory:
    def __init__(self, message_service: MessageDNAService) -> None:
        self._message_service = message_service

    def create(self, project_id: str) -> RealtimeAgent[None]:
        """Create the single call-scoped agent with one injected state tool."""

        async def update_message_dna(patch: MessageDNAPatch) -> str:
            """Merge confirmed Message DNA fields into the active local project."""
            project = self._message_service.update_project(project_id, patch)
            return project.message_dna.model_dump_json()

        tool = function_tool(update_message_dna, strict_mode=True)
        return RealtimeAgent(
            name="Memo",
            instructions=AGENT_INSTRUCTIONS,
            tools=[tool],
        )
