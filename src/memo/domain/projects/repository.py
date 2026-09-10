from abc import ABC, abstractmethod

from memo.domain.message_dna.models import Project


class ProjectRepository(ABC):
    @abstractmethod
    def create(self, project: Project) -> Project:
        """Persist a new project atomically."""

    @abstractmethod
    def get(self, project_id: str) -> Project | None:
        """Return one project or None when it does not exist."""

    @abstractmethod
    def list(self) -> list[Project]:
        """Return projects ordered by most recent update."""

    @abstractmethod
    def update(self, project: Project) -> Project:
        """Replace an existing project atomically."""

    @abstractmethod
    def delete(self, project_id: str) -> bool:
        """Delete a project and report whether it existed."""

    @abstractmethod
    def close(self) -> None:
        """Release repository resources."""
