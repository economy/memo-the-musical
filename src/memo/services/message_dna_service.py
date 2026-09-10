from datetime import UTC, datetime

from memo.domain.message_dna.models import (
    CallToAction,
    DeliveryContext,
    FactStatus,
    LockedFact,
    MessageDNA,
    Project,
    StrictModel,
    Vibe,
)
from memo.domain.message_dna.updates import MessageDNAPatch
from memo.domain.projects.repository import ProjectRepository

SPECIAL_PATCH_FIELDS = frozenset({"call_to_action", "delivery", "fact_corrections", "vibe"})


class MessageDNAService:
    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def create_project(self, project: Project) -> Project:
        """Create a project through the injected persistence boundary."""
        return self._repository.create(project)

    def get_project(self, project_id: str) -> Project | None:
        """Return a project without exposing repository details."""
        return self._repository.get(project_id)

    def list_projects(self) -> list[Project]:
        """List persisted projects in repository-defined order."""
        return self._repository.list()

    def update_project(self, project_id: str, patch: MessageDNAPatch) -> Project:
        """Merge only supplied fields and persist the resulting project atomically."""
        project = self._require_project(project_id)
        supplied = patch.model_fields_set - SPECIAL_PATCH_FIELDS
        changes = {
            field: value for field in supplied if (value := getattr(patch, field)) is not None
        }
        if patch.call_to_action is not None:
            existing = project.message_dna.call_to_action
            action_data = existing.model_dump() if existing is not None else {}
            action_data.update(self._nonnull_updates(patch.call_to_action))
            changes["call_to_action"] = CallToAction.model_validate(action_data)
        if patch.delivery is not None:
            delivery_data = project.message_dna.delivery.model_dump()
            delivery_data.update(self._nonnull_updates(patch.delivery))
            changes["delivery"] = DeliveryContext.model_validate(delivery_data)
        if patch.vibe is not None:
            vibe_data = project.message_dna.vibe.model_dump()
            vibe_data.update(self._nonnull_updates(patch.vibe))
            changes["vibe"] = Vibe.model_validate(vibe_data)
        if patch.fact_corrections:
            facts = list(project.message_dna.locked_facts)
            for correction in patch.fact_corrections:
                facts = self._apply_correction(facts, correction.key, correction.value)
            changes["locked_facts"] = facts
        message_data = project.message_dna.model_dump()
        message_data.update(changes)
        message_dna = MessageDNA.model_validate(message_data)
        project_data = project.model_dump()
        project_data.update({"message_dna": message_dna, "updated_at": datetime.now(UTC)})
        updated = Project.model_validate(project_data)
        return self._repository.update(updated)

    def reset_project(self, project_id: str) -> Project:
        """Clear extracted Message DNA while keeping the project identity."""
        project = self._require_project(project_id)
        project_data = project.model_dump()
        project_data.update(
            {
                "message_dna": MessageDNA(),
                "updated_at": datetime.now(UTC),
            }
        )
        return self._repository.update(Project.model_validate(project_data))

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and report whether it existed."""
        return self._repository.delete(project_id)

    def _require_project(self, project_id: str) -> Project:
        project = self._repository.get(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

    @staticmethod
    def _nonnull_updates(patch: StrictModel) -> dict[str, object]:
        return {
            field: value
            for field in patch.model_fields_set
            if (value := getattr(patch, field)) is not None
        }

    @staticmethod
    def _apply_correction(
        facts: list[LockedFact],
        key: str,
        value: str,
    ) -> list[LockedFact]:
        active_index = next(
            (
                index
                for index in range(len(facts) - 1, -1, -1)
                if facts[index].key == key and facts[index].status is FactStatus.ACTIVE
            ),
            None,
        )
        previous_id = facts[active_index].id if active_index is not None else None
        corrected = LockedFact.new(key=key, value=value, supersedes_id=previous_id)
        if active_index is not None:
            previous_data = facts[active_index].model_dump()
            previous_data.update(
                {
                    "status": FactStatus.SUPERSEDED,
                    "superseded_by_id": corrected.id,
                }
            )
            facts[active_index] = LockedFact.model_validate(previous_data)
        facts.append(corrected)
        return facts
