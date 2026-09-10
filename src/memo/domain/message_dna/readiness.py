from pydantic import Field, StrictBool, StrictStr

from memo.domain.message_dna.models import FactStatus, MessageDNA, StrictModel


class Readiness(StrictModel):
    ready: StrictBool
    unresolved: list[StrictStr] = Field(default_factory=list)


def assess_readiness(message_dna: MessageDNA) -> Readiness:
    """Derive readiness from confirmed content without persisting a duplicate score."""
    unresolved: list[str] = []
    if message_dna.chorus is None:
        unresolved.append("chorus")
    if message_dna.call_to_action is None:
        unresolved.append("call_to_action")
    if not message_dna.audience:
        unresolved.append("audience")
    if not any(fact.status is FactStatus.ACTIVE for fact in message_dna.locked_facts):
        unresolved.append("locked_facts")
    if not message_dna.guardrails:
        unresolved.append("guardrails")
    return Readiness(ready=not unresolved, unresolved=unresolved)
