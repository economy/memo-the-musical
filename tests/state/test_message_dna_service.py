from pathlib import Path

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.domain.message_dna.models import Chorus, FactStatus, LockedFact, MessagePreset, Project
from memo.domain.message_dna.updates import FactCorrection, MessageDNAPatch
from memo.services.message_dna_service import MessageDNAService


def test_partial_updates_merge_without_erasing_existing_fields(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    service.create_project(project)

    service.update_project(
        project.id,
        MessageDNAPatch(chorus=Chorus(summary="Training keeps everyone safer.")),
    )
    updated = service.update_project(
        project.id,
        MessageDNAPatch(audience="Employees and contractors"),
    )

    assert updated.message_dna.chorus == Chorus(summary="Training keeps everyone safer.")
    assert updated.message_dna.audience == "Employees and contractors"
    repository.close()


def test_exact_fact_correction_supersedes_instead_of_overwriting(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    original = LockedFact.new(key="deadline", value="Friday, October 16 at 5 PM Pacific")
    project.message_dna.locked_facts.append(original)
    service.create_project(project)

    updated = service.update_project(
        project.id,
        MessageDNAPatch(
            fact_corrections=[
                FactCorrection(
                    key="deadline",
                    value="Thursday, October 15 at 5 PM Pacific",
                )
            ]
        ),
    )

    old_fact, corrected_fact = updated.message_dna.locked_facts
    assert old_fact.value == "Friday, October 16 at 5 PM Pacific"
    assert old_fact.status is FactStatus.SUPERSEDED
    assert old_fact.superseded_by_id == corrected_fact.id
    assert corrected_fact.status is FactStatus.ACTIVE
    assert corrected_fact.supersedes_id == old_fact.id
    repository.close()
