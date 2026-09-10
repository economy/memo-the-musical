import sqlite3
from pathlib import Path

import pytest

from memo.adapters.storage.sqlite_project_repository import (
    SQLiteProjectRepository,
    UnsupportedDatabaseSchemaError,
)
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


def test_sqlite_repository_rejects_newer_schema_with_actionable_error(tmp_path: Path) -> None:
    database = tmp_path / "future.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE schema_metadata (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_metadata (version) VALUES (999)")
    connection.commit()
    connection.close()

    with pytest.raises(
        UnsupportedDatabaseSchemaError,
        match=r"found 999, expected 1.*back up and remove",
    ):
        SQLiteProjectRepository(database)

    reopened = sqlite3.connect(database)
    assert reopened.execute("SELECT version FROM schema_metadata").fetchone() == (999,)
    reopened.close()
