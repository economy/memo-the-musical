from datetime import UTC, datetime

from memo.domain.message_dna.models import FactStatus, LockedFact, Project
from memo.domain.message_dna.updates import MessageDNAPatch
from memo.domain.projects.repository import ProjectRepository


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
        supplied = patch.model_fields_set - {"fact_corrections"}
        changes = {field: getattr(patch, field) for field in supplied}
        if patch.fact_corrections:
            facts = list(project.message_dna.locked_facts)
            for correction in patch.fact_corrections:
                facts = self._apply_correction(facts, correction.key, correction.value)
            changes["locked_facts"] = facts
        message_dna = project.message_dna.model_copy(update=changes)
        updated = project.model_copy(
            update={"message_dna": message_dna, "updated_at": datetime.now(UTC)}
        )
        return self._repository.update(updated)

    def delete_project(self, project_id: str) -> bool:
        """Delete a project and report whether it existed."""
        return self._repository.delete(project_id)

    def _require_project(self, project_id: str) -> Project:
        project = self._repository.get(project_id)
        if project is None:
            raise KeyError(project_id)
        return project

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
            facts[active_index] = facts[active_index].model_copy(
                update={
                    "status": FactStatus.SUPERSEDED,
                    "superseded_by_id": corrected.id,
                }
            )
        facts.append(corrected)
        return facts
