from pathlib import Path

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.domain.demo.constants import SECURITY_DEMO_TEXT
from memo.domain.message_dna.models import MessagePreset, Project
from memo.services.message_dna_service import MessageDNAService
from memo.services.transcript_ingest import TranscriptIngestor


def test_ingest_uses_stored_brief_when_user_only_says_hello(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    project.message_dna.original_request = SECURITY_DEMO_TEXT
    service.create_project(project)

    updated = TranscriptIngestor(service).ingest_text(project.id, "Hello?")

    assert updated is not None
    assert updated.message_dna.chorus is not None
    assert updated.message_dna.call_to_action is not None
    assert updated.message_dna.audience == "Employees and contractors"
    assert any(
        fact.key == "deadline" and fact.value.startswith("Thursday")
        for fact in updated.message_dna.locked_facts
        if fact.status.value == "active"
    )
    repository.close()


def test_repeat_ingest_does_not_duplicate_the_same_deadline(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    project.message_dna.original_request = SECURITY_DEMO_TEXT
    service.create_project(project)
    ingestor = TranscriptIngestor(service)

    first = ingestor.ingest_text(project.id, SECURITY_DEMO_TEXT)
    second = ingestor.ingest_text(project.id, SECURITY_DEMO_TEXT)

    assert first is not None
    assert second is not None
    deadlines = [fact for fact in second.message_dna.locked_facts if fact.key == "deadline"]
    assert len(deadlines) == 1
    repository.close()
