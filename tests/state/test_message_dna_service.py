from pathlib import Path
from typing import cast

import pytest
from agents import FunctionTool
from pydantic import ValidationError

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.domain.message_dna.models import (
    CallToAction,
    Chorus,
    DeliveryContext,
    FactStatus,
    LockedFact,
    MessagePreset,
    Project,
)
from memo.domain.message_dna.updates import (
    CallToActionPatch,
    DeliveryContextPatch,
    FactCorrection,
    MessageDNAPatch,
)
from memo.services.message_dna_service import MessageDNAService
from memo.services.realtime_agent import RealtimeAgentFactory


def test_reset_project_clears_extracted_fields_and_keeps_demo_request(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    project_data = project.model_dump()
    project_data["id"] = "security-training"
    project = service.create_project(Project.model_validate(project_data))
    service.update_project(
        project.id,
        MessageDNAPatch(
            chorus=Chorus(summary="Finish training."),
            audience="Employees and contractors",
        ),
    )

    cleared = service.reset_project(project.id)

    assert cleared.message_dna.chorus is None
    assert cleared.message_dna.audience is None
    assert cleared.message_dna.locked_facts == []
    assert cleared.message_dna.original_request is None
    repository.close()


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


def test_strict_tool_null_shape_does_not_clear_existing_fields(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    project.message_dna.chorus = Chorus(summary="Keep the team secure.")
    project.message_dna.call_to_action = CallToAction(action="Complete LearnHub.")
    project.message_dna.delivery = DeliveryContext(
        channel="Email",
        context="Annual security training",
    )
    service.create_project(project)
    tool = cast(FunctionTool, RealtimeAgentFactory(service).create(project.id).tools[0])
    schema = cast(dict[str, object], cast(object, tool.params_json_schema))
    properties = cast(dict[str, object], schema["properties"])
    definitions = cast(dict[str, object], schema.get("$defs", {}))
    assert "chorus" in properties
    assert "MessageDNAPatch" not in definitions

    updated = service.update_project(
        project.id,
        MessageDNAPatch(
            audience="Employees and contractors",
            delivery=DeliveryContextPatch(deadline="Thursday at 5 PM Pacific"),
        ),
    )

    assert updated.message_dna.chorus == Chorus(summary="Keep the team secure.")
    assert updated.message_dna.call_to_action == CallToAction(action="Complete LearnHub.")
    assert updated.message_dna.audience == "Employees and contractors"
    assert updated.message_dna.delivery == DeliveryContext(
        channel="Email",
        deadline="Thursday at 5 PM Pacific",
        context="Annual security training",
    )
    repository.close()


def test_realistic_partial_tool_update_validates_and_reloads(tmp_path: Path) -> None:
    database = tmp_path / "memo.db"
    repository = SQLiteProjectRepository(database)
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    service.create_project(project)

    updated = service.update_project(
        project.id,
        MessageDNAPatch(
            chorus=Chorus(summary="Twelve minutes now prevents trouble later."),
            call_to_action=CallToActionPatch(action="Complete LearnHub by Thursday."),
            audience="Employees and contractors",
            guardrails=["Never joke about phishing victims."],
            fact_corrections=[
                FactCorrection(key="deadline", value="Thursday, October 15 at 5 PM Pacific")
            ],
        ),
    )
    repository.close()

    reopened = SQLiteProjectRepository(database)
    assert reopened.get(project.id) == updated
    reopened.close()


def test_invalid_constructed_patch_is_rejected_before_persistence(tmp_path: Path) -> None:
    repository = SQLiteProjectRepository(tmp_path / "memo.db")
    service = MessageDNAService(repository)
    project = Project.new(title="Training", preset=MessagePreset.TRAINING)
    service.create_project(project)
    invalid_patch = MessageDNAPatch.model_construct(audience=42)

    with pytest.raises(ValidationError):
        service.update_project(project.id, invalid_patch)

    assert repository.get(project.id) == project
    repository.close()
