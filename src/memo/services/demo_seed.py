from memo.domain.demo.constants import (
    PRESET_LABELS,
    REPLAY_DEMO_PROJECT_ID,
    SECURITY_DEMO_PROJECT_ID,
    SECURITY_DEMO_TEXT,
)
from memo.domain.demo.replay import build_replay_project
from memo.domain.message_dna.models import MessageDNA, MessagePreset, Project
from memo.services.message_dna_service import MessageDNAService


def ensure_demo_projects(service: MessageDNAService) -> None:
    """Create the live and replay security-training projects when they are absent."""
    if service.get_project(SECURITY_DEMO_PROJECT_ID) is None:
        service.create_project(_build_live_project())
    if service.get_project(REPLAY_DEMO_PROJECT_ID) is None:
        service.create_project(build_replay_project())


def create_preset_project(service: MessageDNAService, preset: MessagePreset) -> Project:
    """Create a fresh project for one of the demo preset choices."""
    title = PRESET_LABELS[preset]
    return service.create_project(Project.new(title=title, preset=preset))


def _build_live_project() -> Project:
    """Prepare the default live demo project with the scripted request text."""
    project = Project.new(
        title="Security Training",
        preset=MessagePreset.TRAINING,
    )
    project_data = project.model_dump()
    project_data["id"] = SECURITY_DEMO_PROJECT_ID
    project_data["message_dna"] = MessageDNA(
        original_request=SECURITY_DEMO_TEXT,
    ).model_dump()
    return Project.model_validate(project_data)
