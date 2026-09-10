from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from memo.domain.demo.constants import (
    ACTIVE_PROJECT_COOKIE,
    REPLAY_DEMO_PROJECT_ID,
)
from memo.domain.message_dna.models import MessagePreset, Project, StrictModel
from memo.services.demo_seed import create_preset_project
from memo.services.message_dna_service import MessageDNAService


class CreateProjectRequest(BaseModel):
    """Accept JSON preset values while rejecting unknown fields."""

    model_config = ConfigDict(extra="forbid")

    preset: MessagePreset
    title: StrictStr | None = Field(default=None, min_length=1)


class ProjectSummary(StrictModel):
    id: StrictStr
    title: StrictStr
    preset: MessagePreset


class SelectProjectResponse(StrictModel):
    project_id: StrictStr
    mode: StrictStr


def build_projects_router(message_service: MessageDNAService) -> APIRouter:
    """Build project CRUD and selection routes backed by SQLite."""
    router = APIRouter(prefix="/api/projects", tags=["projects"])

    async def list_projects() -> list[ProjectSummary]:
        return [
            ProjectSummary(id=project.id, title=project.title, preset=project.preset)
            for project in message_service.list_projects()
        ]

    async def create_project(body: CreateProjectRequest) -> Project:
        if body.title is None:
            return create_preset_project(message_service, body.preset)
        return message_service.create_project(Project.new(title=body.title, preset=body.preset))

    async def get_project(project_id: str) -> Project:
        project = message_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project

    async def select_project(project_id: str) -> Response:
        project = message_service.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        mode = "replay" if project_id.endswith("-replay") else "live"
        payload = SelectProjectResponse(project_id=project_id, mode=mode)
        response = Response(
            content=payload.model_dump_json(),
            media_type="application/json",
        )
        response.set_cookie(
            key=ACTIVE_PROJECT_COOKIE,
            value=project_id,
            httponly=False,
            samesite="lax",
        )
        return response

    async def select_replay() -> Response:
        return await select_project(REPLAY_DEMO_PROJECT_ID)

    router.add_api_route("", list_projects, methods=["GET"])
    router.add_api_route("", create_project, methods=["POST"], status_code=status.HTTP_201_CREATED)
    router.add_api_route("/replay", select_replay, methods=["POST"])
    router.add_api_route("/select/{project_id}", select_project, methods=["POST"])
    router.add_api_route("/{project_id}", get_project, methods=["GET"])
    return router
