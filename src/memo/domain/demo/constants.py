from memo.domain.message_dna.models import MessagePreset, StrictStr

SECURITY_DEMO_PROJECT_ID = "security-training"
REPLAY_DEMO_PROJECT_ID = "security-training-replay"
ACTIVE_PROJECT_COOKIE = "memo_active_project"

SECURITY_DEMO_TEXT = (
    "Make our security training reminder memorable. Everyone, including contractors, "
    "must complete LearnHub by Friday, October 16 at 5 PM Pacific. It takes about "
    "12 minutes. Give it playful spy-movie energy, but never joke about phishing "
    "victims. Actually, correction: Thursday, October 15—not Friday. Don't invent prizes."
)

PRESET_LABELS: dict[MessagePreset, StrictStr] = {
    MessagePreset.TRAINING: "Security Training",
    MessagePreset.ANNOUNCEMENT: "Town Hall Announcement",
    MessagePreset.PRODUCT: "Product Launch",
    MessagePreset.REPORT: "Quarterly Report",
}
