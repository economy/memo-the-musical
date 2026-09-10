from memo.domain.demo.constants import SECURITY_DEMO_TEXT
from memo.domain.message_dna.extraction import extract_message_dna_patch
from memo.domain.message_dna.models import HumorLevel


def test_security_demo_text_extracts_live_widget_fields() -> None:
    patch = extract_message_dna_patch(SECURITY_DEMO_TEXT)

    assert patch.chorus is not None
    assert "security training" in patch.chorus.summary.lower()
    assert patch.call_to_action is not None
    assert "LearnHub" in (patch.call_to_action.action or "")
    assert patch.audience == "Employees and contractors"
    assert patch.vibe is not None
    assert patch.vibe.humor is HumorLevel.PLAYFUL
    assert patch.guardrails is not None
    assert any("phishing" in rule.lower() for rule in patch.guardrails)
    keys = {item.key: item.value for item in patch.fact_corrections or []}
    assert keys["deadline"] == "Thursday, October 15 at 5 PM Pacific"
    assert keys["duration"] == "about 12 minutes"


def test_small_talk_does_not_invent_message_dna() -> None:
    patch = extract_message_dna_patch("Hello? Hell yeah, let's go with it.")

    assert patch.chorus is None
    assert patch.call_to_action is None
    assert patch.fact_corrections in (None, [])
