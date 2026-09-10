import pytest
from pydantic import ValidationError

from memo.domain.message_dna.models import (
    CallToAction,
    Chorus,
    LockedFact,
    MessageDNA,
    MessagePreset,
    Project,
)
from memo.domain.message_dna.readiness import assess_readiness


def test_message_dna_rejects_coerced_values() -> None:
    with pytest.raises(ValidationError):
        Chorus(summary=42)  # type: ignore[arg-type]


def test_readiness_is_derived_from_required_message_dna() -> None:
    project = Project.new(title="Security reminder", preset=MessagePreset.TRAINING)
    project.message_dna = MessageDNA(
        chorus=Chorus(summary="Finish security training before the deadline."),
        call_to_action=CallToAction(action="Complete LearnHub training."),
        audience="Employees and contractors",
        locked_facts=[
            LockedFact.new(
                key="deadline",
                value="Thursday, October 15 at 5 PM Pacific",
            )
        ],
        guardrails=["Never joke about phishing victims."],
    )

    readiness = assess_readiness(project.message_dna)

    assert readiness.ready is True
    assert readiness.unresolved == []


def test_readiness_reports_missing_fields_without_persisting_a_score() -> None:
    project = Project.new(title="Unfinished", preset=MessagePreset.GENERAL)

    readiness = assess_readiness(project.message_dna)

    assert readiness.ready is False
    assert readiness.unresolved == [
        "chorus",
        "call_to_action",
        "audience",
        "locked_facts",
        "guardrails",
    ]
    assert "readiness" not in project.model_dump()
