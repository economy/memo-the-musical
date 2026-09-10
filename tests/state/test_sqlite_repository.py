from pathlib import Path

from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.domain.message_dna.models import MessagePreset, Project


def test_sqlite_repository_persists_project_across_instances(tmp_path: Path) -> None:
    database = tmp_path / "memo.db"
    first = SQLiteProjectRepository(database)
    project = Project.new(title="Quarterly numbers", preset=MessagePreset.REPORT)

    first.create(project)
    first.close()

    second = SQLiteProjectRepository(database)
    restored = second.get(project.id)

    assert restored == project
    second.close()
