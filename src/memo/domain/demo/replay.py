from datetime import UTC, datetime

from memo.domain.demo.constants import (
    REPLAY_DEMO_PROJECT_ID,
    SECURITY_DEMO_TEXT,
)
from memo.domain.message_dna.models import (
    CallToAction,
    Chorus,
    DeliveryContext,
    FactStatus,
    HumorLevel,
    LockedFact,
    MessageDNA,
    MessagePreset,
    Project,
    Vibe,
)


def build_replay_project() -> Project:
    """Build the completed security-training replay project with correction history."""
    now = datetime.now(UTC)
    old_deadline = LockedFact(
        id="fact-deadline-friday",
        key="deadline",
        value="Friday, October 16 at 5 PM Pacific",
        status=FactStatus.SUPERSEDED,
        superseded_by_id="fact-deadline-thursday",
        recorded_at=now,
    )
    corrected_deadline = LockedFact(
        id="fact-deadline-thursday",
        key="deadline",
        value="Thursday, October 15 at 5 PM Pacific",
        status=FactStatus.ACTIVE,
        supersedes_id="fact-deadline-friday",
        recorded_at=now,
    )
    return Project(
        id=REPLAY_DEMO_PROJECT_ID,
        title="Security Training (Replay)",
        preset=MessagePreset.TRAINING,
        message_dna=MessageDNA(
            original_request=SECURITY_DEMO_TEXT,
            chorus=Chorus(
                summary=(
                    "Your mission, should you choose to accept it: complete security "
                    "training before the clock runs out."
                )
            ),
            call_to_action=CallToAction(action="Complete LearnHub by Thursday."),
            audience="Employees and contractors",
            locked_facts=[old_deadline, corrected_deadline],
            vibe=Vibe(
                emotional_response="Playful spy-movie energy",
                humor=HumorLevel.PLAYFUL,
                notes=["Lightly tease procrastination, never individuals."],
            ),
            guardrails=[
                "Never joke about phishing victims.",
                "Don't invent prizes.",
            ],
            delivery=DeliveryContext(
                duration="about 12 minutes",
                deadline="Thursday, October 15 at 5 PM Pacific",
                context="Annual security training reminder",
            ),
            unresolved_questions=["What is the LearnHub URL?"],
        ),
        created_at=now,
        updated_at=now,
    )
