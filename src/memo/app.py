from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from memo.adapters.realtime.agents_sideband import AgentsSDKSidebandAttacher
from memo.adapters.realtime.openai_call_client import OpenAIRealtimeCallClient
from memo.adapters.storage.sqlite_project_repository import SQLiteProjectRepository
from memo.config import Settings
from memo.domain.demo.constants import (
    ACTIVE_PROJECT_COOKIE,
    SECURITY_DEMO_PROJECT_ID,
)
from memo.domain.message_dna.models import MessagePreset
from memo.domain.message_dna.readiness import assess_readiness
from memo.domain.realtime.ports import RealtimeCallPort
from memo.routes.fragments import build_fragments_router
from memo.routes.projects import build_projects_router
from memo.routes.realtime import build_realtime_router
from memo.services.demo_seed import ensure_demo_projects
from memo.services.message_dna_service import MessageDNAService
from memo.services.realtime_agent import RealtimeAgentFactory
from memo.services.sideband_registry import SidebandSessionRegistry
from memo.services.transcript_ingest import TranscriptIngestor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEMO_PRESETS = (
    MessagePreset.TRAINING,
    MessagePreset.ANNOUNCEMENT,
    MessagePreset.PRODUCT,
    MessagePreset.REPORT,
)


def create_app(
    call_client: RealtimeCallPort,
    registry: SidebandSessionRegistry,
    message_service: MessageDNAService,
    shutdown: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    """Create the application with externally supplied I/O dependencies."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
        yield
        try:
            await registry.close_all()
        finally:
            if shutdown is not None:
                await shutdown()

    app = FastAPI(title="Memo: The Musical", lifespan=lifespan)
    templates = Jinja2Templates(directory=PROJECT_ROOT / "templates")
    app.mount("/static", StaticFiles(directory=PROJECT_ROOT / "static"), name="static")
    app.include_router(build_realtime_router(call_client, registry, message_service))
    app.include_router(build_projects_router(message_service))
    app.include_router(build_fragments_router(message_service, templates))

    async def index(request: Request) -> HTMLResponse:
        project_id = request.cookies.get(ACTIVE_PROJECT_COOKIE, SECURITY_DEMO_PROJECT_ID)
        project = message_service.get_project(project_id)
        if project is None:
            project = message_service.get_project(SECURITY_DEMO_PROJECT_ID)
        if project is None:
            raise RuntimeError("Security training demo project is missing")
        readiness = assess_readiness(project.message_dna)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "project": project,
                "presets": DEMO_PRESETS,
                "readiness": readiness,
                "is_replay": project.id.endswith("-replay"),
            },
        )

    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_api_route("/", index, methods=["GET"], response_class=HTMLResponse)
    app.add_api_route("/health", health, methods=["GET"])
    return app


def create_default_app() -> FastAPI:
    """Wire local adapters for the one-command development server."""
    settings = Settings()
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    repository = SQLiteProjectRepository(settings.database_path)
    service = MessageDNAService(repository)
    ensure_demo_projects(service)

    http_client = httpx.AsyncClient(base_url="https://api.openai.com", timeout=30)
    call_client = OpenAIRealtimeCallClient(
        http_client,
        api_key=settings.openai_api_key.get_secret_value(),
    )
    attacher = AgentsSDKSidebandAttacher(
        RealtimeAgentFactory(service),
        TranscriptIngestor(service),
        api_key=settings.openai_api_key.get_secret_value(),
    )
    registry = SidebandSessionRegistry(attacher)

    async def shutdown() -> None:
        await http_client.aclose()
        repository.close()

    return create_app(call_client, registry, service, shutdown)
