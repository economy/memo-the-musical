import sqlite3
from pathlib import Path

from memo.domain.message_dna.models import Project
from memo.domain.projects.repository import ProjectRepository

DATABASE_VERSION = 1


class SQLiteProjectRepository(ProjectRepository):
    def __init__(self, database_path: Path) -> None:
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    def create(self, project: Project) -> Project:
        """Persist a new project in one transaction."""
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO projects (id, schema_version, payload, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.schema_version,
                    project.model_dump_json(),
                    project.updated_at.isoformat(),
                ),
            )
        return project

    def get(self, project_id: str) -> Project | None:
        """Load and validate one versioned project payload."""
        row = self._connection.execute(
            "SELECT payload FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        if row is None:
            return None
        return Project.model_validate_json(str(row["payload"]))

    def list(self) -> list[Project]:
        """Load projects ordered by the latest persisted update."""
        rows = self._connection.execute(
            "SELECT payload FROM projects ORDER BY updated_at DESC"
        ).fetchall()
        return [Project.model_validate_json(str(row["payload"])) for row in rows]

    def update(self, project: Project) -> Project:
        """Replace an existing payload without exposing partial writes."""
        with self._connection:
            cursor = self._connection.execute(
                """
                UPDATE projects
                SET schema_version = ?, payload = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    project.schema_version,
                    project.model_dump_json(),
                    project.updated_at.isoformat(),
                    project.id,
                ),
            )
            if cursor.rowcount == 0:
                raise KeyError(project.id)
        return project

    def delete(self, project_id: str) -> bool:
        """Delete one project atomically."""
        with self._connection:
            cursor = self._connection.execute(
                "DELETE FROM projects WHERE id = ?",
                (project_id,),
            )
        return cursor.rowcount > 0

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._connection.close()

    def _migrate(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    version INTEGER NOT NULL
                )
                """
            )
            row = self._connection.execute("SELECT version FROM schema_metadata LIMIT 1").fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_metadata (version) VALUES (?)",
                    (DATABASE_VERSION,),
                )
            elif int(row["version"]) != DATABASE_VERSION:
                raise RuntimeError("Unsupported database schema version")
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    schema_version INTEGER NOT NULL,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
